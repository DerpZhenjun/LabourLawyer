"""Own functional-area identity, raw examples and original bytes stay distinct."""
import copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from regional_guides import RegionalStore
from routes.regional_guides import router
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang'


@unittest.skipUnless((BASE / 'downloads-0425/original-file.json').is_file(),
                     'Local HTTP capture retains response cookies; not distributed in public checkout')
class RongjiangCaptureTests(unittest.TestCase):
    def setUp(self):
        self.raw=json.loads((BASE/'source-0425/dom.json').read_text('utf8'))
        self.original=json.loads((BASE/'downloads-0425/original-file.json').read_text('utf8'))
        self.identity=json.loads((BASE/'identity-0430/identity.json').read_text('utf8'))
        self.slots=json.loads((BASE/'document-qa/original-slots.json').read_text('utf-8-sig'))

    def parse(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_jiangxi'),'Missing own Rongjiang source parser')
        import regional_jiangxi
        return regional_jiangxi.parse_rongjiang_capture(self.raw,self.original,self.identity,self.slots)

    def test_own_service_directory_identity_not_administrative_or_neighbour_jurisdiction(self):
        g=self.parse()
        self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('jiangxi','赣州市','蓉江新区','360798'))
        self.assertIsNone(g['official_region_code'])
        self.assertEqual(g['official_service_region_code'],'360798')
        self.assertEqual(g['fields']['咨询方式']['raw_value'],'0797-8168180')
        self.assertNotEqual(g['fields']['咨询方式']['raw_value'],'0797-8166011')
        self.assertIn('碧玉南路1号',g['fields']['办理地点']['normalized_value'])
        self.assertEqual(g['channel']['online_status'],'unverified')
        self.assertIsNone(g['channel']['entry_url'])
        self.assertIsNone(g['fields']['是否收费']['normalized_value'])
        self.assertIsNone(g['fields']['到办事现场次数']['normalized_value'])

    def test_two_blank_original_pages_not_inferred_from_the_web_pages_filled_examples(self):
        g=self.parse();t=g['templates'][0]
        self.assertEqual(t['official_kind'],'blank')
        self.assertEqual(t['contained_document_types'],['application','evidence'])
        self.assertEqual(t['document_types'],[]);self.assertFalse(t['can_generate'])
        self.assertEqual(t['original_pages'],2)
        self.assertIn('示例',g['sections']['官方文书正文及填写示例'])
        self.assertNotIn('示例',self.slots['text'])
        self.assertEqual(t['evidence_columns'],['序号','证据名称','证据来源','证明目的','页数'])

    def test_own_conditional_evidence_does_not_inherit_baiyun_exclusion_or_sample_page_numbers(self):
        g=self.parse();materials=g['materials']
        self.assertEqual(len(materials),11)
        self.assertIn('身份证',materials[1]['name']);self.assertEqual(materials[1]['required'],'必须提供')
        self.assertIn('工商登记',materials[2]['name']);self.assertEqual(materials[2]['required'],'必须提供')
        self.assertEqual(materials[3]['required'],'根据实际情况提供')
        self.assertIn('工伤',materials[7]['applicable_conditions'])
        self.assertEqual(materials[1]['copies'],'被申请人（第三人）人数+1份')
        self.assertEqual(materials[4]['details']['示例页码（不是要求）'],'6-8')
        self.assertNotIn('6-8',materials[4]['copies'])

    def test_reject_wrong_directory_foreign_original_or_missing_review_evidence(self):
        for mutate in [lambda:setattr(self,'identity',{**self.identity,'directory_record':{**self.identity['directory_record'],'district':'南康区'}}),
                       lambda:setattr(self,'raw',{**self.raw,'url':self.raw['url'].replace('rjxq.ganzhou','www.ganzhou')}),
                       lambda:setattr(self,'original',{**self.original,'sha256':'0'*64}),
                       lambda:setattr(self,'slots',{**self.slots,'sha256':'0'*64})]:
            with self.subTest(mutate=mutate):
                saved=copy.deepcopy((self.raw,self.original,self.identity,self.slots));mutate()
                with self.assertRaises(ValueError):self.parse()
                self.raw,self.original,self.identity,self.slots=saved

    def test_exact_api_download_and_unsupported_generation_never_fall_back_to_whole_city(self):
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'public.sqlite');g=store.put_guide(self.parse())
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=store),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                t=g['templates'][0];r=client.get('/api/regional-guides/templates/'+t['id'],params=params)
                self.assertEqual(r.status_code,200);self.assertEqual(hashlib.sha256(r.content).hexdigest(),t['sha256'])
                for district in ['南康区','章贡区','赣州市']:
                    self.assertIsNone(client.get('/api/regional-guides/lookup',params={**params,'district':district}).json()['source_id'])
                payload={k:g[k] for k in ['province','city','district','source_id','version']}
                payload.update(template_id=t['id'],kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)
                self.assertNotEqual(g['source_id'],'453e9a1c8cb2122fe7fa910d')


if __name__=='__main__':unittest.main()
