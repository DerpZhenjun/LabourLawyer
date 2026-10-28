/** Actual MCP rendering of own functional-area source; no application submission. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {createHash} from 'node:crypto'
import {call,close} from './ui-devtools-session.mjs'
const base=process.env.SITE_BASE||'http://127.0.0.1:5174',api=process.env.TEST_API_BASE||'http://127.0.0.1:8001'
const out=path.resolve(process.env.ECO_UI_OUTPUT),checks=[],pageId=2
assert(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!result.isError,JSON.stringify(result.content));return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const r=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(r.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(label){const snap=await tool('take_snapshot');const line=snap.split('\n').find(x=>x.includes(label));assert(line,`Missing ${label}`);return line.match(/uid=(\S+)/)[1]}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const navigate=(province,city,district)=>tool('navigate_page',{type:'url',url:`${base}/province/${province}?`+new URLSearchParams({city,district})})
const check=async(name,fn)=>{try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  let ready=false
  for(let i=0;i<40&&!ready;i++){
    try{const g=await(await fetch(api+'/api/regional-guides/lookup?'+new URLSearchParams({province:'tianjin',city:'天津市',district:'中新天津生态城'}),{signal:AbortSignal.timeout(1000)})).json();ready=g.source_id==='9da523e907f1e26a9f0fb9ce'&&g.materials.length===5}catch{}
    if(!ready)await new Promise(r=>setTimeout(r,500))
  }
  assert(ready,'Own staged guide must be ready')
  await tool('new_page',{url:base,isolatedContext:'eco-city-exact-functional-area'})
  await check('Own functional area is partial, not all Tianjin or an official admin code',async()=>{
    await navigate('tianjin','天津市','中新天津生态城');await wait('劳动争议仲裁申请')
    assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),'9da523e907f1e26a9f0fb9ce')
    assert((await inspect('document.body.innerText')).includes('平台内部识别码'))
    await tool('take_screenshot',{filePath:path.join(out,'own-guide.png'),fullPage:false})
  })
  await check('Actual window address hours and both conflicting phone sources are visible',async()=>{
    const txt=await inspect(`document.querySelector('.verified-guide').innerText`)
    for(const value of ['中新友好图书馆B5','13：30','022-66179792','022-66328970','部分内容待核实'])assert(txt.includes(value),value)
    assert(txt.includes('待核实'),'Absent deadline must stay unknown')
  })
  await check('Explicitly unavailable online channel never becomes an online apply button',async()=>{
    assert.equal(await inspect(`document.querySelector('[data-channel-state]').dataset.channelState`),'unavailable')
    assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
    await tool('click',{uid:await uid('link "怎样提交"')})
    await tool('take_screenshot',{filePath:path.join(out,'window-only.png'),fullPage:false})
  })
  await check('Five own materials and two distinct raw original downloads, no unapproved generator',async()=>{
    assert.equal(await inspect(`document.querySelectorAll('.regional-material').length`),5)
    assert.equal(await inspect(`document.querySelectorAll('.regional-template').length`),2)
    assert.equal(await inspect(`document.querySelectorAll('#document-workspace input').length`),0)
    const originalLinks=await inspect(`Array.from(document.querySelectorAll('.regional-template > a')).map(a=>({href:a.href,text:a.textContent}))`)
    assert.equal(originalLinks.length,2)
    for(const [i,filename] of ['110943177zze.doc','081434099aia.docx'].entries()){
      assert(originalLinks[i].href.includes(filename))
      const response=await fetch(originalLinks[i].href);assert.equal(response.status,200)
      const sha=createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex')
      assert.equal(sha,i===0?'2257fa08781ece314f4d1c595f68478c8495b4882a528501dcf78ff5f1f5c825':'929229327433e0457b4a4fbdf4dc11551dbebc6156278b3e5fd22d025ff8a556')
    }
    await tool('click',{uid:await uid('link "准备材料"')})
    await tool('take_screenshot',{filePath:path.join(out,'own-materials.png'),fullPage:false})
    await tool('click',{uid:await uid('link "文书与下载"')})
    await tool('take_screenshot',{filePath:path.join(out,'own-original-downloads.png'),fullPage:false})
  })
  await check('375 768 1440 responsive layouts do not overflow',async()=>{
    for(const width of [375,768,1440]){
      await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'})
      assert(await inspect(`document.documentElement.scrollWidth<=window.innerWidth`),`${width}px`)
      await tool('take_screenshot',{filePath:path.join(out,`responsive-${width}.png`),fullPage:false})
    }
  })
  await check('Actual district input switch clears own guide rather than giving all Binhai these rules',async()=>{
    await tool('fill',{uid:await uid('combobox "办理区县"'),value:'滨海新区'})
    await wait('该地区办事指南尚未核验')
    assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
    assert.equal(await inspect(`!!document.querySelector('#regional-materials')`),false)
    await tool('take_screenshot',{filePath:path.join(out,'neighbour-unverified.png'),fullPage:false})
  })
  await check('Approved Jianhu own blank forms and source remain distinct',async()=>{
    await navigate('jiangsu','盐城市','建湖县');await wait('你的信息和公司的信息')
    assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),'ef1eb897ebf880c6f2a316f5')
    assert((await inspect(`document.querySelector('.reference-source-note summary').textContent`)).includes('官方空白表格'))
  })
  await check('Console and network contain no warnings errors or model calls',async()=>{
    const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
    const net=await tool('list_network_requests');assert(!/11434|\/api\/chat|\/api\/tts/.test(net))
  })
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),base,checks,failed:checks.filter(x=>!x.passed).length},null,2));close()}
if(checks.some(c=>!c.passed))process.exitCode=1
