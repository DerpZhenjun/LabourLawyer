"""Durable collection never treats a failed official visit as missing service."""
import json
import asyncio
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

REGION={'province':'江苏省','city':'苏州市','district':'张家港市','region_code':'320582'}

def entry(url):return {'url':url,'region':REGION}

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        environment=patch.dict('os.environ',{'LABOURLAWYER_AUTH_DB':str(self.root/'test-auth.sqlite3')})
        environment.start();self.addCleanup(environment.stop)

    def queue(self, **changes):
        from linux_guide_collector import CollectorConfig, GuideQueue
        values = dict(data_dir=self.root/'var', release_dir=self.root/'release',
                      browser_executable=self.root/'chrome', allowed_hosts=('szzjg.jszwfw.gov.cn',),
                      capacity=2, batch_limit=2, min_interval_seconds=0)
        values.update(changes)
        return GuideQueue(CollectorConfig(**values))

    def test_failed_visit_remains_unverified_and_retry_preserves_attempts(self):
        q = self.queue()
        job = q.submit([{'url': 'https://szzjg.jszwfw.gov.cn/guide', 'region': {'province':'江苏省','city':'苏州市','district':'张家港市','region_code':'320582'}}])[0]
        claimed = q.claim()
        q.finish(job['id'], {'state': 'network_failed', 'service_verified': False})
        self.assertEqual(q.get(job['id'])['result']['state'], 'network_failed')
        self.assertFalse(q.get(job['id'])['result']['service_verified'])
        q.retry(job['id'])
        self.assertEqual(q.claim()['attempt'], 2)
        q.finish(job['id'], {'state': 'blocked', 'service_verified': False})
        with self.assertRaisesRegex(ValueError, 'attempt'):
            q.retry(job['id'])
        self.assertEqual(claimed['attempt'], 1)

    def test_capacity_validation_dedupe_and_resume_survive_new_queue_instance(self):
        q = self.queue()
        first = q.submit([entry('https://szzjg.jszwfw.gov.cn/a')])[0]
        self.assertEqual(q.submit([entry('https://szzjg.jszwfw.gov.cn/a')])[0]['id'], first['id'])
        q.submit([entry('https://szzjg.jszwfw.gov.cn/b')])
        with self.assertRaisesRegex(ValueError, 'capacity'):
            q.submit([entry('https://szzjg.jszwfw.gov.cn/c')])
        q.claim()
        reopened = self.queue()
        self.assertEqual(reopened.recover_interrupted(), 1)
        self.assertEqual(reopened.get(first['id'])['state'], 'queued')
        self.assertEqual(reopened.claim()['attempt'], 2)

    def test_hosts_private_addresses_credentials_and_release_writes_rejected(self):
        q = self.queue()
        for url in ['http://127.0.0.1/a', 'https://szzjg.jszwfw.gov.cn.attacker.example/',
                    'https://other.gov.cn/a', 'https://user:pass@szzjg.jszwfw.gov.cn/',
                    'file:///etc/passwd', 'https://szzjg.jszwfw.gov.cn:9443/a',
                    'https://szzjg.jszwfw.gov.cn/a?access_token=private']:
            with self.assertRaises(ValueError, msg=url): q.submit([entry(url)])
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.queue(data_dir=self.root/'release'/'var')

    def test_queue_cancel_is_bounded_and_cannot_cancel_running_job(self):
        q = self.queue()
        jobs = q.submit([entry('https://szzjg.jszwfw.gov.cn/a'),entry('https://szzjg.jszwfw.gov.cn/b')])
        q.claim()
        with self.assertRaises(ValueError):q.cancel(jobs[0]['id'])
        q.cancel(jobs[1]['id'])
        self.assertEqual(q.get(jobs[1]['id'])['state'], 'cancelled')
        self.assertEqual(q.summary()['counts'], {'running': 1, 'cancelled': 1})

    def test_evidence_manifest_hashes_files_and_never_asserts_absence(self):
        from linux_guide_collector import evidence_manifest, classify_observation
        self.root.joinpath('page.txt').write_text('办理材料 劳动人事争议仲裁申请 办理流程', encoding='utf8')
        manifest = evidence_manifest(self.root)
        self.assertEqual(len(manifest[0]['sha256']), 64)
        self.assertEqual(manifest[0]['bytes'], self.root.joinpath('page.txt').stat().st_size)
        self.assertEqual(classify_observation('验证码', 200), 'captcha_required')
        self.assertEqual(classify_observation('劳动人事争议仲裁申请 办理材料 办理流程', 200), 'guide_observed')
        self.assertEqual(classify_observation('劳动人事争议仲裁申请 申报材料 办理流程', 200), 'guide_observed')
        self.assertEqual(classify_observation('服务不可用', 503), 'http_failed')
        self.assertEqual(classify_observation('欢迎访问政府网站，这里提供公共服务入口', 200), 'unverified')

    def test_admin_api_enforces_auth_and_hides_operator_paths_and_raw_html(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from auth_dependencies import require_admin
        from routes.official_collector import router, configured_queue
        app=FastAPI();app.include_router(router,prefix='/api/official-collector')
        client=TestClient(app)
        self.assertEqual(client.get('/api/official-collector').status_code,401)
        self.assertEqual(client.post('/api/official-collector/jobs',json={'items':[]}).status_code,401)
        app.dependency_overrides[require_admin]=lambda:object()
        q=self.queue();app.dependency_overrides[configured_queue]=lambda:q
        response=client.post('/api/official-collector/jobs',json={'items':[{'url':'https://szzjg.jszwfw.gov.cn/a','region':{'province':'江苏省','city':'苏州市','district':'张家港市','region_code':'320582'}}]})
        self.assertEqual(response.status_code,202)
        identifier=response.json()['items'][0]['id']
        q.claim();q.finish(identifier,{'state':'runtime_failed','service_verified':False,'error':'/home/operator/private/path', 'evidence_directory':'evidence/'+identifier+'/attempt-1'})
        output=client.get('/api/official-collector').text
        self.assertNotIn('/home/operator',output)
        self.assertNotIn('evidence_directory',output)
        self.assertIn('江苏省',output)
        self.assertEqual(client.get('/api/official-collector/jobs/'+identifier+'/evidence/page.html').status_code,404)

    def test_outbox_preserves_unverified_issue_and_region_without_runtime_paths(self):
        q=self.queue()
        job=q.submit([entry('https://szzjg.jszwfw.gov.cn/a')])[0]
        q.claim();q.finish(job['id'],{'state':'blocked','error':'/home/operator/private','service_verified':False})
        proposal=json.loads((q.root/'outbox'/(job['id']+'-1.json')).read_text(encoding='utf8'))
        self.assertEqual(proposal['state'],'pending_review')
        self.assertEqual(proposal['region']['district'],'张家港市')
        self.assertFalse(proposal['service_absent'])
        self.assertNotIn('/home/operator',json.dumps(proposal))

    def test_region_is_preserved_and_whole_batch_rolls_back_on_capacity(self):
        q=self.queue(capacity=1)
        with self.assertRaisesRegex(ValueError,'capacity'):
            q.submit([entry('https://szzjg.jszwfw.gov.cn/a'),entry('https://szzjg.jszwfw.gov.cn/b')])
        self.assertEqual(q.summary()['items'],[])
        region={'province':'江苏省','city':'苏州市','district':'张家港市','region_code':'320582'}
        job=q.submit([{'url':'https://szzjg.jszwfw.gov.cn/a','region':region}])[0]
        self.assertEqual(self.queue(capacity=1).get(job['id'])['region'],region)

    def test_finish_rejects_nonrunning_without_creating_outbox(self):
        q=self.queue()
        job=q.submit([entry('https://szzjg.jszwfw.gov.cn/a')])[0]
        with self.assertRaises(ValueError):q.finish(job['id'],{'state':'unverified'})
        self.assertFalse((q.root/'outbox'/(job['id']+'-0.json')).exists())

    def test_browser_route_rejects_private_dns_and_redirects_to_unconfigured_hosts(self):
        from linux_guide_collector import public_destination
        q=self.queue()
        async def inspect():
            with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
                self.assertFalse(await public_destination(q.config,'https://szzjg.jszwfw.gov.cn/a',navigation=True,cache={}))
            with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):
                self.assertFalse(await public_destination(q.config,'https://other.gov.cn/a',navigation=True,cache={}))
                self.assertTrue(await public_destination(q.config,'https://static.gov.cn/file.js',navigation=False,cache={}))
                self.assertFalse(await public_destination(q.config,'http://localhost/a',navigation=False,cache={}))
                self.assertFalse(await public_destination(q.config,'https://files.gov.cn/form.docx',navigation=True,cache={}))
                self.assertTrue(await public_destination(q.config,'https://files.gov.cn/form.docx',navigation=True,cache={},document_active=True))
                self.assertFalse(await public_destination(q.config,'https://files.gov.cn/login',navigation=True,cache={},document_active=True))
        asyncio.run(inspect())

    def test_empty_scope_or_nonnumeric_region_cannot_enter_queue(self):
        q=self.queue()
        for region in ({},{**REGION,'city':' '},{**REGION,'region_code':'abc'},{**REGION,'district':''}):
            with self.assertRaises(ValueError):q.submit([{'url':'https://szzjg.jszwfw.gov.cn/a','region':region}])

    def test_spa_guide_route_is_preserved_but_auth_fragment_is_rejected(self):
        from linux_guide_collector import public_url
        url='https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=abc123'
        self.assertEqual(public_url(url),url)
        self.assertEqual(public_url(url+'&nonce=private'),url)
        q=self.queue()
        with self.assertRaises(ValueError):q.submit([entry('https://szzjg.jszwfw.gov.cn/#access_token=private')])

    def test_public_guide_with_blocked_hidden_sso_frame_remains_an_observation(self):
        from linux_guide_collector import classify_observation, record_auth_boundary
        result={}
        record_auth_boundary(result,'https://sso.gov.cn/login?nonce=private',main_frame=False)
        self.assertNotIn('auth_boundary_url',result)
        self.assertEqual(result['blocked_auth_frames'][0]['url'],'https://sso.gov.cn/login')
        self.assertEqual(classify_observation('劳动人事争议仲裁申请 办理材料 办理流程',200,main_frame_auth=bool(result.get('auth_boundary_url'))),'guide_observed')
        record_auth_boundary(result,'https://sso.gov.cn/login?nonce=private',main_frame=True)
        self.assertEqual(classify_observation('劳动人事争议仲裁申请 办理材料 办理流程',200,main_frame_auth=bool(result.get('auth_boundary_url'))),'auth_required')

    def test_browser_attachment_bytes_are_hashed_but_template_kind_stays_unknown(self):
        from linux_guide_collector import store_attachment
        q=self.queue()
        record={}
        store_attachment(q.config,self.root,1,b'%PDF-1.7\npublic fixture\n',record)
        self.assertEqual(record['state'],'downloaded')
        self.assertEqual(record['template_kind'],'unknown_until_review')
        self.assertEqual(record['sha256'],__import__('hashlib').sha256((self.root/record['file']).read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError,'recognized'):store_attachment(q.config,self.root,2,b'<html>Please login</html>',{})
        self.assertFalse((self.root/'attachment-2').exists())

    def test_actual_browser_document_response_is_saved_without_download_event(self):
        from linux_guide_collector import capture_response_document
        q=self.queue()
        class Response:
            url='https://files.gov.cn/form.pdf'
            headers={'content-length':'22'}
            async def body(self):return b'%PDF-1.7\npublic fixture\n'
        async def run():
            record={}
            with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):
                self.assertTrue(await capture_response_document(q.config,[Response()],self.root,1,record))
            self.assertEqual(record['capture_method'],'browser_response')
            self.assertEqual(record['source_url'],Response.url)
        asyncio.run(run())

    def test_future_unrelated_document_traffic_cannot_become_a_click_attachment(self):
        from linux_guide_collector import ClickDocumentRequests
        observed=ClickDocumentRequests()
        observed.add('https://files.gov.cn/clicked.docx')
        observed.freeze()
        observed.add('https://files.gov.cn/unrelated-background.docx')
        self.assertEqual(observed.urls,('https://files.gov.cn/clicked.docx',))

    def test_law_and_whole_guide_exports_do_not_consume_template_candidates(self):
        from linux_guide_collector import material_anchor
        self.assertTrue(material_anchor({'url':'https://files.gov.cn/a.docx','label':'劳动仲裁申请书'}))
        self.assertTrue(material_anchor({'url':'https://files.gov.cn/a.doc','label':'证据清单'}))
        self.assertFalse(material_anchor({'url':'https://files.gov.cn/a.pdf','label':'劳动争议调解仲裁法'}))
        self.assertFalse(material_anchor({'url':'https://files.gov.cn/a.pdf','label':'办事指南下载'}))

    @unittest.skipUnless(sys.platform=='linux','Worker is deliberately Linux-only')
    def test_os_worker_lock_rejects_second_process_and_releases_on_exit(self):
        from linux_guide_collector import worker_lock
        source="""import sys
from pathlib import Path
from linux_guide_collector import worker_lock
try:
    with worker_lock(Path(sys.argv[1])):pass
except RuntimeError:sys.exit(23)
"""
        environment={**__import__('os').environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
        with worker_lock(self.root):
            second=subprocess.run([sys.executable,'-c',source,str(self.root)],env=environment,capture_output=True,timeout=10)
            self.assertEqual(second.returncode,23,second.stderr.decode())
        released=subprocess.run([sys.executable,'-c',source,str(self.root)],env=environment,capture_output=True,timeout=10)
        self.assertEqual(released.returncode,0,released.stderr.decode())


if __name__ == '__main__':unittest.main()
