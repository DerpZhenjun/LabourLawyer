/** Existing, operator-started candidate site only. No services or models are launched. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const base='http://127.0.0.1:5174',api='http://127.0.0.1:8001/api/regional-guides'
const out=path.resolve(process.env.CANDIDATE_UI_OUTPUT||'.runtime/candidate-browser-20261029/root-a-01'),checks=[],downloads=[]
assert(!fs.existsSync(out),'Preserve previous acceptance evidence; choose a new output directory')
fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId:2,...args});assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
async function read(expression){const r=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(r.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function until(expression){for(let n=0;n<70;n++){if(await read(expression))return;await new Promise(r=>setTimeout(r,300))}throw Error('Candidate state timed out: '+expression)}
async function uid(label){const s=await tool('take_snapshot');const line=s.split('\n').find(l=>l.includes(label));assert(line,label);return line.match(/uid=(\S+)/)[1]}
const click=async label=>tool('click',{uid:await uid(label)})
const fill=async(label,value)=>tool('fill',{uid:await uid(label),value})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(error){checks.push({name,passed:false,error:error.message});throw error}}
async function lookup(province,city,district){const r=await fetch(api+'/lookup?'+new URLSearchParams({province,city,district}));assert(r.ok);return r.json()}
async function go(g){await tool('navigate_page',{type:'url',url:base+`/province/${g.province}?`+new URLSearchParams({city:g.city,district:g.district})});await until(`document.querySelector('[data-source-id]')?.dataset.sourceId===${JSON.stringify(g.source_id)}`)}
async function capturePost(g,kind){
 const requests=await tool('list_network_requests',{resourceTypes:['fetch']})
 const last=requests.split('\n').filter(l=>l.includes('POST')&&l.includes('/generate')).at(-1);assert(last?.includes('[200]'),requests)
 const prefix=path.join(out,g.region_code+'-'+kind)
 const detail=await tool('get_network_request',{reqid:Number(last.match(/reqid=(\d+)/)[1]),requestFilePath:prefix+'.network-request',responseFilePath:prefix+'.network-response'})
 const payload=JSON.parse(fs.readFileSync(prefix+'.network-request','utf8'))
 assert.equal(payload.source_id,g.source_id);assert.equal(payload.district,g.district);assert.equal(payload.kind,kind)
 assert(detail.toLowerCase().includes('x-document-origin:official-blank-filled'),detail)
 assert(detail.includes(g.source_id))
 const bytes=fs.readFileSync(prefix+'.network-response');const binary=bytes.subarray(0,2).toString()==='PK'
 if(binary)fs.copyFileSync(prefix+'.network-response',prefix+'-actual-browser.docx')
 downloads.push({district:g.district,kind,source_id:g.source_id,bytes:bytes.length,file:prefix+'-actual-browser.docx',origin:binary?'actual_browser_post_response':'browser_http_only_binary_unverified',byte_validation_complete:binary})
}
try{
 const ai=await fetch('http://127.0.0.1:8001/api/ai/status').then(r=>r.json());assert.equal(ai.ready,false);assert.equal(ai.local_model_started,false)
 const all=await fetch(api+'/inventory').then(r=>r.json());assert.equal(all.items.length,188)
 const locals=await Promise.all([lookup('zhejiang','宁波市','海曙区'),lookup('zhejiang','宁波市','鄞州区'),lookup('anhui','合肥市','肥东县'),lookup('anhui','合肥市','瑶海区'),lookup('sichuan','成都市','青羊区')])
 await tool('new_page',{url:base,isolatedContext:'oct29-a-own-candidate-only'})
 for(const g of locals.slice(0,3)){
  await go(g)
  await check(g.district+' source, local materials and form-first layout',async()=>{
   assert.equal(await read(`document.querySelector('.selector-panel').nextElementSibling.id`),'document-workspace')
   assert(await read(`document.querySelector('#document-workspace form').textContent.includes('虚构示例')`))
   assert.equal(await read(`document.querySelectorAll('#regional-materials .regional-material').length`),g.materials.length)
   assert.equal(await read(`document.querySelector('[data-field="handling-form"]').textContent.trim()`),g.fields['办理形式']?.raw_value || '待核实')
  })
  if(g.region_code==='340122')await check('Feidong overflow is explained before confirmation; no text is cropped',async()=>{
   await fill('textbox "申请人第1行"','字'.repeat(21));await click('button "生成并下载仲裁申请书"')
   assert.equal(await read(`!!document.querySelector('.reference-dialog')`),false)
   assert(await read(`document.querySelectorAll('.feidong-error').length>0`))
   await fill('textbox "申请人第1行"','虚构候选验收劳动者')
  })
  else await fill('textbox "你的姓名"','虚构候选验收劳动者')
  await check(g.district+' cancellation and actual application HTTP request',async()=>{
   await click('button "生成并下载仲裁申请书"');await click('button "取消"')
   assert.equal(await read(`!!document.querySelector('.reference-dialog')`),false)
   await click('button "生成并下载仲裁申请书"');await tool('press_key',{key:'Escape'})
   assert.equal(await read(`!!document.querySelector('.reference-dialog')`),false)
   await click('button "生成并下载仲裁申请书"');await click('button "确认生成"')
   await until(`document.querySelector('#document-workspace form').textContent.includes('文书已生成并下载')`)
   await capturePost(g,'application')
  })
  if(g.province==='zhejiang')await check(g.district+' one evidence row, add/remove and actual evidence HTTP request',async()=>{
   await click('button "证据清单"');await until(`document.querySelectorAll('#document-workspace .regional-material').length===1`)
   await click('button "添加一项证据"');assert.equal(await read(`document.querySelectorAll('#document-workspace .regional-material').length`),2)
   await click('button "删除第2项证据"');assert.equal(await read(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
   await fill('textbox "材料名称"','虚构候选证据');await click('button "生成并下载证据清单"');await click('button "确认生成"')
   await until(`document.querySelector('#document-workspace form').textContent.includes('文书已生成并下载')`);await capturePost(g,'evidence')
  })
 }
 await check('Ningbo district switch replaces source instead of inheriting the last one',async()=>{
  await go(locals[0]);await fill('combobox "办理区县"','鄞州区')
  await until(`document.querySelector('[data-source-id]')?.dataset.sourceId===${JSON.stringify(locals[1].source_id)}`)
  assert.notEqual(locals[0].source_id,locals[1].source_id)
 })
 for(const g of locals.slice(3))await check(g.district+' own guide does not falsely expose an unadapted generator',async()=>{
  await go(g);assert.equal(await read(`!!document.querySelector('#document-workspace form')`),false)
  assert.equal(await read(`!!document.querySelector('[data-generate]')`),false)
  if(g.district==='青羊区')assert.equal(await read(`!!document.querySelector('[data-online-entry]')`),false)
 })
 await go(locals[2])
 for(const width of [375,768,1440])await check('Candidate Feidong form responsive '+width,async()=>{
  await tool('emulate',{viewport:`${width}x1000x1`});assert(await read(`document.documentElement.scrollWidth<=innerWidth`))
  await tool('press_key',{key:'Control+Home'});await tool('take_screenshot',{filePath:path.join(out,`candidate-${width}.png`)})
 })
 await check('Candidate console and network contain no model inference',async()=>{
  assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
  assert(!/11434|\/api\/chat|\/api\/ask|\/api\/tts/.test(await tool('list_network_requests')))
 })
}catch(error){checks.push({name:'acceptance',passed:false,error:error.message});console.error(error);process.exitCode=1}
finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({checked_at:new Date().toISOString(),base,candidate_acceptance:true,checks,downloads,failed:checks.filter(c=>!c.passed).length},null,2));close()}
