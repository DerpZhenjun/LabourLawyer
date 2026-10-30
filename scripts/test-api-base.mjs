import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync} from 'node:fs'
import vm from 'node:vm'
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript'),vue=require('vue'),sfc=require('@vue/compiler-sfc')
const shared=await import('../packages/client-contracts/src/index.ts')
const wire=await import('../packages/regional-contracts/src/index.ts')
const workspace=await import('../packages/regional-contracts/src/workspace.ts')
const {createRegionalClient}=await import('../frontend/src/api/regional.ts')
const read=file=>readFileSync(new URL('../'+file,import.meta.url),'utf8')
const evaluate=(source,modules,env={VITE_API_BASE_URL:'http://127.0.0.1:8000'})=>{
 const code=source.replaceAll('import.meta.env',JSON.stringify(env))
 const js=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
 const module={exports:{}}
 vm.runInNewContext(js,{module,exports:module.exports,location:{origin:'http://127.0.0.1:45678'},Headers,AbortController,Blob,Response,setTimeout,clearTimeout,
  require:ref=>{assert(ref in modules,'Unexpected actual module dependency: '+ref);return modules[ref]}})
 return module.exports
}
const token='S'.repeat(43)
const httpFor=api=>evaluate(read('frontend/src/api/http.ts'),{
 '../../../packages/client-contracts/src/index.ts':shared,
 '../../../packages/regional-contracts/src/index.ts':wire,
 './authSession.ts':{authSession:{get:()=>({access_token:token})}},
 './connection.ts':{savedConnection:()=>api?{api,digital:''}:null},
},api?{VITE_API_BASE_URL:'http://127.0.0.1:8000'}:{VITE_API_BASE_URL:'/'})
const sameOrigin=httpFor('')
assert.equal(sameOrigin.API_BASE,'')
assert.equal(sameOrigin.apiURL('/health'),'http://127.0.0.1:45678/health','Desktop same-origin API configuration must resolve through its own proxy')
assert.throws(()=>sameOrigin.apiURL('//untrusted.invalid'))
assert.throws(()=>sameOrigin.apiURL('/api/../secret'))
for(const selected of ['https://selected-service.example','']){
 const http=httpFor(selected),requests=[]
 assert.equal(http.API_BASE,selected,'Saved API must override a different build-time address; relative base remains valid')
 const region={province:'fiction',city:'虚构市',district:'虚构区'}
 const context={...region,region_code:'990001',source_id:'synthetic-own-source',version:203,template_id:'synthetic-blank',kind:'application',mode:'blank',adapter:'synthetic-own'}
 const contract=wire.assertFormContract({schema_version:1,contract_id:'1'.repeat(64),context,fields:[],defaults:{},policy:{unknown_fields:'reject',invalid_xml:'reject',capacity_is_official_requirement:false}},context)
 const fetcher=async(url,options={})=>{
  requests.push({url,options})
  if(url.includes('/lookup?'))return Response.json({...context,templates:[],materials:[],fields:{},sections:{},channel:{}})
  if(url.includes('/form-contract?'))return Response.json(contract)
  assert(url.endsWith('/generate'))
  return new Response(new Uint8Array([80,75,3,4]),{headers:{'X-Document-Origin':'official-blank-filled','X-Form-Contract-ID':contract.contract_id,'X-Guide-Source-ID':context.source_id,'X-Guide-Version':String(context.version)}})
 }
 const regional=evaluate(read('frontend/src/composables/useRegionalGuide.ts'),{
  vue,'../../../packages/regional-contracts/src/index.ts':wire,'../api/http.ts':http,
  '../api/regional.ts':{createRegionalClient:base=>createRegionalClient(base,fetcher)},
 })
 await regional.regionalClient.lookup(region)
 await regional.regionalClient.contract(context)
 await regional.regionalClient.generate(contract,{})
 assert.equal(requests.length,3)
 for(const request of requests)assert(request.url.startsWith(selected+'/api/regional-guides/'),'Actual regional request must use selected service: '+request.url)
 const template=regional.templateURL(region,context.template_id,context)
 assert(template.startsWith(selected+'/api/regional-guides/templates/'))
 assert(template.includes('source_id='+context.source_id)&&template.includes('version=203'))
 const posts=[],gets=[],mounted=[],scope=vue.effectScope()
 const axios={__esModule:true,default:{get:async url=>{gets.push(url);return{data:{items:[],guides:[]}}},post:async(url,payload,options)=>{posts.push({url,payload,options});return{data:{id:'synthetic-task'}}}}}
 const component=file=>{
  const descriptor=sfc.parse(read(file),{filename:file}).descriptor
  const code=sfc.compileScript(descriptor,{id:'configured-api',inlineTemplate:false}).content
  return evaluate(code,{
   vue:{...vue,onMounted:fn=>mounted.push(fn),onBeforeUnmount:()=>{}},'vue-router':{RouterLink:{}},axios,
   '@/api/http.ts':http,'../api/http.ts':http,'@/data/provinces':{provinces:[]},
   '@/composables/downloadDocument':{downloadDocument:async()=>{}},
   '../../../packages/regional-contracts/src/workspace':workspace,
  }).default
 }
 scope.run(()=>component('frontend/src/components/DistrictWorkflow.vue').setup({slug:'fiction'},{expose(){}}))
 const documents=scope.run(()=>component('frontend/src/views/DocumentCenter.vue').setup({},{expose(){}}))
 for(const fn of mounted)await fn()
 await documents.startAgent();await documents.createReport()
 assert.equal(posts.length,2,'Both admin collection actions must use the selected service')
 for(const request of posts){
  assert(request.url.startsWith(selected+'/api/portal-reports'),'Admin token must never go to the build-time server: '+request.url)
  assert.equal(request.options.headers.Authorization,'Bearer '+token)
 }
 assert(gets.some(url=>url===selected+'/api/portal-reports/workflows/fiction'),'Actual workflow must use selected service')
 for(const url of gets)assert(url.startsWith(selected+'/api/portal-reports'))
 assert(documents.agentEvidence('task','fiction','step.png').startsWith(selected+'/api/portal-reports/'))
 scope.stop()
}
console.log('PASS actual configured API overrides build address for regional lookup/contract/Word/originals, workflow and authenticated collection; relative same-origin base remains valid')

// Distinct renderer origins cannot share localStorage; the narrow desktop bridge can.
let persisted=null
const bridge={read:()=>persisted,write:value=>{persisted=value}}
const connectionCode=read('frontend/src/api/connection.ts')
const connectionRuntime=storage=>{
 const js=ts.transpileModule(connectionCode,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,module={exports:{}}
 vm.runInNewContext(js,{module,exports:module.exports,window:{labourLawyerDesktop:{connection:bridge}},localStorage:storage,require:()=>shared})
 return module.exports
}
const memory=()=>{const data=new Map();return{getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)}}
const first=connectionRuntime(memory());first.saveConnection({api:'http://192.168.110.81:8088',digital:''})
const restarted=connectionRuntime(memory());assert.equal(restarted.savedConnection().api,'http://192.168.110.81:8088','Actual frontend must preserve selection across a new desktop origin')
restarted.clearConnection();assert.equal(connectionRuntime(memory()).savedConnection(),null)
assert.throws(()=>first.saveConnection({api:'https://user:secret@server',digital:''}));assert.equal(persisted,null)
console.log('PASS actual connection module uses origin-independent desktop settings across restart; reset and shared address validation preserved')
