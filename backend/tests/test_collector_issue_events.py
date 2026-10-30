"""Public collector observations and a dedicated temporary durable outbox only."""
from copy import deepcopy
from contextlib import closing
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
HOSTS=('www.zjzwfw.gov.cn',)
URL='https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=ee47fff8-558c-4a85-88e9-8a28d2bddbdc'
REGION={'province':'zhejiang','city':'杭州市','district':'淳安县','region_code':'330127'}
FJ_URL='https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=442BD04C55F500427A01682CD4325DC4&infoType=1'
JS_URL='https://szks.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=32&iddept_ql_inf=1132058301418949XF4002014302002&ql_kind=20&iddept_yw_inf=1132058301418949XF400201430200201'
OWN_HOSTS=('zwfw.fujian.gov.cn','szks.jszwfw.gov.cn')
FJ_REGION={'province':'fujian','city':'福州市','district':'台江区','region_code':'350103'}
JS_REGION={'province':'jiangsu','city':'苏州市','district':'昆山市','region_code':'320583'}


def job(state='auth_required'):
    return {'id':'a'*32,'attempt':1,'state':'complete','url':URL,'region':dict(REGION),
        'updated_at':'2026-10-31T02:00:00+08:00','result':{'state':state,'observed_at':'2026-10-31T02:00:00+08:00',
        'service_verified':False,'model_used':False,'evidence':[],'attachments':[]}}


