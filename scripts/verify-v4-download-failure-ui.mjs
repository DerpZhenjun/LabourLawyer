/** Real browser proof: retain source/materials while refusing unavailable files. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const batch=path.resolve('reports/nationwide-localization-20261023-night/batches/v4-forms-0215')
const codes=['510704000000','510723000000'],checks=[],pageId=2
const base=process.env.SITE_BASE||'http://127.0.0.1:5174',out=path.resolve(process.env.BATCH_UI_OUTPUT||path.join(batch,'browser-staging'))
assert(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true})
async function tool(name,args={}){
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(c=>c.type!=='image')}})+'\n')
  assert(!r.isError,JSON.stringify(r.content));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')
}
const inspect=async x=>JSON.parse((await tool('evaluate_script',{function:`() => (${x})`})).match(/```json\s*([\s\S]*?)\s*```/)[1])
const wait=x=>tool('wait_for',{text:[x],timeout:15000})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:base,isolatedContext:'v4-unavailable-own-file'})
  for(const code of codes){
    const g=JSON.parse(fs.readFileSync(path.join(batch,code+'-failure-guide.json'),'utf8'))
    await check(`${g.district}: own source, HTTP504 visible, own materials retained, no false download/generation`,async()=>{
      await tool('navigate_page',{type:'url',url:base+'/province/sichuan?'+new URLSearchParams({city:g.city,district:g.district})})
      await wait('办理机关：'+g.authority)
      const body=await inspect(`document.querySelector('.verified-guide').textContent`)
      await tool('take_screenshot',{filePath:path.join(out,code+'.png'),fullPage:false})
      assert(body.includes('文件网关返回 HTTP 504'))
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),g.source_id)
      assert.equal(await inspect(`document.querySelectorAll('#regional-materials .regional-material').length`),g.materials.length)
      assert.equal(await inspect(`document.querySelectorAll('#regional-documents a.ll-button').length`),0)
      assert.equal(await inspect(`document.querySelectorAll('#document-workspace input').length`),0)
      assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
    })
  }
  if(!process.argv.includes('--before')){
    await check('375/768/1440 retain readable failure state',async()=>{
      for(const width of [375,768,1440]){
        await tool('emulate',{viewport:`${width}x900x1`})
        assert(await inspect(`document.documentElement.scrollWidth<=window.innerWidth`))
        await tool('take_screenshot',{filePath:path.join(out,`responsive-${width}.png`),fullPage:false})
      }
    })
    await check('Another source still has real existing form',async()=>{
      await tool('navigate_page',{type:'url',url:base+'/province/sichuan?'+new URLSearchParams({city:'成都市',district:'锦江区'})})
      await wait('你的信息和公司的信息');assert(await inspect(`document.querySelectorAll('#document-workspace input').length>10`))
    })
    await check('No console error or model/submission request',async()=>{
      assert(!(await tool('list_console_messages',{types:['warn','error']})).includes('msgid='))
      assert(!/11434|POST.*(generate|completion|chat|ask|tts)/.test(await tool('list_network_requests')))
    })
  }
}finally{const failed=checks.filter(c=>!c.passed).length;fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),codes,base,checks,failed,model_calls:0},null,2));close();if(failed)process.exitCode=1}
