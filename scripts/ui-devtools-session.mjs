/** Local, isolated Chrome DevTools MCP session for reproducible UI verification. */
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const serverPath=process.env.CHROME_DEVTOOLS_MCP_PATH
if(!serverPath)throw new Error('Set CHROME_DEVTOOLS_MCP_PATH to the installed chrome-devtools-mcp.js entry point.')
const accessibilityArgs=process.env.UI_REDUCED_MOTION==='1'?['--chrome-arg=--force-prefers-reduced-motion']:[]
const server=spawn(process.execPath,[serverPath,'--isolated','--headless','--no-usage-statistics','--no-performance-crux',`--workspace=${root}`,...accessibilityArgs],{cwd:root,windowsHide:true,stdio:['pipe','pipe','pipe']})
let sequence=0, queue=Promise.resolve()
const pending=new Map()
const send=value=>{if(!server.stdin.writableEnded)server.stdin.write(JSON.stringify(value)+'\n')}
server.stdin.on('error',error=>{if(error.code!=='ERR_STREAM_WRITE_AFTER_END')process.stderr.write(error.message+'\n')})
const request=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++sequence
  const timeout=setTimeout(()=>{pending.delete(id);reject(new Error(`${method} timed out`))},60000)
  pending.set(id,{resolve,reject,timeout});send({jsonrpc:'2.0',id,method,params})
})
createInterface({input:server.stdout}).on('line',line=>{
  let message;try{message=JSON.parse(line)}catch{return}
  if(message.method==='roots/list'){send({jsonrpc:'2.0',id:message.id,result:{roots:[{uri:pathToFileURL(root).href,name:'LabourLawyer'}]}});return}
  const item=pending.get(message.id);if(!item)return
  clearTimeout(item.timeout);pending.delete(message.id)
  if(message.error)item.reject(new Error(JSON.stringify(message.error)));else item.resolve(message.result)
})
server.stderr.on('data',data=>process.stderr.write(data))
server.on('exit',()=>{for(const item of pending.values()){clearTimeout(item.timeout);item.reject(new Error('MCP server exited'))}pending.clear()})
const init=await request('initialize',{protocolVersion:'2024-11-05',capabilities:{roots:{listChanged:false}},clientInfo:{name:'LabourLawyer UI checks',version:'1.0'}})
send({jsonrpc:'2.0',method:'notifications/initialized'})
console.log(JSON.stringify({ready:true,server:init.serverInfo}))
export const call = (name,args={}) => request('tools/call',{name,arguments:args})
export const close = () => server.stdin.end()
if (path.resolve(process.argv[1]||'')===fileURLToPath(import.meta.url)) {
const input=createInterface({input:process.stdin})
input.on('line',line=>{queue=queue.then(async()=>{
  try{
    const command=JSON.parse(line)
    if(command.name==='exit'){server.stdin.end();input.close();return}
    const result=await request('tools/call',{name:command.name,arguments:command.arguments||{}})
    // Images are saved by take_screenshot to explicit workspace paths, not printed as base64.
    console.log(JSON.stringify({name:command.name,result:{...result,content:result.content?.filter(item=>item.type!=='image')}}))
  }catch(error){console.log(JSON.stringify({error:error.message}))}
})})
input.on('close',()=>{queue.finally(()=>server.stdin.end())})
}
