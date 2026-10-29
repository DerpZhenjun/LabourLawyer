"""Own E Zhejiang bindings; public roots and temporary filled copies only."""
from copy import deepcopy
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class ZhejiangETests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_zhejiang_oct29e'), 'E requires its own source adapter')
        import regional_zhejiang_oct29e as provider
        self.p = provider

    def own(self, name='fuyang', root=None):
        return self.p.with_capabilities(self.p.parse_capture(name, root=root), root=root)

    def template(self, guide, kind):
        return next(t for t in guide['templates'] if t.get('document_types') == [kind])

    def fill(self, guide, kind, data, root=None):
        t = self.template(guide, kind)
        return self.p.fill_document(guide, t, kind, Path(root or ROOT) / t['file'], data, root=root)

    def public_copy(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        white = json.loads((ROOT / self.p.REPORT / 'PUBLIC-WHITELIST.json').read_text('utf8'))
        for relative in [r['path'] for r in white['files']] + [self.p.REPORT + '/PUBLIC-WHITELIST.json']:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        return root

    def test_two_real_own_guides_have_four_blanks_and_preserve_material_phone_differences(self):
        f, j = self.own(), self.own('jiande')
        self.assertEqual([f['region_code'], j['region_code']], ['330111', '330182'])
        self.assertEqual((j['city'], j['district']), ('杭州市', '建德市'))
        self.assertEqual([len(g['materials']) for g in [f, j]], [4, 5])
        self.assertTrue(all(len([t for t in g['templates'] if t['can_generate']]) == 2 for g in [f, j]))
        self.assertNotEqual(f['source_id'], j['source_id'])
        self.assertNotEqual(f['service_code'], j['service_code'])
        self.assertEqual(j['fields']['窗口联系电话']['raw_value'], '0571-64721626')
        self.assertEqual(j['fields']['咨询电话']['raw_value'], '0571-64721936')
        self.assertTrue(all(len(g['raw_business_fields']) == 252 for g in [f, j]))
        self.assertTrue(any('不构成' in w and '身份证' in w for w in f['warnings']))
        self.assertEqual([len(self.p.DATA_FIELDS[k]) for k in ['application', 'evidence', 'evidence_item']], [23, 5, 4])

    def test_equal_bytes_cannot_cross_scope_source_material_service_or_annex(self):
        f, j = self.own(), self.own('jiande')
        t = self.template(f, 'application')
        self.assertEqual(t['sha256'], self.template(j, 'application')['sha256'])
        self.assertIsNone(self.p.blank_binding(j, t))
        for key in ['district', 'source_url', 'source_id', 'service_code', 'authority']:
            bad = deepcopy(f); bad[key] += '-bad'
            self.assertIsNone(self.p.blank_binding(bad, t))
        for key in ['id', 'material_id', 'official_annex_id', 'file', 'sha256', 'download_url', 'region_code']:
            bad = deepcopy(t); bad[key] += '-bad'
            self.assertIsNone(self.p.blank_binding(f, bad))
        bad = deepcopy(f); bad['materials'][0]['copies'] = '99'
        self.assertIsNone(self.p.blank_binding(bad, t))
        with self.assertRaises(ValueError): self.p.checked_adapter(f, t, 'evidence')
        with self.assertRaises(ValueError): self.p.fill_document(f, t, 'application', ROOT / self.template(j, 'application')['file'], {})

    def test_samples_never_become_downloadable_or_generatable(self):
        j = self.own('jiande')
        t = next(t for t in j['templates'] if t['official_kind'] == 'sample')
        self.assertFalse(t['can_generate']); self.assertIsNone(t['file'])
        self.assertIsNone(self.p.blank_binding(j, t))
        self.assertFalse(self.p.approved_report_attachment(j, t, ROOT))
        for k in ['application', 'evidence']:
            with self.assertRaises(ValueError): self.p.checked_adapter(j, t, k)

    def test_public_proof_requires_explicit_root_and_entire_frozen_57_file_chain(self):
        root = self.public_copy()
        with patch.object(self.p, 'ROOT', root / 'unavailable-original'):
            g = self.own(root=root); t = self.template(g, 'application')
            self.assertEqual(self.p.public_evidence(g, root), g['evidence'])
            self.assertTrue(self.p.approved_report_attachment(g, t, root))
            self.assertTrue(self.fill(g, 'application', {'phone': '虚构电话'}, root).tables)
        self.assertIsNone(self.p.public_evidence(g, None))
        self.assertFalse(self.p.approved_report_attachment(g, t, None))
        f = root / self.p.REPORT / 'jiande/faq.png'; f.write_bytes(f.read_bytes() + b'changed')
        self.assertIsNone(self.p.blank_binding(g, t, root))
        self.assertIsNone(self.p.public_evidence(g, root))
        with self.assertRaises(ValueError): self.p.parse_capture('fuyang', root=root)

    def test_missing_manifest_wrong_whitelist_and_foreign_roots_fail_without_fallback(self):
        for relative in ['fuyang/SOURCE-MANIFEST.json', 'jiande/PUBLIC-WHITELIST.json', 'PUBLIC-WHITELIST.json']:
            root = self.public_copy(); (root / self.p.REPORT / relative).unlink()
            with self.assertRaises((ValueError, OSError)): self.p.parse_capture('fuyang', root=root)
        with self.assertRaises((ValueError, OSError)): self.p.parse_capture('fuyang', root=ROOT / 'reports')

    def test_wrong_shape_inputs_fail_closed(self):
        g = self.own(); t = self.template(g, 'application')
        for bad in [None, [], 'guide', 7, {'region_code': 'wrong'}]:
            self.assertIsNone(self.p.blank_binding(bad, t))
            self.assertIsNone(self.p.public_evidence(bad, ROOT))
            with self.assertRaises(ValueError): self.p.with_capabilities(bad)
        for bad in [None, [], 'template', 7]:
            self.assertIsNone(self.p.blank_binding(g, bad))
            self.assertFalse(self.p.approved_report_attachment(g, bad, ROOT))
            with self.assertRaises(ValueError): self.p.checked_adapter(g, bad, 'application')
        for bad in [None, [], 'data', 7]:
            with self.assertRaises(ValueError): self.fill(g, 'application', bad)
        for bad in [None, [], 'templates']:
            changed = deepcopy(g); changed['templates'] = bad
            self.assertIsNone(self.p.blank_binding(changed, t))

    def test_non_string_kind_and_missing_template_metadata_are_explicitly_rejected(self):
        g = self.own(); t = self.template(g, 'application')
        for kind in [None, [], {}, 7]:
            with self.assertRaises(ValueError): self.p.checked_adapter(g, t, kind)
        changed = deepcopy(g)
        sample = self.own('jiande')
        del next(t for t in sample['templates'] if t['official_kind'] == 'sample')['file']
        self.assertIsNone(self.p.public_evidence(sample, ROOT))

    def test_lifecycle_notice_needs_both_gates_and_always_preserves_official_warnings(self):
        g = self.own(); warnings = list(g['warnings'])
        for published, qa, complete in [(False, 'PASS', False), (True, 'NOT_RUN', False), (True, 'PASS', True)]:
            changed = deepcopy(g); changed.update(published=published, candidate_web_qa=qa)
            got = self.p.with_capabilities(changed)
            self.assertEqual(any('已通过填写、版式及网页验收' in w for w in got['warnings']), complete)
            self.assertEqual(any('不代表已发布' in w for w in got['warnings']), not complete)
            self.assertTrue(any('材料详情' in w for w in got['warnings']))
            self.assertEqual(self.p.with_capabilities(got)['warnings'], got['warnings'])
        g['warnings'] = []
        self.assertTrue(any('材料详情' in w for w in self.p.with_capabilities(g)['warnings']))

    def test_four_own_fills_preserve_fields_instructions_blank_signatures_and_only_document_xml(self):
        for name in ['fuyang', 'jiande']:
            g = self.own(name)
            data = {k: '  虚构' + k + '  ' for k in self.p.APPLICATION_TEXT_FIELDS if k not in {'householdType', 'birthDate', 'applicationDate'}}
            data.update(birthDate='1991-02-03', applicationDate='2026-10-29', householdType='外籍人员', copyCount=3, requests=['虚构请求甲', '', '虚构请求乙'])
            for kind, values in [('application', data), ('evidence', {'committeeName': '虚构委员会', 'caseNumber': '虚构案号', 'copyCount': 3, 'submitDate': '2026-10-29', 'evidenceList': [{'name': '  虚构证据  ', 'pageCount': '2', 'source': '虚构来源', 'purpose': '虚构目的'}, {'name': '', 'purpose': '无名条目仍保留'}]})]:
                d = self.fill(g, kind, values)
                text = '\n'.join(p.text for p in d.paragraphs) + '\n' + '\n'.join(c.text for tb in d.tables for row in tb.rows for c in row.cells)
                if kind == 'application':
                    self.assertEqual(len(d.tables), 1); self.assertNotIn('用于用人单位申请', text)
                    for k,v in data.items():
                        if isinstance(v, str) and k not in {'householdType', 'birthDate', 'applicationDate'}: self.assertIn(v, text, k)
                    self.assertIn('4.申请书副本份数，应按对方当事人人数提交。', text)
                    self.assertIn('2.申请人应同时提交身份证复印件或其他身份证件。', text)
                    self.assertNotIn(data['applicantName'], next(p.text for p in d.tables[0].rows[-1].cells[0].paragraphs if '申请人：' in p.text))
                    self.assertIn('☑', text)
                else:
                    self.assertIn('  虚构证据  ', text); self.assertIn('无名条目仍保留', text)
                    self.assertEqual(d.tables[0].rows[-2].cells[2].text, '')
                    self.assertEqual(d.tables[0].rows[-1].cells[2].text, '')
                out = BytesIO(); d.save(out)
                with ZipFile(ROOT / self.template(g, kind)['file']) as before, ZipFile(out) as after:
                    self.assertEqual(before.namelist(), after.namelist())
                    self.assertEqual([n for n in before.namelist() if before.read(n) != after.read(n)], ['word/document.xml'])

    def test_blank_dates_copies_and_ambiguous_household_are_never_invented(self):
        for name in ['fuyang', 'jiande']:
            g = self.own(name); app = self.fill(g, 'application', {})
            self.assertIn('年   月    日', app.tables[0].rows[-1].cells[0].text)
            self.assertIn('申请书副本      份', app.tables[0].rows[-1].cells[0].text)
            self.assertEqual(self.fill(g, 'evidence', {}).tables[0].rows[0].cells[5].text, '')
            for data in [{'householdType': '外省非农业户口'}, {'postalCode': 'unsupported'}, {'applicantName': '字' * 301}, {'requests': ['一'] * 5}, {'copyCount': True}, {'copyCount': 1.5}, {'factsReason': '\x00'}]:
                with self.assertRaises(ValueError): self.fill(g, 'application', data)
            for data in [{'submitterName': 'no automatic signature'}, {'evidenceList': ['bad']}, {'evidenceList': [{'originalType': '原件'}]}]:
                with self.assertRaises(ValueError): self.fill(g, 'evidence', data)
            t = self.template(g, 'application')
            with self.assertRaises(ValueError): self.p.fill_document(g, t, 'application', ROOT / t['file'], {}, applicant_mode='employer')


if __name__ == '__main__':
    unittest.main()
