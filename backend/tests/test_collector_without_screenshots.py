"""Unit-only fake Playwright/Temp evidence. No real browser, screenshot or network."""
import asyncio
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
from types import ModuleType,SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import linux_guide_collector as collector

URL='https://www.zjzwfw.gov.cn/unit-only-collector-fixture'
DOCUMENT='https://files.gov.cn/unit-only-fixture.pdf'
REGION={'province':'浙江省','city':'杭州市','district':'淳安县','region_code':'330127'}
TEXT='Unit-only synthetic DOM fixture：劳动人事争议仲裁申请 办理材料 办理流程'
BODY=b'%PDF-1.7\nUnit-only synthetic attachment fixture\n'

class FakeDownload:
    url=DOCUMENT
    async def save_as(self,path):Path(path).write_bytes(BODY)

class FakeDownloadEvent:
    async def __aenter__(self):
        self.value=asyncio.get_running_loop().create_future();self.value.set_result(FakeDownload());return self
    async def __aexit__(self,*args):return False

class FakeLocator:
    def __init__(self,page,selector):self.page=page;self.selector=selector
    async def inner_text(self,**kwargs):
        if self.page.mode=='body_timeout':raise TimeoutError('unit-only body timeout')
        return 'Unit-only fixture 验证码' if self.page.mode=='captcha' else TEXT
    async def evaluate_all(self,*args):
        return [{'url':DOCUMENT,'label':'Unit-only 仲裁申请书'}] if self.page.mode=='anchor' else []
    async def scroll_into_view_if_needed(self,**kwargs):self.page.panel_seen=True
    async def click(self,**kwargs):
        if self.page.mode=='material_failure':raise TimeoutError('unit-only material click timeout')
        request=SimpleNamespace(url=DOCUMENT,frame=SimpleNamespace(page=self.page))
        response=SimpleNamespace(url=DOCUMENT,status=200,headers={'content-length':str(len(BODY)),'content-type':'application/pdf'},body=AsyncMock(return_value=BODY))
        for callback in self.page.context.listeners.get('request',[]):callback(request)
        for callback in self.page.context.listeners.get('response',[]):callback(response)

class ScreenshotForbiddenPage:
    """Fake calls are unit-only; even enabled screenshots never create PNG fixtures."""
    def __init__(self,context,mode,screenshots_allowed):
        self.context=context;self.mode=mode;self.screenshots_allowed=screenshots_allowed
        self.url=URL;self.main_frame=self;self.frames=[self];self.screenshot_calls=[];self.panel_seen=False
    async def goto(self,url,**kwargs):
        self.url=url
        if self.mode=='worker_timeout':await asyncio.Event().wait()
        if self.mode=='navigation_failure':raise OSError('unit-only navigation failed')
        if self.mode=='auth':
            self.url='https://www.zjzwfw.gov.cn/login'
            request=SimpleNamespace(url=self.url,frame=self,is_navigation_request=lambda:True)
            route=SimpleNamespace(request=request,abort=AsyncMock(),continue_=AsyncMock())
            await self.context.route_handler(route)
            assert route.abort.await_count==1
            raise OSError('unit-only auth navigation blocked')
        return SimpleNamespace(status=503 if self.mode=='http_failure' else 200)
    async def wait_for_load_state(self,*args,**kwargs):return None
    async def wait_for_timeout(self,*args):return None
    async def title(self):return 'Unit-only guide fixture'
    def locator(self,selector):return FakeLocator(self,selector)
    async def content(self):return '<html><body>'+TEXT+(' MATERIAL PANEL' if self.panel_seen else '')+'</body></html>'
    async def screenshot(self,**kwargs):
        self.screenshot_calls.append(kwargs)
        if not self.screenshots_allowed:raise AssertionError('UNIT FORBIDS EVERY SCREENSHOT CALL')
        return None  # No fake image bytes or fake image evidence.
    def on(self,*args):return None
    def expect_download(self,**kwargs):return FakeDownloadEvent()
    async def close(self):return None

