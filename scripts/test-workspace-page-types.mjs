import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
import {spawnSync} from 'node:child_process'
import {createHash} from 'node:crypto'

const root=fileURLToPath(new URL('../',import.meta.url))
const require=createRequire(new URL('../frontend/package.json',import.meta.url))
const ts=require('typescript'),vue=require('vue'),sfc=require('@vue/compiler-sfc')
const scratch=path.join(root,'.runtime/workspace-page-types');mkdirSync(scratch,{recursive:true})
const key='labourlawyer.workspace.v1'
const memory=raw=>({raw,writes:0,getItem(name){assert.equal(name,key);return this.raw},setItem(name,value){assert.equal(name,key);this.raw=value;this.writes++}})
globalThis.localStorage=memory(null)
// This branch also executes before the migration, exposing the unsafe saved-JSON boundary.
if(process.argv.includes('--baseline-storage') || process.argv.includes('--storage-getter-denied')){
  const storage=memory(JSON.stringify({cases:[{id:'fictional-broken',amount:'not-a-number'}]}))
  globalThis.localStorage=storage
  if(process.argv.includes('--storage-getter-denied'))Object.defineProperty(globalThis,'localStorage',{get(){throw new Error('synthetic denied storage getter')},configurable:true})
  const api=await import(new URL('../frontend/src/composables/useWorkspace.js?storage-counterexample',import.meta.url))
  const workspace=api.createWorkspace(globalThis.localStorage)
  assert.equal(typeof workspace.state.cases[0].amount,'number','Untrusted saved case amounts must not reach numeric page rendering')
  assert.doesNotThrow(()=>workspace.totalAmount.value)
  assert.equal(storage.writes,0,'Reading invalid saved content must preserve its original bytes')
  if(process.argv.includes('--storage-getter-denied'))assert.match(workspace.storageIssue.value,/当前显示示例/,'A denied storage getter must mark fallback examples immediately')
  console.log(process.argv.includes('--storage-getter-denied')?'PASS denied storage getter shows fallback examples without writing':'PASS invalid saved JSON is isolated without overwriting its original bytes')
}else{

const files=['frontend/src/views/Dashboard.vue','frontend/src/views/CaseCenter.vue','frontend/src/views/DeadlineCenter.vue',
  'frontend/src/views/DocumentCenter.vue','frontend/src/views/EvidenceCenter.vue','frontend/src/views/KnowledgeCenter.vue',
  'frontend/src/components/DocumentWorkspace.vue','frontend/src/components/DistrictWorkflow.vue']
const modules=['frontend/src/composables/useWorkspace.ts','packages/regional-contracts/src/workspace.ts']
for(const file of modules)assert(existsSync(path.join(root,file)),`Missing typed workspace boundary: ${file}`)
for(const file of files){
  const descriptor=sfc.parse(readFileSync(path.join(root,file),'utf8')).descriptor
  assert.equal(descriptor.scriptSetup?.lang,'ts',`${file} must check its actual script and template`)
  const tree=ts.createSourceFile(file+'.ts',descriptor.scriptSetup.content,ts.ScriptTarget.Latest,true)
  const visit=node=>{assert.notEqual(node.kind,ts.SyntaxKind.AnyKeyword,`${file} contains an unbounded type`);ts.forEachChild(node,visit)}
  visit(tree);assert(!/@ts-(ignore|nocheck|expect-error)/.test(descriptor.scriptSetup.content))
}
for(const file of modules){
  const source=readFileSync(path.join(root,file),'utf8'),tree=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true)
  const visit=node=>{assert.notEqual(node.kind,ts.SyntaxKind.AnyKeyword,`${file} contains an unbounded type`);ts.forEachChild(node,visit)}
  visit(tree);assert(!/@ts-(ignore|nocheck|expect-error)/.test(source))
}
const imports=`import {createWorkspace} from '../../frontend/src/composables/useWorkspace.ts'
import {parseWorkspaceSnapshot,parsePortalReports,parseAgentTasks,parseDistrictGuides} from '../../packages/regional-contracts/src/workspace.ts'
import type {WorkspaceCase,NewCaseInput,WorkspaceStorage,WorkflowGuide,PortalReport,AgentTask} from '../../packages/regional-contracts/src/workspace.ts'
`
const positive=imports+`
const storage:WorkspaceStorage={getItem:()=>null,setItem:(_k,value)=>{const text:string=value}}
const workspace=createWorkspace(storage)
const input:NewCaseInput={title:'虚构案件',client:'虚构甲',employer:'虚构单位',region:'虚构地区',amount:'12',deadline:''}
workspace.addCase(input)
const amount:number=workspace.state.cases[0]!.amount
const unknownDocument:unknown=workspace.state.recentDocuments[0]
const parsed=parseWorkspaceSnapshot({cases:[],recentDocuments:[]})
const reports:PortalReport[]=parsePortalReports({items:[]})
const tasks:AgentTask[]=parseAgentTasks({items:[]})
const guides:WorkflowGuide[]=parseDistrictGuides({guides:[]})
`
const negative=imports+`
const unsafeAmount:NewCaseInput={amount:true} // reject: boolean-amount
const unsafeName:NewCaseInput={client:7} // reject: numeric-client
const unknownSlot:NewCaseInput={id:'unbound'} // reject: unbound-input-key
createWorkspace({getItem:()=>({}),setItem:()=>{}}) // reject: storage-must-return-text
const leaked:number=parseWorkspaceSnapshot({}).cases[0].amount // reject: unchecked-unknown-snapshot
const badReport:PortalReport={id:'only-id'} // reject: incomplete-report
const badFlow:WorkflowGuide={id:'id',guide_url:'https://example.invalid'} // reject: incomplete-workflow
const data:unknown={};data.cases // reject: unknown-stays-unknown
createWorkspace().state.cases[0].amount.toFixed() // reject: unchecked-case-index
createWorkspace().state.recentDocuments[0].title // reject: recent-document-stays-unknown
`
const goodFile=path.join(scratch,'positive.ts'),badFile=path.join(scratch,'negative.ts')
writeFileSync(goodFile,positive);writeFileSync(badFile,negative)
const options={strict:true,noUncheckedIndexedAccess:true,exactOptionalPropertyTypes:true,noEmit:true,skipLibCheck:true,
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,moduleResolution:ts.ModuleResolutionKind.Bundler,
  allowImportingTsExtensions:true,verbatimModuleSyntax:true,lib:['lib.es2023.d.ts','lib.dom.d.ts']}
