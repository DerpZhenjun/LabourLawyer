import assert from 'node:assert/strict'
import {existsSync} from 'node:fs'
const url=new URL('../frontend/src/api/regional.ts',import.meta.url),api=existsSync(url)?await import(url):{}
assert.equal(typeof api.createRegionalClient,'function','Typed regional API client is missing')
const region={province:'zhejiang',city:'杭州市',district:'富阳区'}
const guide={...region,region_code:'330111',source_id:'own-source',version:209,fields:{},materials:[],templates:[],sections:{},channel:{}}
let received=[]
const client=api.createRegionalClient('http://127.0.0.1:8000/',async(url,init)=>{
  received.push({url:String(url),init})
  return Response.json(guide)
})
assert.equal((await client.lookup(region)).source_id,'own-source')
assert.match(received[0].url,/\/api\/regional-guides\/lookup\?province=zhejiang&city=/)
const controller=new AbortController();await client.lookup(region,controller.signal)
assert.equal(received[1].init.signal,controller.signal)
await assert.rejects(()=>api.createRegionalClient('http://test',async()=>Response.json({...guide,district:'建德市'})).lookup(region))
await assert.rejects(()=>api.createRegionalClient('http://test',async()=>Response.json({detail:[{input:'private'}]},{status:422})).lookup(region),e=>!e.message.includes('private'))
const error=new DOMException('Stopped','AbortError')
await assert.rejects(()=>api.createRegionalClient('http://test',async()=>{throw error}).lookup(region),e=>e.name==='AbortError')
console.log('PASS typed regional client binding, URLs, cancellation and safe errors')

const ctx={...region,region_code:'330111',source_id:'own-source',version:209,template_id:'own-evidence',kind:'evidence',mode:'blank',adapter:'own'}
const contract={schema_version:1,contract_id:'a'.repeat(64),context:ctx,fields:[{key:'name',label:'名称',type:'text',maxLength:20}],defaults:{name:''},policy:{unknown_fields:'reject',invalid_xml:'reject',capacity_is_official_requirement:false}}
const headers={'X-Guide-Source-ID':ctx.source_id,'X-Guide-Version':String(ctx.version),'X-Document-Origin':'official-blank-filled','X-Form-Contract-ID':contract.contract_id}
const word=new Uint8Array([0x50,0x4b,3,4,0,0])
const binary=(h=headers,body=word)=>api.createRegionalClient('http://test',async(url,init)=>{const p=JSON.parse(init.body);assert.equal(p.contract_id,contract.contract_id);assert.deepEqual(p.data,{name:'虚构材料'});return new Response(body,{headers:h})})
assert.equal((await binary().generate(contract,{name:'虚构材料'})).size,word.length)
for(const key of Object.keys(headers))await assert.rejects(()=>binary({...headers,[key]:'wrong'}).generate(contract,{name:'虚构材料'}),/不匹配/)
await assert.rejects(()=>binary(headers,new Uint8Array([1,2,3,4])).generate(contract,{name:'虚构材料'}),/Word/)
let invalidSent=false;await assert.rejects(()=>api.createRegionalClient('http://test',async()=>{invalidSent=true;return new Response()}).generate(contract,{name:'虚构材料',foreign:''}));assert(!invalidSent)
console.log('PASS generated response identity, payload, invalid binary and lossless validation before network')
