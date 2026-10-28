/** Same-region anchor navigation must not refetch/clear the selected guide or edits. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const pageId=2,out=path.resolve('reports/chengdu-district-expansion-20261023'),checks=[]
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});assert(!r.isError,JSON.stringify(r.content));return r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')}
async function uid(text){const s=await tool('take_snapshot');const l=s.split('\n').find(l=>l.includes(text));assert(l,text);return l.match(/uid=(\S+)/)[1]}
async function inspect(expression){const t=await tool('evaluate_script',{function:`() => (${expression})`});return JSON.parse(t.match(/```json\s*([\s\S]*?)\s*```/)[1])}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/province/sichuan?'+new URLSearchParams({city:'成都市',district:'金牛区'}),isolatedContext:'chengdu-anchor-regression'})
  await tool('wait_for',{text:['你的信息和公司的信息']})
  await tool('fill',{uid:await uid('textbox "你的姓名"'),value:'保留输入测试'})
  for(const [label,id] of [['怎样提交','regional-submit'],['准备材料','regional-materials']]){
    // Return above the content nav so native auto-scroll cannot place it under
    // the sticky site header when approaching a link from below.
    await tool('press_key',{key:'Control+Home'})
    const before=(await tool('list_network_requests',{resourceTypes:['fetch']})).split('\n').filter(l=>l.includes('/lookup?')).length
    await tool('click',{uid:await uid(`link "${label}"`)})
    let top=10000;const deadline=Date.now()+4000
    do{top=await inspect(`document.querySelector('#${id}')?.getBoundingClientRect().top??10000`);if(top>=0&&top<200)break;await new Promise(r=>setTimeout(r,100))}while(Date.now()<deadline)
    const after=(await tool('list_network_requests',{resourceTypes:['fetch']})).split('\n').filter(l=>l.includes('/lookup?')).length
    assert.equal(after,before,'Hash-only navigation must not reload the guide')
    assert(top>=0&&top<200,`Anchor ${id} off-screen: ${top}`)
    assert.equal(await inspect(`document.querySelector('#document-workspace input').value`),'保留输入测试')
    checks.push({label,passed:true,lookup_count:after,top})
    await tool('take_screenshot',{filePath:path.join(out,`${id}-anchor-verified.png`)})
  }
  console.log('PASS same-region anchors preserve guide, input and correct viewport position')
}catch(e){checks.push({passed:false,error:e.message,state:await inspect(`({url:location.href,text:document.body.innerText.slice(0,1800),ids:Array.from(document.querySelectorAll('[id]')).map(x=>x.id)})`),network:await tool('list_network_requests',{resourceTypes:['fetch']})});throw e}finally{
  fs.writeFileSync(path.join(out,process.argv.includes('--baseline')?'ANCHOR-BEFORE.json':'ANCHOR-RESULTS.json'),JSON.stringify(checks,null,2));close()
}