const diagnostics=file=>ts.getPreEmitDiagnostics(ts.createProgram([file,path.join(root,'frontend/node_modules/vite/client.d.ts')],options)).filter(d=>d.category===ts.DiagnosticCategory.Error)
const display=list=>list.map(d=>`${d.file?path.relative(root,d.file.fileName):'compiler'} TS${d.code}: ${ts.flattenDiagnosticMessageText(d.messageText,' ')}`).join('\n')
assert.equal(diagnostics(goodFile).length,0,display(diagnostics(goodFile)))
const bad=diagnostics(badFile),expected=new Set()
negative.split('\n').forEach((line,i)=>{if(line.includes('// reject:'))expected.add(i)})
assert(bad.every(d=>d.file && path.resolve(d.file.fileName)===badFile),display(bad))
assert.deepEqual(new Set(bad.map(d=>d.file.getLineAndCharacterOfPosition(d.start).line)),expected,display(bad))
const typeEvidence={positive:'PASS',rejected_counterexamples:[...expected].map(line=>({
  name:negative.split('\n')[line].split('// reject:')[1].trim(),
  codes:[...new Set(bad.filter(d=>d.file.getLineAndCharacterOfPosition(d.start).line===line).map(d=>d.code))],
}))}
const config=path.join(scratch,'tsconfig.json')
writeFileSync(config,JSON.stringify({compilerOptions:{...options,target:'ES2022',module:'ESNext',moduleResolution:'Bundler',
  lib:['ES2023','DOM','DOM.Iterable'],allowJs:true,checkJs:false,resolveJsonModule:true,
  types:[path.join(root,'frontend/node_modules/vite/client.d.ts')],typeRoots:[path.join(root,'frontend/node_modules/@types')],
  baseUrl:path.join(root,'frontend'),paths:{'@/*':['src/*']}},vueCompilerOptions:{strictTemplates:true,dataAttributes:['data-*']},
  files:[...modules,...files].map(file=>path.join(root,file))},null,2))
