"""Rollout aggregation and resumable planning must not promote directory/candidates."""
from contextlib import closing
import importlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_directory import DirectoryStore
from regional_guides import RegionalStore

CAT=[{'slug':'sichuan','name':'四川省'},{'slug':'jiangsu','name':'江苏省'}]
def area(code,city,district,provider='national'):
    return dict(provider=provider,code=code,province='sichuan',city=city,district=district,level=4,
                source_url='https://www.sczwfw.gov.cn/',collected_at='2026-10-28T00:00:00Z')
def guide(city,district,ready=False):
    return dict(province='sichuan',city=city,district=district,region_code='fixture:'+district,
        service_name='劳动人事争议仲裁申请',source_url='https://www.sczwfw.gov.cn/'+district,
        collected_at='2026-10-28T00:00:00Z',verified_at='2026-10-28T00:00:00Z',
        verification_status='verified',templates=[{'can_generate':ready}],fields={},sections={})

class RolloutTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_rollout'),'Rollout implementation missing')
        return importlib.import_module('regional_rollout')

    # Break caught: directory rows, aliases or candidates falsely inflate readiness.
    def test_exact_union_preserves_provider_records_and_unpublished_candidates(self):
        m=self.module();rows=[area('1','成都市','高新区'),area('2','成都市','高新区','local'),
             area('1','成都市','武侯区','local'),area('3','自贡市','高新区'),area('4','成都市','成都高新区')]
        published=[guide('成都市','武侯区',True),guide('自贡市','沿滩区')]
        candidates=[dict(province='sichuan',city='成都市',district='高新区',can_generate=True,offline_adapter_matches=[{}]),
                    dict(province='sichuan',city='成都市',district='武侯区',can_generate=True)]
        status=m.build_rollout_status(rows,published,candidates,CAT)
        self.assertEqual({k:status[k] for k in ['targets_total','published_guides','generatable_localities','unpublished_candidates']},
                         dict(targets_total=5,published_guides=2,generatable_localities=1,unpublished_candidates=1))
        p=status['provinces'][0]
        self.assertEqual((p['targets_total'],p['guide_only'],p['candidates'],p['uncollected']),(5,1,1,2))
        self.assertTrue(status['directory_is_not_guide_coverage'])
        self.assertEqual(status['province_count'],2)
        targets=m.build_rollout_targets(rows,published,candidates)
        merged=next(t for t in targets if (t['city'],t['district'])==('成都市','高新区'))
        self.assertEqual([r['provider'] for r in merged['directory_records']],['national','local'])
        self.assertEqual(rows[0]['code'],'1')

    # Break caught: all currently known entries being ready falsely means census complete.
    def test_no_independent_census_never_claims_complete(self):
        status=self.module().build_rollout_status([], [guide('成都市','武侯区',True)],[],CAT)
        self.assertEqual([p['completion_status'] for p in status['provinces']],['incomplete','incomplete'])
        self.assertEqual(status['targets_total'],1)
        self.assertEqual(status['provinces'][1]['targets_total'],0)

    def workspace(self,root):
        d=DirectoryStore(root/'backend/data/regional-directory.sqlite')
        for row in [area('1','成都市','未采集区'),area('2','成都市','候选区'),area('3','成都市','仅指南区'),area('4','成都市','可生成区')]:d.put_area(row)
        g=RegionalStore(root/'backend/data/regional-guides.sqlite')
        g.put_guide(guide('成都市','仅指南区'));g.put_guide(guide('成都市','可生成区',True))
        cat=root/'frontend/src/data/provinceCatalog.json';cat.parent.mkdir(parents=True);cat.write_text(json.dumps(CAT),encoding='utf8')
        reg=root/'reports/nationwide-localization-20261028/CANDIDATES.json';reg.parent.mkdir(parents=True)
        reg.write_text(json.dumps([dict(province='sichuan',city='成都市',district='候选区',can_generate=True)]),encoding='utf8')
        return d,g

    # Break caught: dry-run initialization, migration or queue insertion changes public DB.
    def test_dry_run_does_not_write_databases_or_create_missing_database(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);d,g=self.workspace(root);before={p:p.read_bytes() for p in [d.path,g.path]}
            plan=m.plan_workspace(root)
            self.assertEqual(sorted(t['kind'] for t in plan['tasks']),['candidate_review','document_adaptation','service_discovery'])
            self.assertTrue(all(p.read_bytes()==body for p,body in before.items()))
            self.assertFalse(plan['applied'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);cat=root/'frontend/src/data/provinceCatalog.json';cat.parent.mkdir(parents=True);cat.write_text(json.dumps(CAT))
            self.assertEqual(m.plan_workspace(root)['tasks'],[])
            self.assertFalse((root/'backend/data').exists())

    # Break caught: repeated plans or provider additions reset/duplicate done/running work.
    def test_apply_backs_up_directory_and_preserves_existing_jobs_idempotently(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);d,g=self.workspace(root)
            done=d.enqueue('service_discovery',dict(province='sichuan',city='成都市',district='未采集区',provider='old',code='old'))
            d.finish(done,'done',{'own_evidence':'retained'})
            running=d.enqueue('document_adaptation',dict(province='sichuan',city='成都市',district='仅指南区'))
            self.assertEqual(d.claim('document_adaptation')['id'],running)
            guide_bytes=g.path.read_bytes()
            first=m.plan_workspace(root,apply=True)
            self.assertTrue(Path(first['backup']).is_file());self.assertEqual(first['enqueued'],1)
            second=m.plan_workspace(root,apply=True);self.assertEqual(second['enqueued'],0)
            with d.connection() as db:jobs=[dict(r) for r in db.execute('SELECT * FROM discovery_jobs')]
            self.assertEqual(len(jobs),3)
            self.assertEqual(next(j['state'] for j in jobs if j['id']==done),'done')
            self.assertEqual(next(j['state'] for j in jobs if j['id']==running),'running')
            self.assertEqual(g.path.read_bytes(),guide_bytes)
            with closing(sqlite3.connect(first['backup'])) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM discovery_jobs').fetchone()[0],2)

    # Break caught: arbitrary registry paths or historical fallback shadow current review state.
    def test_fixed_registry_precedence_and_historical_fallback(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.workspace(root)
            fallback=root/'reports/nationwide-localization-20261023-night/PENDING-SOURCES.json';fallback.parent.mkdir(parents=True)
            fallback.write_text(json.dumps([dict(province='sichuan',city='旧城',district='旧区')]))
            self.assertEqual(m.load_rollout_candidates(root)[0]['district'],'候选区')
            (root/'reports/nationwide-localization-20261028/CANDIDATES.json').unlink()
            self.assertEqual(m.load_rollout_candidates(root)[0]['district'],'旧区')

    def test_canonical_registry_is_not_shadowed_by_old_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.workspace(root)
            release=root/'config/regional_candidates.json';release.parent.mkdir()
            release.write_text(json.dumps([dict(province='sichuan',city='成都市',district='最新候选区')]))
            self.assertEqual(self.module().load_rollout_candidates(root)[0]['district'],'最新候选区')

    # Break caught: API drops directory rows or exposes the full nationwide target payload.
    def test_endpoint_returns_only_compact_province_aggregates(self):
        self.module()
        import routes.regional_guides as routes
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);d,g=self.workspace(root);app=FastAPI();app.include_router(routes.router,prefix='/api/regional-guides')
            with patch.object(routes,'ROOT',root),patch.object(routes,'store',return_value=g),patch.object(routes,'directory_store',return_value=d),TestClient(app) as client:
                response=client.get('/api/regional-guides/rollout-status')
            self.assertEqual(response.status_code,200)
            body=response.json();self.assertEqual(body['targets_total'],4);self.assertEqual(body['generatable_localities'],1)
            self.assertNotIn('targets',body);self.assertNotIn('directory_records',json.dumps(body))
            self.assertEqual(len(body['provinces']),2)

if __name__=='__main__':unittest.main()
