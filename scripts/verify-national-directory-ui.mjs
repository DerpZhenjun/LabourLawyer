/** Actual Chrome DevTools MCP acceptance: directory ≠ guide/document support. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('reports/nationwide-localization-20261023-night'),pageId=2,checks=[]
const baseline=process.argv.includes('--baseline')
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,baseline?'ui-before.jsonl':'ui-mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!result.isError,JSON.stringify(result.content));return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const result=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(result.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(x=>x.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const go=path=>tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173'+path})
const shot=name=>tool('take_screenshot',{filePath:path.join(out,name+'.png'),fullPage:false})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/province/shandong?city=济南市&district=济南高新区',isolatedContext:'national-directory-night'})
  await wait('该地区办事指南尚未核验')
  if(baseline){await shot('before-national-directory');process.exitCode=0}
  else{
    await wait('区县与功能区')
    await check('Long locality list is collapsed so document workspace stays close',async()=>{
      assert.equal(await inspect(`document.querySelector('.region-directory').open`),false)
      await tool('click',{uid:await uid('区县与功能区')})
      await wait('选择本市区县或功能区')
    })
    await check('National functional-area directory appears without fake official guide',async()=>{
      assert(await inspect(`Array.from(document.querySelectorAll('#known-districts option')).some(x=>x.value==='济南高新区')`))
      assert(await inspect(`!!document.querySelector('[data-guide-state="unverified"]')`))
      assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
      assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      await shot('after-national-functional-area')
    })
    await check('Actual select changes district and clears old guide',async()=>{
      await tool('fill',{uid:await uid('combobox "选择本市区县或功能区"'),value:'历下区 · 待核验'})
      await wait('该地区办事指南尚未核验')
      assert.equal(await inspect(`new URL(location.href).searchParams.get('district')`),'历下区')
      assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      await shot('district-switch-no-inheritance')
    })
    await check('Verified Chengdu form still immediately follows selector with defaults',async()=>{
      await go('/province/sichuan?city=成都市&district=金牛区');await wait('你的信息和公司的信息')
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.regionCode`),'510106000000')
      assert(await inspect(`Array.from(document.querySelectorAll('input')).filter(e=>e.value.trim()).length>=10`))
    })
    for(const width of [375,768,1440])await check(`Responsive directory at ${width}px`,async()=>{
      await tool('emulate',{viewport:`${width}x900x1`})
      await go('/province/shandong?city=济南市&district=济南高新区');await wait('区县与功能区')
      assert.equal(await inspect(`innerWidth`),width)
      assert(await inspect(`document.documentElement.scrollWidth<=innerWidth`))
      await shot(`national-directory-${width}`)
    })
    await check('Browser console has no warnings/errors',async()=>{
      const result=await tool('list_console_messages',{types:['error','warn']});assert(!result.includes('msgid='),result)
    })
  }
}finally{
  fs.writeFileSync(path.join(out,baseline?'ui-before-result.json':'ui-result.json'),JSON.stringify({at:new Date().toISOString(),checks,failed:checks.filter(x=>!x.passed).length},null,2));close()
}
if(checks.some(x=>!x.passed))process.exitCode=1
