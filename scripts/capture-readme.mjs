/** Capture real product screens with fictional examples, never private cases. */
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import {call,close} from './ui-devtools-session.mjs'
const pageId=2,out=path.resolve('docs/images'),log=path.resolve('.runtime/readme-capture-20261028')
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(log,{recursive:true})
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});fs.appendFileSync(path.join(log,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(c=>c.type!=='image')}})+'\n');assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const go=pathname=>tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173'+pathname})
const shot=name=>tool('take_screenshot',{filePath:path.join(out,name+'.png'),fullPage:false})
async function uid(text){const snap=await tool('take_snapshot');const line=snap.split('\n').find(l=>l.includes(text));assert(line,text);return line.match(/uid=(\S+)/)[1]}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'readme-product-screens'})
  await tool('emulate',{viewport:'1440x1000x1'});await wait('你准备在哪个省份办理？');await shot('home')
  await go('/province/sichuan?city=成都市&district=武侯区');await wait('你的信息和公司的信息');await tool('click',{uid:await uid('textbox "你的姓名"')});await shot('document-form')
  await tool('click',{uid:await uid('link "怎样提交"')});await wait('这不是网站故障');await shot('local-guide')
  await tool('emulate',{viewport:'390x844x1'});await go('/province/sichuan?city=成都市&district=锦江区');await wait('你的信息和公司的信息');await tool('click',{uid:await uid('textbox "你的姓名"')});await shot('mobile-form')
  const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
  fs.writeFileSync(path.join(log,'result.json'),JSON.stringify({captured_at:new Date().toISOString(),screens:['home','document-form','local-guide','mobile-form'],fictional_examples_only:true},null,2))
  console.log('PASS four actual product screenshots captured')
}finally{close()}
