/** Real main-site issue integration; never candidate publication acceptance. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const iteration=process.argv[2]||'browser-main-0440'
assert(/^browser-[a-z0-9-]+$/.test(iteration))
const out=path.resolve('reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang',iteration),pageId=2,checks=[]
assert(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(c=>c.type!=='image')}})+'\n');assert(!r.isError,JSON.stringify(r));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
async function read(expression){return JSON.parse((await tool('evaluate_script',{function:`() => (${expression})`})).match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/admin/regions',isolatedContext:'rongjiang-pending-public-only'})
  await tool('wait_for',{text:['OpenClaw 实际状态'],timeout:20000});await tool('emulate',{viewport:'1440x1000x1'})
  await check('Both own public events are actually visible and pending, not coverage',async()=>{
    const text=await read(`document.querySelector('.collection-page').textContent`)
    const events=JSON.parse(fs.readFileSync('reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang/outbox/own-source-0440.json','utf8'))
    assert.equal(events.length,2);for(const e of events)assert(text.includes(e.id),e.id)
    assert(text.includes('等待确认 263 条'));assert(text.includes('PENDING_OPENCLAW'))
    assert(!text.includes('9324666463f34ff63056367a'))
    for(const [category,title,name] of [
      ['网上办理支持','蓉江新区 · ONLINE_CHANNEL_UNVERIFIED','own-online-unknown'],
      ['地区间要求差异','蓉江新区 · MATERIAL_INFORMATION_MISSING','own-materials-partial']]){
      let snapshot=await tool('take_snapshot')
      const disclosure=snapshot.split('\n').find(l=>l.includes('DisclosureTriangle')&&l.includes(category));assert(disclosure)
      await tool('click',{uid:disclosure.match(/uid=(\S+)/)[1]});snapshot=await tool('take_snapshot')
      const heading=snapshot.split('\n').find(l=>l.includes('heading')&&l.includes(title));assert(heading)
      await tool('hover',{uid:heading.match(/uid=(\S+)/)[1]})
      const pos=await read(`Array.from(document.querySelectorAll('.original-section h3')).filter(e=>e.textContent===${JSON.stringify(title)}).map(e=>({top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom,height:innerHeight}))`)
      assert(pos.length&&pos[0].top>=0&&pos[0].bottom<=pos[0].height)
      await tool('take_screenshot',{filePath:path.join(out,name+'.png'),fullPage:false})
    }
  })
  await check('Unpublished locality and neighbour do not inherit a guide or online entry',async()=>{
    for(const district of ['蓉江新区','南康区']){
      await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/jiangxi?'+new URLSearchParams({city:'赣州市',district})})
      await tool('wait_for',{text:['该地区办事指南尚未核验'],timeout:20000})
      assert.equal(await read(`!!document.querySelector('[data-source-id]')`),false)
      assert.equal(await read(`!!document.querySelector('[data-online-entry]')`),false)
      await tool('take_screenshot',{filePath:path.join(out,`unpublished-${district}.png`),fullPage:false})
    }
  })
  await check('Published Jianhu source and auth boundary persist at 375/768/1440',async()=>{
    await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/jiangsu?'+new URLSearchParams({city:'盐城市',district:'建湖县'})})
    await tool('wait_for',{text:['你的信息和公司的信息'],timeout:20000})
    assert.equal(await read(`document.querySelector('[data-source-id]').dataset.sourceId`),'ef1eb897ebf880c6f2a316f5')
    assert.equal(await read(`document.querySelector('[data-channel-state]').dataset.channelState`),'auth_required')
    for(const width of [375,768,1440]){
      await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'})
      assert(await read('document.documentElement.scrollWidth<=innerWidth'))
      await tool('take_screenshot',{filePath:path.join(out,`existing-${width}.png`),fullPage:false})
    }
  })
  await check('No console warnings/errors or model/chat requests',async()=>{
    assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
    assert(!/11434|\/api\/chat|\/api\/tts/.test(await tool('list_network_requests')))
  })
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),checks,failed:checks.filter(c=>!c.passed).length,candidate_guide_acceptance:'NOT_RUN',known_ai_button_occlusion:'not_fixed',models:0},null,2));close()}
if(checks.some(c=>!c.passed))process.exitCode=1
