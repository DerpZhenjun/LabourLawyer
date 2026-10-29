// Exercise the actual Next API handler, without starting a server or calling a model.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const ts = require('../ChatVRM/node_modules/typescript');
const filename = require('node:path').resolve('ChatVRM/src/pages/api/health.ts');
const mod = new Module(filename, module);
mod._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,filename);
const handler = mod.exports.default;
async function run(replies) {
  let calls = [];
  const previous = global.fetch;
  global.fetch = async url => {calls.push(String(url));const response=replies.shift();if(response instanceof Error)throw response;return {ok:response.status===200,status:response.status,json:async()=>response.body};};
  const res={setHeader(){},status(s){this.statusCode=s;return this},json(body){this.body=body;return this}};
  try {await handler({method:'GET'},res);assert(calls.every(u=>!u.includes('/api/chat')));return res.body;} finally {global.fetch=previous;}
}
(async()=>{
  let result=await run([{status:200,body:{service:'api'}},{status:404,body:{detail:'Not Found'}}]);
  assert.equal(result.ai.status,'backend_update_required');
  assert.equal(result.ai.ready,false);
  assert.match(result.ai.message,/后端.*重启/);
  result=await run([new Error('down')]);
  assert.equal(result.ai.status,'backend_unavailable');
  result=await run([{status:200,body:{service:'api'}},new Error('SSH metadata timed out')]);
  assert.equal(result.backend,true);
  assert.equal(result.ai.status,'unavailable');
  result=await run([{status:200,body:{service:'api'}},{status:200,body:{ready:true,model:'other-model'}}]);
  assert.equal(result.ai.ready,false);
  assert.equal(result.ai.status,'model_mismatch');
  result=await run([{status:200,body:{service:'api'}},{status:200,body:{ready:true,model:'qwen3.8:27b',provider:'Ubuntu Ollama'}}]);
  assert.equal(result.ai.ready,true);
  assert.equal(result.ai.model,'qwen3.8:27b');
  result=await run([{status:200,body:{service:'api'}},{status:200,body:{ready:false,status:'not_connected',message:'请检查 SSH 连接'}}]);
  assert.equal(result.ai.message,'请检查 SSH 连接');
  console.log('PASS six real digital health handler scenarios, zero model calls');
})().catch(e=>{console.error(e);process.exitCode=1;});
