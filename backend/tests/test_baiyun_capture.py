"""Own county notice, archive identity and download boundary, not province fallback."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from regional_guides import RegionalStore
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.regional_guides import router
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-baiyun'


class BaiyunCaptureTests(unittest.TestCase):
    def setUp(self):
        self.raw=json.loads((BASE/'source-0405/dom.json').read_text('utf8'))
        self.files=json.loads((BASE/'downloads-0410/original-files.json').read_text('utf8'))

    def parse(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_guangdong'),'缺少白云区自身来源解析器')
        import regional_guangdong
        return regional_guangdong.parse_baiyun_capture(self.raw,self.files)

    def test_paper_materials_and_mailed_receipt_do_not_prove_window_only_or_online_submission(self):
        g=self.parse()
        self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('guangdong','广州市','白云区','440111'))
        self.assertEqual(g['source_type'],'official_material_notice')
        self.assertEqual(g['channel']['form'],'unverified')
        self.assertEqual(g['channel']['online_status'],'unverified')
        self.assertIsNone(g['channel']['entry_url'])
        self.assertIsNone(g['fields']['办理形式']['normalized_value'])
        self.assertEqual(g['fields']['办理形式']['verification_status'],'missing')
        self.assertIsNone(g['service_code'])

    def test_six_own_materials_conditional_copies_and_distinct_blank_examples_instructions(self):
        g=self.parse()
        self.assertEqual(len(g['materials']),6)
        self.assertEqual([m['copies'] for m in g['materials']],['2','1','1','2','2','收件单及存根各1份'])
        self.assertIn('每增加一个被申请人',g['materials'][3]['applicable_conditions'])
        self.assertIn('身份证件和企业注册登记信息不属于证据',g['materials'][3]['details']['官方材料原文'])
        self.assertIn('光盘',g['materials'][4]['details']['官方材料原文'])
        self.assertEqual(len(g['templates']),8)
        byfile={t['file']:t for t in g['templates']}
        blank=byfile['templates/_docx/_regional/440111/package-1/05.doc']
        self.assertEqual(blank['official_kind'],'blank')
        self.assertEqual(blank['contained_document_types'],['application','evidence'])
        self.assertEqual(byfile['templates/_docx/_regional/440111/package-1/04.docx']['official_kind'],'instruction')
        self.assertTrue(all(t['official_kind']=='sample' for t in g['templates'] if '/package-2/' in t['file']))
        self.assertTrue(all(not t['can_generate'] and not t['document_types'] for t in g['templates']))

    def test_reject_foreign_source_changed_title_or_missing_duplicate_and_foreign_archive(self):
        original=copy.deepcopy(self.raw)
        for key,value in [('url',self.raw['url'].replace('www.by.gov.cn','www.other.gov.cn')),
                          ('html',self.raw['html'].replace('白云区劳动人事争议仲裁申请材料清单','劳动人事争议调解'))]:
            self.raw[key]=value
            with self.assertRaises(ValueError):self.parse()
            self.raw=copy.deepcopy(original)
        originals=copy.deepcopy(self.files)
        for files in [[self.files[0],copy.deepcopy(self.files[0])],self.files[:1]]:
            self.files=files
            with self.assertRaises(ValueError):self.parse()
        self.files=originals;self.files[0]['download_url']='https://other.gov.cn/template.zip'
        with self.assertRaises(ValueError):self.parse()

    def test_actual_api_downloads_own_eight_originals_blocks_generation_and_neighbour_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'public.sqlite');g=store.put_guide(self.parse())
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=store),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                for t in g['templates']:
                    r=client.get('/api/regional-guides/templates/'+t['id'],params=params)
                    self.assertEqual(r.status_code,200)
                    self.assertEqual(hashlib.sha256(r.content).hexdigest(),t['sha256'])
                self.assertIsNone(client.get('/api/regional-guides/lookup',params={**params,'district':'天河区'}).json()['source_id'])
                wrong={**params,'district':'天河区'}
                self.assertEqual(client.get('/api/regional-guides/templates/'+g['templates'][0]['id'],params=wrong).status_code,404)
                payload={k:g[k] for k in ['province','city','district','source_id','version']}
                payload.update(template_id=g['templates'][4]['id'],kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)

    def test_official_material_change_gets_a_new_version_without_overwriting_previous_requirements(self):
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'public.sqlite');first=store.put_guide(self.parse())
            self.raw['html']=self.raw['html'].replace('复印件两份（签名并盖手印）','复印件三份（签名并盖手印）')
            second=store.put_guide(self.parse())
            self.assertNotEqual(first['version'],second['version'])
            self.assertEqual(second['materials'][0]['copies'],'3')
            self.assertEqual(store.versions('guangdong','广州市','白云区')[1]['materials'][0]['copies'],'2')
            self.assertEqual(first['source_id'],second['source_id'])
            self.assertNotEqual(first['source_id'],'5725c8df9cb686d0517254e8')


if __name__=='__main__':unittest.main()
