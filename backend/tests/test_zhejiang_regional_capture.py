"""Protect exact Zhejiang evidence from locality, manifest and annex substitution."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
REPORT = ROOT / 'reports/nationwide-localization-20261028/zhejiang'
try:
    from regional_zhejiang import parse_yuhang_capture, parse_xihu_capture
except ModuleNotFoundError:
    parse_yuhang_capture = parse_xihu_capture = None


@unittest.skipUnless((REPORT / 'SHA256-MANIFEST.json').is_file(),
                     'Local sealed capture contains login-flow context; not distributed in public checkout')
class ZhejiangRegionalCaptureTests(unittest.TestCase):
    def manifest(self):
        return json.loads((REPORT / 'SHA256-MANIFEST.json').read_text(encoding='utf8'))

    def parse(self, name='yuhang', root=REPORT, manifest=None):
        parser = {'yuhang': parse_yuhang_capture, 'xihu': parse_xihu_capture}[name]
        self.assertIsNotNone(parser, 'Own-source Zhejiang parser is not implemented')
        return parser(root, self.manifest() if manifest is None else manifest)

    def fixture(self):
        parent = REPORT / 'strict-parser-tmp'
        parent.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name)
        for name in self.manifest()['files']:
            source = REPORT / name.replace('\\', '/')
            destination = target / name.replace('\\', '/')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        return target

    def replace_json(self, root, relative, mutate):
        path = root / relative
        value = json.loads(path.read_text(encoding='utf8'))
        mutate(value)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf8')

    def test_own_guides_independently_bind_shared_blank_originals(self):
        # Break: accepting the provincial guide or inferring another district from equal bytes.
        for name, district, code, local in [
            ('yuhang', '余杭区', '330110', '8f1bc917-6583-4541-be13-231de0b91d0b'),
            ('xihu', '西湖区', '330106', '2b882c41-1fc2-4689-9f56-631917cf63fe'),
        ]:
            with self.subTest(district=district):
                guide = self.parse(name)
                self.assertEqual((guide['province'], guide['city'], guide['district'], guide['region_code']),
                                 ('zhejiang', '杭州市', district, code))
                self.assertEqual(guide['service_code'], local)
                self.assertEqual(guide['authority'], '杭州市' + district + '人力资源和社会保障局')
                self.assertEqual(len(guide['materials']), 5)
                blanks = [t for t in guide['templates'] if t['official_kind'] == 'blank']
                self.assertEqual({t['sha256'] for t in blanks}, {
                    '0eab0f0a2ee98e8ca1e4d2fa5469fcb5738d0c0f24671345bebc8394099ae41f',
                    '4965bf3d2bf76404ab190d1e47d2fa250c8cb8bd93762949df94be38b2d4ca8c'})
                self.assertTrue(all(t['source_url'] == guide['source_url'] and t['region_code'] == code
                                    and not t['can_generate'] and t['document_types'] == [] for t in guide['templates']))
                self.assertEqual([t['official_kind'] for t in guide['templates']].count('sample'), 1)

    def test_time_units_and_copy_conflict_are_preserved(self):
        # Break: treating five-day acceptance as overall completion or silently rewriting copies.
        guide = self.parse()
        self.assertEqual(guide['fields']['法定办结时限']['raw_value'], '60天')
        self.assertEqual(guide['fields']['承诺办结时限']['raw_value'], '44工作日')
        self.assertEqual(guide['fields']['受理决定时限']['raw_value'], '5个工作日')
        self.assertEqual(guide['fields']['受理决定时限']['scope'], 'acceptance_decision_only')
        self.assertEqual(guide['fields']['实施主体']['raw_value'], '区人力社保局')
        self.assertTrue(all(m['raw_copies'] == '纸质材料 2份，A4' for m in guide['materials']))
        self.assertTrue(all(m['original_copy'] == '原件' for m in guide['materials']))
        self.assertIn('申请书副本份数，应按对方当事人人数提交。', guide['copy_conflict']['attachment_note'])
        self.assertEqual(guide['copy_conflict']['status'], 'retained_unresolved')
        self.assertEqual(guide['collected_at'], '2026-10-28T08:57:08.197Z')

    def test_auth_boundary_does_not_claim_post_login_submission(self):
        # Break: calling a public 登录 header online submission verification.
        for name in ['yuhang', 'xihu']:
            with self.subTest(name=name):
                channel = self.parse(name)['channel']
                self.assertEqual(channel['form'], 'window_and_online')
                self.assertEqual(channel['online_status'], 'auth_required')
                self.assertEqual(channel['entry_check']['post_login_flow'], 'unknown')
                self.assertFalse(channel['entry_check']['submitted'])

    def test_cross_district_body_and_login_swaps_are_rejected(self):
        # Break: trusting relabelled URL/region fields when the retained own body changed.
        for original, replacement in [
            ('yuhang-expanded/dom.json', 'xihu-expanded/dom.json'),
            ('yuhang-window/dom.json', 'xihu-window-actual/dom.json'),
            ('yuhang-search/dom.json', 'xihu-search/dom.json'),
            ('yuhang-online-boundary/dom.json', 'xihu-online-boundary/dom.json'),
        ]:
            with self.subTest(original=original):
                root = self.fixture()
                shutil.copyfile(root / replacement, root / original)
                with self.assertRaises(ValueError):
                    self.parse(root=root)

    def test_manifest_cannot_authorize_rehashed_other_source(self):
        # Break: trusting a caller-supplied new checksum for substituted evidence.
        root = self.fixture()
        path = root / 'yuhang-expanded/dom.json'
        path.write_bytes((root / 'xihu-expanded/dom.json').read_bytes())
        manifest = self.manifest()
        manifest['files']['yuhang-expanded\\dom.json']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.parse(root=root, manifest=manifest)
        with self.assertRaises(ValueError):
            self.parse(manifest={'files': {}})

    def test_annex_names_kinds_urls_and_local_files_cannot_be_swapped(self):
        # Break: accepting renamed blank/sample records or a different source/path as local proof.
        cases = [
            lambda a: a[1].update(file='xihu/attachments/application.docx'),
            lambda a: a[1].update(file='yuhang/attachments/evidence-list.docx'),
            lambda a: a[1].update(kind='sample_identity_document'),
            lambda a: a[1].update(source_url='https://example.com/application.docx'),
        ]
        for mutate in cases:
            with self.subTest(mutation=cases.index(mutate)):
                root = self.fixture()
                self.replace_json(root, 'yuhang/attachments.json', mutate)
                with self.assertRaises(ValueError):
                    self.parse(root=root)

    def test_changed_official_original_bytes_are_rejected(self):
        # Break: accepting a DOCX with the expected filename but wrong source bytes.
        root = self.fixture()
        shutil.copyfile(root / 'yuhang/attachments/evidence-list.docx', root / 'yuhang/attachments/application.docx')
        with self.assertRaises(ValueError):
            self.parse(root=root)

    def test_derived_guide_does_not_override_source_requirements(self):
        # Break: copying the unchecked derived guide rather than parsing retained raw DOM.
        root = self.fixture()
        self.replace_json(root, 'yuhang/guide.json', lambda d: d.update(city='宁波市', materials=[], timing_raw={'promised': '1天'}))
        guide = self.parse(root=root)
        self.assertEqual(guide['city'], '杭州市')
        self.assertEqual(len(guide['materials']), 5)
        self.assertEqual(guide['fields']['承诺办结时限']['raw_value'], '44工作日')


if __name__ == '__main__':
    unittest.main()
