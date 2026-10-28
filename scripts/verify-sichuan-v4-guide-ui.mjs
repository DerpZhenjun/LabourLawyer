/** Real isolated MCP acceptance for guide-only localities, no invented generator. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {call,close} from './ui-devtools-session.mjs'
const root=path.resolve('reports/nationwide-localization-20261023-night/batches/v4-guides-0205')
const out=path.resolve(process.env.BATCH_UI_OUTPUT||path.join(root,'browser-staging'))
const base=process.env.SITE_BASE||'http://127.0.0.1:5174',checks=[],pageId=2
assert(!fs.existsSync(out),'Fresh browser evidence folder required');fs.mkdirSync(out,{recursive:true})
const codes=JSON.parse(fs.readFileSync(path.join(root,'staging.json'),'utf8')).codes
const guides=codes.map(code=>JSON.parse(fs.readFileSync(path.join(root,'guides',code,'guide.json'),'utf8')))
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!result.isError,JSON.stringify(result.content));return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
const inspect=async expression=>JSON.parse((await tool('evaluate_script',{function:`() => (${expression})`})).match(/```json\s*([\s\S]*?)\s*```/)[1])
const wait=text=>tool('wait_for',{text:[text],timeout:15000})
async function uid(text){const line=(await tool('take_snapshot')).split('\n').find(x=>x.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const click=async text=>tool('click',{uid:await uid(text)})
const url=g=>base+'/province/sichuan?'+new URLSearchParams({city:g.city,district:g.district})
const sid=g=>crypto.createHash('sha256').update(JSON.stringify(g.source_url)).digest('hex').slice(0,24)
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:base,isolatedContext:'v4-guide-only-verification'})
  if(process.argv.includes('--before')){
    await tool('navigate_page',{type:'url',url:url(guides.find(g=>g.district==='广汉市'))})
    await wait('当地文书尚未通过填写核验')
    await tool('take_screenshot',{filePath:path.join(out,'before.png'),fullPage:false})
    await check('No downloaded file must not promise immediate local file download',async()=>{
      assert((await inspect(`document.querySelector('#document-workspace .workspace-unavailable p').textContent`)).includes('尚未核实可下载文件'))
    })
    await check('Official reduction badge stays separate and conditional',async()=>{
      await tool('navigate_page',{type:'url',url:url(guides.find(g=>g.district==='色达县'))})
      await wait('办理机关：'+guides.find(g=>g.district==='色达县').authority)
      assert((await inspect(`document.querySelector('#regional-materials').textContent`)).includes('标记“免”'))
    })
  }else{
    assert.equal(new Set(guides.map(sid)).size,15)
    for(const g of guides){
      await check(`${g.city}/${g.district}: own eight-tab guide, exact fields/materials, no false forms/online entry`,async()=>{
        await tool('navigate_page',{type:'url',url:url(g)});await wait('办理机关：'+g.authority)
        assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),sid(g))
        assert.equal(await inspect(`document.querySelector('[data-region-code]').dataset.regionCode`),g.region_code)
        assert.equal(await inspect(`document.querySelector('[data-field="handling-form"]').textContent.trim()`),g.fields['办理形式'].raw_value)
        assert.equal(await inspect(`document.querySelector('.guide-source a').href`),g.source_url)
        assert.equal(await inspect(`document.querySelectorAll('.original-section').length`),8)
        assert.equal(await inspect(`document.querySelectorAll('#regional-materials .regional-material').length`),g.materials.length)
        const rendered=await inspect(`Array.from(document.querySelectorAll('#regional-materials .material-top')).map(n=>n.textContent)`)
        g.materials.forEach((m,i)=>{for(const text of [m.name,m.required,m.original_copy,m.format,m.copies+' 份'])assert(rendered[i].includes(text))})
        assert.equal(await inspect(`!!document.querySelector('[data-online-entry]')`),false)
        assert.equal(await inspect(`document.querySelectorAll('#document-workspace input').length`),0)
        assert.equal(await inspect(`Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('生成并下载'))`),false)
        assert.equal(await inspect(`document.querySelectorAll('#regional-documents a.ll-button').length`),0)
        assert((await inspect(`document.querySelector('#document-workspace .workspace-unavailable p').textContent`)).includes('尚未核实可下载文件'))
        if(!g.materials.length)assert((await inspect(`document.querySelector('.verified-guide').textContent`)).includes('不代表无需'))
        if(g.district==='色达县')assert((await inspect(`document.querySelector('#regional-materials').textContent`)).includes('标记“免”'))
        const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
        if(['广汉市','游仙区','盐亭县','色达县'].includes(g.district)){
          await click('link "准备材料"');await tool('take_screenshot',{filePath:path.join(out,g.region_code+'-materials.png'),fullPage:false})
        }
      })
    }
    await check('375/768/1440 responsive pending state',async()=>{
      for(const width of [375,768,1440]){
        await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'})
        assert(await inspect(`document.documentElement.scrollWidth<=window.innerWidth`))
        await tool('take_screenshot',{filePath:path.join(out,`responsive-${width}.png`),fullPage:false})
      }
    })
    await check('Real city and district inputs clear previous source then replace own materials',async()=>{
      await tool('fill',{uid:await uid('combobox "办理城市"'),value:'绵阳市'});await wait('请选择城市和区县')
      assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      await tool('fill',{uid:await uid('combobox "办理区县"'),value:'游仙区'});await wait('办理机关：绵阳市游仙区人力资源和社会保障局')
      const first=await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`)
      assert.equal(await inspect(`document.querySelectorAll('#regional-materials .regional-material').length`),4)
      await tool('fill',{uid:await uid('combobox "办理区县"'),value:'盐亭县'});await wait('办理机关：'+guides.find(g=>g.district==='盐亭县').authority)
      assert.notEqual(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),first)
      assert.equal(await inspect(`document.querySelectorAll('#regional-materials .regional-material').length`),3)
      await tool('take_screenshot',{filePath:path.join(out,'district-switch.png'),fullPage:false})
    })
    await check('Unknown exact region inherits neither source nor material',async()=>{
      await tool('fill',{uid:await uid('combobox "办理区县"'),value:'尚未核验的功能区'});await wait('该地区办事指南尚未核验')
      assert.equal(await inspect(`!!document.querySelector('[data-source-id]')`),false)
      assert.equal(await inspect(`document.querySelectorAll('#regional-materials .regional-material').length`),0)
    })
    await check('Existing Chengdu source still fills immediately after region selector',async()=>{
      await tool('navigate_page',{type:'url',url:base+'/province/sichuan?'+new URLSearchParams({city:'成都市',district:'天府新区'})})
      await wait('你的信息和公司的信息')
      assert(await inspect(`document.querySelectorAll('#document-workspace input').length>10`))
      assert(await inspect(`document.querySelector('#document-workspace').compareDocumentPosition(document.querySelector('#regional-overview'))&Node.DOCUMENT_POSITION_FOLLOWING`))
    })
    await check('No model requests or accidental submissions',async()=>{
      const requests=await tool('list_network_requests',{pageSize:500})
      assert(!requests.match(/POST.*(generate|chat|ask|tts|completion)|11434|ollama/i),requests)
      fs.writeFileSync(path.join(out,'network.txt'),requests)
      assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
    })
  }
}finally{
  const failed=checks.filter(c=>!c.passed).length
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),codes,base,checks,failed,model_calls:0},null,2))
  close();if(failed)process.exitCode=1
}
