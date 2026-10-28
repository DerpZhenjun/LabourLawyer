"""Exact new Zhejiang guides must preserve source gaps and locality identity."""
import hashlib,json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
REPORT=ROOT/'reports/nationwide-localization-20261028-next/zhejiang'
try:
    from regional_zhejiang_more import parse_binjiang_capture,parse_shangcheng_capture
except ModuleNotFoundError:
    parse_binjiang_capture=parse_shangcheng_capture=None

@unittest.skipUnless((REPORT/'SOURCE-MANIFEST.json').is_file(),
                     'Local sealed capture contains login-flow context; not distributed in public checkout')
class ZhejiangMoreCaptureTests(unittest.TestCase):
    def manifest(self):return json.loads((REPORT/'SOURCE-MANIFEST.json').read_text(encoding='utf8'))
    def parse(self,name,root=REPORT,manifest=None):
        parser={'binjiang':parse_binjiang_capture,'shangcheng':parse_shangcheng_capture}[name]
        self.assertIsNotNone(parser,'New own-source Zhejiang parser is not implemented')
        return parser(root,self.manifest() if manifest is None else manifest)
    def fixture(self):
        parent=REPORT/'test-tmp';parent.mkdir(exist_ok=True)
        temporary=tempfile.TemporaryDirectory(dir=parent);self.addCleanup(temporary.cleanup)
        target=Path(temporary.name)
        for relative in self.manifest()['files']:
            p=target/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPORT/relative,p)
        return target
    def test_shangcheng_uses_its_actual_four_materials_and_downloaded_blanks(self):
        # Break: inheriting Yuhang's five rows or another district's annex path.
        g=self.parse('shangcheng')
        self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('zhejiang','杭州市','上城区','330102'))
        self.assertEqual(g['service_code'],'01a9e0fa-ab7e-4232-99e1-014d3ad99b45')
        self.assertEqual(g['authority'],'杭州市上城区人力资源和社会保障局')
        self.assertEqual([m['name'] for m in g['materials']],['用人单位登记注册材料','《劳动人事争议仲裁申请书》','《证据清单》','存在劳动关系的证据和可证实申请人主张的证据'])
        self.assertEqual(len(g['templates']),2)
        self.assertEqual({t['sha256'] for t in g['templates']},{'0eab0f0a2ee98e8ca1e4d2fa5469fcb5738d0c0f24671345bebc8394099ae41f','4965bf3d2bf76404ab190d1e47d2fa250c8cb8bd93762949df94be38b2d4ca8c'})
        self.assertTrue(all(t['file'].startswith('templates/_docx/_regional/330102/') and not t['can_generate'] for t in g['templates']))
        self.assertEqual(g['fields']['办理时间']['raw_value'],'法定工作日：9：00-12：00 14:00-5:30')
    def test_binjiang_material_gap_never_inherits_shared_blanks(self):
        # Break: equating a zero-row portal message with no legal material burden.
        g=self.parse('binjiang')
        self.assertEqual(g['service_code'],'a3163f38-bd62-4d18-8374-a79177c440fb')
        self.assertEqual(g['district'],'滨江区')
        self.assertEqual(g['fields']['实施主体']['raw_value'],'区人力社保局（区党委编办）')
        self.assertEqual(g['materials'],[]);self.assertEqual(g['templates'],[])
        self.assertEqual(g['materials_status'],'portal_material_flow_conflict')
        self.assertEqual(g['fields']['材料栏原文']['raw_value'],'当前情形下，无需递交材料')
        self.assertEqual(g['verification_status'],'conflict')
    def test_raw_time_units_and_actual_login_boundaries_remain_distinct(self):
        # Break: treating login header/five-day acceptance as completed online arbitration.
        for name in ['binjiang','shangcheng']:
            g=self.parse(name)
            self.assertEqual(g['fields']['法定办结时限']['raw_value'],'60天')
            self.assertEqual(g['fields']['承诺办结时限']['raw_value'],'44工作日')
            self.assertEqual(g['fields']['受理决定时限']['scope'],'acceptance_decision_only')
            self.assertEqual(g['channel']['online_status'],'auth_required')
            self.assertEqual(g['channel']['entry_check']['post_login_flow'],'unknown')
            self.assertFalse(g['channel']['entry_check']['submitted'])
    def test_district_body_login_or_original_swap_is_rejected(self):
        # Break: accepting relabelled old/local/provincial bytes as this own capture.
        for target,source in [('shangcheng-basic/dom.json','binjiang-basic/dom.json'),('shangcheng-online/dom.json','binjiang-online/dom.json'),('shangcheng/originals/application.docx','shangcheng/originals/evidence-list.docx')]:
            with self.subTest(target=target):
                root=self.fixture();shutil.copyfile(root/source,root/target)
                with self.assertRaises(ValueError):self.parse('shangcheng',root)
    def test_caller_cannot_reseal_or_supply_old_district_manifest(self):
        # Break: caller-supplied replacement checksums authorizing a substituted source.
        manifest=self.manifest();manifest['files']['shangcheng-basic/dom.json']['sha256']='0'*64
        with self.assertRaises(ValueError):self.parse('shangcheng',manifest=manifest)
        old=json.loads((ROOT/'reports/nationwide-localization-20261028/zhejiang/SHA256-MANIFEST.json').read_text(encoding='utf8'))
        with self.assertRaises(ValueError):self.parse('shangcheng',manifest=old)
    def test_unobserved_binjiang_attachment_metadata_cannot_create_capability(self):
        # Break: falling back to shared provincial forms when no own controls exist.
        root=self.fixture();p=root/'binjiang/originals.json';p.parent.mkdir(exist_ok=True)
        p.write_bytes((root/'shangcheng/originals.json').read_bytes())
        g=self.parse('binjiang',root)
        self.assertEqual(g['templates'],[])

if __name__=='__main__':unittest.main()
