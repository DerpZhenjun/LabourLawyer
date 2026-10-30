import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import AsyncMock,MagicMock
import asyncio
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import openclaw_browser_tasks as tasks
import openclaw_task_service as service
from openclaw_job_lock import acquisition_lock

class BrowserRecoveryTests(unittest.TestCase):
    def test_gateway_cold_start_wait_is_bounded_and_emitted(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            lane=object.__new__(tasks.BrowserLane)
            lane.root=Path(temp);lane.prefix=['node','openclaw.mjs'];lane.port=12345;lane.env={}
            lane._start_rpc=MagicMock();lane.call=MagicMock();lane.__exit__=MagicMock()
            gateway=MagicMock();gateway.poll.return_value=None
            with patch.object(tasks.subprocess,'Popen',return_value=gateway),patch.object(tasks.socket,'create_connection',side_effect=OSError('not ready')),patch.object(tasks.time,'monotonic',side_effect=[0,1,46]),patch.object(tasks.time,'sleep'),patch.object(tasks,'emit') as event:
                with self.assertRaisesRegex(TimeoutError,'within 45s'):lane.__enter__()
            self.assertEqual(event.call_args_list[0].kwargs['timeout_seconds'],45)
            self.assertEqual(event.call_args_list[-1].args,('browser','failed'))
            lane.__exit__.assert_called_once()
            lane.log.close()

    def test_login_frame_search_cannot_replace_public_root(self):
        lane=object.__new__(tasks.BrowserLane)
        root={'snapshot':'- link "个人服务" [ref=e1]','refs':{'e1':{}}}
        framed={'snapshot':'- textbox "搜索" [ref=e2]\n- button "搜索" [ref=e3]','refs':{'e2':{},'e3':{}}}
        doc={'url':'http://www.hbzwfw.gov.cn/','frames':[{'src':'http://www.hbzwfw.gov.cn/login/panel','visible':True}]}
        lane.call=MagicMock(side_effect=[{},root,{'result':doc},framed,root])
        result=lane.snapshot('tab')
        self.assertNotIn('active_frame',result);self.assertTrue(result['restored_root'])

    def test_selected_district_without_city_breadcrumb_is_confirmed(self):
        state={'snapshot':'- link "石家庄市" [ref=e1]\n- link "新华区" [ref=e2]\n- link "确定" [ref=e3]','document':{'text':'地区切换\n您选择的是：新华区\n确定\n取消'}}
        self.assertEqual(tasks.public_control_plan(state,'石家庄市')['ref'],'e3')

    def test_hover_uses_current_public_ref_and_the_native_browser_action(self):
        state='- button "站点切换" [ref=e2]\n- link "在线办理" [ref=e3]'
        plan=tasks.validate_action({'action':'hover','ref':'e2'},state)
        lane=object.__new__(tasks.BrowserLane)
        with patch.object(lane,'call',return_value={'ok':True}) as call:
            lane.act(plan,'target')
            call.assert_called_once_with('hover','e2','--target-id','target')
        with self.assertRaises(ValueError):tasks.validate_action({'action':'hover','ref':'e99'},state)
        with self.assertRaises(ValueError):tasks.validate_action({'action':'hover','ref':'e3'},state)

    def test_hainan_region_dialog_uses_first_actual_district_before_background_guide(self):
        state={'snapshot':'- button "办事指南：劳动人事争议仲裁申办" [ref=e1]\n- generic "美兰区" [ref=e2]\n- generic "琼山区" [ref=e3]\n- button "确定" [ref=e4]','document':{'text':'请选择办理地点：海口市\n您选择是:\n海南省 > 海口市地级市级单位 > 海口市人力资源和社会保障局\n确定\n取消'}}
        self.assertEqual(tasks.public_control_plan(state,'海口市')['ref'],'e2')
        state['document']['text']='您选择是: 海南省 > 海口市 > 美兰区\n确定\n取消'
        self.assertEqual(tasks.public_control_plan(state,'海口市')['ref'],'e4')

    def test_employee_guide_precedes_case_lookup_under_same_parent_matter(self):
        state={'snapshot':'- link "查看指南：案件进度查询 · 劳动人事争议仲裁申请" [ref=e1]\n- link "查看指南：用人单位申请立案 · 劳动人事争议仲裁申请" [ref=e2]\n- link "查看指南：劳动者申请立案 · 劳动人事争议仲裁申请" [ref=e3]'}
        self.assertEqual(tasks.public_control_plan(state,'武汉市')['ref'],'e3')
        with self.assertRaises(ValueError):tasks.validate_action({'action':'click','ref':'e1'},state['snapshot'])

    def test_stuck_search_uses_remaining_queries_and_never_private_fields(self):
        state={'snapshot':'- textbox "公开事项搜索" [ref=e4]'}
        history=[{'plan':{'action':'type','text':'劳动仲裁'}}]
        self.assertEqual(tasks.recovery_search_plan(state,history)['text'],'劳动人事争议仲裁')
        history.extend({'plan':{'action':'type','text':w}} for w in ('劳动人事争议仲裁','劳动人事争议调解'))
        self.assertIsNone(tasks.recovery_search_plan(state,history))
        self.assertIsNone(tasks.recovery_search_plan({'snapshot':'- textbox "手机号码" [ref=e2]'},[]))

    def test_browser_uses_installed_normal_chrome_identity_without_disabling_sandbox(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime/openclaw-tests') as tmp:
            lane=tasks.BrowserLane(Path(tmp))
            config=json.loads((Path(tmp)/'openclaw.json').read_text('utf8'))
            self.assertFalse(config['browser']['noSandbox'])
            self.assertTrue(config['browser']['headless'])
            identity=next(x for x in config['browser']['extraArgs'] if x.startswith('--user-agent='))
            self.assertNotIn('HeadlessChrome',identity)
            self.assertNotIn('--ignore-certificate-errors',config['browser']['extraArgs'])

    def test_provincial_header_picker_then_observed_capital_control(self):
        state={'province_name':'黑龙江省','snapshot':'- generic "黑龙江省" [ref=e8] [cursor:pointer]\n- link "黑龙江省" [ref=e9]','document':{'text':'黑龙江省\n个人服务'}}
        self.assertEqual(tasks.public_control_plan(state,'哈尔滨市')['ref'],'e8')
        state['snapshot']+='\n- button "哈尔滨市" [ref=e10]'
        self.assertEqual(tasks.public_control_plan(state,'哈尔滨市')['ref'],'e10')
        state['document']['text']='哈尔滨市\n个人服务'
        self.assertIsNone(tasks.public_control_plan(state,'哈尔滨市'))

    def test_disabled_confirmation_selects_district_list_item_not_breadcrumb(self):
        state={'snapshot':'  - button "城东区" [ref=e62] [nth=1]\n    - button "城东区" [ref=e63] [nth=2]\n  - button "城东区" [ref=e57]\n  - button "确认" [ref=e58] [disabled]','document':{'text':'地区切换\n您选择的是：青海省 西宁市 城东区\n确 认\n取 消'}}
        plan=tasks.public_control_plan(state,'西宁市')
        self.assertEqual(plan['ref'],'e63')
        tasks.validate_action(plan,state['snapshot'])

    def test_native_region_picker_uses_first_district_then_exact_confirmation(self):
        state={'snapshot':'- button "西宁市" [ref=e55]\n- button "城东区" [ref=e61]\n- button "确 认" [ref=e56]','document':{'text':'地区切换\n您选择的是：青海省 西宁市\n确 认\n取 消'}}
        self.assertEqual(tasks.public_control_plan(state,'西宁市')['ref'],'e61')
        state['document']['text']='地区切换\n您选择的是：青海省 西宁市 城东区\n确 认\n取 消'
        self.assertEqual(tasks.public_control_plan(state,'西宁市')['ref'],'e56')
        tasks.validate_action(tasks.public_control_plan(state,'西宁市'),state['snapshot'])

    def test_public_guide_association_and_ip_confirmation_use_current_refs(self):
        state={'snapshot':'- button "办事指南" [ref=e1]\n- button "办事指南：劳动人事争议仲裁申请" [ref=e2]','document':{'text':'搜索结果'}}
        self.assertEqual(tasks.public_control_plan(state,'西宁市')['ref'],'e2')
        state={'snapshot':'- button "确定" [ref=e3]','document':{'text':'当前IP所在地为长沙市，是否搜索IP所在地结果?'}}
        self.assertEqual(tasks.public_control_plan(state,'长沙市')['ref'],'e3')

    def test_animated_screenshots_do_not_reset_stall_detection(self):
        plan={'action':'click','ref':'e142'}
        self.assertEqual(tasks.progress_signature(plan,'- link "南宁市" [ref=e142] [new]\n1 new element(s) since last snapshot'),tasks.progress_signature(plan,'- link "南宁市" [ref=e142]'))
        self.assertNotEqual(tasks.progress_signature(plan,'- link "南宁市" [ref=e142]'),tasks.progress_signature(plan,'- button "确认" [ref=e142]'))

    def test_unrelated_iframe_cannot_replace_root_search_controls(self):
        for framed in ({'snapshot':'(empty)','refs':{}},{'snapshot':'- link "帮助" [ref=e7]','refs':{'e7':{}}},{'snapshot':'- link "登录" [ref=e7]\nLinks:\n1. 劳动人事争议仲裁申请 -> https://www.shandong.gov.cn/guide','refs':{'e7':{}}}):
            with self.subTest(framed=framed):
                lane=object.__new__(tasks.BrowserLane)
                root={'snapshot':'- textbox "搜索" [ref=e1]','refs':{'e1':{}}}
                doc={'url':'https://search.shandong.gov.cn/','text':'搜索结果','frames':[{'src':'https://www.shandong.gov.cn/footer','visible':True}]}
                lane.call=MagicMock(side_effect=[{},root,{'result':doc},framed,root])
                result=lane.snapshot('tab')
                self.assertIn('e1',result['refs']);self.assertNotIn('active_frame',result)
                self.assertTrue(result['restored_root']);self.assertNotIn('--frame',lane.call.call_args.args)

    def test_visible_guideline_frame_retains_native_refs(self):
        lane=object.__new__(tasks.BrowserLane)
        root={'snapshot':'- link "首页" [ref=e1]','refs':{'e1':{}}}
        framed={'snapshot':'- button "仲裁申请书下载" [ref=e8]','refs':{'e8':{}},'stats':{'refs':1}}
        doc={'url':'https://www.sxzwfw.gov.cn/guide','text':'办事指南','frames':[{'src':'https://zwfwpt.sxzwfw.gov.cn/guide','visible':True}]}
        lane.call=MagicMock(side_effect=[{},root,{'result':doc},framed])
        result=lane.snapshot('tab')
        self.assertEqual(result['refs'],framed['refs']);self.assertEqual(result['stats'],framed['stats'])

    def test_only_search_input_can_be_in_an_initially_empty_government_frame(self):
        lane=object.__new__(tasks.BrowserLane)
        root={'snapshot':'- Iframe "第三方政务搜索服务" [ref=e1]','refs':{'e1':{}}}
        framed={'snapshot':'- textbox [ref=e2]\n- button "搜索" [ref=e3]','refs':{'e2':{},'e3':{}}}
        doc={'url':'https://ywtb.qhzwfw.gov.cn/','frames':[{'src':'https://ywtb.qhzwfw.gov.cn/govportal/pc/search/search','visible':True}]}
        lane.call=MagicMock(side_effect=[{},root,{'result':doc},framed])
        self.assertEqual(lane.snapshot('tab')['refs'],framed['refs'])

    def test_hebei_unnamed_input_with_adjacent_search_is_allowed(self):
        tasks.validate_action({'action':'type','ref':'e21','text':'劳动仲裁'},'- textbox [ref=e21] value="请输入您想了解的内容"\n- link "搜索" [ref=e22]')
        tasks.validate_action({'action':'type','ref':'e36','text':'劳动仲裁'},'- textbox [ref=e36] value="劳动人事争议仲裁"\n- generic [ref=e37]\n- button "搜 索" [ref=e33]')
        with self.assertRaises(ValueError):
            tasks.validate_action({'action':'type','ref':'e21','text':'劳动仲裁'},'- textbox "手机号码" [ref=e21]\n- button "搜索" [ref=e22]')

    def test_rpc_translation_uses_native_search_and_snapshot_arguments(self):
        lane=object.__new__(tasks.BrowserLane)
        request=lane._rpc_request(('type','e21','劳动仲裁','--target-id','tab','--slowly','--submit'),40)
        self.assertEqual(request['body'],{'kind':'type','ref':'e21','text':'劳动仲裁','targetId':'tab','slowly':True,'submit':True})
        snapshot=lane._rpc_request(('snapshot','--target-id','tab','--format','ai','--interactive','--depth','18'),40)
        self.assertEqual(snapshot['query']['targetId'],'tab');self.assertTrue(snapshot['query']['interactive'])

    def test_rpc_late_response_cannot_be_used_for_next_action(self):
        lane=object.__new__(tasks.BrowserLane);lane.rpc=MagicMock();lane.replies=tasks.queue.Queue()
        lane.replies.put({'id':'previous-timed-out-request','result':{'wrong':True}})
        lane.replies.put({'id':'current-request','result':{'ok':True}})
        with patch.object(tasks.uuid,'uuid4',return_value=SimpleNamespace(hex='current-request')):
            self.assertEqual(lane.call('tabs'),{'ok':True})

    def test_incomplete_parent_batch_is_not_silently_published(self):
        spec=importlib.util.spec_from_file_location('acquire_under_test',ROOT/'scripts/openclaw-acquire-guides.py')
        acquire=importlib.util.module_from_spec(spec);spec.loader.exec_module(acquire)
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        guide={'guide_url':'https://www.sxzwfw.gov.cn/guide','service_name':'劳动人事争议仲裁申请','materials':['申请书']}
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            experience=Path(tmp);(experience/'old/shanxi').mkdir(parents=True)
            tasks.save(experience/'old/shanxi/experience.json',{'slug':'shanxi'})
            tasks.save(experience/'latest.json',{'id':'old'})
            with patch.object(acquire,'EXPERIENCE_ROOT',experience),patch.object(acquire,'load_experiences',return_value={'run_id':'old','provinces':{'shanxi':{}}}):
                with self.assertRaisesRegex(RuntimeError,'missing province evidence'):
                    acquire.publish(Path(tmp)/'native',{'shanxi':{'selected_guide':guide}})
            self.assertEqual(json.loads((experience/'latest.json').read_text())['id'],'old')
            self.assertEqual(sorted(p.name for p in experience.iterdir()),['latest.json','old'])

    def test_refresh_publishes_only_after_native_ai_succeeds_and_retains_parent(self):
        from province_documents import PROVINCE_DOCUMENTS
        spec=importlib.util.spec_from_file_location('refresh_under_test',ROOT/'scripts/refresh-province-experiences.py')
        refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        for failed in (True,False):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory(dir=parent) as tmp:
                root=Path(tmp);experience=root/'templates/_reports/province-experiences';run=experience/'new-batch';run.mkdir(parents=True)
                source=root/'templates/_reports/portal-audits';source.mkdir(parents=True);tasks.save(source/'latest.json',{'id':'source'})
                tasks.save(experience/'latest.json',{'id':'previous-valid-batch'})
                tasks.save(run/'experiences.json',{'parent_run':'previous-valid-batch','openclaw_run':'native-test'})
                for slug,p in PROVINCE_DOCUMENTS.items():
                    tasks.save(run/slug/'experience.json',{'slug':slug,'name':p['name'],'state':'fresh','selected_guide':{'guide_url':f'https://test.gov.cn/guide/{slug}','service_name':'劳动人事争议仲裁申请','materials':['申请书']},**({'openclaw_task':'native-test/shanxi'} if slug=='shanxi' else {})})
                browser=MagicMock();browser.close=AsyncMock();pw=MagicMock();pw.chromium.launch=AsyncMock(return_value=browser);manager=MagicMock();manager.__aenter__=AsyncMock(return_value=pw);manager.__aexit__=AsyncMock(return_value=False)
                reviewed=[]
                def review(profile,context):
                    reviewed.append((profile['slug'],context))
                    return {'state':'failed','parse_state':'invalid'} if failed and profile['slug']=='shanxi' else {'state':'reviewed','parse_state':'valid'}
                synthetic_ua='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                with patch.object(refresh,'ROOT',root),patch.object(refresh,'EXPERIENCE_ROOT',experience),patch.object(refresh,'review',review),patch('playwright.async_api.async_playwright',return_value=manager),patch('browser_identity.normal_user_agent',return_value=synthetic_ua),patch('subprocess.run') as execute,patch.dict('os.environ',{'LABOURLAWYER_ARTIFACT_PYTHON':str(root/'missing-runtime')}):
                    asyncio.run(refresh.main(SimpleNamespace(resume=str(run),without_browser_agent=True,with_browser_agent=False)))
                pw.chromium.launch.assert_awaited_once()
                self.assertEqual(pw.chromium.launch.call_args.kwargs['args'],['--user-agent='+synthetic_ua])
                manager.__aexit__.assert_awaited_once()
                self.assertEqual([slug for slug,_ in reviewed],list(PROVINCE_DOCUMENTS))
                self.assertTrue(all(context==run for _,context in reviewed))
                latest=json.loads((experience/'latest.json').read_text(encoding='utf8'))
                self.assertEqual(latest['id'],'previous-valid-batch' if failed else 'new-batch')
                manifest=json.loads((run/'experiences.json').read_text(encoding='utf8'));self.assertEqual(manifest['parent_run'],'previous-valid-batch')
                calls=[call.args[0] for call in execute.call_args_list]
                self.assertIn('--no-publish',calls[0]);self.assertEqual(len(calls),1 if failed else 2)
    def test_new_guides_wait_for_successful_parseable_ai_review(self):
        from province_experience import pending_openclaw_reviews
        profiles={'a':{'openclaw_task':'run/a','ai_review':{'state':'failed'}},'b':{'openclaw_task':'run/b','ai_review':{'state':'reviewed','parse_state':'invalid'}},'c':{'openclaw_task':'run/c','ai_review':{'state':'reviewed','parse_state':'valid'}},'d':{'ai_review':{'state':'failed'}}}
        self.assertEqual(pending_openclaw_reviews(profiles),['a','b'])

    def test_other_province_guide_is_not_promoted_and_discovered_portal_is_recognized(self):
        from province_experience import guide_belongs_to_province
        self.assertFalse(guide_belongs_to_province({'guide_url':'https://zwfw.tj.gov.cn/guide','region_code':'120000'},'shanxi'))
        self.assertTrue(guide_belongs_to_province({'guide_url':'https://www.sxzwfw.gov.cn/guide','region_code':'140100'},'shanxi'))
        self.assertFalse(guide_belongs_to_province({'guide_url':'https://www.sxzwfw.gov.cn/guide','region_code':'120000'},'shanxi'))
    def test_rejects_submission_login_arbitrary_navigation_and_text(self):
        snapshot='- button "在线办理" [ref=e1]\n- textbox "搜索" [ref=e2]\n- link "查看指南" [ref=e3]\n  /url: https://zwfw.tj.gov.cn/guide'
        for plan in ({'action':'click','ref':'e1'},{'action':'click','ref':'e9'},{'action':'type','ref':'e3','text':'劳动仲裁'},{'action':'type','ref':'e2','text':'个人信息'},{'action':'navigate','url':'https://evil.com'},{'action':'navigate','url':'https://unseen.gov.cn/'},{'action':'evaluate','code':'x'}):
            with self.subTest(plan=plan),self.assertRaises(ValueError):tasks.validate_action(plan,snapshot)
        tasks.validate_action({'action':'type','ref':'e2','text':'劳动仲裁'},snapshot)
        tasks.validate_action({'action':'navigate','url':'https://zwfw.tj.gov.cn/guide'},snapshot)

    def test_ip_confirmation_and_public_guide_allowed(self):
        for label in ('确定','查看指南','申请材料','办理流程'):
            tasks.validate_action({'action':'click','ref':'e1'},f'- button "{label}" [ref=e1]')

    def test_certificate_interstitial_cannot_be_bypassed_by_model(self):
        with self.assertRaises(ValueError):tasks.validate_action({'action':'click','ref':'e1'},'NET::ERR_CERT_DATE_INVALID\n- button "继续访问" [ref=e1]')
        tasks.validate_action({'action':'blocked'},'NET::ERR_CERT_DATE_INVALID')

    def test_refs_do_not_match_prefixes(self):
        with self.assertRaises(ValueError):tasks.validate_action({'action':'click','ref':'e1'},'- button "查看指南" [ref=e10]')

    def test_prior_observed_public_url_can_be_revisited_but_auth_cannot(self):
        tasks.validate_action({'action':'navigate','url':'https://test.gov.cn/guide'},'',{'https://test.gov.cn/guide'})
        with self.assertRaises(ValueError):tasks.validate_action({'action':'navigate','url':'https://test.gov.cn/login'},'',{'https://test.gov.cn/login'})

    def test_private_ports_and_malformed_urls_rejected(self):
        for url in ('http://localhost:11434','https://a.gov.cn:7000','https://a.gov.cn:invalid','https://gov.cn.evil.com','https://x:y@a.gov.cn/'):
            self.assertFalse(tasks.official_url(url))
        self.assertTrue(tasks.official_url('https://zwfw.hubei.gov.cn:60443/hbfss/index.html'))
        self.assertTrue(tasks.official_url('https://zwfwpt.sxzwfw.gov.cn:10002/aaa/person/public'))
        self.assertFalse(tasks.official_url('https://other.gov.cn:60443/'))

    def test_native_action_failure_is_observed_again_and_ai_finish_is_not_proof(self):
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temporary:
            folder=Path(temporary)
            class Lane:
                cdp_port=1
                def __init__(self,*_):self.actions=[]
                def __enter__(self):return self
                def __exit__(self,*_):pass
                def call(self,op,*_):return {'targetId':'tab'} if op=='open' else {'tabs':[{'targetId':'tab','url':'https://test.gov.cn/'}]}
                def snapshot(self,*_):return {'snapshot':'- button "查看指南" [ref=e1]'}
                def screenshot(self,target,path):path.write_bytes(b'fixture');return {'filename':path.name,'sha256':'test'}
                def act(self,*_):raise RuntimeError('Element not visible. Run a new snapshot.')
            plans=iter([{'action':'click','ref':'e1'},{'action':'finish'}])
            def infer(image,output,*_,**kwargs):
                tasks.save(output,{'result':{'outputs':[{'text':json.dumps(next(plans))}]}});return output
            with patch.object(tasks,'BrowserLane',Lane),patch.object(tasks,'describe_image',infer):
                result=tasks.run_task('tianjin','https://test.gov.cn/',folder,'天津市',max_steps=2,inspect=lambda *_:None)
            self.assertEqual(result['state'],'step_limit');self.assertFalse(result['status']['guide_found'])
            self.assertIn('execution_error',result['actions'][0]);self.assertEqual(len(result['actions']),2)

    def test_success_requires_independent_inspector_and_keeps_fill_disabled(self):
        # Reuse the fake browser but confirm actual structured guide evidence.
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        from unittest.mock import MagicMock
        lane=MagicMock();lane.cdp_port=1;lane.call.side_effect=lambda op,*_:{'targetId':'t'} if op=='open' else {'tabs':[{'targetId':'t','url':'https://test.gov.cn/guide'}]} if op=='tabs' else {'ok':True};lane.snapshot.return_value={'snapshot':'办理流程'};lane.screenshot.return_value={'filename':'step.png','sha256':'test'}
        with tempfile.TemporaryDirectory(dir=parent) as tmp,patch.object(tasks,'BrowserLane') as factory,patch.object(tasks,'describe_image') as infer:
            factory.return_value.__enter__.return_value=lane
            result=tasks.run_task('tianjin','https://test.gov.cn/guide',Path(tmp),'天津市',inspect=lambda *_:{'downloaded_files':[{'sha256':'verified'}]})
            infer.assert_not_called()
        self.assertEqual(result['state'],'acquired');self.assertTrue(result['status']['guide_found']);self.assertTrue(result['status']['template_downloaded']);self.assertFalse(result['status']['fill_verified'])

    def test_acquisition_lock_rejects_parallel_worker_and_recovers(self):
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as folder,patch('openclaw_job_lock.PATH',Path(folder)/'lock'):
            with acquisition_lock():
                with self.assertRaises(RuntimeError):
                    with acquisition_lock():pass
            with acquisition_lock():pass

    def test_api_input_and_missing_job(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.portal_reports import router
        from auth_dependencies import require_admin
        from auth_store import Identity
        app=FastAPI();app.include_router(router,prefix='/api/portal-reports');client=TestClient(app)
        # The public caller must be rejected before any collection job starts.
        with patch.object(service,'start') as start:
            self.assertEqual(client.post('/api/portal-reports/openclaw-tasks',json={'provinces':['tianjin']}).status_code,401)
            start.assert_not_called()
        # Isolate the existing input/job checks behind the new admin boundary.
        app.dependency_overrides[require_admin]=lambda:Identity('fixture-admin','fixture-admin','admin')
        self.assertEqual(client.post('/api/portal-reports/openclaw-tasks',json={'provinces':['invalid']}).status_code,400)
        self.assertEqual(client.post('/api/portal-reports/openclaw-tasks',json={'provinces':[]}).status_code,400)
        self.assertEqual(client.get('/api/portal-reports/openclaw-tasks/bad').status_code,400)
        self.assertEqual(client.get('/api/portal-reports/openclaw-tasks/20000101-000000-00000000').status_code,404)
        with patch.object(service,'start',return_value={'id':'test','state':'queued'}):
            self.assertEqual(client.post('/api/portal-reports/openclaw-tasks',json={'provinces':['tianjin']}).status_code,202)

if __name__=='__main__':unittest.main()
