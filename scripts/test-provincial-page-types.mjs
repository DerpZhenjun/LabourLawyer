import assert from 'node:assert/strict'
import {readFileSync,existsSync,mkdirSync,writeFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {createRequire} from 'node:module'
import {spawnSync} from 'node:child_process'
import path from 'node:path'
import {createHash} from 'node:crypto'

const root=fileURLToPath(new URL('../',import.meta.url))
const require=createRequire(new URL('../frontend/package.json',import.meta.url))
const {parse}=require('@vue/compiler-sfc')
const pages=['views/Zhejiang/LA.vue','views/Zhejiang/EL.vue','views/Guangdong/LA.vue','views/Guangdong/EL.vue',
  'components/GenerateConfirmation.vue','components/HunanApplicationFields.vue','components/FeidongApplicationFields.vue']
for(const file of pages){
  const source=readFileSync(path.join(root,'frontend/src',file),'utf8')
  assert.equal(parse(source).descriptor.scriptSetup?.lang,'ts',`${file} must use checked TypeScript`)
  assert(!/@ts-ignore|@ts-nocheck|\bany\b/.test(source),`${file} must not bypass checking`)
}
for(const file of ['api/provincial.ts','data/hunanApplicationFields.ts','data/feidongApplicationFields.ts'])assert(existsSync(path.join(root,'frontend/src',file)),file)
const work=path.join(root,'.runtime/provincial-page-types');mkdirSync(work,{recursive:true})
writeFileSync(path.join(work,'tsconfig.json'),JSON.stringify({extends:'../../frontend/tsconfig.json',compilerOptions:{types:[]},include:pages.map(p=>'../../frontend/src/'+p).concat(['../../frontend/node_modules/vite/client.d.ts','../../frontend/src/api/provincial.ts','../../frontend/src/data/hunanApplicationFields.ts','../../frontend/src/data/feidongApplicationFields.ts'])},null,2))
const run=spawnSync(process.execPath,[require.resolve('vue-tsc/bin/vue-tsc.js'),'--project',path.join(work,'tsconfig.json'),'--noEmit'],{cwd:root,encoding:'utf8'})
assert.equal(run.status,0,run.stdout+run.stderr)
console.log('PASS 7 provincial SFCs and owned data/API strict Vue TypeScript checks')

const negative=path.join(work,'negative.ts')
writeFileSync(negative,"import type {HunanApplicationForm} from '../../frontend/src/data/hunanApplicationFields.ts'\nimport type {FeidongApplicationForm} from '../../frontend/src/data/feidongApplicationFields.ts'\nconst h:HunanApplicationForm={requests:[2],factsReason:'',evidenceList:[]}\nconst f:FeidongApplicationForm={applicant_lines:[3],agent_lines:[],respondent_lines:[],representative_lines:[],requests:[],facts:''}\nvoid h;void f\n")
writeFileSync(path.join(work,'negative.json'),JSON.stringify({extends:'../../frontend/tsconfig.json',compilerOptions:{types:[]},include:['negative.ts','../../frontend/node_modules/vite/client.d.ts']},null,2))
const rejected=spawnSync(process.execPath,[require.resolve('vue-tsc/bin/vue-tsc.js'),'--project',path.join(work,'negative.json'),'--noEmit'],{cwd:root,encoding:'utf8'})
assert.notEqual(rejected.status,0)
assert.equal((rejected.stdout.match(/error TS2322/g)||[]).length,2,rejected.stdout+rejected.stderr)
console.log('PASS negative types reject numeric requests and party lines without suppression directives')

const vue=require('vue'),esbuild=require('esbuild')
const provinceData=await import(new URL('../frontend/src/data/provinces.js',import.meta.url))
const pure=await import(new URL('../packages/regional-contracts/src/provincial.ts',import.meta.url))
const captures=[],downloads=[]
const axiosFixture={post:async(url,payload,options)=>{const{signal,...stableOptions}=options;assert(!signal||signal instanceof AbortSignal);captures.push({url,payload:structuredClone(payload),options:stableOptions});return {data:new Blob(['synthetic Word body'])}},isAxiosError:value=>!!value&&typeof value==='object'&&value.isAxiosError===true}
function execute(source,resolve){const module={exports:{}};new Function('require','module','exports',esbuild.transformSync(source,{loader:'ts',format:'cjs',define:{'import.meta.env.VITE_API_BASE_URL':'"http://synthetic.invalid"'}}).code)(resolve,module,module.exports);return module.exports}
const api=execute(readFileSync(path.join(root,'frontend/src/api/provincial.ts'),'utf8'),name=>name==='axios'?axiosFixture:name==='./http'?{apiURL:p=>'http://synthetic.invalid'+p}:pure)
const draftScopes=execute(readFileSync(path.join(root,'frontend/src/api/publicDraftScope.ts'),'utf8'),name=>name==='vue'?vue:name==='./auth'?{currentUser:vue.shallowRef(null)}:{API_BASE:'http://synthetic.invalid'})
let storage=new Map()
globalThis.localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)}
globalThis.window={addEventListener(){},removeEventListener(){},scrollTo(){},matchMedia:()=>({matches:true})}
globalThis.document={getElementById:()=>null}
const node=(type,text='')=>({type,text,children:[],props:{},parent:null})
const remove=el=>{if(el.parent){const index=el.parent.children.indexOf(el);if(index>=0)el.parent.children.splice(index,1);el.parent=null}}
const insert=(el,parent,anchor)=>{remove(el);const i=anchor?parent.children.indexOf(anchor):-1;parent.children.splice(i<0?parent.children.length:i,0,el);el.parent=parent}
const renderer=vue.createRenderer({createElement:node,createText:t=>node('#text',t),createComment:t=>node('#comment',t),setText:(el,t)=>{el.text=t},setElementText:(el,t)=>{el.text=t;el.children=[]},patchProp:(el,k,old,value)=>{el.props[k]=value},insert,remove,parentNode:el=>el.parent,nextSibling:el=>el.parent?.children[el.parent.children.indexOf(el)+1]||null,setScopeId(){},insertStaticContent:(html,parent,anchor)=>{const el=node('#static',html);insert(el,parent,anchor);return[el,el]}})
function component(file,inline=false,fieldData={}) {
 const {descriptor}=parse(readFileSync(file,'utf8'),{filename:file})
 const compiled=require('@vue/compiler-sfc').compileScript(descriptor,{id:'provincial-mounted',inlineTemplate:inline})
 const compiledTemplate=require('@vue/compiler-sfc').compileTemplate({source:descriptor.template.content,filename:file,id:'provincial-mounted',compilerOptions:{bindingMetadata:compiled.bindings}})
 assert.deepEqual(compiledTemplate.errors,[])
 const output=execute(compiled.content,name=>name==='vue'?vue:name==='axios'?axiosFixture:name==='vue-router'?{RouterLink:{}}:name==='@/api/provincial'?api:name==='@/api/publicDraftScope'?draftScopes:name==='@/data/provinces'?provinceData:name==='@/composables/downloadDocument'?{downloadDocument:async(blob,filename)=>downloads.push({blob,filename})}:name.includes('ApplicationFields')?fieldData:{})
 const result=output.default
 if(!inline)result.render=()=>vue.h('div')
 return result
}
async function mountPage(file,province){const el=node('root'),app=renderer.createApp(component(file),{province});const instance=app.mount(el);await vue.nextTick();return {app,state:instance.$.setupState}}
const flush=async()=>{await vue.nextTick();await new Promise(resolve=>setImmediate(resolve));await new Promise(resolve=>setImmediate(resolve))}
let pairs=0
const fixturePath=path.join(root,'reports/typescript-frontends-release-20261030/provincial-pages/BASELINE-PAYLOADS.json')
const recordBaseline=process.argv.includes('--record-baseline')
const fixture=existsSync(fixturePath)?JSON.parse(readFileSync(fixturePath,'utf8')):null
assert(recordBaseline||fixture,'Pinned pre-migration request fixture is required')
const pinned=[]
for(const province of provinceData.provinces)for(const kind of ['application','evidence']){
 if(!province[kind+'Route'])continue
 const short=kind==='application'?'LA':'EL',baseline=path.join(work,'baseline-'+short+'.vue')
 if(recordBaseline)assert(existsSync(baseline),'Root must export the immutable pre-migration SFC baseline: '+short)
 const results=[]
 for(const file of (recordBaseline?[baseline,path.join(root,'frontend/src/views/Zhejiang',short+'.vue')]:[path.join(root,'frontend/src/views/Zhejiang',short+'.vue')])){
  storage=new Map();captures.length=0;downloads.length=0
  const {app,state}=await mountPage(file,province.slug)
  state.requestGeneration();assert.equal(state.showConfirm,true);state.showConfirm=false;assert.equal(captures.length,0)
  state.requestGeneration();state.confirmGeneration();await flush();assert.equal(captures.length,1);assert.equal(downloads.length,1)
  const filled=structuredClone(captures[0]);state.requestGeneration(true);state.confirmGeneration();await flush();assert.deepEqual(captures[1].payload,{})
  results.push(filled);app.unmount()
 }
 if(results.length===2)assert.deepEqual(results[1],results[0],province.slug+' '+kind+' migrated payload/route/options must match actual old SFC')
 const digest=createHash('sha256').update(JSON.stringify(results.at(-1))).digest('hex')
 const expected=fixture?.requests.find(row=>row.province===province.slug&&row.kind===kind)
 if(!recordBaseline)assert.equal(digest,expected?.sha256,province.slug+' '+kind+' pinned old request capture')
 pinned.push({province:province.slug,kind,sha256:digest})
 pairs++
}
assert.equal(pairs,34)
if(recordBaseline){mkdirSync(path.dirname(fixturePath),{recursive:true});writeFileSync(fixturePath,JSON.stringify({baseline_revision:'78903a98',baseline_sources:['LA','EL'].map(short=>({file:'frontend/src/views/Zhejiang/'+short+'.vue',sha256:createHash('sha256').update(readFileSync(path.join(work,'baseline-'+short+'.vue'))).digest('hex')})),requests:pinned},null,2)+'\n')}
console.log('PASS 34 mounted provincial SFC requests match pre-migration captures; cancellation, blank payloads and downloads')

