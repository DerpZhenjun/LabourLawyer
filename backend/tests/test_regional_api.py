import os
import sys
import tempfile
import unittest
import io
import json
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_regional_guides import guide
from regional_guides import RegionalStore

class RegionalAPI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'regional.sqlite'
        env=patch.dict(os.environ,{'LABOURLAWYER_REGIONAL_DB':str(self.db)});env.start();self.addCleanup(env.stop)
        from routes.regional_guides import router
        app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
        self.client=TestClient(app);self.store=RegionalStore(self.db)
        self.store.put_guide(guide())
    def test_region_query_exact_and_required(self):
        r=self.client.get('/api/regional-guides/lookup',params={'province':'sichuan','city':'成都市','district':'武侯区'})
        self.assertEqual(r.status_code,200);self.assertIsNone(r.json()['source_id'])
        self.assertEqual(self.client.get('/api/regional-guides/lookup').status_code,422)
    def test_generation_rejects_unverified_district(self):
        r=self.client.post('/api/regional-guides/generate',json={'province':'sichuan','city':'成都市','district':'武侯区','source_id':'other','version':1,'template_id':'x','kind':'application','mode':'reference_adaptation','data':{}})
        self.assertEqual(r.status_code,409)
    def test_template_cannot_use_neighbor_id(self):
        r=self.client.get('/api/regional-guides/templates/x',params={'province':'sichuan','city':'成都市','district':'天府新区'})
        self.assertEqual(r.status_code,404)
    def test_public_reporting_cannot_acknowledge_or_mutate(self):
        self.store.record_event({'type':'AUTH_REQUIRED','url':'https://www.sczwfw.gov.cn/'})
        self.assertEqual(self.client.get('/api/regional-guides/events').json()['pending'],1)
        self.assertEqual(self.client.post('/api/regional-guides/events',json={}).status_code,405)
    def test_versions_return_real_history(self):
        changed=guide();changed['materials'][0]['copies']='4';self.store.put_guide(changed)
        r=self.client.get('/api/regional-guides/versions',params={'province':'sichuan','city':'成都市','district':'天府新区'})
        self.assertEqual(len(r.json()['items']),2)

    def test_report_pending_count_is_live_not_last_attempt(self):
        self.store.record_event({'type':'AUTH_REQUIRED','url':'https://www.sczwfw.gov.cn/'})
        self.assertEqual(self.client.get('/api/regional-guides/report').json()['openclaw']['pending_count'],1)

    def real_guide(self):
        root=Path(__file__).resolve().parents[2]
        d=json.loads((root/'reports/government-guide-localization/SOURCE-INVENTORY.json').read_text(encoding='utf8'))
        return self.store.put_guide(next(g for g in d['regions'] if g['district']=='天府新区'))

    def test_real_official_sample_download_and_reference_generation(self):
        from docx import Document
        g=self.real_guide();t=next(t for t in g['templates'] if t.get('can_generate'))
        r=self.client.get('/api/regional-guides/templates/'+t['id'],params={k:g[k] for k in ['province','city','district']})
        self.assertEqual(r.status_code,200)
        for kind in ['application','evidence']:
            payload={k:g[k] for k in ['province','city','district','source_id','version']}
            payload.update(template_id=t['id'],kind=kind,mode='reference_adaptation',data={})
            r=self.client.post('/api/regional-guides/generate',json=payload)
            self.assertEqual(r.status_code,200);self.assertEqual(r.headers['x-document-origin'],'official-sample-adaptation-not-blank')
            doc=Document(io.BytesIO(r.content));self.assertIn('请本人手写签名' if kind=='application' else '提交人：','\n'.join(p.text for p in doc.paragraphs))

    def test_reference_cannot_be_falsely_requested_as_official_blank(self):
        g=self.real_guide();t=next(t for t in g['templates'] if t.get('can_generate'))
        payload={k:g[k] for k in ['province','city','district','source_id','version']}
        payload.update(template_id=t['id'],kind='application',mode='blank',data={})
        self.assertEqual(self.client.post('/api/regional-guides/generate',json=payload).status_code,409)

if __name__=='__main__':unittest.main()
