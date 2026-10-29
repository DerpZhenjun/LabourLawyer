/** Existing-site compact digital-counsel UI checks. --answers sends one synthetic question. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('.runtime/compact-counsel-20261029'),checks=[]
fs.mkdirSync(out,{recursive:true});let pageId=2
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
async function inspect(expression){const s=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(s.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function until(expression,seconds=40){const end=Date.now()+seconds*1000;while(Date.now()<end){if(await inspect(expression))return;await new Promise(r=>setTimeout(r,500))}throw new Error('Timed out: '+expression)}
async function uid(text){const snapshot=await tool('take_snapshot'),line=snapshot.split('\n').find(l=>l.includes(text));assert(line,text);return line.match(/uid=(\S+)/)[1]}
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS '+name)}
try{
 await tool('new_page',{url:'http://127.0.0.1:3000/',isolatedContext:'compact-avatar-only'})
 await tool('emulate',{viewport:'1440x900x1'})
 await check('Standalone digital counsel uses a customer-service card',async()=>{
   await until(`!!document.querySelector('.digital-app')`)
   assert(await inspect(`document.querySelector('.digital-app').getBoundingClientRect().width<=420`),'Digital counsel must not fill the desktop width')
   assert(await inspect(`document.querySelector('.digital-app').getBoundingClientRect().height<=700`))
   await until(`document.querySelector('.avatar-stage')?.dataset.avatarState==='ready'`)
   assert(await inspect(`document.querySelector('.avatar-stage').getBoundingClientRect().height<=150`))
   assert(await inspect(`document.querySelector('.avatar-portrait').getBoundingClientRect().width<=160`))
 })
 if(process.argv.includes('--answers'))await check('Compact chat retains the real remote conversation',async()=>{
   await until(`!!document.querySelector('.connection-notice.connected')`)
   await tool('fill',{uid:await uid('textbox "描述你的劳动争议问题"'),value:'虚构连通性测试，请只回复：客服小窗测试成功。'})
   await tool('click',{uid:await uid('button "发送问题 ↗"')})
   await until(`document.querySelector('.counsel-message.assistant')?.textContent.includes('客服小窗测试成功')&&!document.querySelector('.reply-loading')`,180)
   await until(`document.querySelector('.counsel-composer button[type="submit"]').textContent==='发送问题 ↗'`)
 })
 for(const width of [375,768,1440])await check('Compact card responsive '+width,async()=>{
   await tool('emulate',{viewport:`${width}x900x1`})
   assert(await inspect(`document.documentElement.scrollWidth<=innerWidth`))
   assert(await inspect(`document.querySelector('.digital-app').getBoundingClientRect().width<=420`))
   assert(await inspect(`document.querySelector('.counsel-composer').getBoundingClientRect().bottom<=innerHeight`))
   await tool('take_screenshot',{filePath:path.join(out,`card-${width}.png`)})
 })
 await tool('take_screenshot',{uid:await uid(' main'),filePath:path.resolve('docs/images/digital-human.png')})
 assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
 await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'compact-widget-parent'})
 pageId=3;await tool('emulate',{viewport:'1440x900x1'})
 await tool('click',{uid:await uid('button "打开 AI 法律顾问"')})
 await tool('click',{uid:await uid('button "数字人：打开法律数字人"')})
 await until(`!!document.querySelector('.vrm-iframe')`)
 await check('Floating widget leaves the document page available',async()=>{
   assert.equal(await inspect(`document.querySelector('.digital-lawyer-modal').getAttribute('aria-modal')`),'false')
   assert.equal(await inspect(`!!document.querySelector('.digital-mask')||document.querySelector('#app').inert||document.body.style.overflow==='hidden'`),false)
   assert.equal(await inspect(`!!document.querySelector('button[aria-label="扩大窗口"]')`),false)
   await tool('fill',{uid:await uid('searchbox "搜索办理省份"'),value:'浙江'})
   assert.equal(await inspect(`document.querySelector('[aria-label="搜索办理省份"]').value`),'浙江')
   assert(await inspect(`!!document.querySelector('.digital-lawyer-modal')`))
 })
 await check('Collapse restores the same conversation iframe',async()=>{
   const before=await inspect(`document.querySelector('.vrm-iframe').src`)
   await tool('click',{uid:await uid('button "收起对话"')})
   assert(await inspect(`document.querySelector('.digital-lawyer-modal').getBoundingClientRect().height<=80`))
   await tool('click',{uid:await uid('button "展开对话"')})
   assert.equal(await inspect(`document.querySelector('.vrm-iframe').src`),before)
 })
 for(const width of [375,768,1440])await check('Floating widget stays small at '+width,async()=>{
   await tool('emulate',{viewport:`${width}x900x1`})
   assert(await inspect(`document.documentElement.scrollWidth<=innerWidth`))
   assert(await inspect(`document.querySelector('.digital-lawyer-modal').getBoundingClientRect().width<=420`))
   assert(await inspect(`document.querySelector('.digital-lawyer-modal').getBoundingClientRect().height<=680`))
   await tool('take_screenshot',{filePath:path.join(out,`widget-${width}.png`)})
 })
 await tool('click',{uid:await uid('button "收起对话"')})
 await tool('press_key',{key:'Escape'})
 await until(`!document.querySelector('.digital-lawyer-modal')`)
 await until(`document.activeElement?.classList.contains('assistant-fab')`)
 assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
}catch(error){checks.push({name:'acceptance',passed:false,error:error.message});console.error(error);process.exitCode=1}
finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({checked_at:new Date().toISOString(),checks},null,2));close()}
