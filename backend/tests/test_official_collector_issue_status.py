"""Admin read-only collector issue status against synthetic Temp stores only."""
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from auth_dependencies import require_admin
from collector_issue_events import CollectorIssueOutbox
from linux_guide_collector import CollectorConfig,GuideQueue
from routes import official_collector as route


class CollectorIssueStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='collector-status-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.path=self.root/'collector-issues-v1.sqlite3'
        auth_environment=patch.dict(os.environ,{'LABOURLAWYER_AUTH_DB':str(self.root/'auth.sqlite3')})
        auth_environment.start();self.addCleanup(auth_environment.stop)
        self.config=CollectorConfig(data_dir=self.root/'queue-state',release_dir=self.root/'release',browser_executable=self.root/'chrome',allowed_hosts=('www.zjzwfw.gov.cn',),issue_outbox=self.path)
        self.queue=GuideQueue(self.config)
        self.app=FastAPI();self.app.include_router(route.router,prefix='/api/official-collector')
        self.app.dependency_overrides[require_admin]=lambda:object()
        self.app.dependency_overrides[route.configured_queue]=lambda:self.queue
        self.client=TestClient(self.app)

    def read(self):
        response=self.client.get('/api/official-collector');self.assertEqual(response.status_code,200)
        result=response.json();self.assertIn('items',result);self.assertNotIn(str(self.root),json.dumps(result));return result

    def create_result(self):
        self.queue.submit([{'url':'https://www.zjzwfw.gov.cn/public-guide?areaCode=330127','region':{'province':'浙江省','city':'杭州市','district':'淳安县','region_code':'330127'}}])
        job=self.queue.claim();self.queue.finish(job['id'],{'state':'guide_observed','title':'虚构公开观察','observed_at':'2026-10-31T02:00:00Z','evidence':[],'attachments':[{'state':'failed'}]})

    def test_available_actual_outbox_counts_are_independent_and_read_only(self):
        self.create_result()
        with closing(sqlite3.connect(self.path)) as db,db:
            first=db.execute('SELECT id FROM collection_outbox ORDER BY id LIMIT 1').fetchone()[0]
            db.execute("UPDATE collection_outbox SET delivery_status='ACKNOWLEDGED_OPENCLAW',receipt=? WHERE id=?",(json.dumps({'synthetic_fixture':True}),first))
        before=self.path.read_bytes();result=self.read();issue=result['issue_events']
        self.assertEqual(issue,{'enabled':True,'journal':{'status':'available','observations':1,'states':{'outbox_persisted':1}},
            'outbox':{'status':'available','events':2,'pending':1,'acknowledged':1},'model_calls':0,'ai_reviewed':False})
        self.assertEqual(self.path.read_bytes(),before);self.assertEqual(result['counts']['complete'],1)

    def test_missing_database_is_null_not_zero_and_never_created(self):
        before=set(self.root.iterdir())
        with patch.object(CollectorIssueOutbox,'summary',side_effect=AssertionError('must not touch missing DB')):
            result=self.read()['issue_events']
        self.assertEqual(result['outbox'],{'status':'missing','events':None,'pending':None,'acknowledged':None})
        self.assertEqual(set(self.root.iterdir()),before);self.assertFalse(self.path.exists())

    def test_existing_valid_empty_store_may_honestly_report_zero(self):
        CollectorIssueOutbox(self.path)._initialize()
        self.assertEqual(self.read()['issue_events']['outbox'],{'status':'available','events':0,'pending':0,'acknowledged':0})

    def test_disabled_database_does_not_open_existing_or_create_store(self):
        from dataclasses import replace
        self.queue=GuideQueue(replace(self.config,issue_outbox=None))
        with patch.object(CollectorIssueOutbox,'summary',side_effect=AssertionError('disabled')):
            result=self.read()['issue_events']
        self.assertFalse(result['enabled']);self.assertEqual(result['outbox']['status'],'disabled');self.assertIsNone(result['outbox']['events'])
        self.assertFalse(self.path.exists())

    def test_bad_schema_stays_unchanged_and_job_status_remains_visible(self):
        self.create_result()
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('CREATE TABLE unrelated_private(secret TEXT)')
        before=self.path.read_bytes();result=self.read()
        self.assertEqual(result['issue_events']['outbox'],{'status':'error','events':None,'pending':None,'acknowledged':None})
        self.assertEqual(result['items'][0]['state'],'complete');self.assertEqual(self.path.read_bytes(),before)
        self.assertNotIn('secret',json.dumps(result));self.assertNotIn('schema',json.dumps(result))

    def test_corrupt_directory_and_symlink_outbox_are_safe_errors(self):
        self.path.write_bytes(b'PRIVATE_SENTINEL corrupt database')
        self.assertEqual(self.read()['issue_events']['outbox']['status'],'error')
        self.path.unlink();self.path.mkdir()
        self.assertEqual(self.read()['issue_events']['outbox']['status'],'error')
        self.path.rmdir()
        with patch.object(Path,'is_symlink',return_value=True):
            self.assertEqual(self.read()['issue_events']['outbox']['status'],'error')
        self.assertFalse(self.path.exists())

    def test_journal_failure_does_not_hide_jobs_or_invent_observation_zero(self):
        with patch.object(self.queue,'issue_event_status',side_effect=sqlite3.OperationalError('/private/secret/path')):
            issue=self.read()['issue_events']
        self.assertEqual(issue['journal'],{'status':'error','observations':None,'states':None})
        self.assertEqual(issue['outbox']['status'],'missing')

    def test_file_removed_during_summary_is_not_reported_as_available_zero(self):
        self.create_result()
        def disappeared(store):
            self.path.unlink()
            return {'events':0,'pending':0,'acknowledged':0,'observations':0,'model_calls':0}
        with patch.object(CollectorIssueOutbox,'summary',disappeared):
            result=self.read()
        self.assertEqual(result['issue_events']['outbox'],{'status':'error','events':None,'pending':None,'acknowledged':None})
        self.assertEqual(result['items'][0]['state'],'complete')

    def test_invalid_summary_states_and_inconsistent_counts_fail_closed(self):
        self.create_result()
        for summary in [{'events':True,'pending':0,'acknowledged':0,'model_calls':0},
            {'events':2,'pending':2,'acknowledged':1,'model_calls':0},{'events':2,'pending':1,'acknowledged':1,'model_calls':1}]:
            with patch.object(CollectorIssueOutbox,'summary',return_value=summary):self.assertEqual(self.read()['issue_events']['outbox']['status'],'error')
        with patch.object(self.queue,'issue_event_status',return_value={'enabled':True,'observations':0,'states':{'unknown_private_state':1},'sync_performed':False,'model_calls':0}):
            self.assertEqual(self.read()['issue_events']['journal']['status'],'error')

    def test_anonymous_request_cannot_read_issue_counts(self):
        self.app.dependency_overrides.pop(require_admin)
        with patch.object(self.queue,'issue_event_status',side_effect=AssertionError('anonymous read')):
            response=self.client.get('/api/official-collector')
        self.assertEqual(response.status_code,401)

    def test_actual_typescript_parser_accepts_testclient_available_and_error_wire(self):
        node=shutil.which('node');self.assertIsNotNone(node)
        self.create_result()
        fixtures=[self.read()]
        with patch.object(CollectorIssueOutbox,'summary',side_effect=ValueError('private path')):fixtures.append(self.read())
        for fixture in fixtures:
            completed=subprocess.run(['node',str(ROOT/'backend/tests/fixtures/test-collector-issue-status-wire.mjs')],input=json.dumps(fixture),text=True,capture_output=True,timeout=20)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertIn('PASS actual collector issue wire',completed.stdout)


if __name__=='__main__':unittest.main(verbosity=2)
