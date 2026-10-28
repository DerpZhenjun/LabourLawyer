"""Own Haizhou fixture: preserve district identity, copies and unknown channel."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import regional_jiangsu
from regional_guides import RegionalStore
from regional_adapters import with_reference_capabilities
from routes.regional_guides import router

BASE=Path(__file__).resolve().parents[2]/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou/formal-0525'


class HaizhouCaptureTests(unittest.TestCase):
    def capture(self):return json.loads((BASE/'formal-guide-final.json').read_text('utf8'))
    def parse(self,raw=None):
        self.assertTrue(hasattr(regional_jiangsu,'parse_haizhou_capture'),'Own Haizhou guide parser is missing')
        return regional_jiangsu.parse_haizhou_capture(raw or self.capture())

    def test_own_requirements_not_other_jiangsu_localities(self):
        g=self.parse()
        self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('jiangsu','连云港市','海州区','320706'))
        self.assertEqual(g['service_code'],'11320706014267312C400201430200201')
        self.assertEqual(g['authority'],'连云港市海州区人力资源和社会保障局')
        self.assertEqual(g['fields']['办理地点']['raw_value'],'连云港市海州区基层治理服务中心1楼7-8号人社窗口（连云港市海州区秦东门大街379号）')
        self.assertEqual(g['fields']['咨询方式']['raw_value'],'0518-85207708')
        self.assertEqual(g['fields']['到办事现场次数']['raw_value'],'3')
        self.assertEqual(g['fields']['法定办结时限']['raw_value'],'45个工作日')
        self.assertEqual([m['copies'] for m in g['materials']],['2','2','1','4'])
        self.assertEqual([m['original_copy'] for m in g['materials']],['复印件','原件和复印件','原件','原件'])
        self.assertEqual(len(g['sections']),12)
        self.assertEqual(len(g['templates']),8)
        self.assertEqual(sum(t['official_kind']=='blank' for t in g['templates']),4)
        self.assertEqual(sum(t['official_kind']=='sample' for t in g['templates']),4)
        self.assertEqual(g['channel']['online_status'],'unverified')
        self.assertIsNone(g['channel']['entry_url'])
        self.assertTrue(all(t['source_url']==g['source_url'] and t['region_code']=='320706' for t in g['templates']))
        self.assertFalse(any(t['can_generate'] for t in with_reference_capabilities(g)['templates']))

    def test_wrong_portal_authority_task_or_visible_district_is_rejected(self):
        self.parse()
        for key,old,new in [('url','lyghz.jszwfw.gov.cn','www.jszwfw.gov.cn'),
                            ('url','11320706014267312C400201430200201','113207000142524902300201430200201'),
                            ('html','class="area_local">海州区','class="area_local">连云港市'),
                            ('html','连云港市海州区人力资源和社会保障局','连云港市人力资源和社会保障局')]:
            raw=self.capture();self.assertIn(old,raw[key]);raw[key]=raw[key].replace(old,new)
            with self.assertRaises(ValueError):self.parse(raw)

    def test_storing_own_guide_does_not_enable_province_or_neighbour(self):
        for parser in [regional_jiangsu.parse_xishan_capture,regional_jiangsu.parse_jianhu_capture,regional_jiangsu.parse_dafeng_capture]:
            with self.assertRaises(ValueError):parser(self.capture())
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'guides.sqlite');own=store.put_guide(self.parse())
            self.assertNotIn(own['source_id'],['5725c8df9cb686d0517254e8','b1f8ab307b0a4f634081c052','ef1eb897ebf880c6f2a316f5'])
            self.assertIsNone(store.lookup('jiangsu','连云港市','赣榆区')['source_id'])
            self.assertIsNone(store.lookup('jiangsu','连云港市','')['source_id'])

    def test_api_uses_eight_own_downloads_not_sample_generation_or_neighbour(self):
        own_guide=json.loads((BASE.parent/'staging-0540/reviewed-guide.json').read_text('utf8'))
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'guides.sqlite');g=store.put_guide(own_guide)
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=store),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                for t in g['templates']:
                    response=client.get('/api/regional-guides/templates/'+t['id'],params=params)
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(hashlib.sha256(response.content).hexdigest(),t['sha256'])
                self.assertIsNone(client.get('/api/regional-guides/lookup',params={**params,'district':'赣榆区'}).json()['source_id'])
                wrong={**params,'district':'赣榆区'}
                self.assertEqual(client.get('/api/regional-guides/templates/'+g['templates'][0]['id'],params=wrong).status_code,404)
                payload={k:g[k] for k in ['province','city','district','source_id','version']}
                payload.update(template_id='a9e8100a-b098-4a42-8c09-0f3c7536ed0d',kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)


if __name__=='__main__':unittest.main()
