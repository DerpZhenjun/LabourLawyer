// Mounted account-draft regression; all storage/identities/transports synthetic.
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {fileURLToPath,pathToFileURL} from 'node:url'
import path from 'node:path'

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const require=createRequire(path.join(root,'frontend/package.json'))
const vue=require('vue'),esbuild=require('esbuild'),compiler=require('@vue/compiler-sfc')
const digest=value=>createHash('sha256').update(value).digest('hex')
const files=['frontend/src/api/publicDraftScope.ts','frontend/src/App.vue','frontend/src/api/auth.ts','frontend/src/api/authSession.ts','frontend/src/api/provincial.ts','frontend/src/views/Zhejiang/LA.vue','frontend/src/views/Zhejiang/EL.vue','frontend/src/views/RegionalDocument.vue','frontend/src/composables/useRegionalForm.ts','frontend/src/components/DocumentWorkspace.vue']
const sourceBefore=Object.fromEntries(files.map(name=>[name,digest(readFileSync(path.join(root,name)))]))
class MemoryStorage {
  values=new Map();reads=[];writes=[];failReads=false
  getItem(key){this.reads.push(key);if(this.failReads)throw Error('synthetic unavailable read');return this.values.get(key)??null}
  setItem(key,value){this.writes.push(key);this.values.set(key,String(value))}
  removeItem(key){this.values.delete(key)}
}
const local=new MemoryStorage(),session=new MemoryStorage(),listeners=new Map()
Object.defineProperty(globalThis,'localStorage',{configurable:true,value:local})
Object.defineProperty(globalThis,'sessionStorage',{configurable:true,value:session})
globalThis.window={addEventListener(name,fn){listeners.set(fn,name)},removeEventListener(name,fn){listeners.delete(fn)},scrollTo(){},matchMedia:()=>({matches:true})}
globalThis.document={getElementById:()=>null,querySelector:()=>null}
globalThis.fetch=()=>{throw Error('Real network forbidden in private draft audit')}
const noTransport=()=>{throw Error('No real HTTP/generation transport permitted')}
function execute(source,resolve){
  const module={exports:{}}
  const code=esbuild.transformSync(source,{loader:'ts',format:'cjs',target:'es2022'}).code
  new Function('require','module','exports',code)(resolve,module,module.exports)
  return module.exports
}
const authSessionModule=execute(readFileSync(path.join(root,'frontend/src/api/authSession.ts'),'utf8'),name=>{
  if(name==='./connection.ts')return{savedConnection:()=>({api:'http://synthetic.invalid'})}
  throw Error('Unexpected auth session import '+name)
})
let nextIdentity='a';const authRequests=[]
class APIError extends Error{}
const http={APIError,readJSON:async(endpoint)=>{
  authRequests.push(endpoint)
  if(endpoint==='/api/auth/logout')return null
  assert.equal(endpoint,'/api/auth/login')
  return{access_token:nextIdentity.repeat(43),token_type:'bearer',expires_at:Date.now()/1000+3600,
    user:{id:'synthetic-user-'+nextIdentity,username:'synthetic-'+nextIdentity,role:'admin'}}
}}
const auth=execute(readFileSync(path.join(root,'frontend/src/api/auth.ts'),'utf8'),name=>{
  if(name==='vue')return vue
  if(name==='./authSession')return authSessionModule
  if(name==='./http')return http
  throw Error('Unexpected auth import '+name)
})
const login=async id=>{nextIdentity=id;assert.equal(await auth.login('synthetic-'+id,'SYNTHETIC-ONLY'),true);await vue.nextTick()}
const logout=async()=>{await auth.logout();assert.equal(auth.currentUser.value,null);await vue.nextTick()}
const provinceData=await import(pathToFileURL(path.join(root,'frontend/src/data/provinces.ts')))
const provincialPure=await import(pathToFileURL(path.join(root,'packages/regional-contracts/src/provincial.ts')))
const scopes=execute(readFileSync(path.join(root,'frontend/src/api/publicDraftScope.ts'),'utf8'),name=>name==='vue'?vue:name==='./auth'?auth:name==='./http'?{API_BASE:'http://synthetic.invalid'}:(()=>{throw Error('Unexpected scope import '+name)})())
const provincialRequests=[],provincialDownloads=[];let holdProvincial=false
const provincial=execute(readFileSync(path.join(root,'frontend/src/api/provincial.ts'),'utf8'),name=>{
  if(name==='axios')return{post:async(url,payload,options)=>{if(!holdProvincial)return{data:new Blob(['synthetic'])};return new Promise(resolve=>provincialRequests.push({url,payload,options,resolve}))},isAxiosError:()=>false}
  if(name==='./http')return{apiURL:p=>'http://synthetic.invalid'+p}
  if(name.includes('packages/regional-contracts/src/provincial'))return provincialPure
  throw Error('Unexpected provincial import '+name)
})
const node=(type,text='')=>({type,text,children:[],props:{},parent:null})
const remove=el=>{if(el.parent){const index=el.parent.children.indexOf(el);if(index>=0)el.parent.children.splice(index,1);el.parent=null}}
const insert=(el,parent,anchor)=>{remove(el);const index=anchor?parent.children.indexOf(anchor):-1;parent.children.splice(index<0?parent.children.length:index,0,el);el.parent=parent}
const body=node('body')
const renderer=vue.createRenderer({createElement:node,createText:t=>node('#text',t),createComment:t=>node('#comment',t),setText:(el,t)=>{el.text=t},setElementText:(el,t)=>{el.text=t;el.children=[]},patchProp:(el,key,old,value)=>{el.props[key]=value},insert,remove,parentNode:el=>el.parent,nextSibling:el=>el.parent?.children[el.parent.children.indexOf(el)+1]??null,setScopeId(){},querySelector:selector=>selector==='body'?body:null,insertStaticContent:(html,parent,anchor)=>{const el=node('#static',html);insert(el,parent,anchor);return[el,el]}})
const stub=vue.defineComponent({setup:(props,{slots})=>()=>vue.h('span',{},slots.default?.())})
function component(relative,modules={},inline=false){
  const filename=path.join(root,relative),{descriptor,errors}=compiler.parse(readFileSync(filename,'utf8'),{filename})
  assert.deepEqual(errors,[])
  const compiled=compiler.compileScript(descriptor,{id:'private-identity-audit',inlineTemplate:inline})
  const output=execute(compiled.content,name=>{
    if(name==='vue')return vue
    if(name in modules)return modules[name]
    if(name.endsWith('.css'))return{}
    if(name.endsWith('.vue'))return stub
    throw Error('Unexpected component import '+name)
  }).default
  if(!inline)output.render=()=>vue.h('div')
  return output
}
const provincialModules={'vue-router':{RouterLink:stub},'@/api/provincial':provincial,'@/data/provinces':provinceData,'@/composables/downloadDocument':{downloadDocument:(blob,name)=>provincialDownloads.push(name)},'@/api/publicDraftScope':scopes}
const mountProvincial=async(short)=>{
  const app=renderer.createApp(component('frontend/src/views/Zhejiang/'+short+'.vue',provincialModules),{province:'zhejiang',embedded:true})
  const instance=app.mount(node('root'));await vue.nextTick()
  return{app,state:instance.$.setupState}
}
const results=[]
assert.notEqual(scopes.provincialDraftKey('http://synthetic-one.invalid','same-user','zhejiang','application'),scopes.provincialDraftKey('http://synthetic-two.invalid','same-user','zhejiang','application'),'Same user IDs on different APIs must be separate')
for(const[short,kind]of[['LA','application'],['EL','evidence']]){
  local.values.clear();await logout()
  const legacyKey='labourlawyer-zhejiang-'+kind+'-draft-v6',anonMarker='QA_SYNTHETIC_ANONYMOUS_'+kind
  const legacy=JSON.stringify(short==='LA'?{applicantName:anonMarker,requests:['']}:{evidenceList:[{name:anonMarker,source:'',purpose:'',pageCount:''}]})
  local.setItem(legacyKey,legacy)
  const anonymous=await mountProvincial(short)
  assert.equal(short==='LA'?anonymous.state.form.applicantName:anonymous.state.evidenceList[0].name,anonMarker)
  assert.match(anonymous.state.draftScopeNotice,/未登录|设备/);anonymous.app.unmount()
  assert.equal(local.values.get(legacyKey),legacy,'Legacy v6 bytes must never be overwritten')
  await login('a');local.reads.length=0
  const a=await mountProvincial(short),marker='QA_SYNTHETIC_A_'+kind.toUpperCase()
  assert(!local.reads.includes(legacyKey),'Logged account must never read device legacy key')
  assert.notEqual(short==='LA'?a.state.form.applicantName:a.state.evidenceList[0].name,anonMarker)
  assert.match(a.state.draftScopeNotice,/账号/)
  if(short==='LA')a.state.form.applicantName=marker;else a.state.evidenceList[0].name=marker
  await vue.nextTick();a.app.unmount()
  const keyA=scopes.provincialDraftLocation('zhejiang',kind).key
  assert.notEqual(keyA,legacyKey);assert(local.values.get(keyA)?.includes(marker))
  await logout();await login('b');const b=await mountProvincial(short)
  const valueB=short==='LA'?b.state.form.applicantName:b.state.evidenceList[0].name
  assert.notEqual(valueB,marker);assert.notEqual(valueB,anonMarker)
  const keyB=scopes.provincialDraftLocation('zhejiang',kind).key;assert.notEqual(keyB,keyA)
  if(short==='LA')b.state.form.applicantName='QA_SYNTHETIC_B';else b.state.evidenceList[0].name='QA_SYNTHETIC_B'
  await vue.nextTick();b.app.unmount();await logout();await login('a')
  const returned=await mountProvincial(short)
  assert.equal(short==='LA'?returned.state.form.applicantName:returned.state.evidenceList[0].name,marker,'A draft must survive B and logout')
  holdProvincial=true;const submitted=returned.state.submitForm();await vue.nextTick()
  assert.equal(provincialRequests.length,1);const request=provincialRequests.shift();returned.app.unmount()
  await logout();await login('b');request.resolve({data:new Blob(['synthetic late A'])});await submitted
  assert.equal(provincialDownloads.length,0,'Late old-account provincial generation must never download')
  assert(request.options.signal.aborted,'Old request must be aborted on unmount');holdProvincial=false
  await logout();const anonAgain=await mountProvincial(short)
  assert.equal(short==='LA'?anonAgain.state.form.applicantName:anonAgain.state.evidenceList[0].name,anonMarker)
  anonAgain.state.clearDraft();await vue.nextTick();anonAgain.app.unmount()
  const cleared=await mountProvincial(short)
  assert.notEqual(short==='LA'?cleared.state.form.applicantName:cleared.state.evidenceList[0].name,anonMarker,'Cleared v7 must suppress legacy fallback')
  cleared.app.unmount();assert.equal(local.values.get(legacyKey),legacy)
  assert(local.values.get(keyA)?.includes(marker),'Clearing anonymous draft must not remove A draft')
  await login('a');const preserved=local.values.get(keyA);local.failReads=true
  const unreadable=await mountProvincial(short);assert.equal(unreadable.state.draftBlocked,false,'Read failure must not disable generation')
  local.failReads=false;unreadable.app.unmount();assert(local.values.get(keyA)===preserved,'Unreadable stored account draft must never be replaced by defaults on unmount');await logout()
  const anonKey=scopes.provincialDraftLocation('zhejiang',kind).key,anonBefore=local.values.get(anonKey),bBefore=local.values.get(keyB)
  await login('a');const resetA=await mountProvincial(short);resetA.state.clearDraft();await vue.nextTick();resetA.app.unmount()
  assert.equal(local.values.get(anonKey),anonBefore,'A reset must not modify anonymous draft');assert.equal(local.values.get(keyB),bBefore,'A reset must not modify B draft');assert.equal(local.values.get(legacyKey),legacy);await logout()
  results.push({case:'provincial-'+kind,account_isolation:true,anonymous_v6_bytes_preserved:true,a_draft_restored_after_b:true,anonymous_clear_does_not_delete_accounts:true,late_a_response_suppressed:true})
  console.log('PASS '+kind+' actual SFC account/API scope, anonymous legacy preservation, logout/B/A restore, clear tombstone and late-response guard')
}

