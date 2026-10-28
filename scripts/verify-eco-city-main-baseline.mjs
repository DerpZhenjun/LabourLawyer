/** Before-publication isolation baseline on the unchanged main site. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city/guide-publication-0340/browser-main-before'),checks=[],pageId=2
assert(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(x=>x.type!=='image')}})+'\n');assert(!r.isError,JSON.stringify(r));return r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')}
async function read(expression){const r=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(r.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
async function navigate(province,city,district){await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/'+province+'?'+new URLSearchParams({city,district})})}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173',isolatedContext:'eco-city-before-publication'})
  await check('Eco-city is still honestly unverified on main before publication',async()=>{
    await navigate('tianjin','天津市','中新天津生态城');await tool('wait_for',{text:['该地区办事指南尚未核验'],timeout:20000})
    assert.equal(await read(`!!document.querySelector('[data-source-id]')`),false)
    assert.equal(await read(`!!document.querySelector('#regional-materials')`),false)
    await tool('take_screenshot',{filePath:path.join(out,'before-unverified.png'),fullPage:false})
  })
  await check('Whole Binhai never inherits the pending functional-area source',async()=>{
    await navigate('tianjin','天津市','滨海新区');await tool('wait_for',{text:['该地区办事指南尚未核验'],timeout:20000})
    assert.equal(await read(`!!document.querySelector('[data-source-id]')`),false)
    assert.equal(await read(`!!document.querySelector('[data-online-entry]')`),false)
  })
  await check('Existing Jianhu own source and auth boundary remain healthy',async()=>{
    await navigate('jiangsu','盐城市','建湖县');await tool('wait_for',{text:['你的信息和公司的信息'],timeout:20000})
    assert.equal(await read(`document.querySelector('[data-source-id]').dataset.sourceId`),'ef1eb897ebf880c6f2a316f5')
    assert.equal(await read(`document.querySelector('[data-channel-state]').dataset.channelState`),'auth_required')
    await tool('take_screenshot',{filePath:path.join(out,'existing-jianhu-regression.png'),fullPage:false})
  })
  await check('375 768 1440 baseline has no horizontal overflow',async()=>{
    for(const width of [375,768,1440]){await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'});assert(await read('document.documentElement.scrollWidth<=window.innerWidth'));await tool('take_screenshot',{filePath:path.join(out,`baseline-${width}.png`),fullPage:false})}
  })
  await check('No console warning or error and no model request',async()=>{
    const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
    assert(!/11434|\/api\/chat|\/api\/tts/.test(await tool('list_network_requests')))
  })
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),checks,failed:checks.filter(c=>!c.passed).length},null,2));close()}
if(checks.some(c=>!c.passed))process.exitCode=1
