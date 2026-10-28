/** End-to-end exact-locality acceptance through the actual Chrome DevTools MCP. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {call,close} from './ui-devtools-session.mjs'
const output=path.resolve('reports/chengdu-district-expansion-20261023'),pageId=2,base='http://127.0.0.1:5173',checks=[]
const baseline=process.argv.includes('--baseline')
fs.mkdirSync(path.join(output,'generated'),{recursive:true})
const locals=fs.readdirSync(path.join(output,'captures')).map(code=>JSON.parse(fs.readFileSync(path.join(output,'captures',code,'guide.json'),'utf8')))
async function tool(name,args={}){
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(output,baseline?'browser-before.jsonl':'browser-mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...r,content:r.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!r.isError,JSON.stringify(r.content));return r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const r=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(r.match(/```json\s*([\s\S]*?)\s*```/)[1])}
const snapshot=()=>tool('take_snapshot')
async function uid(text){const s=await snapshot();const line=s.split('\n').find(x=>x.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const click=async text=>tool('click',{uid:await uid(text)})
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const scope=d=>'/province/sichuan?'+new URLSearchParams({city:'成都市',district:d})
const go=p=>tool('navigate_page',{type:'url',url:base+p})
const shot=name=>tool('take_screenshot',{filePath:path.join(output,name+'.png'),fullPage:true})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
async function generated(g,kind){
  const requests=await tool('list_network_requests',{resourceTypes:['fetch']})
  const line=requests.split('\n').filter(l=>l.includes('POST')&&l.includes('/generate')).at(-1)
  assert(line?.includes('[200]'),requests)
  const file=path.join(output,'generated',`${g.region_code}-${kind}.network-request`)
  await tool('get_network_request',{reqid:Number(line.match(/reqid=(\d+)/)[1]),requestFilePath:file})
  const payload=JSON.parse(fs.readFileSync(file,'utf8'))
  const source=crypto.createHash('sha256').update(JSON.stringify(g.source_url)).digest('hex').slice(0,24)
  assert.equal(payload.district,g.district);assert.equal(payload.source_id,source);assert.equal(payload.kind,kind)
  assert.equal(payload.template_id,g.templates.find(t=>t.original_name==='仲裁申请书(模板).docx').id)
  if(kind==='application')assert.equal(payload.data.requests.length,2)
  else assert.equal(payload.data.evidenceList.length,1)
  const r=await fetch('http://127.0.0.1:8000/api/regional-guides/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
  assert.equal(r.status,200);assert.equal(r.headers.get('x-guide-source-id'),source)
  assert.equal(r.headers.get('x-document-origin'),'official-sample-adaptation-not-blank')
  fs.writeFileSync(path.join(output,'generated',`${g.region_code}-${kind}-replayed.docx`),Buffer.from(await r.arrayBuffer()))
}
try{
  let ready=false;const deadline=Date.now()+30000
  while(Date.now()<deadline){try{ready=(await fetch('http://127.0.0.1:8000/api/regional-guides/inventory',{signal:AbortSignal.timeout(2000)})).ok}catch{}if(ready)break;await new Promise(r=>setTimeout(r,250))}
  assert(ready,'Backend not ready')
  await tool('new_page',{url:base+scope('龙泉驿区'),isolatedContext:'chengdu-acceptance-20261023'})
  await wait('你的信息和公司的信息')
  if(baseline)await shot('before-chengdu-directory')
  await check('Longquanyi conflict does not inherit Tianfu HTTP 502 claim',async()=>{
    assert.equal(await inspect(`document.querySelector('#regional-submit').textContent.includes('HTTP 502')`),false)
    assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
  })
  await check('All 23 officially discovered Chengdu areas selectable with honest pending state',async()=>{
    assert.equal(await inspect(`document.querySelectorAll('#known-districts option').length`),23)
    const s=await snapshot();if(s.includes('查看成都全部'))await click('查看成都全部')
    const options=await inspect(`Array.from(document.querySelector('[aria-label="选择成都区县"]').options).map(x=>({value:x.value,text:x.textContent}))`)
    assert.equal(options.filter(x=>x.value).length,23)
    assert(options.some(x=>x.value==='青羊区'&&x.text.includes('待核验')))
    await shot(baseline?'before-directory-state':'after-chengdu-directory')
  })
  if(!baseline){
    for(const g of locals){
      await check(`${g.district}: own source, default form, real application and evidence generation`,async()=>{
        await go(scope(g.district));await wait('你的信息和公司的信息')
        const source=crypto.createHash('sha256').update(JSON.stringify(g.source_url)).digest('hex').slice(0,24)
        assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),source)
        assert.equal(await inspect(`document.querySelector('.selector-panel').nextElementSibling.id`),'document-workspace')
        assert.equal(await inspect(`document.querySelectorAll('#document-workspace input').length`),16)
        assert.equal(await inspect(`Array.from(document.querySelectorAll('#document-workspace input,#document-workspace textarea')).every(x=>x.value.trim())`),true)
        await click('button "生成并下载仲裁申请书"');await wait('确认生成仲裁申请书？')
        await click('button "取消"')
        assert(!(await tool('list_network_requests',{resourceTypes:['fetch']})).includes('POST'))
        await click('button "生成并下载仲裁申请书"');await click('button "确认生成"');await wait('文书已生成并下载')
        await generated(g,'application')
        await click('button "证据清单"');await wait('添加你的证据')
        assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
        await click('button "生成并下载证据清单"');await click('button "确认生成"');await wait('文书已生成并下载')
        await generated(g,'evidence')
        assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),g.channel.online_status==='auth_required')
        assert.equal(await inspect(`document.querySelector('[data-field="handling-form"]').textContent`),g.fields['办理形式'].raw_value)
        const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
      })
    }
    await check('Responsive 320/375/768/1024/1440 and landscape, no overflow',async()=>{
      for(const [w,h] of [[320,850],[375,812],[768,1024],[1024,768],[1440,1000],[812,375]]){
        await tool('emulate',{viewport:`${w}x${h}x1`})
        assert.equal(await inspect(`innerWidth`),w)
        assert.equal(await inspect(`document.documentElement.scrollWidth<=innerWidth`),true)
        await shot(`chengdu-${w}x${h}`)
      }
      await tool('emulate',{viewport:'1440x1000x1'})
    })
    await check('District selector switches source and unknown Qingyang does not inherit',async()=>{
      await go(scope('金牛区'));await wait('你的信息和公司的信息')
      await click('查看成都全部')
      await tool('fill',{uid:await uid('combobox "选择成都区县"'),value:'双流区 · 可填写生成'})
      await wait('官网明确列出网上办理')
      assert.equal(await inspect(`document.querySelector('[data-region-code]').dataset.regionCode`),'510116000000')
      await shot('district-switch-shuangliu')
      await tool('fill',{uid:await uid('combobox "选择成都区县"'),value:'青羊区 · 待核验'})
      await wait('该地区办事指南尚未核验')
      assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      assert((await snapshot()).includes('不代表所选区县的模板已经核验'))
      await shot('qingyang-unverified')
    })
    await check('Source downloads and public issue evidence are live',async()=>{
      const api='http://127.0.0.1:8000/api/regional-guides'
      const inventory=await (await fetch(api+'/inventory')).json()
      assert.equal(inventory.items.length,22);assert.equal(new Set(inventory.items.map(x=>x.source_id)).size,22)
      for(const g of locals){
        const t=g.templates.find(t=>t.original_name==='仲裁申请书(模板).docx')
        const r=await fetch(api+'/templates/'+t.id+'?'+new URLSearchParams({province:'sichuan',city:'成都市',district:g.district}))
        assert.equal(r.status,200)
        assert.equal(crypto.createHash('sha256').update(Buffer.from(await r.arrayBuffer())).digest('hex'),t.sha256)
      }
      const r=await fetch(api+'/evidence/reports/chengdu-district-expansion-20261023/captures/510106000000/materials.png')
      assert.equal(r.status,200)
      await go('/admin/regions');await wait('可追溯的问题报告');await shot('openclaw-pending-report')
      assert((await snapshot()).includes('PENDING_OPENCLAW'))
    })
    await check('No model or private case requests',async()=>{
      const net=await tool('list_network_requests',{includePreservedRequests:true,pageSize:1000})
      assert(!/11434|ollama|\/api\/chat|\/api\/platform\/cases/.test(net))
    })
  }
}finally{
  fs.writeFileSync(path.join(output,baseline?'BROWSER-BEFORE.json':'BROWSER-RESULTS.json'),JSON.stringify({at:new Date().toISOString(),checks},null,2));close()
}
if(checks.some(x=>!x.passed))process.exitCode=1
