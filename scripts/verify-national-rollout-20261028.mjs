/** Real MCP browser checks against the existing main public database only. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const base='http://127.0.0.1:5173',pageId=2,checks=[]
const out=path.resolve(process.env.ROLLOUT_UI_OUTPUT||'reports/nationwide-localization-20261028/rollout/browser')
assert(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){const result=await call(name,name==='new_page'?args:{pageId,...args});fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n');assert(!result.isError,JSON.stringify(result.content));return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')}
async function inspect(expression){const text=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(text.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const snap=await tool('take_snapshot');const line=snap.split('\n').find(x=>x.includes(text));assert(line,'Missing '+text);return line.match(/uid=(\S+)/)[1]}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const shot=name=>tool('take_screenshot',{filePath:path.join(out,name+'.png'),fullPage:false})
const go=pathname=>tool('navigate_page',{type:'url',url:base+pathname})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  const expected=await fetch('http://127.0.0.1:8000/api/regional-guides/rollout-status').then(r=>{assert(r.ok);return r.json()})
  await tool('new_page',{url:base+'/admin/regions',isolatedContext:'main-national-rollout-no-candidate-publication'});await wait('全国区县接入进度');await wait('候选资料待验收')
  await check('Published, generatable and candidate counts match actual API independently',async()=>{
    const values=await inspect(`Array.from(document.querySelectorAll('.rollout-totals dd')).map(e=>Number(e.textContent.replace(/[^0-9]/g,'')))`)
    assert.deepEqual(values,[expected.published_guides,expected.generatable_localities,expected.unpublished_candidates]);assert.equal(await inspect(`document.querySelectorAll('.rollout-table tbody tr').length`),31)
    assert(await inspect(`document.querySelector('[data-national-rollout]').textContent.includes('不是全国区县和功能区的完整普查')`))
    assert(expected.provinces.every(p=>p.completion_status==='incomplete'))
  })
  await check('Search filters provinces, empty result explains recovery, keyboard focus remains',async()=>{
    const search=await uid('searchbox "查找省份"');await tool('fill',{uid:search,value:'四川'})
    assert.deepEqual(await inspect(`Array.from(document.querySelectorAll('.rollout-table tbody tr')).map(e=>e.dataset.province)`),['sichuan'])
    await tool('fill',{uid:await uid('searchbox "查找省份"'),value:'无此省份'})
    await wait('没有匹配的省份');assert.equal(await inspect(`document.querySelectorAll('.rollout-table tbody tr').length`),0)
    // Native deletion exercises the input event; this MCP version's fill('')
    // clears the DOM property without reliably notifying Vue's model.
    await tool('click',{uid:await uid('searchbox "查找省份"')});await tool('press_key',{key:'Control+A'});await tool('press_key',{key:'Backspace'});await wait('显示 31 个省级地区');await tool('press_key',{key:'Tab'})
    assert(await inspect(`Boolean(document.activeElement.getAttribute('aria-label')?.startsWith('选择'))`))
  })
  for(const width of [375,768,1440])await check('Actual admin rollout reflows at '+width+'px',async()=>{
    await tool('emulate',{viewport:`${width}x900x1`});await tool('click',{uid:await uid('searchbox "查找省份"')})
    assert.equal(await inspect(`innerWidth`),width);assert(await inspect(`document.documentElement.scrollWidth<=innerWidth`));await shot('admin-'+width)
  })
  await check('Own Chengdu directory contains all 23 while unknown Qingyang inherits no guide',async()=>{
    await go('/province/sichuan?city=成都市&district=青羊区');await wait('该地区办事指南尚未核验')
    assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
    assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
    const areas=await fetch('http://127.0.0.1:8000/api/regional-guides/areas?'+new URLSearchParams({province:'sichuan',city:'成都市'})).then(r=>r.json())
    assert.equal(areas.items.length,23);assert.equal(areas.items.find(x=>x.district==='青羊区').source_id,null)
    assert(areas.items.find(x=>x.district==='锦江区').source_id);await shot('qingyang-unverified')
  })
  await check('Own Jinjiang form immediately follows location selector and retains default values',async()=>{
    await go('/province/sichuan?city=成都市&district=锦江区');await wait('你的信息和公司的信息')
    assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.regionCode`),'510104000000')
    assert(await inspect(`Array.from(document.querySelectorAll('#document-workspace input')).filter(e=>e.value.trim()).length>=10`))
    await shot('jinjiang-existing-form')
  })
  await check('Existing Jinjiang generation keeps cancellation, own source and a real backend POST',async()=>{
    await tool('click',{uid:await uid('button "生成并下载仲裁申请书"')});await wait('确认生成仲裁申请书？')
    await tool('press_key',{key:'Escape'});assert.equal(await inspect(`!!document.querySelector('[role="dialog"]')`),false)
    await tool('click',{uid:await uid('button "生成并下载仲裁申请书"')});await wait('确认生成仲裁申请书？')
    await tool('click',{uid:await uid('button "确认生成"')});await wait('文书已生成并下载')
    const requests=await tool('list_network_requests',{resourceTypes:['fetch']})
    const last=requests.split('\n').filter(l=>l.includes('POST')&&l.includes('/generate')).at(-1)
    assert(last?.includes('[200]'),requests)
    const file=path.join(out,'jinjiang-synthetic.network-request')
    await tool('get_network_request',{reqid:Number(last.match(/reqid=(\d+)/)[1]),requestFilePath:file})
    const payload=JSON.parse(fs.readFileSync(file,'utf8'))
    assert.equal(payload.district,'锦江区');assert.equal(payload.kind,'application')
    assert.equal(payload.source_id,await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`))
    await shot('jinjiang-generated')
  })
  await check('Unpublished Yandu does not expose an unaccepted source or template',async()=>{
    await go('/province/jiangsu?city=盐城市&district=盐都区');await wait('该地区办事指南尚未核验')
    assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
    assert.equal(await inspect(`!!document.querySelector('#document-workspace form')`),false);await shot('candidate-not-published')
  })
  await check('No current-page console warnings or model inference requests',async()=>{
    const messages=await tool('list_console_messages',{types:['error','warn']});assert(!messages.includes('msgid='),messages)
    const network=await tool('list_network_requests');assert(!/11434|\/api\/chat|\/api\/ask|\/api\/tts/.test(network))
  })
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),base,candidate_acceptance:false,checks,failed:checks.filter(x=>!x.passed).length},null,2));close()}
if(checks.some(x=>!x.passed))process.exitCode=1
