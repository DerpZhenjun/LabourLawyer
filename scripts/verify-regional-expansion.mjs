/** Real Chrome DevTools MCP acceptance for the two newly enabled localities. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const output=path.resolve(process.env.REGIONAL_EXPANSION_UI_OUTPUT_DIR||'reports/regional-expansion-20261023'),checks=[],pageId=2,base='http://127.0.0.1:5173'
fs.mkdirSync(path.join(output,'generated'),{recursive:true})
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(output,'browser-mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!result.isError,JSON.stringify(result.content))
  return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const t=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(t.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(x=>x.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const click=async text=>tool('click',{uid:await uid(text)})
const fill=async(text,value)=>tool('fill',{uid:await uid(text),value})
const wait=text=>tool('wait_for',{text:[text],timeout:15000})
const scope=d=>'/province/sichuan?'+new URLSearchParams({city:'成都市',district:d})
const go=path=>tool('navigate_page',{type:'url',url:base+path})
const shot=name=>tool('take_screenshot',{filePath:path.join(output,name+'.png'),fullPage:true})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
async function verifyGenerated(district,kind,source,annex){
  const requests=await tool('list_network_requests',{resourceTypes:['fetch']})
  const line=requests.split('\n').filter(x=>x.includes('POST')&&x.includes('/generate')).at(-1)
  assert(line?.includes('[200]'),requests)
  const file=path.join(output,'generated',`${district}-${kind}.network-request`)
  const detail=await tool('get_network_request',{reqid:Number(line.match(/reqid=(\d+)/)[1]),requestFilePath:file})
  assert(detail.includes('x-document-origin:official-sample-adaptation-not-blank'))
  const payload=JSON.parse(fs.readFileSync(file,'utf8'))
  assert.equal(payload.district,district);assert.equal(payload.source_id,source);assert.equal(payload.template_id,annex);assert.equal(payload.kind,kind)
  if(kind==='application'){
    assert.equal(payload.data.requests.length,2,'One request per line must stay separately numbered')
    assert(payload.data.requests[0].includes('24000')&&payload.data.requests[1].includes('20000'))
  }
  // Independently replay the captured synthetic UI payload for file/package QA.
  // This is separate from the actual browser POST, never claimed as its download.
  const replay=await fetch('http://127.0.0.1:8000/api/regional-guides/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
  assert.equal(replay.status,200);assert.equal(replay.headers.get('x-guide-source-id'),source)
  const bytes=Buffer.from(await replay.arrayBuffer());assert.equal(bytes.subarray(0,2).toString(),'PK')
  fs.writeFileSync(path.join(output,'generated',`${district}-${kind}-replayed.docx`),bytes)
}
const locals=[['锦江区','ee967bbf0dfe1d4c069bc829','8cc65371b3224a63ba25a1af9d49c54d'],['武侯区','1f8b592edbfb62253a2b4212','4452a5a18dc64c0f98b84461765b56d8']]
try{
  const deadline=Date.now()+30000
  let ready=false
  while(Date.now()<deadline){
    try{
      const [web,api]=await Promise.all([fetch(base,{signal:AbortSignal.timeout(2000)}),fetch('http://127.0.0.1:8000/api/regional-guides/inventory',{signal:AbortSignal.timeout(2000)})])
      ready=web.ok&&api.ok
    }catch{/* The project's backend may still be warming up after a reload. */}
    if(ready)break
    await new Promise(resolve=>setTimeout(resolve,250))
  }
  assert(ready,'Frontend/backend readiness check timed out before browser verification')
  await tool('new_page',{url:base+scope('锦江区'),isolatedContext:'regional-expansion-20261023'})
  for(const [district,source,annex] of locals){
    await check(`${district}: form-first layout, default examples, exact source`,async()=>{
      await go(scope(district));await wait('你的信息和公司的信息')
      assert.equal(await inspect(`document.querySelector('.selector-panel').nextElementSibling.id`),'document-workspace')
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),source)
      assert.equal(await inspect(`document.querySelectorAll('#document-workspace input').length`),16)
      assert.equal(await inspect(`Array.from(document.querySelectorAll('#document-workspace input,#document-workspace textarea')).every(x=>x.value.trim())`),true)
      assert.equal(await inspect(`document.querySelectorAll('main').length`),1)
      assert((await tool('take_snapshot')).includes('虚构示例'));await shot(`${district}-application`)
    })
    await check(`${district}: cancellation, keyboard focus and real application generation`,async()=>{
      await fill('textbox "你的姓名"',district+'测试劳动者')
      await fill('textbox "受理的仲裁委员会名称"',district+'测试委员会')
      await click('button "生成并下载仲裁申请书"');await wait('确认生成仲裁申请书？')
      assert.equal(await inspect(`document.querySelector('#app').inert`),true)
      await tool('press_key',{key:'Tab'});await tool('press_key',{key:'Tab'})
      assert.equal(await inspect(`!!document.activeElement.closest('[role="dialog"]')`),true)
      await tool('press_key',{key:'Escape'})
      assert.equal(await inspect(`document.activeElement.textContent.trim()`),'生成并下载仲裁申请书')
      await click('button "生成并下载仲裁申请书"');await click('button "取消"')
      await click('button "生成并下载仲裁申请书"');await shot(`${district}-confirmation`);await click('button "确认生成"');await wait('文书已生成并下载')
      await verifyGenerated(district,'application',source,annex)
    })
    await check(`${district}: evidence starts with one, edits, add/remove and real generation`,async()=>{
      await click('button "证据清单"');await wait('添加你的证据')
      assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
      await click('button "添加一项证据"');assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),2)
      await click('button "删除第2项证据"')
      await fill('textbox "材料名称"',district+'测试劳动合同')
      await click('button "生成并下载证据清单"');await wait('确认生成证据清单？');await click('button "确认生成"');await wait('文书已生成并下载')
      await verifyGenerated(district,'evidence',source,annex);await shot(`${district}-evidence`)
    })
    await check(`${district}: handling channel remains local, no false online entry`,async()=>{
      assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),district==='锦江区')
      assert.equal(await inspect(`document.querySelector('[data-field="handling-form"]').textContent`),district==='锦江区'?'窗口办理、网上办理':'窗口办理')
    })
    await check(`${district}: exact responsive widths and no overflow`,async()=>{
      for(const [width,height] of [[320,850],[375,812],[768,1024],[1024,768],[1440,1000],[812,375]]){
        await tool('emulate',{viewport:`${width}x${height}x1`})
        assert.equal(await inspect(`innerWidth`),width)
        assert.equal(await inspect(`document.documentElement.scrollWidth<=innerWidth`),true)
        assert.equal(await inspect(`Array.from(document.querySelectorAll('#document-workspace button,#document-workspace input,#document-workspace select')).filter(e=>e.getClientRects().length&&e.getBoundingClientRect().height<44).length`),0)
        await shot(`${district}-${width}x${height}`)
      }
      await tool('emulate',{viewport:'1440x1000x1'})
    })
  }
  await check('Switching districts isolates edits and restores the correct cached document',async()=>{
    await click('button "锦江区"');await wait('官网明确列出网上办理');await wait('添加你的证据')
    assert.equal(await inspect(`document.querySelector('#document-workspace input').value`),'劳动合同')
    await fill('textbox "材料名称"','仅属于锦江的合成证据')
    await click('button "武侯区"');await wait('这不是网站故障');await wait('添加你的证据')
    assert.equal(await inspect(`document.querySelector('#document-workspace input').value`),'武侯区测试劳动合同')
    await click('button "锦江区"');await wait('官网明确列出网上办理');await wait('添加你的证据')
    assert.equal(await inspect(`document.querySelector('#document-workspace input').value`),'仅属于锦江的合成证据')
    await shot('district-switch-isolation')
  })
  await check('Unknown district never inherits adapted templates; Zhejiang still works',async()=>{
    await fill('combobox "办理区县"','未核验测试区');await wait('该地区办事指南尚未核验')
    assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
    // Provincial documents remain explicitly scoped; no locality source is fabricated.
    assert((await tool('take_snapshot')).includes('不代表所选区县的模板已经核验'))
    await go('/province/zhejiang');await wait('虚构示例')
    assert.equal(await inspect(`!!document.querySelector('#document-workspace form')`),true)
  })
  await check('Reduced-motion setting, clean console, no model or private case requests',async()=>{
    if(process.env.UI_REDUCED_MOTION==='1')assert.equal(await inspect(`matchMedia('(prefers-reduced-motion: reduce)').matches`),true)
    const messages=await tool('list_console_messages',{types:['error','warn'],includePreservedMessages:true});assert(!messages.includes('msgid='),messages)
    const net=await tool('list_network_requests',{includePreservedRequests:true,pageSize:1000})
    assert(!/11434|ollama|\/api\/chat|\/api\/platform\/cases/.test(net))
  })
}finally{
  fs.writeFileSync(path.join(output,'BROWSER-RESULTS.json'),JSON.stringify({at:new Date().toISOString(),checks},null,2))
  close()
}
if(checks.some(x=>!x.passed))process.exitCode=1