// Exercise the actual compiled Feidong template handlers rather than reimplementing the component.
const fd=await import(new URL('../frontend/src/data/feidongApplicationFields.js',import.meta.url))
const rootNode=node('root'),fdState=vue.ref(undefined)
const fdComponent=component(path.join(root,'frontend/src/components/FeidongApplicationFields.vue'),true,fd)
const fdApp=renderer.createApp({setup:()=>()=>vue.h(fdComponent,{modelValue:fdState.value,'onUpdate:modelValue':v=>{fdState.value=v}})})
fdApp.mount(rootNode);await vue.nextTick()
const all=(el=rootNode)=>[el,...el.children.flatMap(child=>all(child))]
const first=all().find(el=>el.type==='input');assert(first)
first.props.onInput({target:{value:'汉'.repeat(21)}});await vue.nextTick()
assert.equal(fdState.value.applicant_lines[0],'汉'.repeat(21));assert(!fd.validateFeidongApplication(fdState.value).valid)
assert(all().some(el=>el.props.id===first.props.id&&el.props['aria-invalid']==='true'))
const facts=all().filter(el=>el.type==='textarea').at(-1);facts.props.onInput({target:{value:'  保留原文😀  '}});await vue.nextTick();assert.equal(fdState.value.facts,'  保留原文😀  ')
fdApp.unmount()
console.log('PASS mounted Feidong native input handlers, overflow retention and linked accessibility state')

