/** Six independent official guides and 12 actual browser generation POSTs. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('reports/nationwide-localization-20261023-night'),pageId=2,checks=[]
const codes=['510302000000','510303000000','510304000000','510311000000','510321000000','510322000000']
fs.mkdirSync(path.join(out,'browser-requests'),{recursive:true})
async function tool(name,args={}){
  const result=await call(name,name==='new_page'?args:{pageId,...args})
  fs.appendFileSync(path.join(out,'zigong-mcp.jsonl'),JSON.stringify({at:new Date().toISOString(),name,args,result:{...result,content:result.content?.filter(x=>x.type!=='image')}})+'\n')
  assert(!result.isError,JSON.stringify(result.content));return result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
async function inspect(expression){const result=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(result.match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function uid(text){const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(x=>x.includes(text));assert(line,`Missing ${text}`);return line.match(/uid=(\S+)/)[1]}
const wait=text=>tool('wait_for',{text:[text],timeout:20000})
const click=async text=>tool('click',{uid:await uid(text)})
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'zigong-night-acceptance'})
  for(const code of codes){
    const guide=JSON.parse(fs.readFileSync(path.join(out,'sichuan/captures',code,'guide.json'),'utf8'))
    await check(`${guide.city}/${guide.district} exact source and two browser downloads`,async()=>{
      const query=new URLSearchParams({city:guide.city,district:guide.district})
      await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/sichuan?'+query})
      await wait('你的信息和公司的信息')
      const sid=crypto.createHash('sha256').update(JSON.stringify(guide.source_url)).digest('hex').slice(0,24)
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.sourceId`),sid)
      assert.equal(await inspect(`document.querySelector('[data-source-id]').dataset.regionCode`),code)
      assert.equal(await inspect(`!!document.querySelector('[aria-label="选择成都区县"]')`),false,'Other-city shortcuts should not lengthen this locality picker')
      assert(await inspect(`Array.from(document.querySelectorAll('#document-workspace input')).filter(e=>e.value.trim()).length>=10`))
      for(const kind of ['application','evidence']){
        const title=kind==='application'?'仲裁申请书':'证据清单'
        if(kind==='evidence'){
          await tool('press_key',{key:'Control+Home'});await click('button "证据清单"');await wait('添加你的证据')
          assert.equal(await inspect(`document.querySelectorAll('#document-workspace .regional-material').length`),1)
        }
        await click(`button "生成并下载${title}"`);await wait(`确认生成${title}？`)
        await click('button "确认生成"');await wait('文书已生成并下载')
        const requests=await tool('list_network_requests',{resourceTypes:['fetch']})
        const line=requests.split('\n').filter(x=>x.includes('POST')&&x.includes('/generate')).at(-1)
        assert(line?.includes('[200]'),requests)
        const file=path.join(out,'browser-requests',`${code}-${kind}.network-request`)
        await tool('get_network_request',{reqid:Number(line.match(/reqid=(\d+)/)[1]),requestFilePath:file})
        const payload=JSON.parse(fs.readFileSync(file,'utf8'))
        assert.equal(payload.source_id,sid);assert.equal(payload.city,guide.city);assert.equal(payload.district,guide.district);assert.equal(payload.kind,kind)
        assert.equal(payload.template_id,guide.templates.find(t=>t.original_name==='仲裁申请书(模板).docx').id)
      }
      if(code===codes[0]){await tool('press_key',{key:'Control+Home'});await tool('take_screenshot',{filePath:path.join(out,'zigong-published-form.png'),fullPage:false})}
    })
  }
  await check('No browser warning/error or inference requests',async()=>{
    const errors=await tool('list_console_messages',{types:['error','warn']});assert(!errors.includes('msgid='),errors)
    const net=await tool('list_network_requests');assert(!/11434|\/api\/chat|\/api\/tts/.test(net))
  })
}finally{fs.writeFileSync(path.join(out,'zigong-ui-result.json'),JSON.stringify({at:new Date().toISOString(),checks,failed:checks.filter(x=>!x.passed).length},null,2));close()}
if(checks.some(x=>!x.passed))process.exitCode=1
