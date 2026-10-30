import assert from 'node:assert/strict'
import {existsSync} from 'node:fs'
const url=new URL('../packages/client-contracts/src/index.ts',import.meta.url)
const api=existsSync(url)?await import(url):{}
assert.equal(typeof api.buildAskRequest,'function','Portable cross-client AI contract missing')
const messages=[{role:'ai',content:'欢迎'},{role:'user',content:'虚构测试问题'},{role:'ai',content:''}]
const request=api.buildAskRequest(' 虚构测试问题 ',messages)
assert.equal(request.question,'虚构测试问题')
assert.deepEqual(request.history,[{role:'assistant',content:'欢迎'},{role:'user',content:'虚构测试问题'}])
assert.equal(api.buildAskRequest('问',Array.from({length:20},()=>({role:'user',content:'问'}))).history.length,12)
assert.equal(api.buildAskRequest('问', [{role:'user',content:'😀'.repeat(8000)}]).history[0].content.length,16000)
assert.throws(()=>api.buildAskRequest('😀'.repeat(8001),[]))
assert.throws(()=>api.buildAskRequest('  ',[]))
assert.throws(()=>api.buildAskRequest('问',[{role:'system',content:'不能发送'}]))
assert.deepEqual(api.parseStoredChat('[{"role":"user","content":"虚构"}]'),[{role:'user',content:'虚构'}])
for(const bad of ['{}','null','[null]','[{"role":"system","content":"x"}]'])assert.equal(api.parseStoredChat(bad),null)
const status={ready:true,provider:'Ubuntu Ollama',model:'qwen3.8:27b',local_model_started:false,status:'ready'}
assert(api.remoteReady(api.assertAIStatus(status)))
assert(!api.remoteReady(api.assertAIStatus({...status,model:'other'})))
assert(!api.remoteReady(api.assertAIStatus({...status,local_model_started:true})))
assert.throws(()=>api.assertAIStatus({...status,ready:'yes'}))
const encoder=new TextEncoder(),bytes=encoder.encode('测试😀完成'),decoder=api.createAnswerDecoder()
assert.equal(decoder.push(bytes.slice(0,2))+decoder.push(bytes.slice(2,7))+decoder.push(bytes.slice(7))+decoder.finish(),'测试😀完成')
assert.equal(api.apiURL('http://127.0.0.1:8000/','/api/ask'),'http://127.0.0.1:8000/api/ask')
for(const path of ['https://other/api','//other/api','/api/../secret'])assert.throws(()=>api.apiURL('http://127.0.0.1:8000',path))
console.log('PASS shared AI request/history/status/Unicode/stream/storage/URL contracts; no network or inference')

const nativeURL=globalThis.URL;try{globalThis.URL=undefined;assert.equal(api.apiURL('http://127.0.0.1:8000','/api/ask'),'http://127.0.0.1:8000/api/ask')}finally{globalThis.URL=nativeURL}
