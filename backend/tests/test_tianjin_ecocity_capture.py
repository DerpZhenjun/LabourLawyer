"""Own functional-area capture must not turn into province-wide authority."""
import copy
import json
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from regional_guides import RegionalStore, select_template

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city'


class EcoCityCaptureTests(unittest.TestCase):
    def setUp(self):
        self.raw={n:json.loads((BASE/'current-path-dom-0330'/f'{n}.json').read_text('utf8'))
                  for n in ['guide','online-channel','official-annexes','current-service-portal','current-list']}
        self.files=json.loads((BASE/'native-downloads-0306/original-files.json').read_text('utf8'))

    def parse(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('regional_tianjin'),'缺少生态城自身指南解析器')
        import regional_tianjin
        return regional_tianjin.parse_ecocity_capture(self.raw,self.files)

    def test_own_five_materials_window_channel_and_conflicting_contact_sources(self):
        g=self.parse()
        self.assertEqual(g['district'],'中新天津生态城')
        self.assertIsNone(g['official_region_code'])
        self.assertEqual(g['region_code'],'function:tianjin-eco-city')
        self.assertEqual(len(g['materials']),5)
        self.assertIn('外省市',g['materials'][4]['applicable_conditions'])
        self.assertEqual(g['fields']['联系电话']['raw_value'],'022-66179792')
        self.assertEqual(g['fields']['联系电话']['verification_status'],'conflict')
        self.assertIn('022-66328970',g['fields']['联系电话']['alternative_sources'][0]['raw_value'])
        self.assertEqual(g['channel']['online_status'],'unavailable')
        self.assertIsNone(g['channel']['entry_url'])
        self.assertIn('中新友好图书馆B5',g['fields']['办理地点']['raw_value'])
        self.assertIn('13：30',g['fields']['办理时间']['raw_value'])
        self.assertEqual(g['fields']['咨询方式']['verification_status'],'conflict')
        self.assertNotIn('承诺办结时限',g['fields'])
        self.assertEqual(g['templates'][0]['official_kind'],'sample')
        self.assertEqual(g['templates'][1]['official_kind'],'blank')
        self.assertTrue(all(not t['can_generate'] for t in g['templates']))

    def test_exact_functional_area_lookup_download_identity_and_generation_block(self):
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'public.sqlite');g=s.put_guide(self.parse())
            for district in ['滨海新区','天津市','中新天津生态城旁的其他地区']:
                self.assertIsNone(s.lookup('tianjin','天津市',district)['source_id'])
            for t in g['templates']:
                with self.assertRaises(ValueError):select_template(g,t['id'],'application','reference_adaptation')
            self.assertNotEqual(g['source_id'],'ef1eb897ebf880c6f2a316f5')

    def test_reject_wrong_host_missing_online_panel_or_foreign_download(self):
        for location,key,value in [('guide','url','https://other.gov.cn/p1/sqldzc/20171010/461.html'),
                                   ('online-channel','text','在线咨询'),
                                   ('current-list','html','<a href="https://other.gov.cn">劳动争议仲裁申请</a>')]:
            with self.subTest(location=location):
                original=copy.deepcopy(self.raw);self.raw[location][key]=value
                with self.assertRaises(ValueError):self.parse()
                self.raw=original
        self.files[0]['download_url']='https://other.gov.cn/application.doc'
        with self.assertRaises(ValueError):self.parse()

    def test_reject_duplicate_annex_in_place_of_missing_own_form(self):
        self.files=[self.files[0],copy.deepcopy(self.files[0])]
        with self.assertRaises(ValueError):self.parse()


if __name__=='__main__':unittest.main()
