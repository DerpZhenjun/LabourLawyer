/** Own blank forms, sample distinction, exact regions and real browser POSTs. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const base=process.env.SITE_BASE||'http://127.0.0.1:5174',pageId=2,checks=[]
const out=path.resolve('reports/nationwide-localization-20261023-night/cross-province/jiangsu-xishan/browser',process.env.UI_RUN||'staging')
fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!result.isError,JSON.stringify(result.content));return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const result=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(result.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(x=>x.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const click=async text=>tool('click',{uid:await uid(text)})
const navigate=(province,city,district)=>tool('navigate_page',{type:'url',url:`${base}/province/${province}?`+new URLSearchParams({city,district})})
async function downloadGenerated(kind,expectedId,expectedMode,sourceId){
  const title=kind==='application'?'仲裁申请书':'证据清单'
  await click(`button "生成并下载${title}"`);await wait(`确认生成${title}？`)
  const description=await inspect(`document.querySelector('#reference-description').textContent`)
  assert(expectedMode==='blank'?description.includes('官网提供的空白表格')&&!description.includes('不是官方空白模板'):description.includes('不是官方空白模板'),description)
  await click('button "确认生成"');await wait('文书已生成并下载')
  const requests=await tool('list_network_requests',{resourceTypes:['fetch']})
  const line=requests.split('\n').filter(x=>x.includes('POST')&&x.includes('/generate')).at(-1)
  assert(line?.includes('[200]'),requests)
  const file=path.join(out,`${sourceId}-${kind}.network-request`)
  await tool('get_network_request',{reqid:Number(line.match(/reqid=(\d+)/)[1]),requestFilePath:file})
  const payload=JSON.parse(fs.readFileSync(file,'utf8'))
  assert.equal(payload.source_id,sourceId);assert.equal(payload.template_id,expectedId);assert.equal(payload.mode,expectedMode)
  assert.equal(payload.kind,kind)
  if(expectedMode==='blank'&&kind==='evidence')assert.equal(payload.data.evidenceList[0].source,'本人保存')
  return payload
}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:base,isolatedContext:'xishan-own-blank-acceptance'})
  await check('Own Xishan blank source is not labelled as a sample',async()=>{
    await navigate('jiangsu','无锡市','锡山区');await wait('你的信息和公司的信息')
    await tool('take_screenshot',{filePath:path.join(out,'source-and-form.png'),fullPage:false})
    assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),'b1f8ab307b0a4f634081c052')
    const note=await inspect(`document.querySelector('.reference-source-note summary').textContent`)
    assert(note.includes('官方空白表格')&&!note.includes('非空白模板'),note)
  })
  await check('Own form fields, default examples and cancellable accessible confirmation',async()=>{
    assert(await inspect(`Array.from(document.querySelectorAll('#document-workspace input')).filter(e=>e.value.trim()).length>=10`))
    await click('补充表格中的其他信息')
    assert(await inspect(`Array.from(document.querySelectorAll('#document-workspace label')).some(e=>e.textContent.includes('是否接受调解'))`))
    await click('button "生成并下载仲裁申请书"');await wait('确认生成仲裁申请书？')
    assert(await inspect(`document.querySelector('[role="dialog"]').contains(document.activeElement)`))
    await tool('press_key',{key:'Escape'})
    assert.equal(await inspect(`!!document.querySelector('[role="dialog"]')`),false)
    assert.equal(await inspect(`document.activeElement.textContent.trim()`),'生成并下载仲裁申请书')
    await downloadGenerated('application','e1ae7409-3195-4eeb-aace-c9de16282335','blank','b1f8ab307b0a4f634081c052')
  })
  await check('Evidence starts with one entry, adds/removes and generates the own six-column form',async()=>{
    await tool('press_key',{key:'Control+Home'});await click('button "证据清单"');await wait('添加你的证据')
    assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
    assert(await inspect(`Array.from(document.querySelectorAll('#document-workspace label')).some(e=>e.textContent.includes('材料从哪里取得'))`))
    await click('button "添加一项证据"')
    assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),2)
    await click('button "删除第2项证据"')
    assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
    await downloadGenerated('evidence','2d7b1fe9-8bdb-4e9b-b0ef-7616a6b87c97','blank','b1f8ab307b0a4f634081c052')
    await tool('take_screenshot',{filePath:path.join(out,'evidence-generated.png'),fullPage:false})
  })
  await check('Guide shows own method, four material counts, eight original downloads and actual login boundary',async()=>{
    assert.equal(await inspect(`document.querySelector('[data-region-code]').dataset.regionCode`),'320205')
    assert.equal(await inspect(`document.querySelector('[data-field="handling-form"]').textContent.trim()`),'窗口办理,网上办理,快递申请')
    assert.equal(await inspect(`document.querySelectorAll('#regional-materials .regional-material').length`),4)
    const materials=await inspect(`Array.from(document.querySelectorAll('#regional-materials .material-top p')).map(e=>e.textContent.trim())`)
    for(const [i,n] of [2,2,1,4].entries())assert(materials[i].includes(`${n} 份`),materials[i])
    assert(await inspect(`document.querySelector('.guide-facts').textContent.includes('45')`))
    const entry=await inspect(`document.querySelector('[data-online-entry]').href`)
    assert(entry.startsWith('https://www.jszwfw.gov.cn/jsjis/front/login.do?'),entry)
    assert(await inspect(`document.querySelector('[data-channel-state="auth_required"]').textContent.includes('已停止操作')`))
    const snapshot=await tool('take_snapshot'),links=snapshot.split('\n').filter(x=>x.includes('link "下载原文件"'))
    assert.equal(links.length,8)
    for(const line of links)await tool('click',{uid:line.match(/uid=(\S+)/)[1]})
    const net=await tool('list_network_requests')
    const downloads=net.split('\n').filter(x=>x.includes('/templates/')&&x.includes('GET'))
    assert.equal(downloads.length,8,net);assert(downloads.every(x=>x.includes('[200]')),net)
    await click('link "准备材料"');await tool('take_screenshot',{filePath:path.join(out,'own-materials.png'),fullPage:false})
    await click('link "怎样提交"');await tool('take_screenshot',{filePath:path.join(out,'channel-login-boundary.png'),fullPage:false})
  })
  await check('375/768/1440 responsive layout and labelled form controls',async()=>{
    for(const width of [375,768,1440]){
      await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'})
      assert.equal(await inspect(`document.documentElement.scrollWidth<=window.innerWidth`),true,`${width}px horizontal overflow`)
      assert.equal(await inspect(`Array.from(document.querySelectorAll('#document-workspace input,#document-workspace textarea,#document-workspace select')).filter(e=>!e.closest('label')&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby')).length`),0)
      await tool('take_screenshot',{filePath:path.join(out,`responsive-${width}.png`),fullPage:false})
      await click('textbox "材料名称"')
      await tool('take_screenshot',{filePath:path.join(out,`responsive-form-${width}.png`),fullPage:false})
    }
  })
  await check('Neighbour switch clears the source and never inherits Xishan requirements',async()=>{
    await tool('fill',{uid:await uid('combobox "办理区县"'),value:'惠山区'})
    await wait('该地区办事指南尚未核验')
    assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
    assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
    assert.equal(await inspect(`!!document.querySelector('#regional-materials')`),false)
    await tool('take_screenshot',{filePath:path.join(out,'neighbour-unverified.png'),fullPage:false})
  })
  await check('Sichuan sample path keeps its distinct source, mode and own channel',async()=>{
    await navigate('sichuan','自贡市','自流井区');await wait('你的信息和公司的信息')
    const sid=await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`)
    assert.notEqual(sid,'b1f8ab307b0a4f634081c052')
    assert((await inspect(`document.querySelector('.reference-source-note summary').textContent`)).includes('非空白模板'))
    const guide=JSON.parse(fs.readFileSync('reports/nationwide-localization-20261023-night/sichuan/captures/510302000000/guide.json','utf8'))
    assert.equal(await inspect(`document.querySelector('[data-online-entry]').href`),guide.channel.entry_url)
    const id=guide.templates.find(t=>t.original_name==='仲裁申请书(模板).docx').id
    await downloadGenerated('application',id,'reference_adaptation',sid)
  })
  await check('No browser warning/error or model inference request',async()=>{
    const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
    const net=await tool('list_network_requests');assert(!/11434|\/api\/chat|\/api\/tts/.test(net))
  })
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),base,checks,failed:checks.filter(x=>!x.passed).length},null,2));close()}
if(checks.some(x=>!x.passed))process.exitCode=1
