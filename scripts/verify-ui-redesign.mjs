/** Real interactions via Chrome DevTools MCP; no DOM mutations or personal browser profile. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { call, close } from './ui-devtools-session.mjs'

const output=path.resolve('.runtime/ui-review')
fs.mkdirSync(output,{recursive:true})
const checks=[],pageId=2
async function tool(name,args={}){
  const result=await call(name,name==='new_page'||name==='list_pages'?args:{pageId,...args})
  fs.appendFileSync(path.join(output,'mcp-transcript.jsonl'),JSON.stringify({name,args,result:{...result,content:result.content?.filter(c=>c.type!=='image')}})+'\n')
  assert(!result.isError,`${name}: ${JSON.stringify(result.content)}`)
  return result.content?.filter(c=>c.type==='text').map(c=>c.text).join('\n')||''
}
async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log(`PASS ${name}`)}catch(error){checks.push({name,passed:false,error:error.message});console.log(`FAIL ${name}: ${error.message}`)}}
const inspect=async expression=>{const result=await tool('evaluate_script',{function:`() => (${expression})`,waitForStableDom:false});const json=result.match(/```json\s*([\s\S]*?)\s*```/);return json?JSON.parse(json[1]):result}
const go=url=>tool('navigate_page',{url:`http://127.0.0.1:5173${url}`,type:'url'})
const snapshot=()=>tool('take_snapshot')
async function uid(needle){const text=await snapshot();const line=text.split('\n').find(line=>line.replace(/"\s+/g,'"').includes(needle));assert(line,`No accessible element: ${needle}`);return line.match(/uid=(\S+)/)[1]}
const click=async needle=>tool('click',{uid:await uid(needle)})
const fill=async(needle,value)=>tool('fill',{uid:await uid(needle),value})
const screenshot=name=>tool('take_screenshot',{filePath:path.join(output,name+'.png'),fullPage:true})
const layout=()=>inspect(`({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,h1:document.querySelectorAll('h1').length,unnamed:Array.from(document.querySelectorAll('button')).filter(b=>b.getClientRects().length&&!b.textContent.trim()&&!b.getAttribute('aria-label')&&!b.getAttribute('title')).length})`)
async function cleanConsole(){const result=await tool('list_console_messages',{types:['error','warn']});assert(/no console messages/i.test(result),result)}

try{
  await tool('new_page',{url:'http://127.0.0.1:5173/',isolatedContext:'ui-regression-suite'})
  await tool('emulate',{viewport:'1440x1000x1'})
  await check('Province search, no-results, clear and all 31 entries',async()=>{
    await fill('searchbox "搜索办理省份"','浙江')
    assert.equal(await inspect(`document.querySelectorAll('.province-card').length`),1)
    await fill('searchbox "搜索办理省份"','不存在')
    assert((await snapshot()).includes('没有找到这个省份'))
    await click('button "查看全部省份"')
    await click('button "查看全国 31 个省份"')
    assert.equal(await inspect(`document.querySelectorAll('.province-card').length`),31)
    await click('button "收起省份"')
    await screenshot('after-home-desktop')
    await cleanConsole()
  })
  await check('Province and document navigation',async()=>{
    await click('link "文书 + 办理指南 浙江省')
    assert.equal(await inspect(`location.pathname`),'/province/zhejiang')
    await screenshot('after-zhejiang-guide')
    await click('link "仲裁申请书')
    assert.equal(await inspect(`location.pathname`),'/documents/zhejiang/application')
    assert.equal(await inspect(`document.activeElement.id`),'main-content')
  })
  await check('Draft survives refresh, form steps retain labels and focus',async()=>{
    await fill('textbox "姓名 必填"','界面测试劳动者')
    await tool('navigate_page',{type:'reload'})
    assert.equal(await inspect(`document.querySelector('input[autocomplete="name"]').value`),'界面测试劳动者')
    await click('button "2 公司信息"')
    assert.equal(await inspect(`document.activeElement.autocomplete`),'organization')
    await screenshot('after-zhejiang-application')
  })
  await check('Generation dialog: cancel, Escape, focus trap and return',async()=>{
    await click('button "生成并下载申请书"')
    assert.equal(await inspect(`document.activeElement.getAttribute('aria-label')`),'取消生成')
    assert.equal(await inspect(`document.querySelector('#app').inert`),true)
    await tool('press_key',{key:'Shift+Tab'})
    assert((await inspect(`document.activeElement.textContent`)).includes('确认生成'))
    await screenshot('after-generation-confirm')
    await tool('press_key',{key:'Escape'})
    assert.equal(await inspect(`document.querySelectorAll('.confirm-dialog').length`),0)
    assert.equal(await inspect(`document.querySelector('#app').inert`),false)
    assert((await inspect(`document.activeElement.textContent`)).includes('生成并下载申请书'))
    await click('button "生成并下载申请书"')
    await click('button "取消"')
    assert.equal(await inspect(`document.querySelectorAll('.confirm-dialog').length`),0)
  })
  await check('Evidence starts at one; add, edit, remove and preset',async()=>{
    await go('/documents/zhejiang/evidence')
    assert.equal(await inspect(`document.querySelectorAll('.evidence-item').length`),1)
    await click('button "添加一项证据"')
    assert.equal(await inspect(`document.querySelectorAll('.evidence-item').length`),2)
    await click('button "删除这一项"')
    assert.equal(await inspect(`document.querySelectorAll('.evidence-item').length`),1)
    await click('button "工资流水')
    assert.equal(await inspect(`document.querySelectorAll('.evidence-item').length`),1)
    assert.equal(await inspect(`document.querySelector('.evidence-item input').value`),'工资流水')
    await screenshot('after-zhejiang-evidence')
    await cleanConsole()
  })
  for(const province of ['zhejiang','guangdong'])for(const kind of ['application','evidence']){
    await check(`${province} ${kind}: real document generation returns 200`,async()=>{
      await go(`/documents/${province}/${kind}`)
      await click(`button "生成并下载${kind==='application'?'申请书':'证据清单'}"`)
      await click('button "确认生成"')
      // wait_for is a native MCP wait, not a JS side-effect.
      await tool('wait_for',{text:kind==='application'?['申请书已生成']:['证据清单已生成'],timeout:30000})
      const requests=await tool('list_network_requests',{resourceTypes:['xhr','fetch']})
      const request=requests.split('\n').find(line=>line.includes(`/${province}/${kind}/generate`))
      assert(request?.includes('200'),requests)
      const reqid=Number(request.match(/reqid=(\d+)/)?.[1])
      assert(reqid)
      await tool('get_network_request',{reqid,responseFilePath:path.join(output,`${province}-${kind}.network-response`)})
      const bytes=fs.readFileSync(path.join(output,`${province}-${kind}.network-response`))
      assert.equal(bytes.subarray(0,2).toString(),'PK')
      fs.copyFileSync(path.join(output,`${province}-${kind}.network-response`),path.join(output,`${province}-${kind}.docx`))
      await cleanConsole()
      // Explicit blank-template download must not include the displayed example.
      await click('button "只需要表格？下载空白模板"')
      assert((await snapshot()).includes('不会带入示例或你已填写的信息'))
      await click('button "确认生成"')
      await tool('wait_for',{text:kind==='application'?['申请书已生成']:['证据清单已生成'],timeout:30000})
      const blankRequests=await tool('list_network_requests',{resourceTypes:['xhr','fetch']})
      const blankRequest=blankRequests.split('\n').filter(line=>line.includes(`/${province}/${kind}/generate`)).at(-1)
      assert(blankRequest?.includes('200'),blankRequests)
      const blankDetails=await tool('get_network_request',{reqid:Number(blankRequest.match(/reqid=(\d+)/)[1]),responseFilePath:path.join(output,`${province}-${kind}-blank.network-response`)})
      assert(blankDetails.includes('### Request Body\n{}'))
      fs.copyFileSync(path.join(output,`${province}-${kind}-blank.network-response`),path.join(output,`${province}-${kind}-blank.docx`))
    })
  }
  await check('AI assistant and digital-human entry, keyboard dismissal',async()=>{
    await go('/')
    await click('button "打开 AI 法律顾问"')
    assert((await snapshot()).includes('AI 法律助手'))
    await screenshot('after-ai-assistant')
    await click('button "数字人：打开法律数字人"')
    await tool('wait_for',{text:['数字人服务已连接'],timeout:30000})
    await screenshot('after-digital-human')
    await tool('press_key',{key:'Escape'})
    assert.equal(await inspect(`document.querySelectorAll('.digital-lawyer-modal').length`),0)
    assert.equal(await inspect(`document.activeElement.className`),'assistant-fab')
    await cleanConsole()
  })
  for(const width of [320,375,768,1024,1440]){
    await tool('emulate',{viewport:`${width}x900x1${width<700?',mobile,touch':''}`})
    for(const route of ['/','/province/guangdong','/documents/guangdong/application','/documents/zhejiang/evidence']){
      await check(`Responsive ${width}px ${route}`,async()=>{
        await go(route)
        const result=await layout()
        assert(result.scrollWidth<=result.width,JSON.stringify(result))
        assert.equal(result.h1,1)
        assert.equal(result.unnamed,0)
        if([375,768,1440].includes(width)){
          await screenshot(`responsive-${width}-${route.replaceAll('/','-')||'home'}`)
          if(width===375)await tool('take_screenshot',{filePath:path.join(output,`viewport-${width}-${route.replaceAll('/','-')||'home'}.png`)})
        }
        await cleanConsole()
      })
    }
    if(width===375)await check('Mobile navigation reaches FAQ',async()=>{
      await go('/');await click('button "菜单"');await click('link "常见问题"')
      assert.equal(await inspect(`location.hash`),'#faq')
      assert.equal(await inspect(`document.querySelector('.nav-toggle').getAttribute('aria-expanded')`),'false')
    })
  }
  await check('Phone landscape layout',async()=>{
    await tool('emulate',{viewport:'812x375x1,mobile,touch,landscape'})
    await go('/documents/guangdong/evidence')
    const result=await layout();assert(result.scrollWidth<=result.width)
    await screenshot('after-landscape-evidence')
  })
  await tool('emulate',{viewport:'1440x1000x1'})
  for(const route of ['/admin','/admin/cases','/admin/evidence','/admin/documents','/admin/deadlines','/admin/knowledge']){
    await check(`Admin route preserved ${route}`,async()=>{await go(route);assert((await snapshot()).includes('后台导航'));await cleanConsole()})
  }
  const catalog=JSON.parse(fs.readFileSync('frontend/src/data/provinceCatalog.json','utf8'))
  for(const province of catalog){await check(`Province guide preserved ${province.slug}`,async()=>{await go(`/province/${province.slug}`);assert.equal((await layout()).h1,1);await cleanConsole()})}
  for(const province of catalog)for(const kind of ['application','evidence']){
    if(!province[kind==='application'?'hasApplication':'hasEvidence'])continue
    await check(`All enabled forms: ${province.slug}/${kind}`,async()=>{
      await go(`/documents/${province.slug}/${kind}`)
      const result=await layout();assert.equal(result.h1,1);assert(result.scrollWidth<=result.width)
      await click(`button "生成并下载${kind==='application'?'申请书':'证据清单'}"`)
      await click('button "确认生成"')
      await tool('wait_for',{text:kind==='application'?['申请书已生成']:['证据清单已生成'],timeout:30000})
      await cleanConsole()
    })
  }
  await go('/')
  await screenshot('final-home-desktop')
  await tool('lighthouse_audit',{device:'desktop',mode:'snapshot',outputDirPath:path.join(output,'lighthouse-final-home')})
  await go('/documents/guangdong/application')
  await tool('lighthouse_audit',{device:'mobile',mode:'snapshot',outputDirPath:path.join(output,'lighthouse-final-application')})
  await go('/documents/zhejiang/evidence')
  await tool('lighthouse_audit',{device:'mobile',mode:'snapshot',outputDirPath:path.join(output,'lighthouse-final-evidence')})
  await go('/')
  await tool('performance_start_trace',{reload:true,autoStop:true,filePath:path.join(output,'after-trace.json.gz')})
}finally{
  fs.writeFileSync(path.join(output,'results.json'),JSON.stringify({generatedAt:new Date().toISOString(),checks},null,2))
  close()
}
console.log(`Completed ${checks.length} checks, ${checks.filter(x=>!x.passed).length} failures. Reports: ${output}`)
if(checks.some(x=>!x.passed))process.exitCode=1
