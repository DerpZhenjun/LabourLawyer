import copy
import json
from pathlib import Path
import unittest

from regional_jiangsu import parse_xishan_capture, official_filename

ROOT=Path(__file__).resolve().parents[2]
CAPTURE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-xishan/formal-guide-final.json'


class JiangsuXishanCapture(unittest.TestCase):
    def capture(self):return json.loads(CAPTURE.read_text('utf8'))

    def test_http_latin1_filename_keeps_real_chinese_name(self):
        self.assertEqual(official_filename('证据清单.docx'.encode('utf8').decode('latin1')),'证据清单.docx')
        self.assertEqual(official_filename('证据清单.docx'),'证据清单.docx')
        self.assertEqual(official_filename('form.docx'),'form.docx')

    def test_actual_local_fields_materials_and_separate_blank_sample(self):
        guide=parse_xishan_capture(self.capture())
        self.assertEqual((guide['province'],guide['city'],guide['district'],guide['region_code']),('jiangsu','无锡市','锡山区','320205'))
        self.assertEqual(guide['authority'],'锡山区人力资源和社会保障局')
        self.assertEqual(guide['fields']['办理形式']['raw_value'],'窗口办理,网上办理,快递申请')
        self.assertEqual(guide['channel']['form'],'window_and_online')
        self.assertEqual(guide['channel']['online_status'],'unverified')
        self.assertIsNone(guide['channel']['entry_url'])
        self.assertEqual(guide['fields']['承诺办结时限']['raw_value'],'45个工作日')
        self.assertEqual(guide['fields']['到办事现场次数']['raw_value'],'3')
        self.assertIn('开庭审理',guide['fields']['必须到现场原因']['raw_value'])
        self.assertEqual([m['copies'] for m in guide['materials']],['2','2','1','4'])
        self.assertEqual([m['raw_copies'] for m in guide['materials']],['2份','2份','1份','4份'])
        self.assertEqual([m['original_copy'] for m in guide['materials']],['复印件','原件和复印件','原件','原件'])
        self.assertEqual(len(guide['templates']),8)
        self.assertEqual(sum(t['official_kind']=='blank' for t in guide['templates']),4)
        self.assertFalse(any(t['can_generate'] for t in guide['templates']))
        for field in guide['fields'].values():
            self.assertEqual(field['source_url'],guide['source_url'])
            self.assertEqual(field['region_code'],'320205')

    def test_neighbor_or_forged_formal_source_is_rejected(self):
        original=self.capture()
        for part,replacement in [('320205','320206'),('www.jszwfw.gov.cn','example.gov.cn')]:
            changed=copy.deepcopy(original);changed['url']=changed['url'].replace(part,replacement)
            with self.assertRaises(ValueError):parse_xishan_capture(changed)
        changed=copy.deepcopy(original);changed['html']=changed['html'].replace('class="area_local">锡山区','class="area_local">惠山区')
        with self.assertRaises(ValueError):parse_xishan_capture(changed)

    def test_missing_details_are_not_filled_from_other_materials(self):
        changed=self.capture();changed['html']=changed['html'].replace('原件和复印件','')
        guide=parse_xishan_capture(changed)
        self.assertIsNone(guide['materials'][1]['original_copy'])
        self.assertEqual(guide['materials'][0]['original_copy'],'复印件')


if __name__=='__main__':unittest.main()