// Regional state uses RAM rather than local/session storage. Mount the REAL App
// with its REAL regional page and composable, but a synthetic RouterView/client.
const wire=await import(pathToFileURL(path.join(root,'packages/regional-contracts/src/index.ts')))
const actualForm=await import(pathToFileURL(path.join(root,'frontend/src/composables/useRegionalForm.ts')))
const route=vue.reactive({path:'/local-documents/jiangsu/application',fullPath:'/local-documents/jiangsu/application',params:{slug:'jiangsu',kind:'application'},query:{},meta:{layout:'public'},hash:''})
const c={province:'jiangsu',city:'虚构市',district:'虚构区',region_code:'990001',source_id:'synthetic-source',version:1,template_id:'synthetic-template',kind:'application',mode:'blank',adapter:'synthetic_own_test'}
const contract={schema_version:1,contract_id:'c'.repeat(64),context:c,
  fields:[{key:'applicantName',label:'虚构姓名',type:'text',maxLength:300},{key:'requests',label:'虚构请求',type:'text_list',maxLength:1200,maxItems:4},{key:'factsReason',label:'虚构经过',type:'text',maxLength:12000}],
  defaults:{applicantName:'',requests:[''],factsReason:''},policy:{unknown_fields:'reject',invalid_xml:'reject',capacity_is_official_requirement:false}}
