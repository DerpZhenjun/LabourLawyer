"""Bounded candidate discovery must never grant guide coverage or consume other jobs."""
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_directory import DirectoryStore

PAYLOAD = {'province':'anhui','city':'合肥市','district':'蜀山区','provider':'national','code':'340104'}
SAMPLE = ROOT / 'reports/nationwide-localization-20261028/anhui/discovery-api-sample/response.bin'


def response(rows):
    return {'status':200,'final_url':'https://gjzwfw.www.gov.cn/fwmh/item/v3/findItemList.do','headers':{'Content-Type':'application/json'},
            'body':json.dumps({'success':True,'code':'200','data':{'list':rows}},ensure_ascii=False).encode()}


def candidate(title='劳动人事争议仲裁申请', **extra):
    return {'taskName':title,'taskBlCode':'own-task-123',**extra}


class RegionalDiscoveryTests(unittest.TestCase):
    def test_lock_owner_recovers_interrupted_discovery_without_other_kind_recovery(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=DirectoryStore(root/'backend/data/regional-directory.sqlite')
            own=store.enqueue('service_discovery',PAYLOAD);other=store.enqueue('candidate_review',PAYLOAD)
            store.claim('service_discovery');store.claim('candidate_review')
            r=m.run_discovery(root,root/'reports/run',apply=True,limit=1,fetcher=lambda *a:response([candidate()]),sleeper=lambda _:None)
            self.assertEqual(len(r['results']),1)
            with store.connection() as db:states={r['id']:r['state'] for r in db.execute('SELECT id,state FROM discovery_jobs')}
            self.assertEqual(states[own],'needs_browser');self.assertEqual(states[other],'running')

    def test_exact_existing_candidate_avoids_network_and_neighbour_still_discovers(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=DirectoryStore(root/'backend/data/regional-directory.sqlite')
            store.enqueue('service_discovery',PAYLOAD);store.enqueue('service_discovery',dict(PAYLOAD,district='包河区',code='340111'))
            registry=root/'reports/nationwide-localization-20261028/CANDIDATES.json';registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps([{**PAYLOAD,'source_id':'own','source_url':'https://hf.ahzwfw.gov.cn/own'}],ensure_ascii=False),encoding='utf8')
            calls=[]
            def fetch(url,form,timeout):calls.append(form['areaCode']);return response([candidate()])
            result=m.run_discovery(root,root/'reports/run',apply=True,limit=2,fetcher=fetch,sleeper=lambda _:None)
            self.assertEqual(calls,['340111']);self.assertTrue(result['results'][0]['network_skipped'])
            self.assertEqual(result['results'][0]['existing_evidence'][0]['source_id'],'own')
            self.assertFalse(result['results'][0]['guide_verified'])

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_discovery'),'Missing bounded candidate discovery worker')
        import regional_discovery
        return regional_discovery

    # Break caught: silently guesses between two provider codes or accepts an unsupported source.
    def test_resolves_legacy_or_new_explicit_identity_but_refuses_ambiguous_codes(self):
        m=self.module()
        self.assertEqual(m.resolve_target(PAYLOAD)['code'],'340104')
        newer={k:PAYLOAD[k] for k in ['province','city','district']}
        newer['directory_sources']=[{'provider':'national','code':'340104'},{'provider':'national','code':'340104'}]
        self.assertEqual(m.resolve_target(newer)['provider'],'national')
        for payload in [dict(PAYLOAD,provider='unknown'),dict(PAYLOAD,code='340104000000'),
                        dict(PAYLOAD,directory_sources=[{'provider':'national','code':'340111'}]),
                        {**newer,'directory_sources':[{'provider':'national','code':'340104'},{'provider':'national','code':'340111'}]},
                        {k:v for k,v in PAYLOAD.items() if k!='code'}]:
            with self.subTest(payload=payload),self.assertRaises(ValueError):m.resolve_target(payload)

    # Break caught: returns mediation/general labour arbitration as complete target or trusts request area as response identity.
    def test_exact_title_only_and_missing_response_region_stays_browser_candidate(self):
        m=self.module()
        rows=[candidate('劳动人事争议调解申请'),candidate('劳动仲裁'),candidate('劳动人事争议仲裁申请（调解）'),candidate(regionCode='340111'),candidate()]
        result=m.classify_response(response(rows)['body'],m.resolve_target(PAYLOAD))
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(result['candidates'][0]['region_match'],'unverified')
        self.assertEqual(result['candidates'][0]['verification_status'],'unverified')
        self.assertEqual(result['candidates'][0]['state'],'needs_browser')
        self.assertEqual(len(result['rejected']),4)

    # Break caught: treats an HTTP200 official failure as proof that no service exists.
    def test_actual_null_api_response_is_error_not_no_service(self):
        m=self.module()
        result=m.classify_response(SAMPLE.read_bytes(),m.resolve_target(PAYLOAD))
        self.assertEqual(result['state'],'manual_review')
        self.assertEqual(result['candidates'],[])
        self.assertEqual(result['api_code'],'1003')
        self.assertFalse(result['absence_verified'])

    # Break caught: dry-run constructs/writes a store, claims jobs, or starts network work.
    def test_default_dry_run_leaves_public_db_bytes_and_other_databases_untouched(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=DirectoryStore(root/'backend/data/regional-directory.sqlite')
            store.enqueue('service_discovery',PAYLOAD);before=store.path.read_bytes()
            calls=[]
            result=m.run_discovery(root,root/'reports/run',fetcher=lambda *a:calls.append(a))
            self.assertEqual(calls,[]);self.assertEqual(store.path.read_bytes(),before)
            self.assertFalse(result['applied']);self.assertEqual(len(result['planned']),1)
            self.assertFalse((root/'backend/data/regional-guides.sqlite').exists())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.assertEqual(m.run_discovery(root,root/'reports/run')['planned'],[])
            self.assertFalse((root/'backend/data').exists())

    # Break caught: apply consumes other queue kinds, skips backup, publishes candidates or stops after unsupported provider.
    def test_apply_backs_up_claims_only_discovery_continues_manual_and_never_done(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=DirectoryStore(root/'backend/data/regional-directory.sqlite')
            untouched=store.enqueue('directory',{'provider':'national','parent':''})
            first=store.enqueue('service_discovery',dict(PAYLOAD,provider='unknown'))
            second=store.enqueue('service_discovery',PAYLOAD)
            third=store.enqueue('service_discovery',dict(PAYLOAD,code='340111',district='包河区'))
            fetches=[]
            def fetch(url,form,timeout):fetches.append((url,form,timeout));return response([candidate()])
            r=m.run_discovery(root,root/'reports/run',apply=True,limit=2,fetcher=fetch,sleeper=lambda _:None)
            self.assertTrue(Path(r['backup']).is_file());self.assertEqual(len(fetches),1)
            with store.connection() as db:states={x['id']:x['state'] for x in db.execute('SELECT id,state FROM discovery_jobs')}
            self.assertEqual(states,{untouched:'pending',first:'manual_review',second:'needs_browser',third:'pending'})
            with closing(sqlite3.connect(r['backup'])) as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM discovery_jobs WHERE state='pending'").fetchone()[0],4)
            self.assertEqual(len(list((Path(r['run_folder'])/'outbox').glob('*.json'))),2)
            self.assertFalse((root/'backend/data/regional-guides.sqlite').exists())

    # Break caught: fallback is only declared, loses failed query bytes, or bypasses rate spacing.
    def test_real_query_fallback_retains_each_raw_response_url_clock_sha_and_outbox(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=DirectoryStore(root/'backend/data/regional-directory.sqlite');store.enqueue('service_discovery',PAYLOAD)
            queries=[];pauses=[]
            def fetch(url,form,timeout):
                queries.append(form['taskName'])
                return response([] if len(queries)==1 else [candidate('劳动争议仲裁申请',regionCode='340104')])
            r=m.run_discovery(root,root/'reports/run',apply=True,limit=1,delay=2.25,timeout=7,fetcher=fetch,sleeper=pauses.append)
            self.assertEqual(queries,['劳动人事争议仲裁申请','劳动争议仲裁申请']);self.assertEqual(pauses,[2.25])
            job=r['results'][0];self.assertEqual(job['state'],'needs_browser');self.assertTrue(job['alias_required'])
            self.assertTrue(all(x['collected_at'] and len(x['sha256'])==64 and Path(x['response_file']).is_file() for x in job['attempts']))
            self.assertEqual(job['candidates'][0]['region_match'],'explicit_match')
            self.assertFalse(job['guide_verified']);self.assertFalse(job['can_generate'])
            self.assertEqual(len(list((Path(r['run_folder'])/'outbox').glob('*.json'))),1)

    # Break caught: one timeout aborts the batch or configurable bounds permit uncontrolled crawling.
    def test_transport_failure_is_durable_and_next_locality_continues_with_bounds(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=DirectoryStore(root/'backend/data/regional-directory.sqlite')
            store.enqueue('service_discovery',PAYLOAD);store.enqueue('service_discovery',dict(PAYLOAD,code='340111',district='包河区'))
            calls=[]
            def fetch(url,form,timeout):
                calls.append(form['areaCode'])
                if len(calls)==1:raise TimeoutError('bounded timeout')
                return response([candidate()])
            r=m.run_discovery(root,root/'reports/run',apply=True,limit=2,fetcher=fetch,sleeper=lambda _:None)
            self.assertEqual([j['state'] for j in r['results']],['manual_review','needs_browser'])
            self.assertIn('bounded timeout',r['results'][0]['attempts'][0]['error'])
            for kwargs in [{'delay':1.99},{'timeout':0},{'limit':10000}]:
                with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):m.run_discovery(root,root/'reports/run',**kwargs)

    # Break caught: a second process can claim jobs while an OS lock is held by the first.
    def test_exclusive_os_lock_fails_closed(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            lock=Path(temp)/'worker.lock'
            with m.exclusive_lock(lock):
                with self.assertRaises(RuntimeError):
                    with m.exclusive_lock(lock):pass


if __name__=='__main__':unittest.main()
