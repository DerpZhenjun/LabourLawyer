const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path')
const {createConnectionStore,handleConnectionRequest,trustedConnectionFrame}=require('./connection-store.cjs')
const {normalizeServiceAddress}=require('../packages/client-contracts/generated/index.cjs')
test('selected service persists across independent stores and reset, without accepting arbitrary fields or unsafe addresses',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'labourlawyer-connection-')),file=path.join(root,'connection.json')
 try{
  const a=createConnectionStore(file,normalizeServiceAddress);assert.equal(a.read(),null)
  const value={api:'http://192.168.110.81:8088',digital:''};a.write(value)
  assert.deepEqual(createConnectionStore(file,normalizeServiceAddress).read(),value)
  const before=fs.readFileSync(file)
  for(const invalid of [{...value,access_token:'must-not-persist'},{api:'http://public.invalid',digital:''},{api:'https://user:password@host',digital:''},{api:'file:///secret',digital:''},{api:value.api,digital:123}])assert.throws(()=>a.write(invalid))
  assert.deepEqual(fs.readFileSync(file),before)
  fs.writeFileSync(file,'broken-json');assert.throws(()=>a.read());assert.equal(fs.readFileSync(file,'utf8'),'broken-json')
  a.write(null);assert.equal(createConnectionStore(file,normalizeServiceAddress).read(),null)
 }finally{fs.rmSync(root,{recursive:true,force:true})}
})
test('persistence IPC refuses untrusted frames, unknown operations and invalid envelopes without touching the store',()=>{
 let reads=0,writes=0;const store={read(){reads++;return null},write(){writes++}}
 for(const payload of [{action:'read'},{action:'write',value:null}]){
  const event={};handleConnectionRequest(event,payload,()=>false,store);assert.deepEqual(event.returnValue,{ok:false})
 }
 for(const payload of [{action:'exec'}, {action:'read',extra:true},null]){const event={};handleConnectionRequest(event,payload,()=>true,store);assert.deepEqual(event.returnValue,{ok:false})}
 assert.equal(reads,0);assert.equal(writes,0)
 const read={};handleConnectionRequest(read,{action:'read'},()=>true,store);assert.deepEqual(read.returnValue,{ok:true,value:null})
 const write={};handleConnectionRequest(write,{action:'write',value:null},()=>true,store);assert.deepEqual(write.returnValue,{ok:true,value:null});assert.equal(writes,1)
})
test('only the pinned main frame of the app window may use connection persistence',()=>{
 const frame={url:'http://127.0.0.1:49152/connection'},sender={id:1,mainFrame:frame},windows=new Map([[1,'http://127.0.0.1:49152']])
 assert.equal(trustedConnectionFrame({sender,senderFrame:frame},windows),true)
 assert.equal(trustedConnectionFrame({sender,senderFrame:{...frame}},windows),false,'same-origin iframe is not the main frame')
 frame.url='https://outside.invalid';assert.equal(trustedConnectionFrame({sender,senderFrame:frame},windows),false)
 frame.url='http://127.0.0.1:49153/connection';assert.equal(trustedConnectionFrame({sender,senderFrame:frame},windows),false)
 frame.url='http://127.0.0.1:49152/connection';windows.clear();assert.equal(trustedConnectionFrame({sender,senderFrame:frame},windows),false)
})
