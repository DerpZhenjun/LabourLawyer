/** Capture the new public event rows themselves, not the first unrelated row. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('reports/nationwide-localization-20261023-night/cross-province/guangdong-baiyun/browser-own-events-0422'),pageId=2
assert(!fs.existsSync(out));fs.mkdirSync(out)
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(c=>c.type!=='image')}})+'\n');assert(!r.isError,JSON.stringify(r));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
let passed=false
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/admin/regions',isolatedContext:'own-guangdong-public-event-screenshots'})
  await tool('wait_for',{text:['OpenClaw 实际状态'],timeout:20000});await tool('emulate',{viewport:'1440x1000x1'})
  for(const [category,title,name] of [
    ['网上办理支持','白云区 · ONLINE_CHANNEL_UNVERIFIED','baiyun-unknown-channel'],
    ['官方页面访问','鹤山市 · GUIDE_PAGE_UNAVAILABLE','heshan-certificate-boundary'],
    ['地区间要求差异','白云区 · MATERIAL_INFORMATION_MISSING','baiyun-missing-current-guide']]){
    let snapshot=await tool('take_snapshot')
    const disclosure=snapshot.split('\n').find(l=>l.includes('DisclosureTriangle')&&l.includes(category));assert(disclosure)
    await tool('click',{uid:disclosure.match(/uid=(\S+)/)[1]})
    snapshot=await tool('take_snapshot')
    const heading=snapshot.split('\n').find(l=>l.includes('heading')&&l.includes(title));assert(heading)
    await tool('hover',{uid:heading.match(/uid=(\S+)/)[1]})
    const state=await tool('evaluate_script',{function:`() => Array.from(document.querySelectorAll('.original-section h3')).filter(e=>e.textContent===${JSON.stringify(title)}).map(e=>({text:e.textContent,top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom,height:innerHeight}))`})
    const position=JSON.parse(state.match(/```json\s*([\s\S]*?)\s*```/)[1]);assert(position.length&&position[0].top>=0&&position[0].bottom<=position[0].height)
    await tool('take_screenshot',{filePath:path.join(out,name+'.png'),fullPage:false})
  }
  assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='));passed=true
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),passed,candidate_acceptance:false},null,2));close()}
