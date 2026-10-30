// Test-only React 18.2 renderer; no browser, WebGL, speech or model process.
const assert=require('node:assert/strict')
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const {createRequire}=require('node:module')
const root=path.resolve(__dirname,'..')
const ts=require(path.join(root,'frontend/node_modules/typescript'))
const testRequire=createRequire(path.join(process.env.LABOURLAWYER_REACT_TEST_ROOT||path.join(root,'scripts/react-mount-fixture'),'package.json'))
const React=testRequire('react'),renderer=testRequire('react-test-renderer')
const source=fs.readFileSync(path.join(root,'ChatVRM/src/pages/index.tsx'),'utf8')
const output=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText
const legacy='  [{"role":"user","content":"PRIVATE_DIGITAL_LEGACY"}]  '
let stored=legacy,storageTouches=0
const storage={getItem(){storageTouches++;return stored},setItem(_key,value){storageTouches++;stored=value}}
const viewerContext=React.createContext({viewer:{}}),Stub=()=>null
const context={exports:{},AbortController,URLSearchParams,setTimeout,clearTimeout,setInterval:()=>1,clearInterval:()=>{},console,
  window:{location:{search:''},addEventListener(){},removeEventListener(){},parent:{}},document:{referrer:''},
  fetch:async()=>({ok:true,json:async()=>({backend:false,voice:'browser',ai:{ready:false}})}),
  require(name){
    if(name==='react')return React
    if(name==='react/jsx-runtime')return testRequire(name)
    if(name==='react-markdown'||name==='remark-gfm'||name==='@/components/vrmViewer')return Stub
    if(name==='@/features/vrmViewer/viewerContext')return{ViewerContext:viewerContext}
    if(name==='@/features/messages/messages')return{textsToScreenplay:()=>[]}
    if(name==='@/features/messages/speakCharacter')return{speakCharacter(){},interruptSpeakCharacter(){}}
    if(name==='@/features/constants/koeiroParam')return{DEFAULT_PARAM:{}}
    if(name==='@/features/chat/openAiChat')return{getChatResponseStream:async()=>{throw Error('Unexpected chat request during mount')}}
    if(name==='@/components/meta')return{Meta:Stub}
    throw Error('Unexpected component import: '+name)
  }}
for(const target of [context,context.window])Object.defineProperty(target,'localStorage',{get(){storageTouches++;return storage}})
vm.runInNewContext(output,context)
async function main(){
  let tree
  await renderer.act(async()=>{tree=renderer.create(React.createElement(context.exports.default));await new Promise(setImmediate)})
  await renderer.act(async()=>{tree.unmount()})
  assert.equal(storageTouches,0,'Mounting the real digital Home must never access persistent chat storage')
  assert.equal(stored,legacy,'Legacy chat bytes must remain unchanged')
  console.log('PASS actual React digital Home mount does not read/write legacy storage; no WebGL, voice or model calls')
}
main().catch(error=>{console.error(error);process.exitCode=1})
