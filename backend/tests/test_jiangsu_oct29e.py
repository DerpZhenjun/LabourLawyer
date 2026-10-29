"""Suzhou E own frozen sources and slot preservation; offline and synthetic only."""
from copy import deepcopy
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
adapter = __import__('regional_jiangsu_oct29e') if importlib.util.find_spec('regional_jiangsu_oct29e') else None


def application():
    return dict(applicantName='虚构验收甲', respondentName='虚构验收单位', gender='女',
                birthDate='1991-05-09', phone='00000000000', idNumber='000000199105090000',
                committeeName='虚构仲裁委员会', requests=['请求支付虚构工资100元。'],
                factsReason='仅为软件验收，事实和当事人均为虚构。', copyCount=3,
                evidenceCopyCount=2, applicationDate='2026-10-29')


def evidence():
    return dict(committeeName='虚构仲裁委员会', caseNumber='虚构案号',
                submitDate='2026-10-29', evidenceList=[dict(name='虚构劳动合同', source='虚构保存',
                purpose='证明虚构关系', originalType='复印件', pageCount='3页')])


class JiangsuOct29ETests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(adapter, 'E own-source adapter is not implemented')

    def test_own_identities_contract_and_published_lifecycle(self):
        for code, district, webid in [('320507', '相城区', '28'), ('320509', '吴江区', '29')]:
            g = adapter.parse_capture(district)
            self.assertEqual(g['region_code'], code)
            self.assertEqual(g['source_id'], adapter.digest(g['source_url'])[:24])
            self.assertEqual(g['scope_identity']['webId'], webid)
            ready = adapter.with_capabilities(g)
            self.assertEqual(sum(t['can_generate'] for t in ready['templates']), 2)
            self.assertEqual(adapter.candidate_contract(ready)['region_code'], code)
            ready.update(published=True, candidate_web_qa='PASS', publication_status='published', version=211)
            ready = adapter.with_capabilities(ready)
            self.assertTrue(ready['published'])
            self.assertEqual(ready['source_issues'], g['source_issues'])
            self.assertFalse(any(x in ' '.join(ready['warnings']) for x in ['未发布', '仅离线', '未做新适配']))
            self.assertTrue(any('登录' in x for x in ready['warnings']))

    def test_application_own_slots_and_only_document_xml_changes(self):
        for code in adapter.SUPPORTED:
            g = adapter.parse_capture(code)
            data = application()
            data.update(otherDocumentType='虚构证件种类', otherDocumentNumber='虚构证件号',
                        acceptMediation='是', legalAid='否', departmentHead='虚构部门负责人',
                        departmentHeadPosition='虚构部门职务', applicantMailingAddress='虚构通讯地址')
            doc = adapter.fill_candidate_document(g, 'application', data)
            text = '\n'.join(p.text for p in doc.paragraphs)
            for token in ['1991-05-09', '本申请书副本3份', '相关证据2份', '虚构证件种类',
                          '虚构证件号', '虚构部门负责人', '虚构部门职务', '虚构通讯地址']:
                self.assertIn(token, text)
            self.assertNotIn('用人单位申请', text)
            signature = next(p.text for p in doc.paragraphs if '签名、盖章或指模' in p.text)
            self.assertNotIn('虚构验收甲', signature)
            out = BytesIO(); doc.save(out)
            binding = adapter.candidate_contract(g)['documents']['application']
            with ZipFile(ROOT / binding['source_file']) as a, ZipFile(out) as b:
                self.assertEqual(a.namelist(), b.namelist())
                self.assertEqual([n for n in a.namelist() if a.read(n) != b.read(n)], ['word/document.xml'])

    def test_partial_fields_and_blank_copy_counts_no_invented_values(self):
        for code in adapter.SUPPORTED:
            doc = adapter.fill_candidate_document(adapter.parse_capture(code), 'application',
                                                  {'phone': '00000000000', 'otherDocumentNumber': '虚构其他证件号'})
            text = '\n'.join(p.text for p in doc.paragraphs)
            self.assertIn('00000000000', text)
            self.assertIn('虚构其他证件号', text)
            self.assertIn('本申请书副本    份', text)
            self.assertIn('相关证据    份', text)
            self.assertNotIn('用人单位申请', text)

    def test_evidence_preserves_partial_items_and_long_content(self):
        for code in adapter.SUPPORTED:
            data = evidence()
            data['evidenceList'] = [dict(source='仅填虚构来源', purpose='虚构用途' * 50)] + [
                dict(name=f'虚构证据{i}', originalType='原件', pageCount='2页') for i in range(1, 13)]
            doc = adapter.fill_candidate_document(adapter.parse_capture(code), 'evidence', data)
            text = '\n'.join(c.text for row in doc.tables[0].rows for c in row.cells)
            self.assertIn('仅填虚构来源', text)
            self.assertIn('虚构用途' * 50, text)
            self.assertIn('虚构证据12', text)
            self.assertEqual(len(doc.tables[0].columns), 6)
            body = '\n'.join(p.text for p in doc.paragraphs)
            self.assertIn('虚构案号', body)
            self.assertIn('2026年10月29日', body)
            self.assertNotIn('提交人：虚构', body)
            self.assertNotIn('本表一式', body)

    def test_reject_wrong_scope_source_authority_and_task(self):
        for key, value in [('region_code', '320508'), ('district', '姑苏区'), ('city', '无锡市'),
                           ('authority', '其他机关'), ('service_code', '002014302002'),
                           ('source_id', 'wrong'), ('source_url', 'https://szgs.jszwfw.gov.cn/'),
                           ('service_name', '劳动人事争议调解申请')]:
            g = adapter.parse_capture('320507'); g[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): adapter.candidate_contract(g)
        with self.assertRaises(ValueError): adapter.parse_capture('320508')

    def test_reject_changed_facts_material_capture_and_platform_markers(self):
        for mutate in [lambda g: g['fields']['办理地点'].update(raw_value='其他窗口'),
                       lambda g: g['materials'][3].update(copies='2'),
                       lambda g: g['materials'][0].update(detail_capture_sha256='0' * 64),
                       lambda g: g['evidence'].update(capture_file='reports/arbitrary.json'),
                       lambda g: g['scope_identity'].update(webId='26'),
                       lambda g: g.update(generation_adapter='foreign_adapter'),
                       lambda g: g['templates'][0].update(render_status='arbitrary-pass')]:
            g = adapter.parse_capture('320507'); mutate(g)
            with self.assertRaises(ValueError): adapter.candidate_contract(g)

    def test_reject_annex_sha_material_sample_placeholder_or_foreign_path(self):
        for key, value in [('official_kind', 'sample'), ('sha256', '0' * 64),
                           ('material_id', '320508-material-4'), ('file', '../private.docx'),
                           ('download_url', 'https://example.test/a.docx'), ('annex_id', 'foreign')]:
            g = adapter.parse_capture('320507')
            t = next(t for t in g['templates'] if t['id'] == adapter.SPECS['320507']['application'])
            t[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): adapter.blank_binding(g, t)
        g = adapter.parse_capture('320507')
        for t in g['templates']:
            if t['official_kind'] != 'blank' or t['content_role'] == 'placeholder_heading_only':
                with self.assertRaises(ValueError): adapter.blank_binding(g, t)
        with self.assertRaises(ValueError): adapter.fill_candidate_document(g, 'identity', {})

    def test_contract_limits_unknown_keys_and_illegal_xml_are_rejected(self):
        g = adapter.parse_capture('320507')
        for kind, data in [('application', {'notAField': ''}), ('application', {'phone': '长' * 301}),
                           ('application', {'factsReason': '长' * 12001}), ('application', {'requests': ['项'] * 5}),
                           ('application', {'copyCount': True}), ('application', {'copyCount': 31}),
                           ('application', {'birthDate': '1991-02-30'}), ('application', {'phone': '\x00'}),
                           ('application', {'phone': '\ud800'}), ('evidence', {'evidenceList': [{'unknown': ''}]}),
                           ('evidence', {'evidenceList': [{'purpose': '长' * 1201}]}),
                           ('evidence', {'evidenceList': [{}] * 41}), ('evidence', {'copyCount': ''})]:
            with self.subTest(kind=kind, data=str(data)[:35]), self.assertRaises(ValueError):
                adapter.fill_candidate_document(g, kind, data)

    def test_clean_public_root_and_missing_or_tampered_root_never_fall_back(self):
        source = ROOT / adapter.REPORT
        manifest = json.loads((source / 'SOURCE-MANIFEST.json').read_text('utf8'))
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as empty:
            root = Path(temp); public = root / adapter.REPORT
            for relative in [*manifest['files'], 'SOURCE-MANIFEST.json', 'PUBLIC-WHITELIST.json']:
                target = public / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, target)
            self.assertFalse(list(public.glob('*/originals/sample/*/*')))
            for code in adapter.SUPPORTED:
                g = adapter.with_capabilities(adapter.parse_capture(code, public), root=root)
                self.assertEqual(adapter.public_evidence(g, root), g['evidence'])
                stripped = deepcopy(g); stripped.pop('evidence')
                self.assertEqual(adapter.public_evidence(stripped, root), g['evidence'])
                self.assertIsNone(adapter.public_evidence(g, None))
                self.assertIsNone(adapter.public_evidence(g, empty))
                for t in g['templates']:
                    self.assertEqual(adapter.approved_report_attachment(g, t, root), t['official_kind'] != 'sample')
                adapter.fill_candidate_document(g, 'application', {'phone': '虚构电话'}, root=root)
                binding = adapter.candidate_contract(g, root=root)['documents']['application']
                path = root / binding['source_file']; original = path.read_bytes(); path.write_bytes(b'corrupt')
                self.assertIsNone(adapter.public_evidence(g, root))
                with self.assertRaises(ValueError): adapter.fill_candidate_document(g, 'application', {}, root=root)
                path.unlink()
                with self.assertRaises(ValueError): adapter.candidate_contract(g, root=root)
                path.write_bytes(original)
            (public / 'SOURCE-MANIFEST.json').write_bytes(b'{}')
            with self.assertRaises(ValueError): adapter.parse_capture('320507', public)


if __name__ == '__main__':
    unittest.main()
