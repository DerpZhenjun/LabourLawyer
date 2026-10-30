import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import vm from 'node:vm'
import {configuredDigitalOrigin} from '../packages/client-contracts/src/services.ts'
import {normalizeServiceAddress} from '../packages/client-contracts/src/index.ts'
assert.equal(configuredDigitalOrigin({digital:{status:'configured',url:'http://192.168.110.81:8089'}}),'http://192.168.110.81:8089')
for(const raw of [{},{digital:{status:true}},{digital:{status:'configured',url:'javascript:alert(1)'}},{digital:{status:'invalid_configuration',url:null}}])assert.throws(()=>configuredDigitalOrigin(raw))
class APIError extends Error{constructor(status){super();this.status=status}}
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript')
const source=readFileSync(new URL('../frontend/src/api/digitalService.ts',import.meta.url),'utf8')
async function run({saved=null,backend='http://192.168.110.81:8088',digital='http://127.0.0.1:3000',response={digital:{status:'configured',url:'http://192.168.110.81:8089'}},failure,expected,rejected=false}){
 let calls=0;const signal=new AbortController().signal,module={exports:{}}
 const modules={'./connection.ts':{savedConnection:()=>saved},'./http.ts':{APIError,apiURL:p=>backend+p,readJSON:async(path,options)=>{calls++;assert.equal(path,'/api/services');assert.equal(options.signal,signal);if(failure)throw new APIError(failure);return response}},'../../../packages/client-contracts/src/index.ts':{normalizeServiceAddress},'../../../packages/client-contracts/src/services.ts':{configuredDigitalOrigin}}
 const js=ts.transpileModule(source.replaceAll('import.meta.env',JSON.stringify({VITE_DIGITAL_LAWYER_URL:digital})),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
 vm.runInNewContext(js,{module,exports:module.exports,URL,require:name=>{assert(name in modules);return modules[name]}})
 if(rejected)await assert.rejects(module.exports.resolveDigitalService(signal));else assert.equal(await module.exports.resolveDigitalService(signal),expected)
 if(saved?.digital)assert.equal(calls,0)
}
await run({expected:'http://192.168.110.81:8089'})
await run({saved:{digital:'https://selected.example'},expected:'https://selected.example'})
await run({failure:404,rejected:true})
await run({failure:503,rejected:true})
await run({backend:'http://127.0.0.1:8003',failure:404,expected:'http://127.0.0.1:3000'})
await run({response:{digital:{status:'not_configured',url:null}},digital:'http://192.168.110.81:8089',expected:'http://192.168.110.81:8089'})
await run({response:{digital:{status:'invalid_configuration',url:null}},rejected:true})
console.log('PASS actual digital resolver uses selected/deployment address; old remote APIs never silently target Windows localhost; no network/model probe during config parsing')

// Exercise the actual SFC connect path, rather than only the new helper.
const vue=require('vue'),sfc=require('@vue/compiler-sfc'),requests=[]
const descriptor=sfc.parse(readFileSync(new URL('../frontend/src/components/DigitalLawyer.vue',import.meta.url),'utf8'),{filename:'DigitalLawyer.vue'}).descriptor
const component=sfc.compileScript(descriptor,{id:'digital-service-config',inlineTemplate:false}).content
const js=ts.transpileModule(component.replaceAll('import.meta.env',JSON.stringify({VITE_DIGITAL_LAWYER_URL:'http://127.0.0.1:3000'})),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
const module={exports:{}}
vm.runInNewContext(js,{module,exports:module.exports,URL,AbortController,setTimeout,clearTimeout,
 fetch:async url=>{requests.push(String(url));return{ok:true,json:async()=>({service:'digital-human'})}},
 require:name=>{
  if(name==='vue')return{...vue,onMounted(){},onUnmounted(){}}
  if(name==='@/api/connection')return{savedConnection:()=>null}
  if(name==='@/api/digitalService')return{resolveDigitalService:async()=> 'http://192.168.110.81:8089'}
  if(name.includes('BrandMark.vue'))return{default:{}}
  throw Error('Unexpected dependency '+name)
 }})
const scope=vue.effectScope(),page=scope.run(()=>module.exports.default.setup({},{expose(){},emit(){}}))
await page.connect();assert.equal(requests[0],'http://192.168.110.81:8089/api/health/','Actual digital window must use the deployed service, not a compiled Windows loopback')
scope.stop()
console.log('PASS actual digital window connect consumes deployment resolver')
