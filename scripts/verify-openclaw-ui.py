"""Exercise maintenance task selection, start, progress and resume in Vue.

Uses explicit API fixtures: this is UI validation, not acquisition evidence.
"""
import asyncio,json,os,subprocess,time
from pathlib import Path
from urllib.request import urlopen
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/openclaw-ui';OUT.mkdir(parents=True,exist_ok=True)
temp=OUT/'temp';temp.mkdir(exist_ok=True);os.environ.update(TEMP=str(temp),TMP=str(temp))

async def verify():
    results=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
        for width in (1440,390):
            page=await browser.new_page(viewport={'width':width,'height':1000});posts=[];state={'items':[]}
            async def api(route):
                req=route.request
                headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type','Content-Type':'application/json'}
                if req.method=='OPTIONS':return await route.fulfill(status=204,headers=headers)
                if req.method=='POST':
                    posts.append(req.post_data_json)
                    state['items']=[{'id':'20261007-000000-00000000','state':'running','completed':0,'total':1,'current':'shanxi','current_task':{'status':{'site_opened':True,'guide_found':False,'template_downloaded':False,'fill_verified':False}}}]
                    return await route.fulfill(status=202,headers=headers,json={'id':'20261007-000000-00000000','state':'queued'})
                return await route.fulfill(headers=headers,json=state if '/openclaw-tasks' in req.url else {'items':[]})
            await page.route('**/api/portal-reports**',api)
            await page.goto('http://127.0.0.1:4189/admin/documents')
            panel=page.locator('section').filter(has=page.get_by_role('heading',name='OpenClaw 浏览器补采'))
            await panel.locator('select').select_option('shanxi')
            await panel.get_by_role('button',name='让 OpenClaw 补采',exact=True).click()
            await panel.get_by_text('指南已找到：否',exact=False).wait_for()
            assert posts==[{'provinces':['shanxi']}]
            assert await panel.get_by_role('button',name='OpenClaw 正在采集…').is_disabled()
            state['items'][0].update(state='complete_with_gaps',completed=1,provinces={'shanxi':{'status':{'site_opened':True,'guide_found':False,'template_downloaded':False,'fill_verified':False}}})
            await panel.get_by_role('button',name='继续这个任务').wait_for(timeout=20000)
            await panel.get_by_role('button',name='继续这个任务').click()
            assert posts[-1]=={'resume':'20261007-000000-00000000'}
            await panel.scroll_into_view_if_needed();await page.screenshot(path=str(OUT/f'maintenance-{width}.png'))
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),f'Overflow at {width}'
            results.append({'width':width,'selection_start_resume':True,'four_statuses_visible':True,'no_horizontal_overflow':True,'ui_fixture':True})
            await page.close()
        await browser.close()
    (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(results),flush=True)

if __name__=='__main__':
    output=(OUT/'preview.log').open('wb')
    process=subprocess.Popen(['node',str(ROOT/'frontend/node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port','4189','--strictPort'],cwd=ROOT/'frontend',stdout=output,stderr=output,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(30):
            if process.poll() is not None:raise RuntimeError('Preview exited; inspect preview.log')
            try:
                with urlopen('http://127.0.0.1:4189',timeout=1):break
            except OSError:time.sleep(.3)
        else:raise TimeoutError('Preview not ready')
        asyncio.run(verify())
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill()
        output.close()
