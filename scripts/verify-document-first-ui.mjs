/** Verify the actual integrated UI via the installed Chrome DevTools MCP. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const output=path.resolve(process.env.DOCUMENT_FIRST_UI_OUTPUT_DIR||'reports/document-first-ui'),checks=[],baseline=process.argv.includes('--baseline')
fs.mkdirSync(output,{recursive:true})
const base='http://127.0.0.1:5173',pageId=2
async function tool(name,args={}){
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(output,baseline?'before-mcp.jsonl':'after-mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!r.isError,JSON.stringify(r.content));return r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const r=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(r.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const s=await tool('take_snapshot');const line=s.split('\n').find(l=>l.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const click=async text=>tool('click',{uid:await uid(text)})
const wait=text=>tool('wait_for',{text:[text],timeout:15000})
const go=p=>tool('navigate_page',{type:'url',url:base+p})
const shot=name=>tool('take_screenshot',{filePath:path.join(output,name+'.png'),fullPage:true})
const scope=d=>`/province/sichuan?${new URLSearchParams({city:'成都市',district:d})}`
async function saveGeneratedResponse(kind){
  const network=await tool('list_network_requests',{resourceTypes:['fetch']})
  const line=network.split('\n').filter(x=>x.includes('POST')&&x.includes('/generate')).at(-1)
  assert(line?.includes('[200]'),network)
  const reqid=Number(line.match(/reqid=(\d+)/)[1])
  const filePath=path.join(output,`generated-${kind}.network-request`)
  const detail=await tool('get_network_request',{reqid,requestFilePath:filePath})
  assert(detail.includes('x-document-origin:official-sample-adaptation-not-blank'))
  const payload=JSON.parse(fs.readFileSync(filePath,'utf8'))
  assert.equal(payload.district,'天府新区');assert.equal(payload.kind,kind)
  // MCP binary response export is empty in this installed version. Replay the
  // captured synthetic UI request separately; do not call this a browser download.
  const replay=await fetch('http://127.0.0.1:8000/api/regional-guides/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
  assert.equal(replay.status,200);assert.equal(replay.headers.get('x-guide-source-id'),payload.source_id)
  const bytes=Buffer.from(await replay.arrayBuffer());assert.equal(bytes.subarray(0,2).toString(),'PK');assert(bytes.length>1000)
  fs.writeFileSync(path.join(output,`replayed-${kind}.docx`),bytes)
}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:base+scope('天府新区'),isolatedContext:'document-first-acceptance'})
  await wait('部分信息有冲突')
  if(baseline)await shot('before-tianfu')
  await check('Region selection is immediately followed by actual document form',async()=>{
    assert.equal(await inspect(`document.querySelector('.selector-panel').nextElementSibling.id`),'document-workspace')
    assert.equal(await inspect(`!!document.querySelector('#document-workspace form')`),true)
    assert.equal(await inspect(`document.querySelectorAll('main').length`),1)
  })
  await check('Application fields, requests and facts are populated with labeled fictional examples',async()=>{
    assert.equal(await inspect(`document.querySelectorAll('#document-workspace input').length`),16)
    assert.equal(await inspect(`Array.from(document.querySelectorAll('#document-workspace input')).every(x=>x.value.trim())`),true)
    assert.equal(await inspect(`Array.from(document.querySelectorAll('#document-workspace textarea')).every(x=>x.value.trim())`),true)
    assert((await tool('take_snapshot')).includes('虚构示例'))
  })
  if(!baseline){
    await shot('after-tianfu-application')
    await check('Document switching retains edits and evidence begins with one example',async()=>{
      await tool('fill',{uid:await uid('textbox "你的姓名"'),value:'测试王晨'})
      await click('button "证据清单"');await wait('添加你的证据')
      assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
      assert.equal(await inspect(`document.querySelector('#document-workspace input').value`),'劳动合同')
      await click('button "添加一项证据"');assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),2)
      await click('button "删除第2项证据"');await shot('after-tianfu-evidence')
      await click('button "生成并下载证据清单"');await wait('确认生成证据清单？');await click('button "确认生成"');await wait('文书已生成并下载');await saveGeneratedResponse('evidence')
      await click('button "仲裁申请书"');await wait('你的信息和公司的信息')
      assert.equal(await inspect(`document.querySelector('#document-workspace input').value`),'测试王晨')
    })
    await check('Confirmation is cancellable, Escape restores focus, generation reaches real backend',async()=>{
      await click('button "生成并下载仲裁申请书"');await wait('确认生成仲裁申请书？')
      assert.equal(await inspect(`document.querySelector('#app').inert`),true)
      assert((await tool('take_snapshot')).includes('虚构示例'))
      await tool('press_key',{key:'Escape'});assert.equal(await inspect(`!!document.querySelector('[role="dialog"]')`),false)
      assert.equal(await inspect(`document.activeElement.textContent.trim()`),'生成并下载仲裁申请书')
      await click('button "生成并下载仲裁申请书"');await click('button "取消"')
      await click('button "生成并下载仲裁申请书"');await shot('after-confirmation');await click('button "确认生成"');await wait('文书已生成并下载')
      const net=await tool('list_network_requests',{resourceTypes:['fetch']});assert(net.includes('/generate')&&net.includes('200'))
      await saveGeneratedResponse('application')
    })
    await check('Newly adapted districts use distinct sources and retain local handling channels',async()=>{
      await click('button "锦江区"');await wait('官网明确列出网上办理')
      await wait('你的信息和公司的信息')
      assert.equal(await inspect(`document.querySelectorAll('#document-workspace form').length`),1)
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),'ee967bbf0dfe1d4c069bc829')
      await click('button "武侯区"');await wait('这不是网站故障')
      await wait('你的信息和公司的信息')
      assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
      assert.equal(await inspect(`document.querySelectorAll('#document-workspace form').length`),1)
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),'1f8b592edbfb62253a2b4212')
      await shot('after-adapted-wuhou')
    })
    await check('Legacy province forms appear inline with existing examples and explicit scope',async()=>{
      await go('/province/zhejiang');await wait('虚构示例')
      assert.equal(await inspect(`!!document.querySelector('#document-workspace form')`),true)
      assert((await tool('take_snapshot')).includes('不代表所选区县的模板已经核验'))
      assert.equal(await inspect(`document.querySelectorAll('main').length`),1)
      await click('button "生成并下载申请书"');await wait('确认生成')
      await click('button "取消"')
      await click('button "证据清单"');await wait('添加你的证据')
      assert.equal(await inspect(`document.querySelectorAll('#document-workspace .evidence-item').length`),1)
      await shot('after-zhejiang-inline')
      await go('/province/guangdong');await wait('虚构示例')
      assert.equal(await inspect(`!!document.querySelector('#document-workspace form')`),true)
      await shot('after-guangdong-inline')
    })
    await check('Standalone regional document route also has default values',async()=>{
      await go('/local-documents/sichuan/application?city=成都市&district=天府新区');await wait('你的信息和公司的信息')
      assert.equal(await inspect(`Array.from(document.querySelectorAll('form input')).every(x=>x.value.trim())`),true)
      assert.equal(await inspect(`document.querySelectorAll('main').length`),1)
    })
    await check('Responsive layout has no horizontal overflow at 320/375/768/1024/1440 and landscape',async()=>{
      await go(scope('天府新区'));await wait('部分信息有冲突')
      for(const [width,height] of [[320,800],[375,812],[768,1024],[1024,768],[1440,1000],[812,375]]){
        await tool('emulate',{viewport:`${width}x${height}x1`})
        assert.equal(await inspect(`window.innerWidth`),width,`Actual viewport is not ${width}px`)
        assert.equal(await inspect(`document.documentElement.scrollWidth<=window.innerWidth`),true,`Overflow at ${width}`)
        assert.equal(await inspect(`Array.from(document.querySelectorAll('#document-workspace button,input,select')).filter(x=>x.getClientRects().length&&x.getBoundingClientRect().height<44).length`),0)
        await shot(`responsive-${width}x${height}`)
      }
      for(const width of [375,1440]){
        await tool('emulate',{viewport:`${width}x${width===375?812:1000}x1`})
        assert.equal(await inspect(`window.innerWidth`),width)
        await go(scope('天府新区'));await wait('部分信息有冲突')
        await tool('take_screenshot',{filePath:path.join(output,`viewport-${width}.png`)})
      }
    })
    await check('Keyboard switching and reduced-motion setting retain an operable form',async()=>{
      await go(scope('天府新区'));await wait('部分信息有冲突')
      if(process.env.UI_REDUCED_MOTION==='1')assert.equal(await inspect(`matchMedia('(prefers-reduced-motion: reduce)').matches`),true)
      await click('button "仲裁申请书"');await tool('press_key',{key:'Tab'});await tool('press_key',{key:'Enter'});await wait('添加你的证据')
      assert.equal(await inspect(`document.querySelector('.document-kind-switch button[aria-pressed="true"]').textContent.trim()`),'证据清单')
      await shot('keyboard-evidence')
    })
    await check('No browser errors or model requests',async()=>{
      const errors=await tool('list_console_messages',{types:['error','warn'],includePreservedMessages:true});assert(!errors.includes('msgid='),errors)
      const network=await tool('list_network_requests',{includePreservedRequests:true});assert(!/11434|ollama|\/api\/chat/.test(network))
    })
  }
}finally{
  fs.writeFileSync(path.join(output,baseline?'baseline-results.json':'browser-results.json'),JSON.stringify({at:new Date().toISOString(),checks},null,2))
  close()
}
if(checks.some(x=>!x.passed))process.exitCode=1
