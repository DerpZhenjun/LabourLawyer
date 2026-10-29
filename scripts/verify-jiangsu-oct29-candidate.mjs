/** Real native Chrome DevTools candidate interactions; raw bodies remain in .runtime. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {spawnSync} from 'node:child_process'
import {call,close} from './ui-devtools-session.mjs'
const root=process.cwd(),output=path.resolve('reports/nationwide-verification-20261029/candidate-jiangsu'),raw=path.resolve('.runtime/candidate-browser-20261029/js')
fs.mkdirSync(output,{recursive:true});fs.mkdirSync(raw,{recursive:true})
const base='http://127.0.0.1:5174',api='http://127.0.0.1:8001/api/regional-guides',checks=[],regions=[],screenshots=[]
let pageId
const sha=b=>crypto.createHash('sha256').update(b).digest('hex')
async function tool(name,args={}){
 const a=name==='new_page'?args:{pageId,...args},r=await call(name,a)
 fs.appendFileSync(path.join(raw,'transcript.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args:a,result:{...r,content:r.content?.filter(c=>c.type!=='image')}})+'\n')
 assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')
}
const snapshot=()=>tool('take_snapshot')
async function uid(text){const s=await snapshot();const l=s.split('\n').find(l=>l.includes(text));assert(l,'Missing '+text);return l.match(/uid=(\S+)/)[1]}
const click=async text=>tool('click',{uid:await uid(text)})
const fill=async(text,value)=>tool('fill',{uid:await uid(text),value})
const wait=text=>tool('wait_for',{text:[text],timeout:15000})
async function read(expression){const r=await tool('evaluate_script',{function:`() => (${expression})`,waitForStableDom:false});const block=r.match(/```json\s*([\s\S]*?)\s*```/);assert(block,r);return JSON.parse(block[1])}
async function shot(name){const file=path.join(output,name+'.png');await tool('take_screenshot',{filePath:file,fullPage:true});screenshots.push(file)}
async function check(name,fn){try{const detail=await fn();checks.push({name,passed:true,...(detail?{detail}:{})});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message);throw e}}
const query=d=>new URLSearchParams({province:'jiangsu',city:'无锡市',district:d})
async function network(){return tool('list_network_requests',{pageSize:1000,includePreservedRequests:true})}
async function captureResponse(label,match){
 const n=await network(),line=n.split('\n').filter(l=>l.includes(match)&&l.includes('[200]')).at(-1);assert(line,'Missing actual browser 200 '+match)
 const reqid=Number(line.match(/reqid=(\d+)/)[1]),requestFilePath=path.join(raw,label+'.network-request'),responseFilePath=path.join(raw,label+'.network-response')
 const detail=await tool('get_network_request',{reqid,requestFilePath,responseFilePath});fs.writeFileSync(path.join(raw,label+'-metadata.txt'),detail)
 const body=fs.existsSync(responseFilePath)?fs.readFileSync(responseFilePath):null
 const binary=!!body&&body.subarray(0,2).toString()==='PK'
 if(binary)fs.copyFileSync(responseFilePath,path.join(raw,label+'.docx'))
 let request=null;if(fs.existsSync(requestFilePath)&&fs.statSync(requestFilePath).size){try{request=JSON.parse(fs.readFileSync(requestFilePath,'utf8'))}catch{}}
 if(!request){const b=detail.match(/### Request Body\r?\n([\s\S]*?)(?=\n###|$)/i);if(b){try{request=JSON.parse(b[1].trim())}catch{}}}
 return {reqid,status:200,detail,request,binary,bytes:body?.length||0,sha256:binary?sha(body):null,path:binary?path.join(raw,label+'.docx'):null}
}
function inspectDocx(file){
 const py="import json,sys,zipfile,xml.etree.ElementTree as E; z=zipfile.ZipFile(sys.argv[1]); r=E.fromstring(z.read('word/document.xml')); n={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}; print(json.dumps([''.join(p.itertext()) for p in r.findall('.//w:p',n)],ensure_ascii=True))"
 const r=spawnSync(path.join(root,'.venv/Scripts/python.exe'),['-c',py,file],{encoding:'utf8',windowsHide:true});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout)
}
async function cancelAndEscape(button,title){
 const before=(await network()).split('\n').filter(l=>l.includes('POST ')&&l.includes('/generate')).length
 await click(button);await wait('确认生成'+title+'？');await tool('press_key',{key:'Escape'});assert.equal(await read(`!!document.querySelector('[role="dialog"]')`),false)
 await click(button);await wait('确认生成'+title+'？');await click('button "取消"');assert.equal(await read(`!!document.querySelector('[role="dialog"]')`),false)
 const after=(await network()).split('\n').filter(l=>l.includes('POST ')&&l.includes('/generate')).length;assert.equal(after,before)
}
try{
 const p=await tool('new_page',{url:base,isolatedContext:'jiangsu-candidate-script-20261029'});pageId=Number(p.split('\n').find(l=>l.includes('[selected]')).match(/^(\d+):/)[1]);assert(pageId)
 await tool('emulate',{viewport:'1440x900x1'})
 await click('link "文书 + 办理指南 江苏省');await wait('办理城市')
 for(const [code,district,source] of [['320281','江阴市','3d304f186983f34c4170a398'],['320282','宜兴市','509219666f61612819e02f36']]){
  const rr={code,district,source_id:source};regions.push(rr)
  await check(district+' native selection / own source and live version',async()=>{
   await fill('combobox "办理城市"','无锡市');await fill('combobox "办理区县"',district);await wait('按'+district+'官方空白表格辅助填写')
   assert.equal(await read(`document.querySelector('[data-source-id]').dataset.sourceId`),source)
   const r=await fetch(api+'/lookup?'+query(district));assert.equal(r.status,200);const g=await r.json();assert.equal(g.source_id,source);assert(g.version);rr.version=g.version;rr.application_template_id=g.templates.find(t=>t.can_generate&&t.document_types.includes('application')).id
   fs.writeFileSync(path.join(raw,code+'-live-guide.json'),JSON.stringify(g,null,2));rr.guide_sha256=sha(Buffer.from(JSON.stringify(g)))
   await shot(code+'-guide');return {source_id:source,version:g.version}
  })
  await check(district+' original real browser download',async()=>{
   const s=await snapshot(),l=s.split('\n').find(l=>l.includes('link "下载原文件"')&&l.includes('/templates/'+rr.application_template_id+'?'));assert(l);await tool('click',{uid:l.match(/uid=(\S+)/)[1]})
   const r=await captureResponse(code+'-original','/templates/'+rr.application_template_id+'?');rr.original={http_status:r.status,actual_browser_body_saved:r.binary,bytes:r.bytes,sha256:r.sha256,limitation:r.binary?null:'Installed MCP did not persist binary response. Real native download request HTTP/headers verified; bytes unverified.'};assert.match(r.detail,/content-disposition:attachment/i);assert.match(r.detail,/application\/vnd.openxmlformats-officedocument.wordprocessingml.document/i)
  })
  await check(district+' application native birthday / 3 and 2 copies / modal cancel and Escape / POST',async()=>{
   await click('button "仲裁申请书"')
   await click('DisclosureTriangle "补充表格中的其他信息"')
   await tool('fill_form',{elements:[{uid:await uid('textbox "出生日期"'),value:'1991-05-09'},{uid:await uid('spinbutton "随申请书附上的副本份数"'),value:'3'},{uid:await uid('spinbutton "随申请书附上的证据份数"'),value:'2'}]})
   assert.equal(await read(`Array.from(document.querySelectorAll('label')).find(l=>l.textContent.trim()==='出生日期').querySelector('input').value`),'1991-05-09')
   await cancelAndEscape('button "生成并下载仲裁申请书"','仲裁申请书')
   await click('button "生成并下载仲裁申请书"');await shot(code+'-application-confirm');await click('button "确认生成"');await wait('文书已生成并下载')
   const r=await captureResponse(code+'-application','POST '+api+'/generate');assert(r.request);assert.equal(r.request.source_id,source);assert.equal(r.request.version,rr.version);assert.equal(String(r.request.data.copyCount),'3');assert.equal(String(r.request.data.evidenceCopyCount),'2');assert.equal(r.request.data.birthDate,'1991-05-09');assert(r.detail.includes('- x-guide-source-id:'+source));assert.match(r.detail,/x-document-origin:official-blank-filled/i);assert.match(r.detail,/application\/vnd.openxmlformats-officedocument.wordprocessingml.document/i)
   rr.application={http_status:200,response_source_id:source,response_document_origin:'official-blank-filled',content_type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',actual_browser_body_saved:r.binary,bytes:r.bytes,sha256:r.sha256,request_source_id:r.request.source_id,request_version:r.request.version,birthDate:r.request.data.birthDate,copyCount:r.request.data.copyCount,evidenceCopyCount:r.request.data.evidenceCopyCount}
   rr.application.actual_docx_birthday_and_copies_verified=false
   if(r.binary){const paragraphs=inspectDocx(r.path),txt=paragraphs.join('\n');fs.writeFileSync(path.join(raw,code+'-application-paragraphs.json'),JSON.stringify(paragraphs,null,2));assert.match(txt,/1991.*5.*9/);assert.match(txt,/副本\s*3\s*份/);assert.match(txt,/相关证据\s*2\s*份/);assert(!txt.includes('锡山区'));rr.application.actual_docx_birthday_and_copies_verified=true}
   else rr.application.limitation='Actual UI input and browser POST body verified; installed MCP did not persist response bytes. No replay used; actual DOCX birthday/copy text is unverified.'
   await shot(code+'-application-generated')
  })
  await check(district+' evidence starts one / add delete / real POST',async()=>{
   await click('button "证据清单"');await wait('添加你的证据');assert.equal(await read(`document.querySelectorAll('form .regional-material').length`),1)
   await click('button "添加一项证据"');assert.equal(await read(`document.querySelectorAll('form .regional-material').length`),2);await click('button "删除第2项证据"');assert.equal(await read(`document.querySelectorAll('form .regional-material').length`),1)
   await cancelAndEscape('button "生成并下载证据清单"','证据清单')
   await click('button "生成并下载证据清单"');await shot(code+'-evidence-confirm');await click('button "确认生成"');await wait('文书已生成并下载')
   const r=await captureResponse(code+'-evidence','POST '+api+'/generate');assert.equal(r.request.source_id,source);assert.equal(r.request.kind,'evidence');assert.equal(r.request.data.evidenceList.length,1);assert(r.detail.includes('- x-guide-source-id:'+source));assert.match(r.detail,/x-document-origin:official-blank-filled/i);rr.evidence={http_status:200,response_source_id:source,response_document_origin:'official-blank-filled',actual_browser_body_saved:r.binary,bytes:r.bytes,sha256:r.sha256,evidence_items:r.request.data.evidenceList.length,limitation:r.binary?null:'Actual browser POST body/200 verified; MCP writes a zero-byte response file. No replay used.'};await shot(code+'-evidence-generated')
  })
  for(const width of [375,768,1440])await check(district+' responsive '+width,async()=>{
   await tool('emulate',{viewport:`${width}x900x1`});const dims=await read(`({width:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth})`);assert(dims.scroll<=dims.width&&dims.body<=dims.width,JSON.stringify(dims));await shot(code+'-evidence-'+width)
   await click('button "仲裁申请书"');const a=await read(`({width:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth})`);assert(a.scroll<=a.width&&a.body<=a.width,JSON.stringify(a));await shot(code+'-application-'+width);await click('button "证据清单"');return {evidence:dims,application:a}
  })
  await check(district+' wrong district does not inherit',async()=>{await fill('combobox "办理区县"','虚构未核验测试区');await wait('该地区办事指南尚未核验');assert.equal(await read(`!!document.querySelector('[data-source-id]')`),false);assert.equal(await read(`document.querySelectorAll('form').length`),0);await shot(code+'-wrong-district')})
 }
 await check('Console zero error/warn; no model requests',async()=>{const c=await tool('list_console_messages',{types:['error','warn'],includePreservedMessages:true});assert(/no console messages/i.test(c),c);assert(!/\/api\/chat|\/api\/ai|\/v1\/chat/.test(await network()));return {error:0,warn:0}})
}catch(e){console.error(e.stack);process.exitCode=1}finally{
 const result={tested_at:new Date().toISOString(),site:base,api,engine:'Installed Chrome DevTools MCP; isolated context; native click/fill/fill_form only; evaluate read-only',synthetic_only:true,services_started:false,models_called:false,regions,checks,passed:checks.length>0&&checks.every(c=>c.passed),acceptance_scope:'UI and real browser HTTP/request body/response headers. Binary proof only if actual_browser_body_saved=true; zero-byte MCP output is never counted.',byte_validation_complete:regions.length===2&&regions.every(r=>r.application?.actual_docx_birthday_and_copies_verified&&r.evidence?.actual_browser_body_saved&&r.original?.actual_browser_body_saved),raw_evidence_policy:'Raw transcript, requests, response bodies, DOCX and full guide JSON stay under ignored .runtime/candidate-browser-20261029/js. Never use replay as browser response evidence.',screenshots:screenshots.map(f=>path.basename(f))}
 fs.writeFileSync(path.join(output,'BROWSER-RESULTS.json'),JSON.stringify(result,null,2)+'\n');close()
 const files=[...screenshots,path.join(output,'BROWSER-RESULTS.json'),path.resolve('scripts/verify-jiangsu-oct29-candidate.mjs')]
 fs.writeFileSync(path.join(output,'PUBLIC-WHITELIST.json'),JSON.stringify({files:files.map(f=>({path:path.relative(root,f).replaceAll('\\','/'),bytes:fs.statSync(f).size,sha256:sha(fs.readFileSync(f))})),manifest_path:path.relative(root,path.join(output,'PUBLIC-WHITELIST.json')).replaceAll('\\','/'),excluded_directory:'.runtime/candidate-browser-20261029/js'},null,2)+'\n')
}
