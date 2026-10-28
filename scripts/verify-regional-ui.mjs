/** Actual Chrome DevTools MCP interactions against the integrated website. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const output=path.resolve(process.env.REGIONAL_UI_OUTPUT_DIR||'reports/government-guide-localization'),pageId=2,checks=[]
fs.mkdirSync(output,{recursive:true})
const base='http://127.0.0.1:5173'
async function tool(name,args={}){
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(output,'browser-mcp-transcript.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!r.isError,JSON.stringify(r.content));return r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const t=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(t.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const s=await tool('take_snapshot');const line=s.split('\n').find(l=>l.includes(text));assert(line,`Missing element ${text}`);return line.match(/uid=(\S+)/)[1]}
const click=async text=>tool('click',{uid:await uid(text)})
const fill=async(text,value)=>tool('fill',{uid:await uid(text),value})
const wait=text=>tool('wait_for',{text:[text],timeout:10000})
const go=p=>tool('navigate_page',{type:'url',url:base+p})
const shot=name=>tool('take_screenshot',{filePath:path.join(output,name+'.png'),fullPage:true})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
const scope=(district,city='成都市')=>`/province/sichuan?${new URLSearchParams({city,district})}`
try{
  await tool('new_page',{url:base+'/province/sichuan',isolatedContext:'regional-localization-acceptance'})
  await check('No district selected never inherits Tianfu',async()=>{await wait('请选择城市和区县');assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false);await shot('after-region-selector')})
  await check('Real district switching updates source ID, time limit and materials',async()=>{
    await click('button "天府新区"');await wait('部分信息有冲突')
    const a=await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`)
    assert.equal(await inspect(`document.querySelector('[data-field="handling-form"]').textContent`),'窗口办理')
    assert.equal(await inspect(`document.querySelectorAll('.regional-material').length`),4)
    assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
    await shot('after-tianfu-guide')
    await click('button "锦江区"');await wait('官网明确列出网上办理')
    const b=await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`)
    assert.notEqual(a,b);assert.equal(await inspect(`document.querySelector('[data-field="handling-form"]').textContent`),'窗口办理、网上办理')
    assert.match(await inspect(`document.querySelector('[data-online-entry]').href`),/^https:\/\/www.sczwfw.gov.cn\//)
    await shot('after-switch-jinjiang')
    await click('button "武侯区"');await wait('这不是网站故障')
    const c=await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`)
    assert.equal(new Set([a,b,c]).size,3);assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
    assert((await tool('take_snapshot')).includes('1个工作日'));await shot('after-window-wuhou')
  })
  await check('Unknown district and cross-province never retain previous guide',async()=>{
    await fill('combobox "办理区县"','测试未核验区');await wait('该地区办事指南尚未核验')
    assert.equal(await inspect(`document.querySelectorAll('.regional-material').length`),0)
    await fill('combobox "办理省份"','浙江省');await wait('请选择城市和区县')
    assert.equal(await inspect(`document.querySelector('[aria-label="办理城市"]').value`),'')
    assert.equal(await inspect(`document.querySelector('[aria-label="办理区县"]').value`),'')
    assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
    await shot('after-unverified-zhejiang')
  })
  await check('Slow/offline requests clear old content, latest district wins, retry recovers',async()=>{
    await go(scope('天府新区'));await wait('部分信息有冲突')
    try{
      await tool('emulate',{networkConditions:'Slow 3G'})
      await click('button "锦江区"');await click('button "武侯区"');await wait('这不是网站故障')
      assert.equal(await inspect(`document.querySelector('[data-region-code]').dataset.regionCode`),'510107000000')
      await tool('emulate',{networkConditions:'Offline'});await click('button "天府新区"');await wait('无法连接指南服务')
      assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      await shot('after-offline-retry')
    }finally{await tool('emulate',{})}
    await click('button "重新读取"');await wait('部分信息有冲突')
  })
  await check('Materials details, sample labels and official downloads',async()=>{
    await go(scope('天府新区'));await wait('部分信息有冲突')
    await click('DisclosureTriangle "查看这项材料的详细要求"')
    assert.equal(await inspect(`document.querySelector('.regional-material details').open`),true)
    assert((await tool('take_snapshot')).includes('来源渠道'));await shot('after-material-details')
    assert((await tool('take_snapshot')).includes('官方示例样表（不是空白模板）'))
    const url=await inspect(`document.querySelector('.regional-template .ll-button').href`)
    const r=await fetch(url);assert.equal(r.status,200);assert((await r.arrayBuffer()).byteLength>100)
    await click('link "下载原文件"')
    const network=await tool('list_network_requests',{includePreservedRequests:true});assert(network.includes('/templates/'))
  })
  await check('Evidence starts with one, add/remove, cancel/Escape and real generation',async()=>{
    await click('link "填写证据清单"');await wait('添加你的证据')
    assert.equal(await inspect(`document.querySelectorAll('.regional-material').length`),1)
    await click('button "添加一项证据"');assert.equal(await inspect(`document.querySelectorAll('.regional-material').length`),2)
    await click('button "删除第2项证据"');assert.equal(await inspect(`document.querySelectorAll('.regional-material').length`),1)
    await tool('fill_form',{elements:[{uid:await uid('textbox "材料名称"'),value:'测试劳动合同'},{uid:await uid('textbox "这份材料能说明什么"'),value:'仅作测试，证明劳动关系'}]})
    await click('button "生成并下载证据清单"');await wait('确认生成证据清单？')
    assert.equal(await inspect(`document.querySelector('#app').inert`),true)
    await tool('press_key',{key:'Escape'});assert.equal(await inspect(`!!document.querySelector('[role="dialog"]')`),false)
    await click('button "生成并下载证据清单"');await click('button "取消"')
    await click('button "生成并下载证据清单"');await shot('after-reference-confirmation');await click('button "确认生成"');await wait('文书已生成并下载')
    const net=await tool('list_network_requests',{resourceTypes:['fetch']});assert(net.includes('/generate')&&net.includes('200'))
    await shot('after-generated-evidence')
  })
  await check('Empty application can generate after explicit reference confirmation',async()=>{
    await go('/local-documents/sichuan/application?'+new URLSearchParams({city:'成都市',district:'天府新区'}));await wait('你的信息和公司的信息')
    const snapshot=await tool('take_snapshot')
    const elements=snapshot.split('\n').filter(line=>line.includes('textbox "')).map(line=>({uid:line.match(/uid=(\S+)/)[1],value:''}))
    assert.equal(elements.length,18)
    await tool('fill_form',{elements})
    assert.equal(await inspect(`Array.from(document.querySelectorAll('form input,form textarea')).every(x=>!x.value)`),true)
    await click('button "生成并下载仲裁申请书"');await wait('确认生成仲裁申请书？');await click('button "确认生成"');await wait('文书已生成并下载')
  })
  await check('Unavailable regional document never uses provincial template',async()=>{await go('/local-documents/sichuan/application?'+new URLSearchParams({city:'成都市',district:'未核验测试区'}));await wait('当地文书尚未通过填写核验');assert.equal(await inspect(`document.querySelectorAll('form').length`),0)})
  await check('Public collection admin shows durable outbox and version history',async()=>{
    await go('/admin/regions');await wait('等待 OpenClaw 确认');await click('button "查看版本记录"');await wait('内容 SHA256')
    assert.equal(await inspect(`document.querySelectorAll('.coverage-item').length`),31)
    assert((await tool('take_snapshot')).includes('跨省来源复核（不计入区县覆盖）'))
    const report=await (await fetch('http://127.0.0.1:8000/api/regional-guides/report')).json()
    const events=await (await fetch('http://127.0.0.1:8000/api/regional-guides/events')).json()
    assert.equal(report.openclaw.pending_count,events.pending)
    await click('DisclosureTriangle "官方事项搜索失败');assert((await tool('take_snapshot')).includes('SEARCH_NO_RESULT'))
    await click('button "导出公开问题报告"');await shot('after-openclaw-report')
  })
  for(const width of [375,768,1440])await check(`Responsive ${width}px, no overflow and material visibility`,async()=>{
    await tool('emulate',{viewport:`${width}x900x1${width===375?',mobile,touch':''}`});await go(scope('天府新区'));await wait('部分信息有冲突')
    assert.equal(await inspect(`document.documentElement.scrollWidth<=innerWidth`),true)
    assert.equal(await inspect(`document.querySelectorAll('h1').length`),1)
    assert.equal(await inspect(`Array.from(document.querySelectorAll('button,input,select')).filter(e=>e.getClientRects().length&&e.getBoundingClientRect().height<44).length`),0)
    await shot(`after-regional-${width}`)
    await go('/local-documents/sichuan/evidence?'+new URLSearchParams({city:'成都市',district:'天府新区'}));await wait('添加你的证据');assert.equal(await inspect(`document.documentElement.scrollWidth<=innerWidth`),true);await shot(`after-evidence-${width}`)
  })
  await check('Legacy Zhejiang/Guangdong template pages and AI entry remain available',async()=>{
    for(const p of ['zhejiang','guangdong']){await go(`/documents/${p}/application`);assert.equal(await inspect(`document.querySelectorAll('h1').length`),1);assert(await uid('button "打开 AI 法律顾问"'))}
    await click('button "打开 AI 法律顾问"');assert((await tool('take_snapshot')).includes('数字人'))
    const t=await tool('list_console_messages',{types:['error','warn']});assert(/no console messages/i.test(t),t)
  })
}finally{
  fs.writeFileSync(path.join(output,'BROWSER-TEST-RESULTS.json'),JSON.stringify({tested_at:new Date().toISOString(),engine:'Chrome DevTools MCP (installed server, isolated workspace session)',checks},null,2));close()
}
if(checks.some(c=>!c.passed))process.exitCode=1