if(!process.argv.includes('--runtime-only')){
  const checked=spawnSync(process.execPath,[require.resolve('vue-tsc/bin/vue-tsc.js'),'--project',config,'--noEmit'],{cwd:root,encoding:'utf8'})
  assert.equal(checked.status,0,(checked.stdout+checked.stderr).replaceAll(root,''))
}else console.log('NOT_RUN SFC type compilation in explicit runtime-only mode')

// Load actual SFC scripts and compiled templates in memory. No DOM, browser,
// real storage, network, download, timer worker or collection service is used.
const workspaceModule=await import(new URL('../frontend/src/composables/useWorkspace.ts',import.meta.url))
const boundary=await import(new URL('../packages/regional-contracts/src/workspace.ts',import.meta.url))
let passed=0
const runtimeCases=[]
async function test(name,run){await run();passed++;runtimeCases.push(name);console.log(`PASS ${name}`)}
await test('invalid and partially malformed saved JSON never overwrites the original',()=>{
  for(const raw of ['{','null','[]',JSON.stringify({cases:[{id:'broken',amount:'unsafe'}]})]){
    const storage=memory(raw),workspace=workspaceModule.createWorkspace(storage)
    assert.equal(workspace.state.cases.length,4)
    assert(workspace.storageIssue.value)
    workspace.addCase({title:'虚构未持久化案件',amount:'12'})
    assert.equal(storage.raw,raw);assert.equal(storage.writes,0)
  }
})
await test('valid local cases, examples, totals and unrelated saved keys are preserved',()=>{
  const fresh=workspaceModule.createWorkspace(memory(null)),sample=structuredClone(vue.toRaw(fresh.state))
  sample.cases[0].futureCase={kept:'synthetic-case-extra'}
  const storage=memory(JSON.stringify({...sample,future:{kept:'synthetic-extra'}})),workspace=workspaceModule.createWorkspace(storage)
  const before=workspace.activeCases.value.length,total=workspace.totalAmount.value
  const result=workspace.addCase({title:'虚构案件',client:'虚构甲',employer:'虚构单位',amount:'123',region:'虚构地区',deadline:''})
  assert.equal(result.ok,true);assert.equal(workspace.activeCases.value.length,before+1);assert.equal(workspace.totalAmount.value,total+123)
  assert.equal(workspace.state.cases[0].title,'虚构案件')
  assert.equal(JSON.parse(storage.raw).future.kept,'synthetic-extra')
  assert.equal(JSON.parse(storage.raw).cases[1].futureCase.kept,'synthetic-case-extra')
  assert.equal(JSON.parse(storage.raw).cases[0].amount,123)
  const count=workspace.state.cases.length
  assert.equal(workspace.addCase({amount:'not finite'}).ok,false);assert.equal(workspace.state.cases.length,count)
})
await test('storage write failure stays in memory without a render exception',()=>{
  const storage=memory(null);storage.setItem=()=>{throw new Error('synthetic quota failure')}
  const workspace=workspaceModule.createWorkspace(storage)
  const result=workspace.addCase({title:'虚构当前页案件',amount:1})
  assert.equal(result.ok,true);assert.equal(result.persisted,false);assert(workspace.storageIssue.value)
  assert.equal(workspace.state.cases[0].title,'虚构当前页案件')
})
await test('unknown portal and workflow responses are rejected before template iteration',()=>{
  for(const parse of [boundary.parsePortalReports,boundary.parseAgentTasks])for(const data of [null,{items:{}},{items:[null]},{items:[{id:7}]}])assert.throws(()=>parse(data))
  assert.throws(()=>boundary.parseDistrictGuides({guides:'unsafe'}))
  assert.deepEqual(boundary.parseDistrictGuides({guides:[{id:'bad-url',guide_url:'javascript:alert(1)'}]}),[])
})

