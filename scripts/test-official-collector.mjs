import assert from 'node:assert/strict'
import {parseCollectorStatus,collectorEvidencePath} from '../packages/client-contracts/src/collector.ts'
const job={id:'a'.repeat(32),url:'https://szzjg.jszwfw.gov.cn/guide?id=123',region:{province:'jiangsu',city:'苏州市',district:'张家港市',region_code:'320582'},state:'complete',attempt:1,created_at:'2026-10-30',updated_at:'2026-10-30',result:{state:'guide_observed',title:'劳动人事争议仲裁申请',service_verified:false,model_used:false,review_required:true,evidence:[{file:'page.png',bytes:123,sha256:'b'.repeat(64)}]}}
const raw={counts:{complete:1},items:[job],worker:{state:'idle',alive:true,updated_at:'2026-10-30'},capacity:128,concurrency:1,model_used:false,allowed_hosts:['szzjg.jszwfw.gov.cn'],review_required:true}
const parsed=parseCollectorStatus(raw)
assert.equal(parsed.items[0].region.district,'张家港市');assert.equal(parsed.counts.queued,0)
assert.equal(collectorEvidencePath(job.id,'page.png',1),'/api/official-collector/jobs/'+job.id+'/evidence/page.png?attempt=1')
for(const modify of [x=>x.counts.complete=true,x=>x.items[0].result.service_verified=true,x=>x.items[0].url='javascript:alert(1)',x=>x.items[0].region.region_code='',x=>x.items[0].result.evidence[0].file='../secret',x=>x.items[0].result.evidence[0].sha256='short',x=>x.items[0].state='published']){
 const copy=structuredClone(raw);modify(copy);assert.throws(()=>parseCollectorStatus(copy))
}
for(const [id,file,attempt] of [['../x','page.png',1],[job.id,'../page.png',1],[job.id,'page.html',1],[job.id,'page.png',0]])assert.throws(()=>collectorEvidencePath(id,file,attempt))
assert.deepEqual(parseCollectorStatus({...raw,worker:null,items:[],counts:{}}).items,[])
console.log('PASS actual collector response contract rejects forged verification, unsafe URLs/evidence, malformed counts and missing exact region; empty/offline states preserved')

import {createRequire} from 'node:module'
import {readFileSync} from 'node:fs'
import vm from 'node:vm'
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript'),vue=require('vue')
const {sha256}=await import(new URL('../frontend/node_modules/@noble/hashes/sha2.js',import.meta.url))
const {bytesToHex}=await import(new URL('../frontend/node_modules/@noble/hashes/utils.js',import.meta.url))
const contracts=await import('../packages/client-contracts/src/collector.ts')
const source=readFileSync(new URL('../frontend/src/composables/useOfficialCollector.ts',import.meta.url),'utf8')
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
const pending=[],calls=[],downloads=[],hooks=[],timers=new Map();let timerId=0,token='session-A',fetchCount=0,onRequest
class APIError extends Error{constructor(status,message){super(message);this.status=status}}
const bytes=new TextEncoder().encode('Synthetic public evidence'),hash=bytesToHex(sha256(bytes))
const fixture=structuredClone(raw);fixture.items[0].result.evidence=[{file:'page.txt',bytes:bytes.length,sha256:hash}]
const modules={vue:{...vue,onMounted(){},onBeforeUnmount:fn=>hooks.push(fn)},'@noble/hashes/sha2.js':{sha256},'@noble/hashes/utils.js':{bytesToHex},
 '@/api/http':{APIError,apiURL:path=>'https://chosen-service.example'+path,authorizationHeaders:()=>({Authorization:'Bearer '+token}),readJSON:(path,options)=>{calls.push({path,options});const promise=new Promise((resolve,reject)=>pending.push({resolve,reject}));onRequest?.();onRequest=undefined;return promise}},
 '@/api/authSession':{authSession:{get:()=>({access_token:token})}},'./downloadDocument':{downloadDocument:async(blob,name)=>downloads.push({bytes:blob.size,name})},
 '../../../packages/client-contracts/src/collector.ts':contracts}
const module={exports:{}}
vm.runInNewContext(code,{module,exports:module.exports,AbortController,fetch:async(url,options)=>{fetchCount++;assert(url.startsWith('https://chosen-service.example/api/official-collector/'));assert.equal(options.headers.Authorization,'Bearer '+token);return{ok:true,blob:async()=>new Blob([bytes])}},setTimeout:fn=>{const id=++timerId;timers.set(id,fn);return id},clearTimeout:id=>timers.delete(id),Uint8Array,Error,require:name=>{assert(name in modules,'Unexpected dependency '+name);return modules[name]}})
const scope=vue.effectScope(),page=scope.run(()=>module.exports.useOfficialCollector())
assert.equal(calls.length,0,'Opening a component must never auto-submit a browser task')
let request=page.refresh();pending.shift().resolve(fixture);await request;assert.equal(page.data.value.items[0].region.region_code,'320582')
await page.download(page.data.value.items[0],page.data.value.items[0].result.evidence[0]);assert.equal(downloads.length,1);assert.equal(fetchCount,1)
await page.download(page.data.value.items[0],{...page.data.value.items[0].result.evidence[0],sha256:'c'.repeat(64)});assert.equal(downloads.length,1,'Mismatched bytes cannot be offered as verified evidence')
request=page.submit(job.url,job.region);assert.equal(calls.at(-1).path,'/api/official-collector/jobs');assert.equal(calls.at(-1).options.method,'POST');assert.deepEqual(JSON.parse(calls.at(-1).options.body).items[0].region,job.region)
const followup=new Promise(resolve=>{onRequest=resolve});pending.shift().resolve({items:[job]});await followup;pending.shift().resolve(fixture);await request
request=page.refresh();const old=pending.shift();token='session-B';old.resolve(fixture);await request
hooks[0]();assert.equal(page.data.value,null);assert.equal(timers.size,0,'Unmount must cancel polling')
const count=calls.length;await page.refresh();assert.equal(calls.length,count,'Unmounted component cannot start a new request');assert.equal(page.data.value,null,'Late read after unmount cannot restore another account queue')
scope.stop()
console.log('PASS actual collector controller uses selected authenticated transport, verifies bytes without secure-context WebCrypto, never auto-submits, and cancels stale reads/polling on unmount')