class FakeContext:
    def __init__(self,mode,screenshots_allowed):self.mode=mode;self.screenshots_allowed=screenshots_allowed;self.pages=[];self.listeners={};self.closed=False
    async def route(self,pattern,handler):self.route_handler=handler
    async def new_page(self):
        page=ScreenshotForbiddenPage(self,self.mode if not self.pages else 'document',self.screenshots_allowed);self.pages.append(page);return page
    def on(self,event,callback):self.listeners.setdefault(event,[]).append(callback)
    def remove_listener(self,event,callback):self.listeners[event].remove(callback)
    async def close(self):self.closed=True

class FakeBrowser:
    def __init__(self,mode,screenshots_allowed):self.context=FakeContext(mode,screenshots_allowed);self.closed=False
    async def new_context(self,**kwargs):
        assert kwargs['service_workers']=='block' and kwargs['accept_downloads'] is True
        return self.context
    async def close(self):self.closed=True

class FakePlaywright:
    def __init__(self,mode,screenshots_allowed):self.mode=mode;self.browser=FakeBrowser(mode,screenshots_allowed);self.chromium=self
    async def launch(self,**kwargs):
        assert kwargs['chromium_sandbox'] is True and kwargs['headless'] is True
        if self.mode=='launch_failure':raise RuntimeError('unit-only browser launch failure')
        return self.browser
    async def __aenter__(self):return self
    async def __aexit__(self,*args):return False

class CollectorWithoutScreenshotsTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='collector-no-screenshot-unit-');self.addCleanup(temp.cleanup);self.root=Path(temp.name).resolve()
        # The optional SDK is not a CI dependency. Every capture patches this
        # factory with FakePlaywright; an unpatched call must never launch.
        sdk=ModuleType('playwright');sdk.__path__=[]
        async_api=ModuleType('playwright.async_api')
        def unpatched_factory():raise AssertionError('Unit capture requires an explicit FakePlaywright factory')
        async_api.async_playwright=unpatched_factory;sdk.async_api=async_api
        modules=patch.dict(sys.modules,{'playwright':sdk,'playwright.async_api':async_api})
        modules.start();self.addCleanup(modules.stop)
        self.fake_async_api=async_api
    def config(self,**updates):
        values=dict(data_dir=self.root/'var',release_dir=self.root/'release',browser_executable=self.root/'unit-browser-not-executable',allowed_hosts=('www.zjzwfw.gov.cn',),min_interval_seconds=0,max_attachments=2)
        values.update(updates);return collector.CollectorConfig(**values)
    def capture(self,mode='success',enabled=False):
        config=self.config(capture_screenshots=enabled);pw=FakePlaywright(mode,enabled);folder=self.root/('capture-'+mode)
        controls=[{'url':DOCUMENT,'control_text':'下载','text':'Unit-only 申请书下载','selector':'#unit-only-download'}] if mode in ['material','material_failure'] else []
        async def run():
            with patch('playwright.async_api.async_playwright',return_value=pw),patch('portal_interactions.material_controls',new=AsyncMock(return_value=controls)),patch('socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):
                return await collector.capture_official_guide(config,{'id':'a'*32,'attempt':1,'url':URL,'region':REGION},folder)
        result=asyncio.run(run())
        return config,pw,folder,result
    def assert_text_only(self,pw,folder,result):
        self.assertEqual([call for page in pw.browser.context.pages for call in page.screenshot_calls],[])
        self.assertFalse(list(folder.glob('*.png')))
        self.assertEqual(result['screenshot_capture'],{'enabled':False,'state':'omitted_by_configuration'})
        self.assertFalse(any(row['file'].endswith('.png') for row in result['evidence']))
        self.assertFalse(result['service_verified']);self.assertFalse(result['model_used'])
        self.assertTrue(result.get('observed_at'))
        for row in result['evidence']:
            body=(folder/row['file']).read_bytes();self.assertEqual((len(body),hashlib.sha256(body).hexdigest()),(row['bytes'],row['sha256']))
    def test_config_default_true_and_explicit_json_false(self):
        with self.assertRaisesRegex(AssertionError,'explicit FakePlaywright'):
            self.fake_async_api.async_playwright()
        self.assertIs(self.config().capture_screenshots,True)
        config_path=self.root/'config.json'
        config_path.write_text(json.dumps({'data_dir':str(self.root/'var'),'browser_executable':str(self.root/'unit-browser-not-executable'),'allowed_hosts':['www.zjzwfw.gov.cn'],'capture_screenshots':False}),encoding='utf8')
        loaded=collector.CollectorConfig.load(config_path,self.root/'release');self.assertIs(loaded.capture_screenshots,False)
        data=json.loads(config_path.read_text('utf8'));data.pop('capture_screenshots');config_path.write_text(json.dumps(data),encoding='utf8')
        self.assertIs(collector.CollectorConfig.load(config_path,self.root/'release').capture_screenshots,True)
    def test_config_rejects_non_boolean_direct_and_json(self):
        for invalid in ['false','true',0,1,None,[],{},0.0]:
            with self.subTest(value=invalid),self.assertRaisesRegex(ValueError,'capture_screenshots'):
                self.config(capture_screenshots=invalid)
            path=self.root/'invalid.json';path.write_text(json.dumps({'data_dir':str(self.root/'var'),'browser_executable':str(self.root/'unit-browser'),'allowed_hosts':['www.zjzwfw.gov.cn'],'capture_screenshots':invalid}),encoding='utf8')
            with self.subTest(json=invalid),self.assertRaisesRegex(ValueError,'capture_screenshots'):
                collector.CollectorConfig.load(path,self.root/'release')
    def test_success_false_keeps_text_html_hashes_and_truthful_omission(self):
        _,pw,folder,result=self.capture();self.assertEqual(result['state'],'guide_observed');self.assert_text_only(pw,folder,result)
        self.assertTrue((folder/'page.txt').is_file());self.assertTrue((folder/'page.html').is_file())
    def test_false_retains_real_attachment_bytes_from_unit_download_event(self):
        _,pw,folder,result=self.capture('anchor');self.assert_text_only(pw,folder,result)
        record=result['attachments'][0];self.assertEqual(record['state'],'downloaded')
        self.assertEqual((folder/record['file']).read_bytes(),BODY);self.assertEqual(record['sha256'],hashlib.sha256(BODY).hexdigest())
    def test_material_panel_false_keeps_dom_and_official_download_without_screenshot(self):
        _,pw,folder,result=self.capture('material');self.assert_text_only(pw,folder,result)
        self.assertEqual(result['attachments'][0]['state'],'downloaded')
        self.assertTrue((folder/'materials.txt').is_file());self.assertIn('MATERIAL PANEL',(folder/'materials.html').read_text('utf8'))
    def test_material_click_failure_false_does_not_capture_any_image(self):
        _,pw,folder,result=self.capture('material_failure');self.assert_text_only(pw,folder,result)
        self.assertEqual(result['state'],'guide_observed');self.assertEqual(result['attachments'][0]['state'],'failed')
    def test_navigation_and_body_timeout_false_preserve_classification_no_fallback_image(self):
        for mode in ['navigation_failure','body_timeout']:
            with self.subTest(mode=mode):
                _,pw,folder,result=self.capture(mode);self.assertEqual(result['state'],'network_failed');self.assert_text_only(pw,folder,result)
                self.assertTrue((folder/'failure.html').is_file());self.assertIn('error',result)
                if mode=='body_timeout':
                    self.assertFalse((folder/'failure.txt').exists())
                    self.assertIn({'file':'failure.txt','error_type':'TimeoutError'},result['text_capture_failures'])
    def test_auth_captcha_and_http_boundaries_false_never_call_screenshot(self):
        for mode,expected in [('auth','auth_required'),('captcha','captcha_required'),('http_failure','http_failed')]:
            with self.subTest(mode=mode):
                _,pw,folder,result=self.capture(mode);self.assertEqual(result['state'],expected);self.assert_text_only(pw,folder,result)
    def test_default_true_preserves_page_and_material_call_sites_unit_only(self):
        _,pw,folder,result=self.capture('material',True)
        calls=[Path(call['path']).name for call in pw.browser.context.pages[0].screenshot_calls]
        self.assertEqual(calls,['page.png','materials.png']);self.assertEqual(result['state'],'guide_observed')
        self.assertNotIn('screenshot_capture',result);self.assertFalse(list(folder.glob('*.png')))
    def test_default_true_failure_still_uses_failure_screenshot_call_unit_only(self):
        _,pw,folder,result=self.capture('navigation_failure',True)
        self.assertEqual([Path(c['path']).name for c in pw.browser.context.pages[0].screenshot_calls],['failure.png'])
        self.assertEqual(result['state'],'network_failed');self.assertFalse(list(folder.glob('*.png')))
    def test_text_only_result_replay_uses_temp_outbox_without_png_or_self_ack(self):
        from collector_issue_events import CollectorIssueOutbox
        config= self.config(capture_screenshots=False,issue_outbox=self.root/'issues.sqlite')
        q=collector.GuideQueue(config);q.submit([{'url':URL,'region':REGION}]);job=q.claim()
        pw=FakePlaywright('success',False);folder=q.root/'evidence'/job['id']/'attempt-1'
        async def run():
            with patch('playwright.async_api.async_playwright',return_value=pw),patch('portal_interactions.material_controls',new=AsyncMock(return_value=[])):
                return await collector.capture_official_guide(config,job,folder)
        result=asyncio.run(run());self.assert_text_only(pw,folder,result)
        q.finish(job['id'],result)
        reopened=collector.GuideQueue(config);report=reopened.replay_issue_events();self.assertEqual(report['failed'],0)
        events=CollectorIssueOutbox(config.issue_outbox).pending();self.assertEqual(len(events),1)
        self.assertEqual(events[0]['delivery_status'],'PENDING_OPENCLAW');self.assertNotIn('.png',json.dumps(events))
        self.assertEqual(reopened.get(job['id'])['result']['screenshot_capture']['state'],'omitted_by_configuration')
    def test_worker_outer_timeout_keeps_omission_metadata_and_closes_fake_browser(self):
        config=self.config(capture_screenshots=False);q=collector.GuideQueue(config);job=q.submit([{'url':URL,'region':REGION}])[0]
        pw=FakePlaywright('worker_timeout',False);original_read=Path.read_text;original_wait=asyncio.wait_for
        def read(path,*args,**kwargs):
            return ' '.join(['0']*21+['unit-only-start-ticks']) if path.as_posix()=='/proc/self/stat' else original_read(path,*args,**kwargs)
        async def fast_wait(awaitable,timeout):return await original_wait(awaitable,min(timeout,.01))
        async def run():
            with patch.object(collector,'worker_lock',return_value=nullcontext()),patch.object(Path,'read_text',read),patch('playwright.async_api.async_playwright',return_value=pw),patch.object(collector.asyncio,'wait_for',new=fast_wait):
                await collector.run_worker(config,once=True)
        asyncio.run(run());result=q.get(job['id'])['result']
        self.assertEqual(result['state'],'runtime_failed');self.assertEqual(result['screenshot_capture'],{'enabled':False,'state':'omitted_by_configuration'})
        self.assertEqual([c for p in pw.browser.context.pages for c in p.screenshot_calls],[])
        self.assertTrue(pw.browser.context.closed and pw.browser.closed);self.assertFalse(any(r['file'].endswith('.png') for r in result['evidence']))

if __name__=='__main__':unittest.main(verbosity=2)
