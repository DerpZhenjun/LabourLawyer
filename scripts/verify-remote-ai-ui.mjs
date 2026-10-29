/** Real existing-site acceptance. --answers sends two synthetic questions to Ubuntu. */
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('.runtime/remote-ai-fix-20261029')
fs.mkdirSync(out,{recursive:true})
const answers=process.argv.includes('--answers'), checks=[]
let pageId=2
async function tool(name,args={}) {
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  assert(!r.isError,JSON.stringify(r.content))
  return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')
}
async function inspect(expression) {
  const s=await tool('evaluate_script',{function:`() => (${expression})`})
  return JSON.parse(s.match(/```json\s*([\s\S]*?)\s*```/)[1])
}
async function until(expression,seconds=45) {
  const end=Date.now()+seconds*1000
  while(Date.now()<end) {if(await inspect(expression))return;await new Promise(r=>setTimeout(r,700))}
  throw new Error('Timed out: '+expression)
}
async function uid(text) {
  const snapshot=await tool('take_snapshot'),line=snapshot.split('\n').find(l=>l.includes(text))
  assert(line,text);return line.match(/uid=(\S+)/)[1]
}
async function check(name,fn) {
  await fn();checks.push({name,passed:true});console.log('PASS '+name)
}
try {
  await tool('new_page',{url:'http://127.0.0.1:3000/',isolatedContext:'remote-ai-avatar-synthetic-only'})
  await tool('emulate',{viewport:'1440x1000x1'})
  await check('Avatar finishes loading and Ubuntu qwen3.8 is connected',async()=>{
    await until(`document.querySelector('.avatar-stage')?.dataset.avatarState==='ready'`)
    await until(`document.querySelector('.connection-notice.connected')?.textContent.includes('qwen3.8:27b')`)
    assert.equal(await inspect(`!!document.querySelector('.avatar-notice')`),false)
  })
  if(answers) await check('Digital human returns a complete real remote answer',async()=>{
    await tool('fill',{uid:await uid('textbox "描述你的劳动争议问题"'),value:'连通性测试，不含真实案情。请只回复：Ubuntu Qwen3.8 数字人连接正常。'})
    await tool('click',{uid:await uid('button "发送问题 ↗"')})
    await until(`document.querySelector('.counsel-message.assistant')?.textContent.includes('数字人连接正常') && document.querySelector('.counsel-composer button[type="submit"]')?.textContent==='发送问题 ↗'`,180)
    const network=await tool('list_network_requests',{resourceTypes:['fetch'],pageSize:200})
    const post=network.split('\n').find(l=>l.includes('POST')&&l.includes('/api/chat/')&&l.includes('[200]'))
    assert(post,network)
    const detail=await tool('get_network_request',{reqid:Number(post.match(/reqid=(\d+)/)[1])})
    assert(/cache-control:no-cache, no-transform/i.test(detail))
    assert(!/content-encoding:gzip/i.test(detail))
    fs.writeFileSync(path.join(out,'digital-network.txt'),detail)
  })
  for(const width of [375,768,1440]) await check('Digital human responsive '+width,async()=>{
    await tool('emulate',{viewport:`${width}x900x1`})
    await until(`document.querySelector('.avatar-stage')?.dataset.avatarState==='ready'`)
    assert.equal(await inspect('innerWidth'),width)
    assert(await inspect(`document.documentElement.scrollWidth<=innerWidth`))
    assert(await inspect(`document.querySelector('.counsel-composer').getBoundingClientRect().bottom<=innerHeight`))
    await tool('take_screenshot',{filePath:path.join(out,`digital-${width}.png`)})
  })
  await tool('emulate',{viewport:'1440x1000x1'})
  if(answers) await tool('take_screenshot',{filePath:path.resolve('docs/images/digital-human.png')})
  assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
  await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'remote-ai-advisor-synthetic-only'})
  pageId=3
  await tool('click',{uid:await uid('button "打开 AI 法律顾问"')})
  await check('Text advisor recognises Ubuntu qwen3.8',async()=>{
    await until(`document.querySelector('[data-ai-status]')?.textContent.includes('qwen3.8:27b')`)
    assert.equal(await inspect(`document.querySelector('#assistant-question').disabled`),false)
  })
  if(answers) await check('Text advisor returns real Ubuntu-Ollama response',async()=>{
    await tool('fill',{uid:await uid('textbox "说说你遇到的问题"'),value:'连通性测试，不含真实案情。请只回复：Ubuntu Qwen3.8 文字顾问连接正常。'})
    await tool('click',{uid:await uid('button "发送问题"')})
    await until(`Array.from(document.querySelectorAll('.message.ai .bubble')).some(e=>e.textContent.includes('文字顾问连接正常'))&&!document.querySelector('.typing')`,180)
    const network=await tool('list_network_requests',{resourceTypes:['fetch'],pageSize:100})
    const post=network.split('\n').find(l=>l.includes('POST')&&l.includes('/api/ask')&&l.includes('[200]'))
    assert(post,network)
    const detail=await tool('get_network_request',{reqid:Number(post.match(/reqid=(\d+)/)[1])})
    assert(/x-ai-provider:Ubuntu-Ollama/i.test(detail))
    fs.writeFileSync(path.join(out,'advisor-network.txt'),detail)
  })
  for(const width of [375,768,1440]) await check('Text advisor responsive '+width,async()=>{
    await tool('emulate',{viewport:`${width}x900x1`})
    assert.equal(await inspect('innerWidth'),width)
    assert(await inspect(`document.documentElement.scrollWidth<=innerWidth`))
    await tool('take_screenshot',{filePath:path.join(out,`advisor-${width}.png`)})
  })
  if(answers) await tool('take_screenshot',{filePath:path.resolve('docs/images/ai-advisor.png')})
  assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
} catch(error) {
  checks.push({name:'acceptance',passed:false,error:error.message});console.error(error);process.exitCode=1
} finally {
  fs.writeFileSync(path.join(out,'browser-result.json'),JSON.stringify({checked_at:new Date().toISOString(),checks,model:'qwen3.8:27b',real_synthetic_questions:answers?2:0,existing_services_only:true},null,2))
  close()
}
