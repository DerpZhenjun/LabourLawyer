"""Own 2026 receiving windows must not become a province-wide venue or online claim."""
import copy,importlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha'
class NanshaWindowsTests(unittest.TestCase):
    def setUp(self):
        from regional_nansha import parse_nansha_capture
        self.raw=json.loads((BASE/'windows-round23/dom.json').read_text('utf8'))
        # Rebuild the historical material-only guide from immutable captures, not the updated candidate cache.
        self.g=parse_nansha_capture(json.loads((BASE/'source-round23/dom.json').read_text('utf8')),json.loads((BASE/'downloads-round23/original-files.json').read_text('utf8')))
    def module(self):
        m=importlib.import_module('regional_nansha');self.assertTrue(hasattr(m,'parse_nansha_windows'),'Missing own window parser');return m
    def test_receiving_windows_personnel_office_and_dispatch_courts_remain_distinct(self):
        parsed=self.module().parse_nansha_windows(self.raw)
        self.assertEqual(parsed['publication_date'],'2026-06-02')
        windows=parsed['labour_receiving_windows'];self.assertEqual(len(windows),10)
        self.assertEqual((windows[0]['town'],windows[0]['phone_raw']),('黄阁镇','84970830'))
        self.assertEqual(windows[-1]['address_raw'],'南沙区港前大道南133号')
        lanhe=next(x for x in windows if x['town']=='榄核镇')
        self.assertIn('新地路12号',lanhe['address_raw']);self.assertNotIn('镇南路67号',lanhe['address_raw'])
        self.assertIn('镇南路67号',parsed['dispatch_courts_raw'])
        self.assertIn('初晴路19号',parsed['agency_office_raw']);self.assertIn('初晴路19号',parsed['personnel_receiving_raw'])
        self.assertIn('港前大道北97号一楼12号',parsed['special_receiving_raw'])
        self.assertIn('港前大道北97号401室',parsed['special_court_raw'])
        self.assertEqual(parsed['working_hours_scope'],'labour_receiving_windows')
        self.assertIn('14:00-18:00',parsed['working_hours_raw'])
    def test_foreign_source_changed_structure_and_missing_hours_never_fall_back_to_footer(self):
        m=self.module();original=copy.deepcopy(self.raw)
        for k,old,new in [('url','post_3868389','post_5801798'),('html','广州市南沙区劳动人事争议仲裁机构设置和收件窗口','白云区仲裁窗口'),('html','84970830',''),('html','港湾街','黄阁镇')]:
            p=copy.deepcopy(original);self.assertIn(old,p[k]);p[k]=p[k].replace(old,new)
            with self.assertRaises(ValueError):m.parse_nansha_windows(p)
        p=copy.deepcopy(original);p['html']=p['html'].replace('工作时间：周一至周五 上午9:00-12:00 14:00-18:00（国家法定节假日除外）','')
        missing=m.parse_nansha_windows(p);self.assertIsNone(missing['working_hours_raw'])
        self.assertNotIn('020-12345',missing['agency_contact_raw'])
    def test_merge_uses_each_fields_own_source_preserves_material_clocks_and_history(self):
        m=self.module();self.assertTrue(hasattr(m,'apply_nansha_windows'))
        before=copy.deepcopy(self.g);g=m.apply_nansha_windows(self.g,self.raw)
        self.assertEqual(self.g,before);self.assertEqual(g['materials'],before['materials']);self.assertEqual(g['templates'],before['templates'])
        self.assertEqual(g['fields']['办理时间']['source_url'],self.raw['url'])
        self.assertEqual(g['fields']['办理时间']['collected_at'],self.raw['captured_at'])
        self.assertIn('劳动争议收件窗口',g['fields']['办理时间']['raw_value'])
        self.assertIn('黄阁镇',g['fields']['办理地点']['raw_value']);self.assertIn('港湾街',g['fields']['办理地点']['raw_value'])
        self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url'])
        self.assertEqual(g['fields']['办理形式']['verification_status'],'missing')
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'public.sqlite');a=s.put_guide(before);b=s.put_guide(g)
            self.assertEqual(a['source_id'],b['source_id']);self.assertNotEqual(a['version'],b['version'])
            self.assertEqual(s.versions('guangdong','广州市','南沙区')[1]['fields']['办理地点']['verification_status'],'missing')
            self.assertIsNone(s.lookup('guangdong','广州市','番禺区')['source_id'])
    def test_window_supplement_cannot_be_attached_to_foreign_locality(self):
        m=self.module();self.assertTrue(hasattr(m,'apply_nansha_windows'))
        for key,value in [('district','白云区'),('region_code','440111'),('source_url','https://www.by.gov.cn/')]:
            g=copy.deepcopy(self.g);g[key]=value
            with self.assertRaises(ValueError):m.apply_nansha_windows(g,self.raw)
if __name__=='__main__':unittest.main()
