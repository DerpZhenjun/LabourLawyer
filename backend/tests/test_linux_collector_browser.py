"""Opt-in Linux browser regression with offline fixtures, not official evidence."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


@unittest.skipUnless(sys.platform=='linux' and os.environ.get('LABOURLAWYER_COLLECTOR_BROWSER'), 'Requires the isolated Linux collector browser')
class BrowserCollectorTests(unittest.TestCase):
    def test_popup_document_download_from_visible_public_control_is_captured(self):
        from linux_guide_collector import CollectorConfig,click_document_control
        from playwright.async_api import async_playwright
        async def run():
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary)
                config=CollectorConfig(data_dir=root/'var',release_dir=root/'release',browser_executable=Path(os.environ['LABOURLAWYER_COLLECTOR_BROWSER']),allowed_hosts=('www.zjzwfw.gov.cn',),min_interval_seconds=0)
                async with async_playwright() as pw:
                    browser=await pw.chromium.launch(executable_path=str(config.browser_executable),headless=True,chromium_sandbox=True)
                    context=await browser.new_context(accept_downloads=True)
                    async def fixture(route):
                        if route.request.url.endswith('/fixture.pdf'):
                            await route.fulfill(status=200,headers={'Content-Type':'application/pdf','Content-Disposition':'attachment; filename="fixture.pdf"'},body=b'%PDF-1.7\npublic fixture\n')
                        else:
                            await route.fulfill(status=200,content_type='text/html',body='<button onclick="window.open(\'/fixture.pdf\')">Download fixture</button>')
                    await context.route('**/*',fixture)
                    page=await context.new_page()
                    await page.goto('https://www.zjzwfw.gov.cn/collector-offline-fixture')
                    result={}
                    await click_document_control(config,page,page.get_by_role('button'),result,root,1)
                    self.assertEqual(result['state'],'downloaded')
                    self.assertTrue((root/result['file']).is_file())
                    self.assertEqual(result['template_kind'],'unknown_until_review')
                    await context.close();await browser.close()
        asyncio.run(run())


if __name__=='__main__':unittest.main()
