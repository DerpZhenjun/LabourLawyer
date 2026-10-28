"""Observed onclick controls become native refs without changing the page."""
import asyncio,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from openclaw_browser_tasks import PUBLIC_CONTROL_SEMANTICS
from playwright.async_api import async_playwright

class PublicControlsTests(unittest.IsolatedAsyncioTestCase):
    async def test_region_picker_and_search_checkbox_are_not_confused(self):
        temp=ROOT/'.runtime/public-control-tests';temp.mkdir(exist_ok=True)
        with __import__('unittest.mock',fromlist=['patch']).patch.dict(os.environ,{'TEMP':str(temp),'TMP':str(temp)}):
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
                page=await browser.new_page();await page.set_content('<div style="cursor:pointer" onclick="window.region=1"><span>全省</span></div><form class="search"><input type="checkbox" name="searchAll"><input type="search"><button>搜索</button></form>')
                await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                await page.get_by_role('button',name='全省',exact=True).click()
                self.assertEqual(await page.evaluate('window.region'),1)
                self.assertIsNone(await page.locator('input[type=checkbox]').get_attribute('aria-label'))
                self.assertEqual(await page.get_by_role('searchbox',name='公开事项搜索').count(),1)
                await browser.close()

    async def test_nested_guide_button_uses_its_service_name_without_wrapper_collision(self):
        temp=ROOT/'.runtime/public-control-tests';temp.mkdir(exist_ok=True)
        with __import__('unittest.mock',fromlist=['patch']).patch.dict(os.environ,{'TEMP':str(temp),'TMP':str(temp)}):
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
                page=await browser.new_page();await page.set_content('<section>劳动人事争议仲裁申办<a href="javascript:;"><button onclick="window.hit=1">办事指南</button></a></section>')
                await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                self.assertEqual(await page.get_by_role('button',name='办事指南：劳动人事争议仲裁申办').count(),1)
                self.assertIsNone(await page.locator('a').get_attribute('aria-label'))
                await page.get_by_role('button',name='办事指南：劳动人事争议仲裁申办').click()
                self.assertEqual(await page.evaluate('window.hit'),1)
                await browser.close()

    async def test_search_history_is_not_named_as_an_actual_labour_result(self):
        temp=ROOT/'.runtime/public-control-tests';temp.mkdir(exist_ok=True)
        with __import__('unittest.mock',fromlist=['patch']).patch.dict(os.environ,{'TEMP':str(temp),'TMP':str(temp)}):
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
                page=await browser.new_page();await page.set_content('<section>搜索历史<a href="#">劳动人事争议仲裁</a></section><section><a href="/guide">劳动人事争议仲裁申请</a></section>')
                await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                self.assertEqual(await page.get_by_role('link',name='搜索历史：劳动人事争议仲裁').count(),1)
                self.assertEqual(await page.get_by_role('link',name='劳动人事争议仲裁申请',exact=True).count(),1)
                await browser.close()

    async def test_css_disabled_confirmation_is_observed_then_cleared(self):
        temp=ROOT/'.runtime/public-control-tests';temp.mkdir(exist_ok=True)
        with __import__('unittest.mock',fromlist=['patch']).patch.dict(os.environ,{'TEMP':str(temp),'TMP':str(temp)}):
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
                page=await browser.new_page();await page.set_content('<button class="dissure">确 认</button>')
                await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                self.assertTrue(await page.get_by_role('button',name='确认（当前不可点击）').is_disabled())
                await page.locator('button').evaluate("n=>n.className=''")
                await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                self.assertFalse(await page.get_by_role('button',name='确认').is_disabled())
                await browser.close()

    async def test_rotating_search_hint_keeps_a_stable_native_name(self):
        temp=ROOT/'.runtime/public-control-tests';temp.mkdir(exist_ok=True)
        with __import__('unittest.mock',fromlist=['patch']).patch.dict(os.environ,{'TEMP':str(temp),'TMP':str(temp)}):
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
                page=await browser.new_page();await page.set_content('<div class="search"><input type="search" placeholder="旅馆开办"><button>搜 索</button></div><input placeholder="手机号码">')
                await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                await page.locator('input[type=search]').evaluate("n=>n.placeholder='户口迁出'")
                await page.get_by_role('searchbox',name='公开事项搜索',exact=True).fill('劳动仲裁')
                self.assertEqual(await page.locator('input[type=search]').input_value(),'劳动仲裁')
                self.assertIsNone(await page.get_by_placeholder('手机号码').get_attribute('aria-label'))
                await browser.close()

    async def test_guide_ref_name_uses_its_own_visible_service_row(self):
        temp=ROOT/'.runtime/public-control-tests';temp.mkdir(exist_ok=True)
        with __import__('unittest.mock',fromlist=['patch']).patch.dict(os.environ,{'TEMP':str(temp),'TMP':str(temp)}):
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
                page=await browser.new_page()
                await page.set_content('<section><div>劳动人事争议仲裁申请<button onclick="window.hit=1">办事指南</button><button>在线办理</button></div><div>计量纠纷调解<button>办事指南</button></div></section>')
                before=await page.locator('body').inner_text();await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                self.assertEqual(await page.locator('body').inner_text(),before)
                await page.get_by_role('button',name='办事指南：劳动人事争议仲裁申请').click()
                self.assertEqual(await page.evaluate('window.hit'),1)
                self.assertEqual(await page.get_by_role('button',name='办事指南',exact=True).count(),1)
                await browser.close()

    async def test_clickable_public_card_gets_role_while_apply_and_text_are_untouched(self):
        temp=ROOT/'.runtime/public-control-tests';temp.mkdir(exist_ok=True)
        previous={k:os.environ.get(k) for k in ('TEMP','TMP')};os.environ.update(TEMP=str(temp),TMP=str(temp))
        try:
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
                page=await browser.new_page()
                await page.set_content('<li onclick="window.hit=1">【瑶海区】劳动人事争议仲裁申请</li><li onclick="window.danger=1">在线办理</li><div>劳动人事争议仲裁申请指南</div>')
                before=await page.locator('body').inner_text()
                controls=await page.evaluate(PUBLIC_CONTROL_SEMANTICS)
                self.assertEqual(len(controls),1);self.assertEqual(await page.locator('body').inner_text(),before)
                self.assertEqual(await page.get_by_role('button',name='在线办理').count(),0)
                self.assertEqual(await page.get_by_role('button',name='劳动人事争议仲裁申请指南',exact=True).count(),0)
                await page.get_by_role('button',name='【瑶海区】劳动人事争议仲裁申请',exact=True).click()
                self.assertEqual(await page.evaluate('window.hit'),1)
                self.assertIsNone(await page.evaluate('window.danger??null'))
                await browser.close()
        finally:
            for key,value in previous.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
if __name__=='__main__':unittest.main()
