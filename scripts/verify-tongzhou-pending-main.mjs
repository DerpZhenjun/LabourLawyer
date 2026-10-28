/** Real existing main site only; independent candidate remains unpublished. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {call,close} from './ui-devtools-session.mjs'
const cases={tongzhou:{folder:'beijing-tongzhou',district:'通州区',neighbour:'朝阳区',iteration:'browser-main-0715',outbox:'own-source-0710.json',pending:273,source:'dc45a34eec2aa0526fd71d26'},chaoyang:{folder:'beijing-chaoyang',district:'朝阳区',neighbour:'海淀区',iteration:'browser-main-round23',outbox:'own-source-round23.json',pending:278,source:'cc5c58104f9b879c75169d73'}}
cases.nansha={folder:'guangdong-nansha',province:'guangdong',city:'广州市',district:'南沙区',neighbour:'海珠区',iteration:'browser-main-round23',outbox:'own-source-round23.json',pending:282,source:'00af611e3d879eb1bade5aa5',eventCount:4,category:'地区间要求差异',eventType:'OFFICIAL_SOURCE_CONFLICT',eventScreenshot:'own-materials-conflict.png'}
cases.nanshawindows={...cases.nansha,iteration:'browser-main-round24',outbox:'own-windows-round24.json',pending:283,eventCount:1,eventType:'MATERIAL_INFORMATION_MISSING',eventScreenshot:'own-window-resolution.png'}
cases.futiandiscovery={folder:'guangdong-futian',province:'guangdong',city:'深圳市',district:'福田区',neighbour:'罗湖区',iteration:'browser-main-round24',outbox:'guide-target-round24.json',pending:284,eventCount:1,category:'官方页面访问',eventType:'GUIDE_PAGE_UNAVAILABLE',eventScreenshot:'own-guide-timeout.png'}
cases.futianown={...cases.futiandiscovery,iteration:'browser-main-final-round25',outbox:'own-source-round25.json',pending:288,eventCount:4,source:'d09e8fdcc61cf4d1e83aef21',category:'网上办理支持',eventType:'ONLINE_CHANNEL_UNVERIFIED',eventScreenshot:'own-online-boundary.png'}
cases.furongown={folder:'hunan-furong',province:'hunan',city:'长沙市',district:'芙蓉区',neighbour:'天心区',iteration:'browser-main-final-round26',outbox:'own-source-round26.json',pending:291,eventCount:3,source:'14f4fa82caef6e452d6c61f2',category:'需人工登录或核验',eventType:'AUTH_REQUIRED',eventScreenshot:'own-auth-boundary.png'}
cases.kaifudiscovery={folder:'hunan-kaifu',province:'hunan',city:'长沙市',district:'开福区',neighbour:'芙蓉区',iteration:'browser-main-round27',outbox:'discovery-round27.json',pending:294,eventCount:3,category:'官方页面访问',eventType:'REGION_SELECTION_FAILURE',eventScreenshot:'own-region-identity-unverified.png'}
cases.dongchengown={folder:'beijing-dongcheng',province:'beijing',city:'北京市',district:'东城区',neighbour:'西城区',iteration:'browser-main-round28',outbox:'own-source-round28.json',pending:298,eventCount:4,source:'99643eb40ede8e6a0e0c46bc',category:'需人工登录或核验',eventType:'AUTH_REQUIRED',eventScreenshot:'own-auth-boundary.png'}
const sample=cases[process.argv[2]||'tongzhou'];assert(sample,'Unknown exact test case')
const out=path.resolve('reports/nationwide-localization-20261023-night/cross-province',sample.folder,sample.iteration)
assert(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true})
const pageId=2,checks=[]
async function tool(name,args={}){const r=await call(name,name==='new_page'?args:{pageId,...args});fs.appendFileSync(path.join(out,'mcp.jsonl'),JSON.stringify({name,args,result:{...r,content:r.content?.filter(c=>c.type!=='image')}})+'\n');assert(!r.isError,JSON.stringify(r));return r.content.filter(c=>c.type==='text').map(c=>c.text).join('\n')}
async function read(expression){return JSON.parse((await tool('evaluate_script',{function:`() => (${expression})`})).match(/```json\s*([\s\S]*?)\s*```/)[1])}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS '+name)}catch(e){checks.push({name,passed:false,error:e.message});console.log('FAIL '+name+': '+e.message)}}
try{
  await tool('new_page',{url:'http://127.0.0.1:5173/admin/regions',isolatedContext:'tongzhou-public-outbox-only'})
  await tool('wait_for',{text:['OpenClaw 实际状态'],timeout:20000});await tool('emulate',{viewport:'1440x1000x1'})
  await check('Own public events actually appear pending; candidate source not published',async()=>{
    const events=JSON.parse(fs.readFileSync(path.join('reports/nationwide-localization-20261023-night/cross-province',sample.folder,'outbox',sample.outbox),'utf8'))
    assert.equal(events.length,sample.eventCount||5);const body=await read(`document.querySelector('.collection-page').textContent`)
    for(const e of events)assert(body.includes(e.id),e.id)
    assert(body.includes(`等待确认 ${sample.pending} 条`));assert(body.includes('PENDING_OPENCLAW'))
    if(sample.source)assert(!body.includes(sample.source))
    const snapshot=await tool('take_snapshot');const line=snapshot.split('\n').find(l=>l.includes('DisclosureTriangle')&&l.includes(sample.category||'官方空白模板缺失'));assert(line)
    await tool('click',{uid:line.match(/uid=(\S+)/)[1]})
    const expanded=await tool('take_snapshot'),lines=expanded.split('\n')
    const targetType=sample.eventType||'OFFICIAL_TEMPLATE_NOT_FOUND',ownEvent=events.find(e=>e.type===targetType);assert(ownEvent)
    const at=lines.findIndex(l=>l.includes(ownEvent.id));assert(at>=0,'Own event ID missing from expanded category')
    const event=lines.slice(0,at).reverse().find(l=>l.includes('heading')&&l.includes(`${sample.district} · ${targetType}`));assert(event)
    await tool('hover',{uid:event.match(/uid=(\S+)/)[1]});await tool('take_screenshot',{filePath:path.join(out,sample.eventScreenshot||'own-sample-not-blank-event.png'),fullPage:false})
  })
  await check(`Unknown ${sample.district} and neighbour show no false own guide or online submission`,async()=>{
    for(const district of [sample.district,sample.neighbour]){
      await tool('navigate_page',{type:'url',url:`http://127.0.0.1:5173/province/${sample.province||'beijing'}?`+new URLSearchParams({city:sample.city||'北京市',district})})
      await tool('wait_for',{text:['该地区办事指南尚未核验'],timeout:20000})
      assert.equal(await read(`!!document.querySelector('[data-source-id]')`),false)
      assert.equal(await read(`!!document.querySelector('[data-online-entry]')`),false)
      if(district===sample.district)for(const width of [375,768,1440]){
        await tool('emulate',{viewport:`${width}x900x1`});await tool('press_key',{key:'Control+Home'})
        assert(await read('document.documentElement.scrollWidth<=innerWidth'))
        await tool('take_screenshot',{filePath:path.join(out,`unknown-${sample.folder}-${width}.png`),fullPage:false})
      }
    }
  })
  await check('Existing Jianhu identity, login boundary and filling remain available',async()=>{
    await tool('navigate_page',{type:'url',url:'http://127.0.0.1:5173/province/jiangsu?'+new URLSearchParams({city:'盐城市',district:'建湖县'})})
    await tool('wait_for',{text:['你的信息和公司的信息'],timeout:20000})
    assert.equal(await read(`document.querySelector('[data-source-id]').dataset.sourceId`),'ef1eb897ebf880c6f2a316f5')
    assert.equal(await read(`document.querySelector('[data-channel-state]').dataset.channelState`),'auth_required')
    await tool('take_screenshot',{filePath:path.join(out,'existing-jianhu.png'),fullPage:false})
  })
  await check('No browser console warning/error or model request',async()=>{
    assert(!(await tool('list_console_messages',{types:['error','warn']})).includes('msgid='))
    assert(!/11434|\/api\/chat|\/api\/tts/.test(await tool('list_network_requests')))
  })
}finally{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({at:new Date().toISOString(),checks,failed:checks.filter(c=>!c.passed).length,candidate_guide_acceptance:'NOT_RUN',models:0,known_ai_button_occlusion:'not_fixed'},null,2));close()}
if(checks.some(c=>!c.passed))process.exitCode=1
