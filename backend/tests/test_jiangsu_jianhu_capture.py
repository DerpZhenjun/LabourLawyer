"""Jianhu is a separately captured county, not an alias for the Xishan guide."""
import copy
import json
from pathlib import Path
import unittest
import regional_jiangsu
from regional_adapters import with_reference_capabilities

ROOT=Path(__file__).resolve().parents[2]
CAPTURE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu/attempts/20261024-0227/formal-guide-final.json'


class JianhuOwnCaptureTests(unittest.TestCase):
    def capture(self):return json.loads(CAPTURE.read_text('utf8'))
    def parse(self,capture=None):
        self.assertTrue(hasattr(regional_jiangsu,'parse_jianhu_capture'),'Own Jianhu parser identity must be explicitly registered')
        return regional_jiangsu.parse_jianhu_capture(capture or self.capture())

    def test_own_fields_counts_and_blank_annex_ids(self):
        g=self.parse()
        self.assertEqual((g['city'],g['district'],g['region_code']),('盐城市','建湖县','320925'))
        self.assertEqual(g['authority'],'建湖县人力资源和社会保障局')
        self.assertEqual(g['fields']['咨询方式']['raw_value'],'0515—86225398')
        self.assertEqual(g['fields']['办理地点']['raw_value'],'建湖县近湖街道人民南路225号;5-6号窗口')
        self.assertEqual([m['copies'] for m in g['materials']],['2','2','1','4'])
        self.assertEqual(len(g['sections']),12)
        self.assertEqual(len(g['templates']),8)
        app=next(t for t in g['templates'] if t['original_name']=='劳动人事争议仲裁申请书（空白表格）')
        self.assertEqual(app['id'],'985f4770-1ab2-4264-9482-0f8528b16513')
        evidence=next(t for t in g['templates'] if t['original_name']=='劳动人事争议仲裁案件证据清单（空白表格）')
        self.assertEqual(evidence['id'],'586cf49f-714b-4338-81ce-08a2956d7aa6')
        self.assertFalse(any(t['can_generate'] for t in g['templates']))
        self.assertIsNone(g['channel']['entry_url'])

    def test_no_cross_locality_parser_or_provenance(self):
        g=self.parse()
        with self.assertRaises(ValueError):regional_jiangsu.parse_xishan_capture(self.capture())
        old=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-xishan/formal-guide-final.json'
        with self.assertRaises(ValueError):regional_jiangsu.parse_jianhu_capture(json.loads(old.read_text('utf8')))
        for item in [*g['fields'].values(),*g['materials'],*g['templates']]:
            self.assertEqual(item['source_url'],g['source_url']);self.assertEqual(item['region_code'],'320925')

    def test_rejects_wrong_header_authority_or_task(self):
        self.parse()
        original=self.capture()
        for key,old,new in [('html','class="area_local">建湖县','class="area_local">锡山区'),
                            ('html','建湖县人力资源和社会保障局','锡山区人力资源和社会保障局'),
                            ('url','11320925014387568C400201430200201','11320205014038763X400201430200201')]:
            c=copy.deepcopy(original);c[key]=c[key].replace(old,new)
            with self.assertRaises(ValueError):regional_jiangsu.parse_jianhu_capture(c)

    def test_only_own_annexes_gain_jianhu_generation_not_xishan_label(self):
        path=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu/guide.json'
        raw=json.loads(path.read_text('utf8'));g=with_reference_capabilities(raw)
        enabled={t['id']:t['document_types'] for t in g['templates'] if t.get('can_generate')}
        self.assertEqual(enabled,{'985f4770-1ab2-4264-9482-0f8528b16513':['application'],
                                  '586cf49f-714b-4338-81ce-08a2956d7aa6':['evidence']})
        for t in g['templates']:
            if t.get('can_generate'):
                self.assertIn('建湖县',t['generation_label']);self.assertNotIn('锡山',t['generation_label'])
        for field,value in [('city','无锡市'),('district','锡山区'),('region_code','320205'),
                            ('source_url','https://ycjh.jszwfw.gov.cn/another')]:
            changed=copy.deepcopy(raw);changed[field]=value
            self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
        changed=copy.deepcopy(raw)
        for t in changed['templates']:
            if t.get('official_kind')=='blank':t['file']=t['file'].replace('/320925/','/320205/')
        self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))


if __name__=='__main__':unittest.main()