storage=new Map([['bad','{"requests":[42]}']])
const bad=api.readProvincialDraft('bad',{requests:[''],factsReason:''});assert(bad.blocked);assert.equal(storage.get('bad'),'{"requests":[42]}')
storage=new Map([['good','{"requests":["甲"],"factsReason":"原文","legacy":{"kept":true}}']])
const good=api.readProvincialDraft('good',{requests:[''],factsReason:''});assert(!good.blocked);assert.deepEqual(good.form.legacy,{kept:true})
const originalStorage=globalThis.localStorage;globalThis.localStorage={...originalStorage,getItem(){throw new Error('unavailable')}}
assert(!api.readProvincialDraft('offline',{requests:['']}).blocked,'Storage availability must not impose a new generation restriction')
globalThis.localStorage=originalStorage
assert.equal(await api.provincialError({isAxiosError:true,response:{data:new Blob(['{"detail":"校验文字"}'])}}),'校验文字')
assert.equal(await api.provincialError({isAxiosError:true,response:{data:{detail:{secret:'not text'}}}}),'生成失败，请稍后再试。')
storage=new Map([['null','null']]);assert(api.readProvincialDraft('null',{requests:['']}).blocked);assert.equal(storage.get('null'),'null')
const originalPost=axiosFixture.post
axiosFixture.post=async()=>({data:{detail:'not a document'}})
await assert.rejects(api.postProvincialDocument('/api/province-documents/zhejiang/application/generate',{}),/文书文件/)
axiosFixture.post=originalPost
console.log('PASS untrusted storage/error boundaries retain raw data and only display safe text errors')
for(const [short,kind,raw] of [['LA','application','{"requests":[42],"privateDraft":"retained"}'],['EL','evidence','{"evidenceList":"old incompatible draft","privateDraft":"retained"}']]){
 const key=`labourlawyer-zhejiang-${kind}-draft-v6`
 storage=new Map([[key,raw]]);captures.length=0
 const {app,state}=await mountPage(path.join(root,'frontend/src/views/Zhejiang',short+'.vue'),'zhejiang')
 state.requestGeneration();assert.equal(state.showConfirm,false);assert.equal(captures.length,0)
 state.saveDraft();app.unmount();assert.equal(storage.get(key),raw,'Malformed stored content must survive watch/unmount without replacement')
}
const evidenceKey='labourlawyer-zhejiang-evidence-draft-v6'
const zhejiang=provinceData.findProvince('zhejiang')
storage=new Map([[evidenceKey,JSON.stringify({...provinceData.makeEvidenceExample(zhejiang),legacy:{retained:true}})]])
const storedEvidence=await mountPage(path.join(root,'frontend/src/views/Zhejiang/EL.vue'),'zhejiang')
storedEvidence.state.form.caseNumber='虚构验收案号';storedEvidence.state.saveDraft();storedEvidence.app.unmount()
assert.deepEqual(JSON.parse(storage.get(evidenceKey)).legacy,{retained:true})
assert.deepEqual(JSON.parse(storage.get(draftScopes.provincialDraftLocation('zhejiang','evidence').key)).legacy,{retained:true})
console.log('PASS mounted provincial malformed-draft write protection and preservation of unknown saved evidence headers')
