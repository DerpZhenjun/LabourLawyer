const assert=require('node:assert/strict'),fs=require('node:fs'),Module=require('node:module');
const {EventEmitter}=require('node:events');
const ts=require('../ChatVRM/node_modules/typescript');
const filename=require('node:path').resolve('ChatVRM/src/pages/api/chat.ts');
const mod=new Module(filename,module);
mod._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,filename);
(async()=>{
  let firstWrite,finishUpstream,finished=false;
  const written=new Promise(r=>firstWrite=r),encoder=new TextEncoder();
  const upstream=new ReadableStream({start(c){c.enqueue(encoder.encode('远程首块'));finishUpstream=()=>{if(finished)return;finished=true;c.enqueue(encoder.encode('，完整回答。'));c.close()}}});
  const previous=global.fetch;let payload;
  global.fetch=async(url,options)=>{assert(String(url).endsWith('/api/ask'));payload=JSON.parse(options.body);return {ok:true,body:upstream}};
  const res=Object.assign(new EventEmitter(),{headers:{},chunks:[],destroyed:false,headersSent:false,ended:false,setHeader(k,v){this.headers[k.toLowerCase()]=v},flushHeaders(){this.headersSent=true},write(buffer){this.chunks.push(buffer.toString());firstWrite();return true},end(){this.ended=true},status(){return this},json(){throw new Error('Unexpected error response')}});
  let running;
  try {
    running=mod.exports.default({method:'POST',body:{messages:[{role:'user',content:'虚构测试'}]}},res);
    await written;
    assert.deepEqual(res.chunks,['远程首块']);assert.equal(res.ended,false);
    assert.match(res.headers['cache-control'],/no-transform/,'Streaming must opt out of Next gzip buffering');
    finishUpstream();await running;
    assert.deepEqual(res.chunks,['远程首块','，完整回答。']);assert.equal(res.ended,true);
    assert.equal(payload.question,'虚构测试');
    console.log('PASS actual digital proxy yields the first chunk before upstream completion, with no compression buffering');
  } finally {finishUpstream?.();await running;global.fetch=previous;}
})().catch(e=>{console.error(e);process.exitCode=1});