class CollectorIssueEventTests(unittest.TestCase):
    def setUp(self):
        self.m=importlib.import_module('collector_issue_events')
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.folder=Path(temp.name).resolve()
        self.database=self.folder/'collector-issues.sqlite';self.store=self.m.CollectorIssueOutbox(self.database)

    def events(self,value,**kwargs):return self.m.build_issue_events(value,allowed_hosts=HOSTS,**kwargs)
    def record(self,value,**kwargs):return self.store.record_result(value,allowed_hosts=HOSTS,**kwargs)

    def evidence(self,value,body=b'<html>private input body must never be forwarded</html>'):
        folder=self.folder/'evidence';folder.mkdir(exist_ok=True);(folder/'page.html').write_bytes(body)
        value['result']['evidence']=[{'file':'page.html','bytes':len(body),'sha256':sha256(body).hexdigest()}]
        return folder

    def test_auth_and_captcha_are_boundaries_not_verified_guidance(self):
        for state,kind in [('auth_required','AUTH_REQUIRED'),('captcha_required','CAPTCHA_REQUIRED')]:
            events=self.events(job(state));self.assertEqual(len(events),1);event=events[0]
            self.assertEqual(event['type'],kind);self.assertEqual({k:event[k] for k in REGION},REGION)
            self.assertNotIn('verified',event);self.assertNotIn('can_generate',event)
            self.assertEqual(event['final_status'],'manual_authorization')
            self.assertIn('未',event['reason'])

    def test_failure_states_and_unknown_online_never_claim_unavailable_or_absence(self):
        for state in ['blocked','blank','network_failed','runtime_failed','interrupted','http_failed']:
            value=job(state)
            if state=='http_failed':value['result']['http_status']=503
            self.assertEqual(self.events(value)[0]['type'],'GUIDE_PAGE_UNAVAILABLE')
        for state in ['guide_observed','unverified']:
            value=job(state);value['result'].update(online_status='unavailable',service_absent=True,template_absent=True)
            event=self.events(value)[0];self.assertEqual(event['type'],'ONLINE_CHANNEL_UNVERIFIED')
            self.assertNotIn('ONLINE_APPLICATION_UNAVAILABLE',json.dumps(event))
            self.assertNotIn('OFFICIAL_TEMPLATE_NOT_FOUND',json.dumps(event))

    def test_download_failure_is_observation_not_missing_template(self):
        value=job('guide_observed');value['result']['attachments']=[{'state':'failed','error':'private body',
            'label':'PRIVATE_DOCUMENT','source_url':'https://user:private@example.invalid/?token=private'}]
        events=self.events(value);self.assertEqual([e['type'] for e in events],['ONLINE_CHANNEL_UNVERIFIED','TEMPLATE_DOWNLOAD_FAILED'])
        self.assertNotIn('PRIVATE',json.dumps(events));self.assertNotIn('private',json.dumps(events))
        self.assertIn('不认定模板缺失',events[1]['reason'])

    def test_raw_html_documents_credentials_paths_titles_never_enter_payload(self):
        value=job();value.update(account='PRIVATE_SENTINEL',document='PRIVATE_SENTINEL')
        value['result'].update(error='C:/private/PRIVATE_SENTINEL token=PRIVATE_SENTINEL',html='<b>PRIVATE_SENTINEL</b>',
            title='PRIVATE_SENTINEL',auth_boundary_url='https://account.gov.cn/login?token=PRIVATE_SENTINEL')
        folder=self.evidence(value,b'<html>PRIVATE_SENTINEL 13800138000 11010519491231002X</html>')
        self.record(value,evidence_root=folder)
        with closing(sqlite3.connect(self.database)) as db,db:
            text=''.join(str(r) for r in db.iterdump())
        for private in ['PRIVATE_SENTINEL','13800138000','11010519491231002X','C:/private','<html>','auth_boundary_url']:
            self.assertNotIn(private,text)

    def test_unknown_or_inconsistent_machine_states_refused(self):
        for state in ['verified','service_absent','template_absent','we_inferred_unavailable']:
            with self.assertRaises(ValueError):self.events(job(state))
        value=job('http_failed');value['result']['http_status']=200
        with self.assertRaises(ValueError):self.events(value)
        self.assertFalse(self.database.exists())

    def test_nested_or_non_scalar_state_values_refuse_consistently(self):
        for state in [None,True,[],{}]:
            with self.subTest(state=state),self.assertRaises(ValueError):self.events(job(state))
        value=job('guide_observed');value['result']['attachments']=[{'state':[]}]
        with self.assertRaises(ValueError):self.events(value)

    def test_database_has_no_default_and_cannot_be_a_known_store_path(self):
        for path in [None,'',True,'relative.sqlite',self.folder/'regional-guides.sqlite',self.folder/'queue.sqlite3']:
            with self.subTest(path=path),self.assertRaises(ValueError):self.m.CollectorIssueOutbox(path)
        self.assertFalse(self.database.exists())

    def test_precise_region_and_configured_public_source_validation(self):
        for changes in [{'province':'other'},{'region_code':'320583'},{'city':'张三'},{'district':'C:/private'},
                        {'district':'淳安县\nTOKEN'},{'region_code':'3301277'}]:
            value=job();value['region'].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.record(value)
        urls=['http://127.0.0.1/guide','https://example.invalid/guide','https://evil.gov.cn/guide',
            'https://user:fixture@www.zjzwfw.gov.cn/guide','https://www.zjzwfw.gov.cn/guide?token=fixture',
            'https://www.zjzwfw.gov.cn/guide/13800138000','https://www.zjzwfw.gov.cn/a/../private',
            'https://www.zjzwfw.gov.cn/guide?areaCode=320583']
        for url in urls:
            value=job();value['url']=url
            with self.subTest(url=url),self.assertRaises(ValueError):self.record(value)
        self.assertFalse(self.database.exists())

    def test_evidence_paths_hashes_and_bytes_fail_closed(self):
        value=job();folder=self.evidence(value)
        with self.assertRaises(ValueError):self.events(value)
        for field,bad in [('file','../secret.txt'),('file','C:/secret.txt'),('sha256','0'*64),('bytes',True),('bytes',1000000000)]:
            changed=deepcopy(value);changed['result']['evidence'][0][field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):self.record(changed,evidence_root=folder)
        self.assertFalse(self.database.exists())

    def test_retries_are_one_immutable_pending_event_with_durable_observations(self):
        value=job();first=self.record(value);self.assertEqual(first['inserted'],1)
        pending=self.store.pending();self.assertEqual(len(pending),1);payload=deepcopy(pending[0])
        self.assertEqual(pending[0]['delivery_status'],'PENDING_OPENCLAW')
        again=self.record(value);self.assertEqual((again['inserted'],again['observations_inserted']),(0,0))
        value['attempt']=2;value['result']['observed_at']='2026-10-31T02:05:00+08:00'
        self.assertEqual(self.record(value)['observations_inserted'],1)
        self.assertEqual(self.store.pending(),[payload]);self.assertEqual(self.store.summary()['observations'],2)
        self.assertEqual(self.m.CollectorIssueOutbox(self.database).pending(),[payload])

    def test_external_ack_receipt_is_preserved_and_never_created_by_module(self):
        value=job();self.record(value)
        with closing(sqlite3.connect(self.database)) as db,db:
            db.execute("UPDATE collection_outbox SET delivery_status='ACKNOWLEDGED_OPENCLAW',receipt='opaque fixture receipt'")
        value['attempt']=2;self.record(value)
        with closing(sqlite3.connect(self.database)) as db,db:
            self.assertEqual(db.execute('SELECT delivery_status,receipt FROM collection_outbox').fetchall(),[('ACKNOWLEDGED_OPENCLAW','opaque fixture receipt')])
        self.assertEqual(self.store.pending(),[]);self.assertEqual(self.store.summary()['acknowledged'],1)

    def test_atomic_observation_failure_rolls_back_all_new_events(self):
        self.record(job())
        with closing(sqlite3.connect(self.database)) as db,db:
            before=list(db.execute('SELECT * FROM collection_outbox'))
        with patch.object(self.m,'_insert_observation',side_effect=RuntimeError('observation insert failed')):
            with self.assertRaises(RuntimeError):self.record(job('network_failed'))
        with closing(sqlite3.connect(self.database)) as db:self.assertEqual(db.execute('SELECT * FROM collection_outbox').fetchall(),before)
        self.assertEqual(self.store.summary()['events'],1)

    def test_existing_legacy_or_queue_database_is_never_adopted_or_modified(self):
        for name,sql in [('legacy.sqlite','CREATE TABLE collection_outbox(id TEXT PRIMARY KEY,payload TEXT,delivery_status TEXT,receipt TEXT,created_at TEXT)'),
                         ('worker.sqlite','CREATE TABLE jobs(id TEXT PRIMARY KEY,result TEXT)')]:
            path=self.folder/name
            with closing(sqlite3.connect(path)) as db,db:db.execute(sql)
            before=path.read_bytes()
            with self.assertRaises(ValueError):self.m.CollectorIssueOutbox(path).record_result(job(),allowed_hosts=HOSTS)
            self.assertEqual(path.read_bytes(),before)

    def test_tampered_existing_payload_refused_without_overwrite(self):
        self.record(job())
        with closing(sqlite3.connect(self.database)) as db,db:db.execute("UPDATE collection_outbox SET payload='{}'")
        before=self.database.read_bytes()
        with self.assertRaises(ValueError):self.record(job())
        self.assertEqual(self.database.read_bytes(),before)

    def test_tampered_payload_cannot_escape_through_pending_reader(self):
        self.record(job())
        with closing(sqlite3.connect(self.database)) as db,db:db.execute("UPDATE collection_outbox SET payload='{}'")
        with self.assertRaises(ValueError):self.store.pending()

    def test_document_source_and_private_path_are_not_public_guide_events(self):
        for url in ['https://www.zjzwfw.gov.cn/private/guide','https://www.zjzwfw.gov.cn/files/identity.docx']:
            value=job();value['url']=url
            with self.assertRaises(ValueError):self.events(value)

    def test_process_crash_before_commit_and_after_commit_replay_without_loss(self):
        for phase in ['before','after']:
            path=self.folder/(phase+'-issues.sqlite')
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--collector-crash-fixture',str(path),phase],
                capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.assertEqual(result.returncode,79,result.stderr.decode('utf-8','replace'))
            store=self.m.CollectorIssueOutbox(path)
            self.assertEqual(store.summary()['events'],0 if phase=='before' else 2)
            value=job('guide_observed');value['result']['attachments']=[{'state':'failed'}]
            store.record_result(value,allowed_hosts=HOSTS)
            self.assertEqual((store.summary()['events'],store.summary()['pending']),(2,2))
            self.assertEqual(store.record_result(value,allowed_hosts=HOSTS)['inserted'],0)

    def test_bridge_public_dto_roundtrip_and_workspace_export_keep_pending(self):
        from regional_issue_delivery import _public_event,deliver_pending
        event=self.events(job())[0]
        self.assertEqual(_public_event(json.dumps(event),event['id']),event)
        self.record(job());workspace=self.folder/'workspace';workspace.mkdir()
        result=deliver_pending(self.database,workspace,record_receipts=True)
        self.assertEqual((result['workspace_exported'],result['acknowledged'],result['model_calls']),(1,0,0))
        self.assertEqual(self.store.summary()['pending'],1)
        self.assertEqual(self.record(job())['inserted'],0)

    def test_hash_ids_survive_personal_data_scrubber(self):
        event=self.events(job())[0]
        self.assertTrue(all(len(part)==8 for part in event['id'].split('-')[3:]))
        self.assertRegex(event['id'],r'^collector-issue-v1-(?:[a-f0-9]{8}-){7}[a-f0-9]{8}$')

    def own_job(self,url=FJ_URL,region=FJ_REGION):
        value=job();value.update(url=url,region=dict(region));return value

    def test_real_fujian_jiangsu_urls_survive_new_outbox_dto_and_export_bytes(self):
        from regional_issue_delivery import _public_event,deliver_pending,public_source_url
        expected=set()
        for url,region in [(FJ_URL,FJ_REGION),(JS_URL,JS_REGION)]:
            parts=urlsplit(url);canonical=urlunsplit((*parts[:3],urlencode(sorted(parse_qsl(parts.query))),''))
            event=self.store.record_result(self.own_job(url,region),allowed_hosts=OWN_HOSTS)['events'][0]
            self.assertEqual(event['url'],canonical);self.assertEqual(public_source_url(canonical),canonical)
            public={k:v for k,v in event.items() if k!='delivery_status'}
            self.assertEqual(_public_event(json.dumps(public),event['id']),public);expected.add(canonical)
            with closing(sqlite3.connect(self.database)) as db:
                semantic=json.loads(db.execute('SELECT semantic FROM collector_issue_events WHERE event_id=?',(event['id'],)).fetchone()[0])
            self.assertEqual(semantic['source'],canonical)
        workspace=self.folder/'own-public-workspace';workspace.mkdir();before=self.database.read_bytes()
        exported=deliver_pending(self.database,workspace)
        self.assertEqual((exported['workspace_exported'],exported['acknowledged'],exported['model_calls']),(2,0,0))
        actual=set()
        for receipt in exported['receipts']:
            body=(workspace/receipt['content_file']).read_bytes()
            self.assertEqual(sha256(body).hexdigest(),receipt['content_sha256'])
            actual.add(json.loads(body)['events'][0]['url'])
        self.assertEqual(actual,expected);self.assertEqual(self.database.read_bytes(),before)
        self.assertEqual(self.store.summary()['pending'],2)

    def test_new_projection_reuses_bridge_helper_unknown_values_never_enter_semantics(self):
        import regional_issue_delivery as bridge
        clean=self.own_job();dirty=self.own_job(FJ_URL+'&tracking=PRIVATE_SENTINEL&personName=13800138000')
        with patch.object(bridge,'public_source_url',wraps=bridge.public_source_url) as helper:
            original=self.m.build_issue_events(clean,allowed_hosts=OWN_HOSTS)[0]
            event=self.m.build_issue_events(dirty,allowed_hosts=OWN_HOSTS)[0]
        self.assertGreaterEqual(helper.call_count,2)
        self.assertEqual(event,original)
        self.store.record_result(dirty,allowed_hosts=OWN_HOSTS)
        with closing(sqlite3.connect(self.database)) as db:stored=''.join(db.iterdump())
        for value in ['PRIVATE_SENTINEL','13800138000','tracking','personName']:self.assertNotIn(value,stored)
        with patch.object(bridge,'public_source_url',return_value=None),self.assertRaises(ValueError):
            self.m.build_issue_events(clean,allowed_hosts=OWN_HOSTS)

    def test_cross_path_selectors_and_native_hash_do_not_change_safe_identity(self):
        for url,region in [(FJ_URL,FJ_REGION),(JS_URL,JS_REGION)]:
            parts=urlsplit(url);base=urlunsplit((parts.scheme,parts.netloc,'/public-guide','',''))
            wrong=base+'?'+parts.query
            first=self.m.build_issue_events(self.own_job(base,region),allowed_hosts=OWN_HOSTS)[0]
            second=self.m.build_issue_events(self.own_job(wrong,region),allowed_hosts=OWN_HOSTS)[0]
            self.assertEqual(second,first);self.assertEqual(second['url'],base)
        extra=FJ_URL+'&'+urlsplit(JS_URL).query+'#/workguide?localInnerCode=ee47fff8-558c-4a85-88e9-8a28d2bddbdc'
        first=self.m.build_issue_events(self.own_job(),allowed_hosts=OWN_HOSTS)[0]
        second=self.m.build_issue_events(self.own_job(extra),allowed_hosts=OWN_HOSTS)[0]
        self.assertEqual(second,first)

    def test_own_url_invalid_duplicate_auth_private_and_unsafe_values_refuse(self):
        urls=[FJ_URL+'&unid=442BD04C55F500427A01682CD4325DC4',FJ_URL+'&UNID=duplicate',FJ_URL+'&%75nid=duplicate',
            FJ_URL+'&unknown=one&UNKNOWN=two',FJ_URL+'&tracking=%00',FJ_URL+'&tracking=%GG',FJ_URL+'&bare',
            FJ_URL.replace('infoType=1','infoType=2'),FJ_URL.replace('&infoType=1',''),
            FJ_URL+'&token=PRIVATE_SENTINEL',FJ_URL.replace('/person-todo/todo-fingerpost','/private/todo-fingerpost'),
            FJ_URL.replace('https://','https://user:PRIVATE_SENTINEL@'),
            JS_URL.replace('webId=32','webId=0'),JS_URL.replace('ql_kind=20','ql_kind=100'),
            JS_URL.replace('1132058301418949XF400201430200201','1132058301418949XF400201430200301'),
            JS_URL.replace('webId=32&','')]
        for url in urls:
            region=JS_REGION if urlsplit(url).hostname=='szks.jszwfw.gov.cn' else FJ_REGION
            with self.subTest(url=url),self.assertRaises(ValueError):
                self.store.record_result(self.own_job(url,region),allowed_hosts=OWN_HOSTS)
        self.assertFalse(self.database.exists())

    def test_legacy_truncated_projection_collision_preserves_payload_ack_and_observations(self):
        for status in ['PENDING_OPENCLAW','ACKNOWLEDGED_OPENCLAW']:
            database=self.folder/(status+'.sqlite');store=self.m.CollectorIssueOutbox(database)
            value=self.own_job();event=store.record_result(value,allowed_hosts=OWN_HOSTS)['events'][0]
            with closing(sqlite3.connect(database)) as db,db:
                payload=json.loads(db.execute('SELECT payload FROM collection_outbox').fetchone()[0])
                payload['url']=FJ_URL.split('?')[0]  # Historical bridge_keys projection.
                encoded=self.m._json(payload)
                db.execute('UPDATE collection_outbox SET payload=?,delivery_status=?,receipt=?',(encoded,status,'opaque historical receipt'))
                db.execute('UPDATE collector_issue_events SET payload_sha256=?',(sha256(encoded.encode()).hexdigest(),))
            with closing(sqlite3.connect(database)) as db:before=list(db.iterdump())
            raw=database.read_bytes();value['attempt']=2;value['result']['observed_at']='2026-10-31T02:10:00+08:00'
            with self.assertRaises(ValueError):store.record_result(value,allowed_hosts=OWN_HOSTS)
            with closing(sqlite3.connect(database)) as db:self.assertEqual(list(db.iterdump()),before)
            self.assertEqual(database.read_bytes(),raw)

    def test_harmless_selector_order_and_retry_keep_one_full_url_event(self):
        value=self.own_job();first=self.store.record_result(value,allowed_hosts=OWN_HOSTS)['events'][0]
        parts=urlsplit(FJ_URL);value['url']=urlunsplit((*parts[:3],urlencode(list(reversed(parse_qsl(parts.query)))),''))
        value['attempt']=2;value['result']['observed_at']='2026-10-31T02:05:00+08:00'
        result=self.store.record_result(value,allowed_hosts=OWN_HOSTS)
        self.assertEqual((result['inserted'],result['observations_inserted']),(0,1))
        self.assertEqual(result['events'][0],first)

    def test_unfinished_jobs_no_observation_and_subframe_auth_is_not_main_auth(self):
        value=job();value['state']='queued';value['result']=None
        self.assertEqual(self.record(value)['inserted'],0);self.assertFalse(self.database.exists())
        value=job('guide_observed');value['result']['blocked_auth_frames']=[{'url':'https://login.gov.cn/private','state':'blocked_anonymous_auth_check'}]
        self.assertEqual([e['type'] for e in self.events(value)],['ONLINE_CHANNEL_UNVERIFIED'])


def _crash_fixture(path,phase):
    # Fixed named test fixture only; never accept executable input or real paths.
    path=Path(path);temporary=Path(tempfile.gettempdir()).resolve()
    if not (path.is_absolute() and path.resolve().is_relative_to(temporary) and path.name in {'before-issues.sqlite','after-issues.sqlite'} and phase in {'before','after'}):
        raise ValueError('Crash fixture accepts only its own temporary paths')
    module=importlib.import_module('collector_issue_events');store=module.CollectorIssueOutbox(path)
    store._initialize()
    value=job('guide_observed');value['result']['attachments']=[{'state':'failed'}]
    if phase=='before':
        with patch.object(module,'_insert_observation',side_effect=lambda *args:os._exit(79)):
            store.record_result(value,allowed_hosts=HOSTS)
    else:store.record_result(value,allowed_hosts=HOSTS)
    os._exit(79)


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--collector-crash-fixture':_crash_fixture(sys.argv[2],sys.argv[3])
    else:unittest.main()
