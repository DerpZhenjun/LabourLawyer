/** Exact-source batch acceptance against the real Chrome DevTools MCP. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {call,close} from './ui-devtools-session.mjs'
const night=path.resolve('reports/nationwide-localization-20261023-night')
const base=process.env.SITE_BASE||'http://127.0.0.1:5174',pageId=2,checks=[]
assert(process.env.BATCH_UI_OUTPUT&&process.env.REGION_CODES,'Explicit batch output and codes required')
const out=path.resolve(process.env.BATCH_UI_OUTPUT),codes=process.env.REGION_CODES.split(',')
assert(out.startsWith(path.join(night,'batches')+path.sep)&&codes.every(c=>/^\d{12}$/.test(c)))
fs.mkdirSync(path.join(out,'requests'),{recursive:true})
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!result.isError,JSON.stringify(result.content));return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const result=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(result.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(x=>x.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const click=async text=>tool('click',{uid:await uid(text)})
const scope=g=>'/province/sichuan?'+new URLSearchParams({city:g.city,district:g.district})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
const guides=codes.map(code=>JSON.parse(fs.readFileSync(path.join(night,'sichuan/captures',code,'guide.json'),'utf8')))
const sid=g=>crypto.createHash('sha256').update(JSON.stringify(g.source_url)).digest('hex').slice(0,24)
try{
  await tool('new_page',{url:base,isolatedContext:'night-own-locality-batch'})
  if(process.argv.includes('--baseline')){
    await tool('navigate_page',{type:'url',url:base+scope(guides[0])});await wait('该地区办事指南尚未核验')
    await tool('take_screenshot',{filePath:path.join(out,'before.png'),fullPage:false})
    assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
  }else{
    assert.equal(new Set(guides.map(sid)).size,guides.length,'Every locality needs its own source')
    for(const g of guides){
      await check(`${g.city}/${g.district}: own source, materials, channel and two actual generation POSTs`,async()=>{
        await tool('navigate_page',{type:'url',url:base+scope(g)});await wait('你的信息和公司的信息')
        assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),sid(g))
        assert.equal(await inspect(`document.querySelector('[data-region-code]').dataset.regionCode`),g.region_code)
        assert((await inspect(`document.querySelector('.region-authority').textContent`)).includes(g.authority))
        assert.equal(await inspect(`document.querySelector('[data-field="handling-form"]').textContent.trim()`),g.fields['办理形式'].raw_value)
        const facts=await inspect(`Array.from(document.querySelectorAll('.guide-facts dd')).map(e=>e.textContent.trim())`)
        assert.equal(facts[1],g.fields['承诺办结时限']?.raw_value||'待核实')
        assert.equal(facts[2],g.fields['是否收费']?.raw_value||'待核实')
        assert.equal(await inspect(`document.querySelector('.guide-source a').href`),g.source_url)
        assert.equal(await inspect(`document.querySelectorAll('#regional-materials .regional-material').length`),g.materials.length)
        const rows=await inspect(`Array.from(document.querySelectorAll('#regional-materials .material-top')).map(e=>e.textContent)`)
        g.materials.forEach((m,i)=>{assert(rows[i].includes(m.name));assert(rows[i].includes(m.copies+' 份'));for(const value of [m.required,m.original_copy,m.format].filter(Boolean))assert(rows[i].includes(value))})
        const windowFacts=await inspect(`Array.from(document.querySelectorAll('#regional-submit .window-details dd')).map(e=>e.textContent.trim())`)
        if(g.fields['必须到现场原因']?.raw_value)assert(windowFacts.includes(g.fields['必须到现场原因'].raw_value))
        if(g.channel.online_status==='auth_required')assert.equal(await inspect(`document.querySelector('[data-online-entry]').href`),g.channel.entry_url)
        else if(g.channel.online_status==='unavailable')assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
        else if(g.channel.online_status==='conflict'){
          assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
          assert((await inspect(`document.querySelector('[data-channel-state="conflict"]').textContent`)).includes('官网不同栏目说法不一致'))
        }
        assert((await inspect(`document.querySelector('.reference-source-note summary').textContent`)).includes('非空白模板'))
        assert(await inspect(`Array.from(document.querySelectorAll('#document-workspace input')).filter(e=>e.value.trim()).length>=10`))
        for(const kind of ['application','evidence']){
          const title=kind==='application'?'仲裁申请书':'证据清单'
          if(kind==='evidence'){
            await tool('press_key',{key:'Control+Home'});await click('button "证据清单"');await wait('添加你的证据')
            assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
          }
          await click(`button "生成并下载${title}"`);await wait(`确认生成${title}？`)
          if(g===guides[0]&&kind==='application'){
            await tool('press_key',{key:'Escape'})
            assert.equal(await inspect(`!!document.querySelector('[role="dialog"]')`),false)
            assert.equal(await inspect(`document.activeElement.textContent.trim()`),'生成并下载仲裁申请书')
            await click(`button "生成并下载${title}"`);await wait(`确认生成${title}？`)
          }
          await click('button "确认生成"');await wait('文书已生成并下载')
          const requests=await tool('list_network_requests',{resourceTypes:['fetch']})
          const line=requests.split('\n').filter(x=>x.includes('POST')&&x.includes('/generate')).at(-1)
          assert(line?.includes('[200]'),requests)
          const file=path.join(out,'requests',`${g.region_code}-${kind}.network-request`)
          const response=await tool('get_network_request',{reqid:Number(line.match(/reqid=(\d+)/)[1]),requestFilePath:file})
          assert(response.includes('x-document-origin:official-sample-adaptation-not-blank'),response)
          const payload=JSON.parse(fs.readFileSync(file,'utf8'))
          assert.equal(payload.source_id,sid(g));assert.equal(payload.city,g.city);assert.equal(payload.district,g.district)
          assert.equal(payload.kind,kind);assert.equal(payload.mode,'reference_adaptation')
          assert.equal(payload.template_id,g.templates.find(t=>t.original_name==='仲裁申请书(模板).docx').id)
        }
        await tool('press_key',{key:'Control+Home'});await tool('take_screenshot',{filePath:path.join(out,g.region_code+'-form.png'),fullPage:false})
        await click('link "准备材料"');await tool('take_screenshot',{filePath:path.join(out,g.region_code+'-materials.png'),fullPage:false})
        if(g.channel.online_status==='unavailable'){
          await click('link "怎样提交"')
          assert((await inspect(`document.querySelector('[data-channel-state="unavailable"]').textContent`)).includes('窗口办理'))
          await tool('take_screenshot',{filePath:path.join(out,g.region_code+'-window-only.png'),fullPage:false})
        }
        if(g.channel.online_status==='conflict'){
          await click('link "怎样提交"')
          await tool('take_screenshot',{filePath:path.join(out,g.region_code+'-channel-conflict.png'),fullPage:false})
        }
        const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
      })
    }
    await check('375/768/1440 responsive form',async()=>{
      for(const width of [375,768,1440]){
        await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'})
        assert(await inspect(`document.documentElement.scrollWidth<=window.innerWidth`))
        await tool('take_screenshot',{filePath:path.join(out,`responsive-${width}.png`),fullPage:false})
      }
    })
    await check('Actual district switch replaces source and own institution',async()=>{
      if(guides[0].city!==guides.at(-1).city){
        await tool('fill',{uid:await uid('combobox "办理城市"'),value:guides[0].city})
        await wait('请选择城市和区县')
        assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      }
      await tool('fill',{uid:await uid('combobox "办理区县"'),value:guides[0].district});await wait('办理机关：'+guides[0].authority)
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),sid(guides[0]))
      assert.notEqual(sid(guides[0]),sid(guides.at(-1)))
    })
    await check('Unverified functional area never inherits a guide or online channel',async()=>{
      await tool('fill',{uid:await uid('combobox "办理区县"'),value:'未核验测试功能区'});await wait('该地区办事指南尚未核验')
      assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
      await tool('take_screenshot',{filePath:path.join(out,'unverified.png'),fullPage:false})
    })
    await check('No model inference requests',async()=>{
      const net=await tool('list_network_requests');assert(!/11434|\/api\/chat|\/api\/tts|\/api\/ask/.test(net))
    })
    if(base==='http://127.0.0.1:5173')await check('Public collection report includes the own districts and honestly pending OpenClaw',async()=>{
      await tool('navigate_page',{type:'url',url:base+'/admin/regions'});await wait('OpenClaw 实际状态')
      const text=await inspect(`document.querySelector('.collection-page').textContent`)
      for(const g of guides){assert(text.includes(g.city+' / '+g.district));assert(text.includes(sid(g)))}
      assert(text.includes('PENDING_OPENCLAW'));assert(text.includes('不能把本地报告称为 OpenClaw 已接收'))
      await tool('take_screenshot',{filePath:path.join(out,'public-openclaw-report.png'),fullPage:false})
      const net=await tool('list_network_requests');assert(!/11434|\/api\/chat|\/api\/tts|\/api\/ask/.test(net))
    })
  }
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),base,codes,checks,failed:checks.filter(x=>!x.passed).length},null,2));close()}
if(checks.some(x=>!x.passed))process.exitCode=1
