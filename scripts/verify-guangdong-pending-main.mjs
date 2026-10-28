/** Actual main-site report integration, explicitly not candidate guide acceptance. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('reports/nationwide-localization-20261023-night/cross-province/guangdong-baiyun/browser-main-report-0420')
const pageId=2,checks=[]
assert(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(c=>c.type!=='image')}})+'\n')
  assert(!r.isError,JSON.stringify(r));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')
}
async function read(expression){return JSON.parse((await tool('evaluate_script',{function:`() => (${expression})`})).match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
async function openCategory(title){
  const snapshot=await tool('take_snapshot')
  const line=snapshot.split('\n').find(l=>l.includes('DisclosureTriangle')&&l.includes(title))
  assert(line,'Missing actual disclosure '+title)
  await tool('click',{uid:line.match(/uid=(\S+)/)[1]})
}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/admin/regions',isolatedContext:'guangdong-own-pending-issues'})
  await tool('wait_for',{text:['OpenClaw 实际状态'],timeout:20000})
  await check('Four new public events actually reach the main report and remain pending',async()=>{
    const text=await read(`document.querySelector('.collection-page').textContent`)
    const events=JSON.parse(fs.readFileSync('reports/nationwide-localization-20261023-night/cross-province/guangdong-baiyun/outbox/own-source-0415.json','utf8'))
    assert.equal(events.length,4)
    for(const e of events)assert(text.includes(e.id),e.id)
    assert(text.includes('PENDING_OPENCLAW'));assert(text.includes('等待确认 261 条'))
    assert(!text.includes('453e9a1c8cb2122fe7fa910d')) // not published guide coverage
    await openCategory('网上办理支持')
    assert((await read('document.body.innerText')).includes('白云区 · ONLINE_CHANNEL_UNVERIFIED'))
    await tool('take_screenshot',{filePath:path.join(out,'actual-main-outbox.png'),fullPage:false})
  })
  await check('Certificate boundary is shown honestly as a pending source issue',async()=>{
    await openCategory('官方页面访问')
    const text=await read('document.body.innerText')
    assert(text.includes('鹤山市 · GUIDE_PAGE_UNAVAILABLE'));assert(text.includes('NET::ERR_CERT_AUTHORITY_INVALID'))
    assert(text.includes('未点击继续访问'))
  })
  await check('Candidate and neighbour remain unverified on published main',async()=>{
    for(const district of ['白云区','天河区']){
      await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/guangdong?'+new URLSearchParams({city:'广州市',district})})
      await tool('wait_for',{text:['该地区办事指南尚未核验'],timeout:20000})
      assert.equal(await read(`!!document.querySelector('[data-source-id]')`),false)
      assert.equal(await read(`!!document.querySelector('[data-online-entry]')`),false)
      await tool('take_screenshot',{filePath:path.join(out,`unpublished-${district}.png`),fullPage:false})
    }
  })
  await check('Existing Jianhu source and channel remain correct at three responsive widths',async()=>{
    await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/jiangsu?'+new URLSearchParams({city:'盐城市',district:'建湖县'})})
    await tool('wait_for',{text:['你的信息和公司的信息'],timeout:20000})
    assert.equal(await read(`document.querySelector('[data-source-id]').dataset.sourceId`),'ef1eb897ebf880c6f2a316f5')
    assert.equal(await read(`document.querySelector('[data-channel-state]').dataset.channelState`),'auth_required')
    for(const width of [375,768,1440]){
      await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'})
      assert(await read('document.documentElement.scrollWidth<=window.innerWidth'))
      await tool('take_screenshot',{filePath:path.join(out,`existing-main-${width}.png`),fullPage:false})
    }
  })
  await check('No browser console warning/error or chat/model request',async()=>{
    assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
    assert(!/11434|\/api\/chat|\/api\/tts/.test(await tool('list_network_requests')))
  })
}finally{
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),checks,
    failed:checks.filter(c=>!c.passed).length,candidate_guide_acceptance:'NOT_RUN',no_models:true},null,2));close()
}
if(checks.some(c=>!c.passed))process.exitCode=1
