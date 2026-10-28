/** Supplemental keyboard and OS reduced-motion checks through Chrome DevTools MCP. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
process.env.UI_REDUCED_MOTION='1'
const {call,close}=await import('./ui-devtools-session.mjs')
const output=path.resolve('.runtime/ui-review'),checks=[],pageId=2
fs.mkdirSync(output,{recursive:true})
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  assert(!result.isError,JSON.stringify(result.content))
  fs.appendFileSync(path.join(output,'accessibility-transcript.jsonl'),JSON.stringify({name,args,result:{...result,content:result.content?.filter(c=>c.type!=='image')}})+'\n')
  return result.content?.filter(c=>c.type==='text').map(c=>c.text).join('\n')||''
}
async function inspect(expression){const result=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(result.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(needle){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(line=>line.replace(/"\s+/g,'"').includes(needle));assert(line,needle);return line.match(/uid=(\S+)/)[1]}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log(`PASS ${name}`)}catch(error){checks.push({name,passed:false,error:error.message});console.log(`FAIL ${name}: ${error.message}`)}}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'ui-accessibility'})
  await tool('emulate',{viewport:'1440x900x1'})
  await check('Reduced motion follows OS preference',async()=>{
    assert.equal(await inspect(`matchMedia('(prefers-reduced-motion:reduce)').matches`),true)
    assert.equal(await inspect(`getComputedStyle(document.querySelector('.province-card')).transitionDuration`),'0s')
    assert.equal(await inspect(`getComputedStyle(document.documentElement).scrollBehavior`),'auto')
  })
  await check('Keyboard skip link reaches main content with visible focus',async()=>{
    await tool('press_key',{key:'Tab'})
    assert.equal(await inspect(`document.activeElement.className`),'skip-link')
    assert.equal(await inspect(`getComputedStyle(document.activeElement).outlineStyle`),'solid')
    await tool('press_key',{key:'Enter'})
    assert.equal(await inspect(`document.activeElement.id`),'main-content')
  })
  await check('Search survives province navigation and browser Back',async()=>{
    await tool('fill',{uid:await uid('searchbox "搜索办理省份"'),value:'浙江'})
    assert((await inspect(`location.search`)).includes('q='))
    assert.equal(await inspect(`document.activeElement.id`),'province-query')
    await tool('click',{uid:await uid('link "文书 + 办理指南 浙江省')})
    await tool('navigate_page',{type:'back'})
    assert.equal(await inspect(`document.querySelector('#province-query').value`),'浙江')
    assert.equal(await inspect(`document.querySelectorAll('.province-card').length`),1)
  })
  await check('All four form steps focus their own section',async()=>{
    await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/documents/guangdong/application'})
    const labels=['1 你的信息','2 公司信息','3 你的要求','4 事情经过']
    const sections=['applicant-section','company-section','requests-section','facts-section']
    for(let index=0;index<labels.length;index++){
      await tool('click',{uid:await uid(`button "${labels[index]}"`)})
      assert.equal(await inspect(`document.activeElement.closest('.form-section').id`),sections[index])
      assert.equal(await inspect(`document.querySelector('[aria-current="step"]').textContent.replace(/\s+/g,'')`),labels[index].replace(/\s+/g,''))
    }
  })
}finally{
  fs.writeFileSync(path.join(output,'accessibility-results.json'),JSON.stringify({generatedAt:new Date().toISOString(),checks},null,2))
  close()
}
console.log(`Completed ${checks.length} supplemental checks, ${checks.filter(x=>!x.passed).length} failures.`)
if(checks.some(x=>!x.passed))process.exitCode=1
