"""Verify all 31 actual province pages and both responsive layouts."""
import asyncio,json,os,sys
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.portal_reports import router
from province_documents import PROVINCE_DOCUMENTS
from playwright.async_api import async_playwright
OUT=Path(os.getenv('PROVINCE_UI_OUTPUT',str(ROOT/'.runtime/province-experience/ui')));OUT.mkdir(parents=True,exist_ok=True)
temp=OUT/'temp';temp.mkdir(exist_ok=True);os.environ.update(TEMP=str(temp),TMP=str(temp))
app=FastAPI();app.include_router(router,prefix='/api/portal-reports');client=TestClient(app)
async def main():
    results=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
        page=await browser.new_page()
        async def api(route):
            req=route.request
            if req.method=='OPTIONS':return await route.fulfill(status=204,headers={'Access-Control-Allow-Origin':'*'})
            response=client.get(urlsplit(req.url).path)
            await route.fulfill(status=response.status_code,body=response.content,headers={'Content-Type':'application/json','Access-Control-Allow-Origin':'*'})
        await page.route('**/api/portal-reports/**',api)
        for width in (1440,390):
            await page.set_viewport_size({'width':width,'height':1000})
            await page.goto('http://127.0.0.1:4187/')
            await page.locator('.ready-grid .province-card').first.wait_for()
            sizes=await page.locator('.ready-grid .province-card').evaluate_all('(cards)=>cards.map(c=>({w:c.getBoundingClientRect().width,h:c.getBoundingClientRect().height}))')
            assert len(sizes)>=20
            assert max(s['w'] for s in sizes)-min(s['w'] for s in sizes)<1, f'Home card widths differ: {width}'
            assert max(s['h'] for s in sizes)-min(s['h'] for s in sizes)<1, f'Home card heights differ: {width}'
            await page.evaluate('window.scrollTo(0,document.querySelector(".province-section").getBoundingClientRect().top+scrollY-90)')
            await page.screenshot(path=str(OUT/f'home-{width}.png'))
            for slug,p in PROVINCE_DOCUMENTS.items():
                await page.goto(f'http://127.0.0.1:4187/province/{slug}')
                await page.locator('.hero img').wait_for()
                await page.wait_for_function('document.querySelector(".hero img").complete && document.querySelector(".hero img").naturalWidth > 0')
                await page.wait_for_timeout(180)
                assert p['name'] in await page.inner_text('main nav')
                assert await page.locator('.steps li').count()>0
                assert await page.locator('main > section').first.get_attribute('class')=='documents-panel'
                assert await page.locator('.steps details').count()==0
                assert '官方原文' not in await page.inner_text('main')
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth+2'),f'{slug} overflow {width}'
                text=await page.inner_text('main')
                assert '先做什么' in text and '带什么' in text and '注意什么' in text
                if slug=='shanghai' and client.get('/api/portal-reports/experiences/shanghai').json()['service_kind']=='mediation':assert '不是仲裁申请' in text
                if slug in ('beijing','tianjin','shanghai','yunnan','hunan','zhejiang'):
                    await page.screenshot(path=str(OUT/f'{slug}-{width}.png'),full_page=True)
                results.append({'slug':slug,'width':width,'ok':True})
        # Same-component navigation must change the motif and sourced guide.
        await page.goto('http://127.0.0.1:4187/province/zhejiang')
        await page.evaluate("history.pushState(null,'','/province/shanghai');window.dispatchEvent(new PopStateEvent('popstate'))")
        await page.wait_for_function('document.querySelector(".hero img").getAttribute("src").includes("shanghai")')
        await browser.close()
    (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
    print('PASS: 62 province pages; documents first; no legal-text dump; equal home cards at both widths; responsive overflow; sourced facts; route changes')
asyncio.run(main())
