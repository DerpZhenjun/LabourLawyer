/** Guards against compact national links reintroducing mixed province card sizes. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'

const output=path.resolve('.runtime/province-cards'),checks=[],pageId=2
fs.mkdirSync(output,{recursive:true})
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  assert(!result.isError,JSON.stringify(result.content))
  return result.content?.filter(c=>c.type==='text').map(c=>c.text).join('\n')||''
}
async function inspect(expression){const text=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(text.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(needle){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(line=>line.replace(/"\s+/g,'"').includes(needle));assert(line,needle);return line.match(/uid=(\S+)/)[1]}
const click=async needle=>tool('click',{uid:await uid(needle)})
const cards=()=>inspect(`Array.from(document.querySelectorAll('#provinces a[href^="/province/"]')).filter(e=>e.checkVisibility()).map(e=>({href:e.getAttribute('href'),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,radius:getComputedStyle(e).borderRadius,art:!!e.querySelector('img')}))`)
function uniform(list){
  assert.equal(new Set(list.map(e=>e.href)).size,list.length,'Each province must appear only once')
  assert(Math.max(...list.map(e=>e.width))-Math.min(...list.map(e=>e.width))<1,'All province cards must have equal width')
  assert(Math.max(...list.map(e=>e.height))-Math.min(...list.map(e=>e.height))<1,'All province cards must have equal height')
  assert.equal(new Set(list.map(e=>e.radius)).size,1,'All province cards must share the same shape')
  assert(list.every(e=>e.art),'All province cards must include their illustration')
}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log(`PASS ${name}`)}catch(error){checks.push({name,passed:false,error:error.message});console.log(`FAIL ${name}: ${error.message}`)}}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'province-card-consistency'})
  for(const width of [1440,1024,768,375,320]){
    await check(`Uniform province cards at ${width}px`,async()=>{
      await tool('emulate',{viewport:`${width}x900x1${width<700?',mobile,touch':''}`})
      await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/'})
      const initial=await cards();assert.equal(initial.length,6);uniform(initial)
      await click('"查看全国 31 个省份"')
      await tool('press_key',{key:'Control+Home'})
      await tool('take_screenshot',{filePath:path.join(output,`${process.env.UI_CHECK_PHASE||'after'}-${width}.png`),fullPage:true})
      const expanded=await cards();assert.equal(expanded.length,31,'Expansion must show 31 equally sized cards, not large cards plus small links');uniform(expanded)
      assert.equal(await inspect(`document.documentElement.scrollWidth<=innerWidth`),true)
      await tool('fill',{uid:await uid('searchbox "搜索办理省份"'),value:'浙江'})
      const filtered=await cards();assert.equal(filtered.length,1);uniform(filtered)
      assert(Math.abs(filtered[0].width-initial[0].width)<1,'Search must not stretch a card across the grid')
      assert(Math.abs(filtered[0].height-initial[0].height)<1,'Search must retain the same card height')
      await tool('fill',{uid:await uid('searchbox "搜索办理省份"'),value:'不存在'})
      assert.equal((await cards()).length,0)
      assert((await tool('take_snapshot')).includes('没有找到这个省份'))
      await click('button "查看全部省份"')
      assert.equal((await cards()).length,31,'Clearing search preserves expanded state')
      await click('button "收起省份"')
      assert.equal((await cards()).length,6)
      const consoleText=await tool('list_console_messages',{types:['warn','error']});assert(/no console messages/i.test(consoleText),consoleText)
    })
  }
  await check('National card navigation',async()=>{
    await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/'})
    await click('"查看全国 31 个省份"')
    await click('link "官方办理指南 河北省')
    assert.equal(await inspect(`location.pathname`),'/province/hebei')
  })
}finally{
  fs.writeFileSync(path.join(output,`${process.env.UI_CHECK_PHASE||'after'}-results.json`),JSON.stringify({generatedAt:new Date().toISOString(),checks},null,2))
  close()
}
if(checks.some(c=>!c.passed))process.exitCode=1