function hostNode(type,text=''){
  const node={type,tagName:type.toUpperCase(),text,props:{},children:[],parent:null,value:'',checked:false,selected:false,multiple:false,
    addEventListener(){},removeEventListener(){},setAttribute(){},removeAttribute(){},getRootNode(){return globalThis.document}}
  Object.defineProperty(node,'options',{get(){return node.children.filter(child=>child.type==='option')}})
  return node
}
const runtimeErrors=[]
const renderer=vue.createRenderer({
  createElement:type=>hostNode(type),createText:text=>hostNode('#text',text),createComment:text=>hostNode('#comment',text),
  setText:(node,text)=>{node.text=text},setElementText:(node,text)=>{node.text=text;node.children=[]},
  patchProp:(node,key,_old,value)=>{node.props[key]=value;if(key==='value'){node.value=value;node._value=value}if(key==='multiple')node.multiple=Boolean(value)},
  insert:(node,parent,anchor)=>{if(node.parent){const i=node.parent.children.indexOf(node);if(i>=0)node.parent.children.splice(i,1)}node.parent=parent;const i=anchor?parent.children.indexOf(anchor):-1;i<0?parent.children.push(node):parent.children.splice(i,0,node)},
  remove:node=>{if(node.parent){const i=node.parent.children.indexOf(node);if(i>=0)node.parent.children.splice(i,1)}},
  parentNode:node=>node.parent,nextSibling:node=>node.parent?.children[node.parent.children.indexOf(node)+1]??null,
  insertStaticContent:(content,parent,anchor)=>{const node=hostNode('#static',content);node.parent=parent;const i=anchor?parent.children.indexOf(anchor):-1;i<0?parent.children.push(node):parent.children.splice(i,0,node);return[node,node]},
})
globalThis.Document=class Document {activeElement=null}
globalThis.ShadowRoot=class ShadowRoot {activeElement=null}
globalThis.document=new globalThis.Document()
const text=node=>[node.text,...node.children.map(text)].join('')
const find=(node,predicate)=>predicate(node)?node:node.children.map(child=>find(child,predicate)).find(Boolean)
const all=(node,predicate)=>[...(predicate(node)?[node]:[]),...node.children.flatMap(child=>all(child,predicate))]
const event={preventDefault(){},stopPropagation(){}}
const click=node=>{assert(node,'Expected interactive node');node.props.onClick?.(event)}
const input=(node,value)=>{assert(node,'Expected form control');node.props['onUpdate:modelValue'](value)}
const tick=async()=>{await Promise.resolve();await vue.nextTick();await new Promise(setImmediate);await vue.nextTick();assert.deepEqual(runtimeErrors,[])}
const RouterLink=vue.defineComponent({props:['to'],setup(props,{slots}){return()=>vue.h('a',{href:props.to},slots.default?.())}})
function component(file,{workspace,axios,downloads=[],route=vue.reactive({query:{}}),router={replace(){}}}={}){
  const source=readFileSync(path.join(root,file),'utf8').replaceAll('import.meta.env','({})')
  const compiled=sfc.compileScript(sfc.parse(source).descriptor,{id:'workspace-test',inlineTemplate:true})
  const code=ts.transpileModule(compiled.content,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const output={exports:{}}
  const custom=id=>{
    if(id==='vue')return vue
    if(id==='vue-router')return{RouterLink,useRoute:()=>route,useRouter:()=>router}
    if(id==='axios')return{__esModule:true,default:axios??{get:async()=>({data:{items:[],guides:[]}})}}
    if(id.includes('api/http'))return{API_BASE:'',authorizationHeaders:()=>({})}
    if(id.includes('useWorkspace'))return{useWorkspace:()=>workspace}
    if(id.includes('downloadDocument'))return{downloadDocument:async(...args)=>{downloads.push(args)}}
    if(id.includes('data/provinces'))return{provinces:[{slug:'fiction',shortName:'虚构',name:'虚构省',hasApplication:true,hasEvidence:true,applicationRoute:'/fiction/app',evidenceRoute:'/fiction/evidence',note:'虚构',materialNote:'虚构',scope:'虚构'}]}
    if(id.endsWith('.vue'))return{__esModule:true,default:vue.defineComponent({name:id,inheritAttrs:false,setup(_p,{attrs}){return()=>vue.h('editor',{...attrs,'data-editor':id})}})}
    if(id.includes('regional-contracts/src/workspace'))return boundary
    return require(id)
  }
  new Function('require','exports','module',code)(custom,output.exports,output)
  return output.exports.default
}
function mount(Component,props={}){const container=hostNode('root'),app=renderer.createApp(Component,props);app.config.errorHandler=error=>runtimeErrors.push(String(error));app.config.warnHandler=message=>{throw new Error(message)};app.mount(container);assert.deepEqual(runtimeErrors,[]);return{container,app}}
await test('mounted case search, stage filters, creation and cancel retain the existing workflow',async()=>{
  const storage=memory(null),workspace=workspaceModule.createWorkspace(storage)
  const {container,app}=mount(component(files[1],{workspace}))
  assert.equal(all(container,n=>n.type==='tr').length,5)
  click(find(container,n=>n.type==='button'&&text(n)==='已结案'));await tick()
  assert.equal(all(all(container,n=>n.type==='tbody')[0],n=>n.type==='tr').length,1)
  click(find(container,n=>n.type==='button'&&text(n)==='全部'));await tick()
  click(find(container,n=>n.type==='button'&&text(n).includes('新建案件')));await tick()
  const form=find(container,n=>n.type==='form'),controls=all(form,n=>['input','select'].includes(n.type))
  for(const [i,value] of ['虚构争议','虚构姓名','123','虚构单位','虚构地区',''].entries())input(controls[i],value)
  form.props.onSubmit(event);await tick()
  assert.equal(workspace.state.cases[0].amount,123);assert.equal(storage.writes,1)
  const search=find(container,n=>n.type==='input'&&n.props['data-global-search']!==undefined)
  input(search,'虚构单位');await tick();assert.equal(all(all(container,n=>n.type==='tbody')[0],n=>n.type==='tr').length,1)
  click(find(container,n=>n.type==='button'&&text(n).includes('新建案件')));await tick()
  click(find(container,n=>n.type==='button'&&text(n)==='取消'));await tick();assert.equal(storage.writes,1)
  app.unmount()
})
await test('mounted example pages render without touching a case service',()=>{
  const workspace=workspaceModule.createWorkspace(memory(null))
  for(const file of [files[0],files[2],files[4],files[5]]){const {container,app}=mount(component(file,{workspace}));assert(text(container).length>50);app.unmount()}
})
await test('mounted malformed-storage notice explains that the original saved bytes are preserved',()=>{
  const storage=memory('{'),workspace=workspaceModule.createWorkspace(storage)
  for(const file of [files[0],files[1],files[4]]){
    const {container,app}=mount(component(file,{workspace}))
    assert(text(container).includes('原资料未改动'));assert(text(container).includes('当前显示示例'))
    assert.equal(storage.raw,'{');assert.equal(storage.writes,0);app.unmount()
  }
})
await test('mounted locality workspace never inherits a neighboring template and handles late guide arrival',async()=>{
  const region={province:'fiction',city:'虚构市',district:'虚构一区'}
  const props=vue.reactive({region,province:{hasApplication:true,hasEvidence:true},guide:null,loading:true,error:''})
  const Workspace=component(files[6]),Shell=vue.defineComponent({setup(){return()=>vue.h(Workspace,props)}})
  const {container,app}=mount(Shell)
  click(find(container,n=>n.type==='button'&&text(n).includes('证据清单')));await tick()
  props.guide={...region,source_id:'synthetic-source',version:1,templates:[{id:'own-evidence',can_generate:true,document_types:['evidence']}],materials:[],fields:{},sections:{},channel:{}}
  props.loading=false;await tick();await tick()
  assert.equal(find(container,n=>n.type==='editor')?.props.documentKind,'evidence')
  props.guide={...props.guide,source_id:null,templates:[]};await tick()
  assert.equal(find(container,n=>n.type==='editor'),undefined);assert(text(container).includes('暂未开放'))
  app.unmount()
})
await test('mounted district workflow ignores stale responses and unsafe links',async()=>{
  const requests=[],axios={get:()=>new Promise(resolve=>requests.push(resolve))},slug=vue.ref('first')
  const Workflow=component(files[7],{axios}),Shell=vue.defineComponent({setup(){return()=>vue.h(Workflow,{slug:slug.value})}})
  const {container,app}=mount(Shell);slug.value='second';await tick()
  requests[1]({data:{guides:[{id:'second',guide_url:'https://example.invalid/second',region_name:'虚构二区',plain_steps:[{title:'虚构步骤',text:'虚构说明'}],plain_materials:['虚构材料']}]}});await tick()
  requests[0]({data:{guides:[{id:'first',guide_url:'https://example.invalid/first',region_name:'虚构一区'}]}});await tick()
  assert(text(container).includes('虚构二区'));assert(!text(container).includes('虚构一区'))
  app.unmount()
})
await test('mounted document lists preserve explicit collection and download payloads with isolated transport',async()=>{
  const posts=[],downloads=[],gets=[]
  const result={status:{site_opened:true,guide_found:true,template_downloaded:false,fill_verified:false},screenshot:'step-01.png'}
  const axios={
    get:async url=>{
      gets.push(url)
      if(url.endsWith('/openclaw-tasks'))return{data:{items:[{id:'synthetic-task',state:'interrupted',total:null,current:'fiction',current_task:result,provinces:{fiction:result}}]}}
      if(url.endsWith('/portal-reports'))return{data:{items:[{id:'synthetic-report',state:'complete',recommended:true,ai_report:'synthetic-report.docx',regions_saved:2,total:2}]}}
      return{data:new Blob(['synthetic file'])}
    },
    post:async(url,payload)=>{posts.push({url,payload});return{data:{id:'synthetic-created'}}},
  }
  const {container,app}=mount(component(files[3],{axios,downloads}));await tick()
  assert(text(container).includes('当前完整全国报告'));assert(text(container).includes('网页已打开：是'))
  assert(find(container,n=>n.type==='a'&&n.props.href?.endsWith('/synthetic-task/fiction/evidence/step-01.png')))
  click(find(container,n=>n.type==='button'&&text(n)==='继续这个任务'));await tick()
  assert.deepEqual(posts[0].payload,{resume:'synthetic-task'})
  input(find(container,n=>n.type==='select'),'fiction');await tick()
  click(find(container,n=>n.type==='button'&&text(n)==='让 OpenClaw 补采'));await tick()
  assert.deepEqual(posts[1].payload,{provinces:['fiction']})
  input(find(container,n=>n.type==='input'&&n.props.type==='checkbox'),false);await tick()
  click(find(container,n=>n.type==='button'&&text(n)==='采集全国门户并生成报告'));await tick()
  assert.deepEqual(posts[2].payload,{vision:false})
  click(find(container,n=>n.type==='button'&&text(n)==='下载 AI 验证报告'));await tick()
  assert(gets.some(url=>url.endsWith('/synthetic-report/download-ai')))
  assert.equal(downloads.length,1);assert(downloads[0][0] instanceof Blob)
  app.unmount()
})
await test('mounted malformed report lists show the existing recoverable service messages',async()=>{
  const axios={get:async()=>({data:{items:{unexpected:true}}})}
  const {container,app}=mount(component(files[3],{axios}));await tick()
  assert(text(container).includes('暂时无法连接报告服务'));assert(text(container).includes('暂时无法读取 OpenClaw 任务'))
  app.unmount()
})
await test('mounted document list does not reschedule polling after pending responses resolve following unmount',async()=>{
  const waiting=[],axios={get:url=>new Promise(resolve=>waiting.push({url,resolve}))}
  const timers=[],set=globalThis.setTimeout,clear=globalThis.clearTimeout
  globalThis.setTimeout=(fn,delay)=>{timers.push({fn,delay});return timers.length};globalThis.clearTimeout=()=>{}
  try{
    const {container,app}=mount(component(files[3],{axios}))
    assert(text(container).includes('文书工坊'));assert.equal(waiting.length,2)
    app.unmount()
    for(const request of waiting)request.resolve({data:{items:[{id:'synthetic-task',state:'running'}]}})
    await tick();assert.equal(timers.length,0)
  }finally{globalThis.setTimeout=set;globalThis.clearTimeout=clear}
})
console.log(`PASS workspace pages: ${files.length} typed SFCs (compilation ${process.argv.includes('--runtime-only')?'NOT_RUN':'PASS'}), ${modules.length} typed modules, ${expected.size} rejected type counterexamples, ${passed} isolated runtime/mounted regressions`)
const sha=bytes=>createHash('sha256').update(bytes).digest('hex')
writeFileSync(path.join(scratch,'RESULT.json'),JSON.stringify({
  status:'PASS',strict_sfc_compilation:process.argv.includes('--runtime-only')?'NOT_RUN':'PASS',sfc_count:files.length,typed_modules:modules.length,
  type_evidence:typeEvidence,runtime_regressions:runtimeCases,real_user_storage_read:false,live_transport_used:false,
  script_sha256:sha(readFileSync(fileURLToPath(import.meta.url))),
  sources:[...files,...modules,'frontend/src/composables/useWorkspace.js'].map(file=>({file,sha256:sha(readFileSync(path.join(root,file)))})),
},null,2)+'\n')
}
