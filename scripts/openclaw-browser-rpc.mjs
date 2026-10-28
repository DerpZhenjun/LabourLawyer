// Native OpenClaw browser requests through the installed CLI facade.
// Inputs originate only from the Python executor, never from model code.
import { pathToFileURL } from 'node:url'
import { createInterface } from 'node:readline'
import { readFileSync } from 'node:fs'
const { n: callBrowserRequest } = await import(pathToFileURL(process.env.OPENCLAW_BROWSER_HELPER).href)
const lines=createInterface({input:process.stdin,crlfDelay:Infinity})
for await (const line of lines) {
  let id
  try {
    const message=JSON.parse(line)
    id=message.id
    const {request,timeout}=message
    let publicControls
    if(request.path==='/snapshot' && request.query?.targetId){
      try{
        publicControls=await callBrowserRequest({url:process.env.OPENCLAW_BROWSER_URL,token:process.env.OPENCLAW_BROWSER_TOKEN,timeout:String(timeout)},
          {method:'POST',path:'/act',query:{profile:request.query.profile},body:{kind:'evaluate',targetId:request.query.targetId,fn:readFileSync(new URL('./openclaw-public-controls.js',import.meta.url),'utf8'),timeoutMs:5000}})
      }catch(error){ publicControls={error:String(error).slice(0,300)} }
    }
    const result=await callBrowserRequest({url:process.env.OPENCLAW_BROWSER_URL,token:process.env.OPENCLAW_BROWSER_TOKEN,timeout:String(timeout)},request)
    if(publicControls && result && typeof result==='object')result.public_control_semantics=publicControls.result??publicControls
    process.stdout.write('OPENCLAW_RPC '+JSON.stringify({id,result})+'\n')
  } catch(error) {
    process.stdout.write('OPENCLAW_RPC '+JSON.stringify({id,error:String(error).slice(0,1200)})+'\n')
  }
}
