"""Dafeng must use its own source, not a county-shaped alias for Jianhu."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import regional_jiangsu
from regional_guides import RegionalStore
from regional_adapters import with_reference_capabilities

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'


class DafengCaptureTests(unittest.TestCase):
    def capture(self):return json.loads((BASE/'formal-guide-final.json').read_text('utf8'))
    def parse(self,raw=None):
        self.assertTrue(hasattr(regional_jiangsu,'parse_dafeng_capture'),'Own Dafeng source has no registered parser')
        return regional_jiangsu.parse_dafeng_capture(raw or self.capture())

    def test_own_source_fields_materials_and_provenance(self):
        g=self.parse()
        self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('jiangsu','盐城市','大丰区','320904'))
        self.assertEqual(g['authority'],'盐城市大丰区人力资源和社会保障局')
        self.assertEqual(g['fields']['办理地点']['raw_value'],'盐城市大丰区健康东路全民健身中心非诉讼中心仲裁窗口')
        self.assertEqual(g['fields']['咨询方式']['raw_value'],'0515-69865022')
        self.assertEqual(g['fields']['办理时间']['raw_value'],'周一至周五，9:00—16:30，法定节假日除外。')
        self.assertEqual([m['copies'] for m in g['materials']],['2','2','1','4'])
        self.assertEqual(len(g['sections']),12);self.assertEqual(len(g['templates']),8)
        own_blank={t['original_name']:t['id'] for t in g['templates'] if t['official_kind']=='blank'}
        self.assertEqual(own_blank['劳动人事争议仲裁申请书（空白表格）'],'8984153f-2c04-4676-a8fd-3a627658fb9d')
        self.assertEqual(own_blank['劳动人事争议仲裁案件证据清单（空白表格）'],'b104e1d9-15a7-489a-ad8b-80e22e0673e7')
        self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url'])
        self.assertTrue(all(not t['can_generate'] for t in g['templates']))
        self.assertTrue(all(t['region_code']=='320904' and t['source_url']==g['source_url'] for t in g['templates']))

    def test_no_other_county_parser_or_store_fallback(self):
        raw=self.capture()
        for parser in [regional_jiangsu.parse_xishan_capture,regional_jiangsu.parse_jianhu_capture]:
            with self.assertRaises(ValueError):parser(raw)
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'guide.sqlite');g=s.put_guide(self.parse())
            self.assertNotIn(g['source_id'],['b1f8ab307b0a4f634081c052','ef1eb897ebf880c6f2a316f5'])
            self.assertIsNone(s.lookup('jiangsu','盐城市','阜宁县')['source_id'])
            self.assertIsNone(s.lookup('jiangsu','盐城市','建湖县')['source_id'])

    def test_wrong_actual_header_authority_or_task_rejected(self):
        self.parse()
        for key,old,new in [('html','class="area_local">大丰区','class="area_local">建湖县'),
                            ('html','盐城市大丰区人力资源和社会保障局','建湖县人力资源和社会保障局'),
                            ('url','11320982553776482X400201430200201','11320925014387568C400201430200201')]:
            raw=self.capture();self.assertIn(old,raw[key]);raw[key]=raw[key].replace(old,new)
            with self.assertRaises(ValueError):self.parse(raw)

    def test_only_own_downloaded_blank_annexes_can_match_the_layout_adapter(self):
        guide=json.loads((BASE/'guide.json').read_text('utf8'))
        result=with_reference_capabilities(guide)
        enabled={t['id']:t['document_types'] for t in result['templates'] if t.get('can_generate')}
        self.assertEqual(enabled,{'8984153f-2c04-4676-a8fd-3a627658fb9d':['application'],
                                 'b104e1d9-15a7-489a-ad8b-80e22e0673e7':['evidence']})
        for t in result['templates']:
            if t.get('can_generate'):self.assertIn('大丰区',t['generation_label'])
        for key,value in [('district','建湖县'),('source_url','https://ycdf.jszwfw.gov.cn/unverified-guide'),('region_code','320925')]:
            changed=copy.deepcopy(guide);changed[key]=value
            self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
        changed=copy.deepcopy(guide)
        for t in changed['templates']:t['file']=t['file'].replace('/320904/','/320925/')
        self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))


if __name__=='__main__':unittest.main()
