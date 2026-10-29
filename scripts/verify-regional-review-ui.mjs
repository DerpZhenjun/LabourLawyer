/** Actual existing-site review-register acceptance; no backend launch or model calls. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('.runtime/nationwide-verification-20261029/browser'),checks=[]
fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId:2,...args});assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
async function read(expression){const r=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(r.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(label){const s=await tool('take_snapshot');const line=s.split('\n').find(l=>l.includes(label));assert(line,label);return line.match(/uid=(\S+)/)[1]}
try{
 await tool('new_page',{url:'http://127.0.0.1:5173/admin/regions',isolatedContext:'locality-review-only'})
 await tool('wait_for',{text:['地区采集与问题记录']})
 assert(await read(`!!document.querySelector('[data-regional-reviews]')`),'Per-locality review register is absent')
 checks.push({name:'Actual current collection register is visible without publishing candidates',passed:true})
 await tool('fill',{uid:await uid('searchbox "搜索逐地核验记录"'),value:'青羊'})
 assert(await read(`document.querySelector('[data-regional-reviews]').textContent.includes('本次已查来源未找到')`))
 assert.equal(await read(`!!document.querySelector('[data-regional-reviews] [data-review-row] [data-generate]')`),false)
 checks.push({name:'Search miss is bounded to checked sources and grants no generation',passed:true})
 await tool('fill',{uid:await uid('searchbox "搜索逐地核验记录"'),value:'测试未核验区县'})
 assert(await read(`document.querySelector('[data-regional-reviews]').textContent.includes('尚未登记本批核验结果')`))
 checks.push({name:'Unknown district stays unverified and is never labelled officially unavailable',passed:true})
 await tool('fill',{uid:await uid('searchbox "搜索逐地核验记录"'),value:'青羊'})
 for(const width of [375,768,1440]){
  await tool('emulate',{viewport:`${width}x1000x1`})
  assert(await read(`document.documentElement.scrollWidth<=innerWidth`))
  const element=await uid('region "逐地核验记录"')
  await tool('take_screenshot',{uid:element,filePath:path.join(out,`reviews-${width}.png`)})
  checks.push({name:'Review register responsive '+width,passed:true})
 }
 assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
}catch(error){checks.push({name:'acceptance',passed:false,error:error.message});console.error(error);process.exitCode=1}
finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({checked_at:new Date().toISOString(),checks},null,2));close()}
