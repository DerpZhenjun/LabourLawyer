import assert from 'node:assert/strict'
import {existsSync,readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {createHash} from 'node:crypto'
import {spawnSync} from 'node:child_process'
import path from 'node:path'

const root=fileURLToPath(new URL('../',import.meta.url)),require=createRequire(new URL('../frontend/package.json',import.meta.url))
const stateURL=new URL('../frontend/src/composables/useRegionalForm.ts',import.meta.url)
assert(existsSync(stateURL),'Bound-contract form state is not implemented')
const stateAPI=await import(stateURL),wire=await import(new URL('../packages/regional-contracts/src/index.ts',import.meta.url))
assert.equal(typeof stateAPI.useRegionalForm,'function')
const vue=require('vue'),compiler=require('@vue/compiler-sfc'),ts=require('typescript')
const js=await import(new URL('../frontend/src/data/jiangsuOwnFields.js',import.meta.url))
const zj=await import(new URL('../frontend/src/data/zhejiangOwnFields.js',import.meta.url))
const hn=await import(new URL('../frontend/src/data/hunanApplicationFields.js',import.meta.url))
const fd=await import(new URL('../frontend/src/data/feidongApplicationFields.js',import.meta.url))
let passed=0
const test=async(name,run)=>{await run();passed++;console.log('PASS '+name)}
const tick=async()=>{await Promise.resolve();await vue.nextTick();await Promise.resolve();await vue.nextTick()}
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return{promise,resolve,reject}}
const context=(district='虚构甲区',kind='application',adapter='legacy_own_test',version=1)=>({province:'jiangsu',city:'虚构市',district,region_code:'990001',source_id:'source-'+district,version,template_id:'template-'+kind,kind,mode:'blank',adapter})
const contract=(c,revision='one')=>{
  let defaults,fields
  const text=(key,label=key)=>({key,label,type:'text',maxLength:key==='factsReason'||key==='facts'?12000:300})
  const list=(key,maxItems=4)=>({key,label:key,type:'text_list',maxLength:1200,maxItems})
  if(c.adapter===js.JIANGSU_OWN_ADAPTER)defaults=js.createEmptyJiangsuOwn(c.kind)
  else if(c.adapter.startsWith('zhejiang_own_worker'))defaults=zj.createEmptyZhejiangOwn(c.kind)
  else if(c.adapter.startsWith('hunan_own_legacy_worker'))defaults=hn.createEmptyHunanApplication()
  else if(c.adapter===fd.FEIDONG_ADAPTER_KEY)defaults=fd.createEmptyFeidongApplication()
  else defaults=c.kind==='application'?{applicantName:'',acceptMediation:'',requests:[''],factsReason:''}:{caseNumber:'',evidenceList:[{name:'',source:''}]}
  fields=Object.entries(defaults).map(([key,value])=>{
    if(Array.isArray(value))return key==='evidenceList'?{key,label:'本区证据',type:'object_list',maxItems:2,fields:Object.keys(value[0]??{name:'',source:'',purpose:''}).map(k=>text(k))}:list(key,c.adapter.startsWith('hunan')?8:4)
    if(key==='copyCount'||key==='evidenceCopyCount')return{key,label:key,type:'copies',integer:true,min:1,max:30,nullable:true}
    return text(key,key==='applicantName'?'本区姓名':key)
  })
  if(c.adapter==='legacy_own_test')fields=fields.map(f=>f.key==='acceptMediation'?{...f,choices:['同意','不同意']}:f)
  const value={schema_version:1,contract_id:createHash('sha256').update(JSON.stringify(c)+revision).digest('hex'),context:c,fields,defaults,policy:{unknown_fields:'reject',invalid_xml:'reject',capacity_is_official_requirement:false}}
  return wire.assertFormContract(value,c)
}
const guide=c=>({...c,templates:[{id:c.template_id,can_generate:true,document_types:[c.kind],adapter:c.adapter,official_kind:'blank',sha256:'fictional-pin'}],fields:{},materials:[],sections:{},channel:{}})
const node=(type,text='')=>({type,text,children:[],props:{},parent:null})
const remove=el=>{if(el.parent){const i=el.parent.children.indexOf(el);if(i>=0)el.parent.children.splice(i,1);el.parent=null}}
const insert=(el,parent,anchor)=>{remove(el);const i=anchor?parent.children.indexOf(anchor):-1;parent.children.splice(i<0?parent.children.length:i,0,el);el.parent=parent}
const body=node('body')
const renderer=vue.createRenderer({createElement:node,createText:t=>node('#text',t),createComment:t=>node('#comment',t),setText:(el,t)=>{el.text=t},setElementText:(el,t)=>{el.text=t;el.children=[]},patchProp:(el,k,old,v)=>{el.props[k]=v},insert,remove,parentNode:el=>el.parent,nextSibling:el=>el.parent?.children[el.parent.children.indexOf(el)+1]||null,setScopeId:()=>{},querySelector:selector=>selector==='body'?body:null,insertStaticContent:(html,p,a)=>{const n=node('#static',html);insert(n,p,a);return[n,n]}})
const all=(el)=>[el,...el.children.flatMap(child=>all(child))]
const content=el=>String(el.text||'')+el.children.map(content).join('')
const compile=(relative,modules)=>{
  const filename=path.join(root,relative),source=readFileSync(filename,'utf8'),{descriptor,errors}=compiler.parse(source,{filename})
  assert.deepEqual(errors,[])
  const compiled=compiler.compileScript(descriptor,{id:relative,inlineTemplate:true})
  let code=ts.transpileModule(compiled.content,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText
  code=code.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"];?/g,(_,names,from)=>`const {${names.replace(/\s+as\s+/g,':')}}=__modules[${JSON.stringify(from)}];`)
    .replace(/import\s+([\w$]+)\s+from\s*['"]([^'"]+)['"];?/g,(_,name,from)=>`const ${name}=__modules[${JSON.stringify(from)}];`)
    .replace(/import\s*['"][^'"]+['"];?/g,'').replace('export default','return')
  return new Function('__modules',code)({vue,...modules})
}
const Generic=compile('frontend/src/components/RegionalContractFields.vue',{'../../../packages/regional-contracts/src/index.ts':wire})
const requests=[],generations=[],downloads=[],contractQueue=[],generateQueue=[],specialMounts=[]
let latest,escape,revision='one'
const client={
  contract(c,signal){requests.push({c:{...c},signal});return contractQueue.length?contractQueue.shift().promise:Promise.resolve(contract(c,revision))},
  generate(c,raw,signal){const request=wire.buildGenerateRequest(c,raw);generations.push({request,signal});return generateQueue.length?generateQueue.shift().promise:Promise.resolve(new Blob([new Uint8Array([80,75,3,4])]))},
}
const special=name=>vue.defineComponent({props:['modelValue','kind'],setup(props){const id=specialMounts.length+1;specialMounts.push({id,name,props});return()=>vue.h('section',{'data-special':name,'data-instance':id})}})
const Page=compile('frontend/src/views/RegionalDocument.vue',{
  '../../../packages/regional-contracts/src/index.ts':wire,
  'vue-router':{useRoute:()=>({params:{},query:{}}),RouterLink:vue.defineComponent({setup:(p,{slots})=>()=>vue.h('a',{},slots.default?.())})},
  '@/components/RegionalContractFields.vue':Generic,
  '@/components/JiangsuOwnFields.vue':special('jiangsu'),'@/components/ZhejiangOwnFields.vue':special('zhejiang'),
  '@/components/HunanApplicationFields.vue':special('hunan'),'@/components/FeidongApplicationFields.vue':special('feidong'),
  '@/composables/useRegionalGuide':{regionalClient:client,useRegionalGuide:()=>{throw new Error('Embedded test should not perform guide lookup')}},
  '@/composables/useRegionalForm':{useRegionalForm:(...args)=>(latest=stateAPI.useRegionalForm(...args))},
  '@/api/publicDraftScope':{publicEditorIdentity:vue.ref('synthetic-fixed-owner')},
  '@/composables/useDialogFocus':{useDialogFocus:(open,element,close)=>{escape=close}},
  '@/composables/downloadDocument':{downloadDocument:async(blob,filename)=>{downloads.push({blob,filename})}},
  '@/data/jiangsuOwnFields':js,'@/data/zhejiangOwnFields':zj,'@/data/hunanApplicationFields':hn,'@/data/feidongApplicationFields':fd,
})
const selected=vue.ref(context()),selectedGuide=vue.ref(guide(selected.value)),kind=vue.ref('application'),host=node('root')
const app=renderer.createApp({setup:()=>()=>vue.h(Page,{embedded:true,selectedRegion:selected.value,selectedGuide:selectedGuide.value,documentKind:kind.value})})
const nodes=()=>[...all(host),...all(body)],text=()=>content(host)+content(body)
const button=label=>nodes().find(n=>n.type==='button'&&(n.props['aria-label']===label||content(n).trim()===label))
const click=async label=>{const b=button(label);assert(b,label);assert(!b.props.disabled,label);await b.props.onClick?.();await tick()}
const input=key=>nodes().find(n=>['input','textarea','select'].includes(n.type)&&n.props.id?.endsWith('-'+key))
const change=async c=>{selected.value=c;selectedGuide.value=guide(c);kind.value=c.kind;await tick()}
const delayed=deferred();contractQueue.push(delayed);app.mount(host);await tick()
await test('page waits for its bound contract and aborts a previous pending scope',async()=>{
  assert.match(text(),/表单/);assert(!input('applicantName'));assert.equal(requests.length,1)
  const next=deferred();contractQueue.push(next);const b=context('虚构乙区');await change(b)
  assert(requests[0].signal.aborted);assert.equal(latest.contract.value,null)
  delayed.resolve(contract(context()));await tick();assert.equal(latest.contract.value,null)
  next.resolve(contract(b));await tick();assert.equal(latest.contract.value.context.district,b.district)
})
await test('generic renderer shows only server fields, choices and capacities without truncating',async()=>{
  assert(input('applicantName'));assert(!input('idNumber'));assert(!input('copyCount'))
  assert.equal(input('acceptMediation').type,'select');assert.match(text(),/同意/);assert(!text().includes('请本人选择'))
  input('applicantName').props.onInput({target:{value:'字'.repeat(301)}});await tick()
  assert.equal(latest.draft.value.applicantName.length,301);assert.equal(input('applicantName').props['aria-invalid'],'true')
  assert(!Object.hasOwn(input('applicantName').props,'maxlength'));assert.match(text(),/300/)
  for(const control of nodes().filter(n=>['input','textarea','select'].includes(n.type)))assert(nodes().some(n=>n.type==='label'&&n.props.for===control.props.id))
})
await test('unknown raw draft keys and list extras stay visible to rejection after editing',async()=>{
  const bad=wire.createEmptyForm(latest.contract.value);Object.defineProperty(bad,'oldHidden',{value:'',enumerable:false});bad.requests.extra=''
  latest.draft.value=bad;await tick();input('applicantName').props.onInput({target:{value:'虚构姓名'}});await tick()
  assert(Object.hasOwn(latest.draft.value,'oldHidden'));assert(Object.hasOwn(latest.draft.value.requests,'extra'))
  assert.equal(latest.requestConfirmation(),false);assert.equal(generations.length,0)
  await click('清空填写内容');assert(latest.validation.value.valid)
})
await test('confirmation supports submit prevention, cancel and Escape without generating',async()=>{
  let prevented=false;const form=nodes().find(n=>n.type==='form');form.props.onSubmit({preventDefault(){prevented=true}});await tick()
  assert(prevented);assert(latest.confirmOpen.value);await click('取消');assert(!latest.confirmOpen.value)
  await latest.generate();assert.equal(generations.length,0)
  latest.requestConfirmation();await tick();escape();await tick();assert(!latest.confirmOpen.value)
})
await test('submitted payload carries the bound contract id and preserves known hidden slots',async()=>{
  const raw=wire.createEmptyForm(latest.contract.value);Object.defineProperty(raw,'applicantName',{value:'  虚构隐藏槽  ',enumerable:false,writable:true,configurable:true})
  latest.draft.value=raw;assert(latest.requestConfirmation());await latest.generate();await tick()
  assert.equal(generations.at(-1).request.contract_id,latest.contract.value.contract_id)
  assert.equal(generations.at(-1).request.data.applicantName,'  虚构隐藏槽  ');assert.equal(downloads.length,1);assert(latest.downloaded.value)
})
await test('old confirmations and late generation responses cannot download across scopes',async()=>{
  latest.requestConfirmation();await tick();const staleConfirm=button('确认生成').props.onClick
  await change(context('虚构丙区'));await staleConfirm();await tick();assert.equal(generations.length,1)
  latest.requestConfirmation();await tick();await staleConfirm();await tick()
  assert.equal(generations.length,1);assert(latest.confirmOpen.value);latest.cancelConfirmation()
  const late=deferred();generateQueue.push(late);assert(latest.requestConfirmation());const running=latest.generate();await tick()
  const request=generations.at(-1);await change(context('虚构丁区'));assert(request.signal.aborted)
  late.resolve(new Blob(['old']));await running;await tick();assert.equal(downloads.length,1);assert(!latest.downloaded.value)
})
await test('contract errors expose retry and never reuse old fields or wrong source results',async()=>{
  const failure=deferred();contractQueue.push(failure);const failed=context('虚构失败区');await change(failed);failure.reject(new Error('本区合同暂不可用'));await tick()
  assert.match(text(),/本区合同暂不可用/);assert(!input('applicantName'));assert(!latest.requestConfirmation())
  await click('重试加载本区表单');assert(input('applicantName'))
  const foreign=deferred();contractQueue.push(foreign);const load=latest.reload();foreign.resolve(contract(context('其他区')));await load;await tick()
  assert.equal(latest.contract.value,null);assert(!input('applicantName'));await click('重试加载本区表单')
})
await test('server evidence schema controls row columns, a one-row minimum and its own maximum',async()=>{
  await change(context('虚构证据区','evidence'));assert(input('evidenceList.0.name'));assert(input('evidenceList.0.source'));assert(!input('evidenceList.0.purpose'))
  assert(button('删除第1项本区证据').props.disabled);await click('添加本区证据');assert.equal(latest.draft.value.evidenceList.length,2);assert(button('添加本区证据').props.disabled)
  await click('删除第2项本区证据');assert.equal(latest.draft.value.evidenceList.length,1)
})
await test('generation failures can reload the contract without discarding the same contract draft',async()=>{
  await change(context('虚构生成重试区'));latest.draft.value={...latest.draft.value,applicantName:'虚构重试保留'}
  const failure=deferred();generateQueue.push(failure);assert(latest.requestConfirmation());const running=latest.generate()
  failure.reject(new Error('表单来源需要重新核对'));await running;await tick();assert.match(text(),/表单来源需要重新核对/)
  await click('重新核对本区表单');assert.equal(latest.draft.value.applicantName,'虚构重试保留')
})
await test('specialized components keep their own examples and isolate every full context',async()=>{
  for(const [adapter,name] of [[js.JIANGSU_OWN_ADAPTER,'jiangsu'],['zhejiang_own_worker_oct29e_v1','zhejiang'],['hunan_own_legacy_worker_oct29c_v1','hunan'],[fd.FEIDONG_ADAPTER_KEY,'feidong']]){
    const a=context('虚构'+name+'甲区','application',adapter),b={...a,district:'虚构'+name+'乙区',source_id:a.source_id+'-b'}
    await change(a);assert(nodes().some(n=>n.props['data-special']===name));assert(latest.validation.value.valid)
    const original=latest.draft.value;assert.match(JSON.stringify(original),/虚构/);latest.draft.value={...original, ...(name==='feidong'?{facts:'虚构甲区草稿'}:{factsReason:'虚构甲区草稿'})}
    const count=specialMounts.length;await change(b);assert(specialMounts.length>count);assert(!JSON.stringify(latest.draft.value).includes('虚构甲区草稿'))
    await change(a);assert(JSON.stringify(latest.draft.value).includes('虚构甲区草稿'))
    revision='two';await latest.reload();await tick();assert(!JSON.stringify(latest.draft.value).includes('虚构甲区草稿'));revision='one'
  }
})
await test('source/version/template/kind changes invalidate confirmation immediately',async()=>{
  await change(context('虚构变更区'));latest.requestConfirmation();await tick()
  const update=async value=>{
    const load=deferred();contractQueue.push(load);selectedGuide.value=value
    // Parent props are delivered in Vue's update flush; the child must then
    // invalidate synchronously, before the new contract can possibly resolve.
    await vue.nextTick();assert.equal(latest.confirmOpen.value,false);assert.equal(latest.contract.value,null)
    load.resolve(contract(requests.at(-1).c));await tick()
  }
  await update({...selectedGuide.value,version:2})
  latest.requestConfirmation();await update({...selectedGuide.value,source_id:'new-source'})
  latest.requestConfirmation();await update({...selectedGuide.value,templates:[{...selectedGuide.value.templates[0],id:'new-template'}]})
  latest.requestConfirmation();kind.value='evidence';await vue.nextTick();assert.equal(latest.confirmOpen.value,false);await tick()
})
app.unmount();await tick()
await test('state invalidates a direct context change before any render or network completion',async()=>{
  const selected=vue.ref(context('同步甲区')),pending=deferred();let state
  const instance=renderer.createApp({setup(){state=stateAPI.useRegionalForm(selected,{client,download:async()=>{}});return()=>vue.h('div')}})
  instance.mount(node('direct-state'));await tick();assert(state.requestConfirmation());contractQueue.push(pending)
  selected.value=context('同步乙区');assert.equal(state.contract.value,null);assert.equal(state.confirmOpen.value,false);assert(!state.downloaded.value)
  pending.resolve(contract(selected.value));await tick();instance.unmount()
})
await test('context property order does not discard the same bound draft or refetch',async()=>{
  const selected=vue.ref(context('同值顺序区'));let state
  const instance=renderer.createApp({setup(){state=stateAPI.useRegionalForm(selected,{client,download:async()=>{}});return()=>vue.h('div')}})
  instance.mount(node('context-order'));await tick();state.draft.value={...state.draft.value,applicantName:'虚构保留姓名'}
  const count=requests.length;selected.value=Object.fromEntries(Object.entries(selected.value).reverse())
  assert(state.contract.value);assert.equal(state.draft.value.applicantName,'虚构保留姓名');assert.equal(requests.length,count)
  instance.unmount()
})
await test('an already started save cannot report success in another selection',async()=>{
  const selected=vue.ref(context('虚构保存甲区')),saving=deferred(),names=[];let state
  const instance=renderer.createApp({setup(){state=stateAPI.useRegionalForm(selected,{client,download:(blob,name)=>{names.push(name);return saving.promise}});return()=>vue.h('div')}})
  instance.mount(node('saving'));await tick();assert(state.requestConfirmation());const run=state.generate();await tick()
  assert.equal(names.length,1);assert.match(names[0],/虚构保存甲区/)
  selected.value=context('虚构保存乙区');await tick();saving.resolve();assert.equal(await run,false);assert(!state.downloaded.value)
  instance.unmount()
})
const scratch=path.join(root,'.runtime','regional-form-integration');mkdirSync(scratch,{recursive:true})
writeFileSync(path.join(scratch,'tsconfig.json'),JSON.stringify({compilerOptions:{target:'ES2022',module:'ESNext',moduleResolution:'Bundler',lib:['ES2023','DOM'],strict:true,noUncheckedIndexedAccess:true,exactOptionalPropertyTypes:true,verbatimModuleSyntax:true,allowImportingTsExtensions:true,skipLibCheck:true,noEmit:true},vueCompilerOptions:{strictTemplates:true},files:[path.join(root,'frontend/src/composables/useRegionalForm.ts'),path.join(root,'frontend/src/components/RegionalContractFields.vue')]}))
const checked=spawnSync(process.execPath,[require.resolve('vue-tsc/bin/vue-tsc.js'),'--project',path.join(scratch,'tsconfig.json'),'--noEmit'],{encoding:'utf8',cwd:root})
assert.equal(checked.status,0,(checked.stdout+checked.stderr).replaceAll(root,''))
console.log(`PASS regional form page integration: ${passed} mounted/cancellation/schema cases and strict state/renderer types`)
