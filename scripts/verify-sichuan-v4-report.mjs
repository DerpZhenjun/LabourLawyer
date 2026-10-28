/** Public collection page, fresh isolated MCP, no login or model action. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {call,close} from './ui-devtools-session.mjs'
const batch=path.resolve('reports/nationwide-localization-20261023-night/batches/v4-guides-0205')
const out=process.env.REPORT_UI_OUTPUT?path.resolve(process.env.REPORT_UI_OUTPUT):path.join(batch,'browser-report'),pageId=2
assert(out.startsWith(path.resolve('reports/nationwide-localization-20261023-night/batches')+path.sep))
assert(!fs.existsSync(out));fs.mkdirSync(out)
async function tool(name,args={}){
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(i=>i.type!=='image')}})+'\n')
  assert(!r.isError,JSON.stringify(r.content));return r.content.filter(i=>i.type==='text').map(i=>i.text).join('\n')
}
let passed=false
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/admin/regions',isolatedContext:'v4-public-report'})
  await tool('wait_for',{text:['OpenClaw 实际状态'],timeout:15000})
  const text=JSON.parse((await tool('evaluate_script',{function:'() => document.querySelector(".collection-page").textContent'})).match(/```json\s*([\s\S]*?)\s*```/)[1])
  const codes=JSON.parse(fs.readFileSync(path.join(batch,'staging.json'),'utf8')).codes
  for(const code of codes){const g=JSON.parse(fs.readFileSync(path.join(batch,'guides',code,'guide.json'),'utf8'));assert(text.includes(g.city+' / '+g.district));assert(text.includes(crypto.createHash('sha256').update(JSON.stringify(g.source_url)).digest('hex').slice(0,24)))}
  assert(text.includes('PENDING_OPENCLAW'));assert(text.includes('不能把本地报告称为 OpenClaw 已接收'))
  assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
  await tool('take_screenshot',{filePath:path.join(out,'public-openclaw-report.png'),fullPage:false});passed=true
  console.log('PASS 15 own guides present, OpenClaw pending not acknowledged')
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),passed,model_calls:0},null,2));close()}