wire.assertFormContract(contract,c)
const guide={...c,content_hash:'b'.repeat(64),templates:[{id:c.template_id,can_generate:true,document_types:['application'],adapter:c.adapter,official_kind:'blank',sha256:'a'.repeat(64),source_url:'https://synthetic.gov.cn/guide'}],fields:{},materials:[],sections:{},channel:{}}
let state,regionalMounts=0,contractCalls=0,pendingGeneration,pendingContract,lastContractSignal;const generated=[],downloads=[],navigations=[]
const client={contract:async(context,signal)=>{contractCalls++;lastContractSignal=signal;if(pendingContract){const held=pendingContract;pendingContract=null;return held.promise}return contract},generate:async(bound,data,signal)=>{generated.push({actor:auth.currentUser.value?.id??'anonymous',data,signal});return pendingGeneration?pendingGeneration.promise:new Blob(['synthetic only'])}}
const regionalModules={
  'vue-router':{useRoute:()=>route,RouterLink:stub},
  '@/composables/useRegionalGuide':{regionalClient:client,useRegionalGuide:()=>{throw Error('No guide transport permitted')}},
  '@/api/publicDraftScope':scopes,
  '@/composables/useRegionalForm':{useRegionalForm:(...args)=>{regionalMounts++;state=actualForm.useRegionalForm(...args);return state}},
  '@/composables/useDialogFocus':{useDialogFocus(){}},'@/composables/downloadDocument':{downloadDocument:(blob,name)=>downloads.push(name)},
  '@/data/jiangsuOwnFields':await import(pathToFileURL(path.join(root,'frontend/src/data/jiangsuOwnFields.js'))),
  '@/data/zhejiangOwnFields':await import(pathToFileURL(path.join(root,'frontend/src/data/zhejiangOwnFields.js'))),
  '@/data/hunanApplicationFields':await import(pathToFileURL(path.join(root,'frontend/src/data/hunanApplicationFields.js'))),
  '@/data/feidongApplicationFields':await import(pathToFileURL(path.join(root,'frontend/src/data/feidongApplicationFields.js'))),
  '../../../packages/regional-contracts/src/index.ts':wire,
}
const Regional=component('frontend/src/views/RegionalDocument.vue',regionalModules)
let loginState,loginMounts=0
const Login=component('frontend/src/views/Login.vue',{'vue-router':{useRoute:()=>route,useRouter:()=>({replace:value=>navigations.push(value)}),RouterLink:stub},'@/api/auth':auth})
const RouterView=vue.defineComponent({setup:()=>()=>route.path==='/login'?vue.h(Login,{ref:instance=>{if(instance)loginState=instance.$.setupState},onVnodeMounted:()=>{loginMounts++}}):vue.h(Regional,{embedded:true,selectedRegion:c,selectedGuide:guide,documentKind:'application'})})
const App=component('frontend/src/App.vue',{
  'vue-router':{RouterView,RouterLink:stub,useRoute:()=>route,useRouter:()=>({replace:value=>navigations.push(value),push:value=>navigations.push(value)})},
  '@/api/auth':auth,'@/api/publicDraftScope':scopes,'@/composables/useAssistantDock':{useAssistantDock:()=>({style:vue.ref({}),hidden:vue.ref(false)})},
},true)
const tick=async()=>{await Promise.resolve();await vue.nextTick();await Promise.resolve();await vue.nextTick()}
local.values.clear();local.reads.length=0;local.writes.length=0
await login('a');const app=renderer.createApp(App);app.mount(node('root'));await tick()
const marker='QA_SYNTHETIC_A_REGIONAL',key=state.draftKey.value
state.draft.value={...wire.createEmptyForm(contract),applicantName:marker}
const sameOwner=scopes.publicEditorIdentity.value
authSessionModule.authSession.set({access_token:'r'.repeat(43),token_type:'bearer',expires_at:Date.now()/1000+3600,user:{id:'synthetic-user-a',username:'synthetic-a',role:'admin'}})
await tick();assert.equal(scopes.publicEditorIdentity.value,sameOwner);assert.equal(state.draft.value.applicantName,marker,'Same-user token refresh must not discard an active draft')
assert(state.requestConfirmation());const staleConfirmation=state.confirmationAction.value
await logout();await login('b');await tick()
assert.notEqual(state.draft.value.applicantName,marker);assert(!state.confirmOpen.value)
assert.equal(await staleConfirmation(),false);assert.equal(generated.length,0);assert.equal(downloads.length,0)
assert(regionalMounts>1,'Actual public RouterView must recreate the editor after identity changes')
await logout();await login('a');await tick();state.draft.value={...wire.createEmptyForm(contract),applicantName:marker}
let complete;pendingGeneration={promise:new Promise(resolve=>{complete=resolve})}
assert(state.requestConfirmation());const generating=state.generate();await tick()
const oldRequest=generated.at(-1);await logout();await login('b');await tick()
assert(oldRequest.signal.aborted);complete(new Blob(['late synthetic A']));assert.equal(await generating,false)
assert.equal(downloads.length,0);assert.notEqual(state.draft.value.applicantName,marker)
// Even a synchronous logout and same-account login cannot reuse a cached confirmation.
await logout();await login('a');await tick();state.draft.value={...wire.createEmptyForm(contract),applicantName:marker}
assert(state.requestConfirmation());const fast=state.confirmationAction.value
const before=scopes.publicEditorIdentity.value;authSessionModule.authSession.clear();authSessionModule.authSession.set({access_token:'a'.repeat(43),token_type:'bearer',expires_at:Date.now()/1000+3600,user:{id:'synthetic-user-a',username:'synthetic-a',role:'admin'}})
assert.notEqual(scopes.publicEditorIdentity.value,before);assert.equal(await fast(),false);await tick()
assert.notEqual(state.draft.value.applicantName,marker);assert.equal(downloads.length,0)
let resolveContract;pendingContract={promise:new Promise(resolve=>{resolveContract=resolve})}
const oldContractState=state;const reloading=state.reload();const oldContractSignal=lastContractSignal
await logout();await login('b');await tick();assert(oldContractSignal.aborted)
resolveContract({...contract,contract_id:'d'.repeat(64)});await reloading;await tick()
assert.equal(state.contract.value.contract_id,contract.contract_id);assert.equal(oldContractState.contract.value,null)
await logout();route.path='/login';route.fullPath='/login';await tick()
loginState.username='synthetic-b';loginState.password='SYNTHETIC-ONLY';nextIdentity='b';const beforeLogin=loginMounts
await loginState.submit();await tick();assert.equal(loginMounts,beforeLogin,'Account-bound editor reset must not remount the pending Login route');assert(navigations.includes('/admin'))
app.unmount();await logout()
results.push({case:'regional-same-route',actual_app_and_composable:true,identity_remount:true,ram_confirmation_and_request_reset:true,old_response_aborted_and_suppressed:true,fast_logout_same_user_invalidates:true})
console.log('PASS actual App/RegionalDocument owner reset, old confirmation refusal, ignored late transport after abort and batched logout→same-A')
const sourceAfter=Object.fromEntries(files.map(name=>[name,digest(readFileSync(path.join(root,name)))]))
assert.deepEqual(sourceAfter,sourceBefore)
console.log('PASS public draft identity regression; MemoryStorage and synthetic transport only; no formal source writes')
