/** Small viewport captures, using real public UI controls rather than DOM mutation. */
import assert from 'node:assert/strict'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const out=path.resolve('reports/chengdu-district-expansion-20261023'),pageId=2
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});assert(!r.isError,JSON.stringify(r.content));return r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')}
async function click(label){const s=await tool('take_snapshot');const line=s.split('\n').find(l=>l.includes(label));assert(line,label);await tool('click',{uid:line.match(/uid=(\S+)/)[1]})}
async function jump(label,id){
  await tool('press_key',{key:'Control+Home'})
  await click(label)
  const deadline=Date.now()+4000
  while(Date.now()<deadline){
    const result=await tool('evaluate_script',{function:`() => document.querySelector('${id}').getBoundingClientRect().top`})
    const top=JSON.parse(result.match(/```json\s*([\s\S]*?)\s*```/)[1])
    if(top>=0&&top<200)return
    await new Promise(resolve=>setTimeout(resolve,100))
  }
  throw new Error('Anchor did not settle in viewport: '+id)
}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/province/sichuan?'+new URLSearchParams({city:'成都市',district:'金牛区'}),isolatedContext:'chengdu-views'})
  await tool('wait_for',{text:['你的信息和公司的信息']})
  await tool('emulate',{viewport:'1440x1000x1'})
  await click('查看成都全部')
  await tool('take_screenshot',{filePath:path.join(out,'desktop-region-and-form.png')})
  for(const [width,height] of [[375,812],[768,1024]]){
    await tool('emulate',{viewport:`${width}x${height}x1`})
    await tool('take_screenshot',{filePath:path.join(out,`form-top-${width}.png`)})
  }
  await tool('emulate',{viewport:'1440x1000x1'})
  await jump('link "怎样提交"','#regional-submit')
  await tool('take_screenshot',{filePath:path.join(out,'jinniu-window-guidance.png')})
  await jump('link "准备材料"','#regional-materials')
  await tool('take_screenshot',{filePath:path.join(out,'jinniu-local-materials.png')})
}finally{close()}
