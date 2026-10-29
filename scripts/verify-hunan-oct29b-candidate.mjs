/** Native Chrome DevTools checks against the already operator-started test site. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve(process.env.HUNAN_UI_OUTPUT||'.runtime/candidate-browser-20261029/hunan-mcp'),results=[]
assert(!fs.existsSync(out),'Preserve earlier evidence');fs.mkdirSync(out,{recursive:true})
let pageId
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
async function read(expression){const r=await tool('evaluate_script',{function:`()=>(${expression})`});return JSON.parse(r.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function control(name,role){const s=await tool('take_snapshot');const l=s.split('\n').find(x=>x.includes(`${role} "${name}"`));assert(l,name);return l.match(/uid=(\S+)/)[1]}
const click=async name=>tool('click',{uid:await control(name,'button')})
async function check(name,fn){await fn();results.push({name,passed:true});console.log('PASS '+name)}
try{
 const p=await tool('new_page',{url:'http://127.0.0.1:5174/',isolatedContext:'hunan-oct29b-acceptance'});pageId=Number(p.split('\n').find(l=>l.includes('[selected]')).match(/^(\d+):/)[1])
 const ai=await fetch('http://127.0.0.1:8001/api/ai/status').then(r=>r.json());assert.equal(ai.ready,false)
 for(const district of ['天心区','岳麓区']){
  const query=new URLSearchParams({province:'hunan',city:'长沙市',district})
  const g=await fetch('http://127.0.0.1:8001/api/regional-guides/lookup?'+query).then(r=>r.json());assert(g.source_id)
  await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5174/province/hunan?'+new URLSearchParams({city:'长沙市',district})})
  await tool('wait_for',{text:['附随证据说明是申请书的一部分'],timeout:20000})
  await check(district+' exact source, form-first, own four materials and no invented ID slot',async()=>{
   assert.equal(await read(`document.querySelector('[data-source-id]').dataset.sourceId`),g.source_id)
   assert.equal(await read(`document.querySelector('.selector-panel').nextElementSibling.id`),'document-workspace')
   assert.equal(await read(`document.querySelectorAll('#regional-materials .regional-material').length`),4)
   assert.equal(await read(`document.querySelectorAll('.hunan-application-fields input[id*="idNumber"]').length`),0)
   assert(await read(`document.querySelector('.hunan-application-fields').textContent.includes('虚构示例')`))
   assert(await read(`document.querySelectorAll('.hunan-evidence-item').length===1`))
  })
  await check(district+' embedded evidence add/remove, confirmation cancel and converted DOC origin',async()=>{
   const before=await read(`document.querySelectorAll('.hunan-evidence-item').length`)
   await click('添加附随证据')
   // Native add/remove is also covered by the mounted contract tests; inspect the resulting live labels.
   assert.equal(await read(`document.querySelectorAll('.hunan-evidence-item').length`),before+1)
   await click('删除第2项附随证据');assert.equal(await read(`document.querySelectorAll('.hunan-evidence-item').length`),before)
   await click('添加附随证据')
   await click('生成并下载仲裁申请书');await click('取消')
   assert.equal(await read(`!!document.querySelector('[role="dialog"]')`),false)
   await click('生成并下载仲裁申请书');await tool('press_key',{key:'Escape'})
   assert.equal(await read(`!!document.querySelector('[role="dialog"]')`),false)
   await click('生成并下载仲裁申请书');await click('确认生成')
   await tool('wait_for',{text:['文书已生成并下载'],timeout:20000})
   const requests=await tool('list_network_requests',{pageSize:1000})
   const line=requests.split('\n').filter(l=>l.includes('POST')&&l.includes('/generate')&&l.includes('[200]')).at(-1);assert(line)
   const detail=await tool('get_network_request',{reqid:Number(line.match(/reqid=(\d+)/)[1])})
   assert(detail.includes('official-blank-converted-filled'));fs.writeFileSync(path.join(out,g.region_code+'-http-detail.txt'),detail);const file=path.join(out,g.region_code+'-request.json');const body=fs.existsSync(file)?fs.readFileSync(file,'utf8'):detail.match(/### Request Body\r?\n([\s\S]*?)(?=\n###|$)/i)?.[1];assert(body,'Actual browser request body unavailable');const payload=JSON.parse(body.trim());fs.writeFileSync(file,JSON.stringify(payload,null,2))
   assert.equal(payload.source_id,g.source_id);assert.equal('idNumber' in payload.data,false)
   assert.equal(payload.kind,'application');assert.equal(payload.data.evidenceList.length,2)
  })
  for(const width of [375,768,1440])await check(district+' responsive '+width,async()=>{
   await tool('emulate',{viewport:`${width}x1000x1`});assert(await read('document.documentElement.scrollWidth<=innerWidth'))
   await tool('press_key',{key:'Control+Home'});await tool('take_screenshot',{filePath:path.join(out,g.region_code+'-'+width+'.png')})
  })
 }
 await check('console clean; no model inference',async()=>{
  assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
  assert(!/\/api\/ask|11434|\/api\/chat/.test(await tool('list_network_requests',{pageSize:1000})))
 })
}catch(error){results.push({passed:false,error:error.message});console.error(error);process.exitCode=1}
finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({results,binary_validation:false,models_called:false},null,2));close()}
