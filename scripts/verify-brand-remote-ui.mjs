/** Existing-site UI checks; never substitutes another backend for a blocked restart. */
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('.runtime/remote-ai-localities-20261028/brand-browser')
fs.mkdirSync(out,{recursive:true});let pageId=2;const checks=[]
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
async function inspect(expression){const s=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(s.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(l=>l.includes(text));assert(line,text);return line.match(/uid=(\S+)/)[1]}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const check=async(name,fn)=>{try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
 await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'brand-and-remote-connection-no-case-data'})
 await wait('你准备在哪个省份办理？')
 for(const width of [375,768,1440])await check('New real brand assets and layout at '+width,async()=>{
  await tool('emulate',{viewport:`${width}x900x1`})
  assert(await inspect(`document.documentElement.scrollWidth<=innerWidth`))
  assert(await inspect(`Array.from(document.querySelectorAll('header img.brand-mark,.assistant-fab img.brand-mark')).every(i=>i.complete&&i.naturalWidth>0)`))
  assert(await inspect(`document.querySelector('.assistant-fab img').src.endsWith('/brand/counsel-mark.svg')`))
  await tool('take_screenshot',{filePath:path.join(out,`brand-${width}.png`),fullPage:false})
 })
 await check('Old backend is reported honestly and sending is disabled',async()=>{
  await tool('click',{uid:await uid('button "打开 AI 法律顾问"')})
  await wait('后端需要更新，请重新启动项目')
  assert(await inspect(`document.querySelector('#assistant-question').disabled`))
  assert(await inspect(`document.querySelector('button[aria-label="发送问题"]').disabled`))
  await tool('take_screenshot',{filePath:path.join(out,'restart-required.png'),fullPage:false})
  await tool('press_key',{key:'Escape'})
  assert.equal(await inspect(`!!document.querySelector('.assistant-panel')`),false)
 })
 await tool('new_page',{url:'http://127.0.0.1:3000/',isolatedContext:'digital-human-existing-service'})
 pageId=3;await wait('阿律 · 法律数字人');await wait('远程问答未连接')
 await check('Real avatar page keeps remote unavailability explicit',async()=>{
  assert(await inspect(`document.querySelector('header img').src.endsWith('/brand/counsel-mark.svg')`))
  const network=await tool('list_network_requests')
  assert(!/POST.*\/api\/(chat|ask)|11434/.test(network))
  await tool('emulate',{viewport:'1440x1000x1'})
  await tool('take_screenshot',{filePath:path.resolve('docs/images/digital-human.png'),fullPage:false})
 })
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({checks,blocked_backend_restart:true,real_remote_browser_answer:'NOT_RUN',failed:checks.filter(c=>!c.passed).length},null,2));close()}
if(checks.some(c=>!c.passed))process.exitCode=1
