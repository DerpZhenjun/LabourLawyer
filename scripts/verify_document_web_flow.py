"""Exercise actual default forms and downloads in an isolated headless browser."""
import asyncio
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=ROOT/'templates/_validation/web-flow')
parser.add_argument('--documents-only',action='store_true')
args=parser.parse_args()
OUT=args.output.resolve()
if not OUT.is_relative_to(ROOT):raise ValueError('Validation output must stay in the project directory')
OUT.mkdir(parents=True,exist_ok=True)
temp=OUT/'temp';temp.mkdir(exist_ok=True)
os.environ.update(TEMP=str(temp),TMP=str(temp))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.province_documents import router as documents
from routes.portal_reports import router as reports
from province_documents import PROVINCE_DOCUMENTS
from playwright.async_api import async_playwright

app=FastAPI();app.include_router(documents,prefix='/api/province-documents');app.include_router(reports,prefix='/api/portal-reports')
client=TestClient(app)

async def main():
    records=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
        context=await browser.new_context(accept_downloads=True,viewport={'width':1440,'height':1000})
        async def api(route):
            request=route.request
            if request.method=='OPTIONS':
                await route.fulfill(status=204,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'GET,POST,OPTIONS'});return
            response=client.request(request.method,urlsplit(request.url).path,json=request.post_data_json if request.post_data else None)
            headers={k:v for k,v in response.headers.items() if k.lower() not in ('content-length','content-encoding')}
            headers['Access-Control-Allow-Origin']='*'
            await route.fulfill(status=response.status_code,headers=headers,body=response.content)
        await context.route('**/api/**',api)
        page=await context.new_page()
        for slug,region in PROVINCE_DOCUMENTS.items():
            for kind in region['documents']:
                await page.goto(f'http://127.0.0.1:4187/documents/{slug}/{kind}')
                await page.locator('form').wait_for()
                await page.locator('form button[type="submit"]').click()
                async with page.expect_download(timeout=30000) as download:
                    await page.get_by_role('button',name='确认生成',exact=True).click()
                result=await download.value;output=OUT/f'{slug}-{kind}.docx';await result.save_as(output)
                assert output.read_bytes().startswith(b'PK'),result.failure
                if slug in ('jiangsu','hainan','hunan','zhejiang'):
                    await page.screenshot(path=str(OUT/f'{slug}-{kind}.png'),full_page=True)
                records.append({'slug':slug,'kind':kind,'file':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
                print('Downloaded actual UI example:',slug,kind,flush=True)
        if not args.documents_only:
            await page.goto('http://127.0.0.1:4187/admin/documents')
            await page.get_by_role('heading',name='政务服务门户观察报告').wait_for()
            await page.locator('.report-section').screenshot(path=str(OUT/'portal-report-feature.png'))
            async with page.expect_download(timeout=30000) as download:
                await page.get_by_role('button',name='下载 Word 报告').first.click()
            await (await download.value).save_as(OUT/'portal-report-from-web.docx')
        # Same-component navigation must remount the provincial draft.
        await page.goto('http://127.0.0.1:4187/documents/jiangsu/application')
        await page.locator('input[autocomplete="name"]').fill('江苏切换检查')
        await page.evaluate("history.pushState(null,'','/documents/liaoning/application');window.dispatchEvent(new PopStateEvent('popstate'))")
        await page.wait_for_url('**/documents/liaoning/application')
        await page.get_by_text('辽宁省官方格式',exact=True).wait_for()
        assert await page.locator('input[autocomplete="name"]').input_value() != '江苏切换检查'
        await page.locator('input[placeholder="未填时按出生日期和申请日期计算"]').fill('42')
        await page.goto('http://127.0.0.1:4187/documents/hebei/application')
        await page.wait_for_url('**/province/hebei')
        assert await page.locator('form').count()==0
        await page.goto('http://127.0.0.1:4187/province/tianjin')
        await page.locator('.more-guides > summary').click()
        await page.locator('.district-workflow select').wait_for()
        await page.locator('.district-workflow').screenshot(path=str(OUT/'tianjin-district-flow.png'))
        await browser.close()
    (OUT/'results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
    print('Verified downloads:',len(records),flush=True)

if __name__=='__main__':asyncio.run(main())
