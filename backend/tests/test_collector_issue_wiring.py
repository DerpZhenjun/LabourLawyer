"""Real temporary queue -> durable results -> separate issue outbox; no browser."""
from contextlib import closing,redirect_stdout
from hashlib import sha256
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from linux_guide_collector import CollectorConfig,GuideQueue
from collector_issue_events import CollectorIssueOutbox
URL='https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=ee47fff8-558c-4a85-88e9-8a28d2bddbdc'
REGION={'province':'浙江省','city':'杭州市','district':'淳安县','region_code':'330127'}


def configuration(root,enabled=True,**changes):
    values=dict(data_dir=root/'var',release_dir=root/'release',browser_executable=root/'chrome',allowed_hosts=('www.zjzwfw.gov.cn',),
                min_interval_seconds=0,issue_outbox=root/'auto-issues.sqlite' if enabled else None)
    values.update(changes);return CollectorConfig(**values)


class CollectorIssueWiringTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='collector-wiring-');self.addCleanup(temp.cleanup);self.root=Path(temp.name).resolve()

    def queue(self,enabled=True,**changes):return GuideQueue(configuration(self.root,enabled,**changes))
    def claim(self,q):q.submit([{'url':URL,'region':dict(REGION)}]);return q.claim()
    def result(self,state='auth_required',**extra):return {'state':state,'service_verified':False,'model_used':False,'observed_at':'2026-10-31T02:00:00Z','evidence':[],**extra}

    def test_finish_commits_queue_and_journal_before_issue_write(self):
        q=self.queue();job=self.claim(q);original=CollectorIssueOutbox.record_result;observed=[]
        def inspect(store,issue_job,*args,**kwargs):
            observed.append(q.get(job['id'])['state'])
            with q.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM job_observations').fetchone()[0],1)
            return original(store,issue_job,*args,**kwargs)
        with patch.object(CollectorIssueOutbox,'record_result',inspect):q.finish(job['id'],self.result())
        self.assertEqual(observed,['complete'])
        event=CollectorIssueOutbox(q.config.issue_outbox).pending()[0]
        self.assertEqual((event['province'],event['city'],event['district'],event['region_code']),('zhejiang','杭州市','淳安县','330127'))
        self.assertEqual(q.get(job['id'])['region'],REGION)
        self.assertEqual(event['delivery_status'],'PENDING_OPENCLAW')

    def test_default_disabled_never_creates_a_dedicated_outbox(self):
        q=self.queue(False);job=self.claim(q);q.finish(job['id'],self.result())
        report=q.replay_issue_events();self.assertFalse(report['enabled']);self.assertFalse(report['sync_performed'])
        self.assertFalse((self.root/'auto-issues.sqlite').exists());self.assertEqual(q.get(job['id'])['state'],'complete')

    def test_private_review_file_failure_cannot_prevent_durable_queue_or_issue(self):
        q=self.queue();job=self.claim(q)
        with patch('linux_guide_collector.save_json',side_effect=OSError('PRIVATE_PATH_TOKEN')):
            report=q.finish(job['id'],self.result())
        self.assertEqual(q.get(job['id'])['state'],'complete')
        self.assertEqual(len(CollectorIssueOutbox(q.config.issue_outbox).pending()),1)
        self.assertFalse(report['review_proposal_written'])
        self.assertNotIn('PRIVATE_PATH_TOKEN',json.dumps(report))

    def test_queue_result_and_attempt_journal_roll_back_together(self):
        q=self.queue();job=self.claim(q)
        with patch.object(q,'_journal_observation',side_effect=sqlite3.OperationalError('fixture')):
            with self.assertRaises(sqlite3.OperationalError):q.finish(job['id'],self.result())
        self.assertEqual(q.get(job['id'])['state'],'running')
        with q.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM job_observations').fetchone()[0],0)
        self.assertFalse(q.config.issue_outbox.exists())

    def test_recovered_interrupted_attempt_is_journaled_before_retry(self):
        q=self.queue();job=self.claim(q)
        self.assertEqual(q.recover_interrupted(),1)
        self.assertEqual(q.get(job['id'])['state'],'queued')
        self.assertEqual(q.replay_issue_events()['new_events'],1)
        self.assertEqual(q.claim()['attempt'],2);q.finish(job['id'],self.result())
        events=CollectorIssueOutbox(q.config.issue_outbox).pending()
        self.assertEqual({e['type'] for e in events},{'GUIDE_PAGE_UNAVAILABLE','AUTH_REQUIRED'})
        with q.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM job_observations').fetchone()[0],2)

    def test_outbox_failure_leaves_durable_complete_result_for_restart(self):
        q=self.queue();job=self.claim(q)
        with patch.object(CollectorIssueOutbox,'record_result',side_effect=OSError('PRIVATE_PATH_TOKEN')):
            q.finish(job['id'],self.result())
        self.assertEqual(q.get(job['id'])['state'],'complete')
        self.assertNotIn('PRIVATE_PATH_TOKEN',json.dumps(q.issue_event_status()))
        reopened=self.queue();report=reopened.replay_issue_events()
        self.assertEqual((report['new_events'],report['failed']),(1,0))
        self.assertEqual(reopened.replay_issue_events()['new_events'],0)
        self.assertEqual(len(CollectorIssueOutbox(q.config.issue_outbox).pending()),1)

    def test_old_attempt_is_not_lost_when_retry_result_replaces_latest(self):
        q=self.queue();job=self.claim(q)
        with patch.object(CollectorIssueOutbox,'record_result',side_effect=OSError('offline')):
            q.finish(job['id'],self.result('network_failed'))
        q.retry(job['id']);self.assertEqual(q.claim()['attempt'],2);q.finish(job['id'],self.result('auth_required'))
        report=self.queue().replay_issue_events();self.assertEqual(report['new_events'],1)
        events=CollectorIssueOutbox(q.config.issue_outbox).pending()
        self.assertEqual({e['type'] for e in events},{'GUIDE_PAGE_UNAVAILABLE','AUTH_REQUIRED'})
        with q.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM job_observations').fetchone()[0],2)

    def test_restart_backfills_old_queue_without_journal(self):
        q=self.queue(False);job=self.claim(q);q.finish(job['id'],self.result('network_failed'))
        with q.connect() as db:db.execute('DROP TABLE job_observations')
        reopened=self.queue();report=reopened.replay_issue_events()
        self.assertEqual((report['backfilled'],report['new_events']),(1,1))
        self.assertEqual(reopened.get(job['id'])['region'],REGION)

    def test_unknown_result_retained_but_no_guessed_event_or_false_absence(self):
        q=self.queue();job=self.claim(q);q.finish(job['id'],self.result('future_unrecognized'))
        self.assertEqual(q.get(job['id'])['result']['state'],'future_unrecognized')
        report=q.replay_issue_events();self.assertEqual(report['rejected'],1)
        self.assertFalse(q.config.issue_outbox.exists())

    def test_no_attachments_stays_unknown_not_absence(self):
        q=self.queue();job=self.claim(q);q.finish(job['id'],self.result('guide_observed',attachments=[]))
        event=CollectorIssueOutbox(q.config.issue_outbox).pending()[0]
        self.assertEqual(event['type'],'ONLINE_CHANNEL_UNVERIFIED')
        self.assertNotIn('OFFICIAL_TEMPLATE_NOT_FOUND',json.dumps(event));self.assertNotIn('ONLINE_APPLICATION_UNAVAILABLE',json.dumps(event))
        self.assertFalse(q.get(job['id'])['result']['service_verified'])

    def test_restart_preserves_external_ack_and_receipt(self):
        q=self.queue();job=self.claim(q);q.finish(job['id'],self.result())
        with closing(sqlite3.connect(q.config.issue_outbox)) as db,db:
            db.execute("UPDATE collection_outbox SET delivery_status='ACKNOWLEDGED_OPENCLAW',receipt='opaque fixture receipt'")
        report=self.queue().replay_issue_events();self.assertEqual(report['new_events'],0)
        with closing(sqlite3.connect(q.config.issue_outbox)) as db:
            self.assertEqual(db.execute('SELECT delivery_status,receipt FROM collection_outbox').fetchall(),[('ACKNOWLEDGED_OPENCLAW','opaque fixture receipt')])
        self.assertFalse(report['sync_performed'])

    def test_evidence_root_is_derived_and_missing_files_replay_after_restore(self):
        q=self.queue();job=self.claim(q);folder=q.root/'evidence'/job['id']/'attempt-1'
        body=b'public synthetic capture';fingerprint={'file':'page.png','bytes':len(body),'sha256':sha256(body).hexdigest()}
        q.finish(job['id'],self.result(evidence=[fingerprint],evidence_directory='C:/private/DO_NOT_USE'))
        self.assertEqual(q.get(job['id'])['state'],'complete');self.assertFalse(q.config.issue_outbox.exists())
        folder.mkdir(parents=True);(folder/'page.png').write_bytes(body)
        self.assertEqual(self.queue().replay_issue_events()['new_events'],1)
        self.assertNotIn('DO_NOT_USE',json.dumps(CollectorIssueOutbox(q.config.issue_outbox).pending()))

    def test_config_rejects_release_queue_and_nonabsolute_targets(self):
        for target in [Path('relative.sqlite'),self.root/'release'/'issues.sqlite',self.root/'var'/'queue.sqlite3']:
            with self.subTest(target=target),self.assertRaises(ValueError):configuration(self.root,issue_outbox=target)

    def test_foreign_legacy_outbox_is_not_adopted_and_queue_is_not_lost(self):
        path=self.root/'legacy.sqlite'
        with closing(sqlite3.connect(path)) as db,db:db.execute('CREATE TABLE collection_outbox(id TEXT PRIMARY KEY,payload TEXT,delivery_status TEXT,receipt TEXT,created_at TEXT)')
        before=path.read_bytes();q=self.queue(issue_outbox=path);job=self.claim(q);q.finish(job['id'],self.result())
        self.assertEqual(q.get(job['id'])['state'],'complete');self.assertEqual(path.read_bytes(),before)
        self.assertEqual(q.replay_issue_events()['failed'],1)

    def test_runner_explicit_replay_is_import_safe_and_has_no_sync(self):
        q=self.queue(False);job=self.claim(q);q.finish(job['id'],self.result())
        config=self.root/'collector.json'
        config.write_text(json.dumps({'data_dir':str(q.root),'browser_executable':str(self.root/'chrome'),
            'allowed_hosts':['www.zjzwfw.gov.cn'],'issue_outbox':str(self.root/'auto-issues.sqlite')}),encoding='utf-8')
        spec=importlib.util.spec_from_file_location('collector_runner_test',ROOT/'scripts/run-linux-guide-collector.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        output=StringIO()
        with redirect_stdout(output),patch.object(module,'run_worker',side_effect=AssertionError('No worker or network')):
            self.assertEqual(module.main(['--config',str(config),'replay-issues']),0)
        report=json.loads(output.getvalue());self.assertEqual(report['new_events'],1);self.assertFalse(report['sync_performed'])

    def test_process_death_after_queue_commit_is_replayed_on_restart(self):
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--collector-wiring-crash-fixture',str(self.root)],
            capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.assertEqual(result.returncode,79,result.stderr.decode('utf-8','replace'))
        q=self.queue();self.assertEqual(q.summary()['counts'],{'complete':1})
        self.assertEqual(q.replay_issue_events()['new_events'],1)
        self.assertEqual(q.replay_issue_events()['new_events'],0)


def _crash_fixture(root):
    root=Path(root);temporary=Path(tempfile.gettempdir()).resolve()
    if not (root.is_absolute() and root.resolve().is_relative_to(temporary) and root.name.startswith('collector-wiring-')):
        raise ValueError('Only owned temporary crash fixture directories accepted')
    queue=GuideQueue(configuration(root));queue.submit([{'url':URL,'region':dict(REGION)}]);claimed=queue.claim()
    with patch.object(queue,'_persist_issue_observation',side_effect=lambda *args:os._exit(79)):
        queue.finish(claimed['id'],{'state':'auth_required','service_verified':False,'model_used':False,'evidence':[]})


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--collector-wiring-crash-fixture':_crash_fixture(sys.argv[2])
    else:unittest.main()
