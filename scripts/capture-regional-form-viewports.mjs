import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const output=path.resolve('reports/regional-expansion-20261023'),pageId=2
async function tool(name,args={}){
  const r=await call(name,name==='new_page'?args:{pageId,...args})
  if(r.isError)throw new Error(JSON.stringify(r.content))
  fs.appendFileSync(path.join(output,'viewport-mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(x=>x.type!=='image')}})+'\n')
  return r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')
}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/province/sichuan',isolatedContext:'regional-final-viewports'})
  for(const district of ['锦江区','武侯区']){
    await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/sichuan?'+new URLSearchParams({city:'成都市',district})})
    await tool('wait_for',{text:['你的信息和公司的信息'],timeout:15000})
    for(const width of [1440,375]){
      await tool('emulate',{viewport:`${width}x${width===375?812:1000}x1`})
      const line=(await tool('take_snapshot')).split('\n').find(x=>x.includes('textbox "你的姓名"'))
      await tool('click',{uid:line.match(/uid=(\S+)/)[1]})
      await tool('take_screenshot',{filePath:path.join(output,`${district}-form-viewport-${width}.png`)})
    }
  }
}finally{close()}
