"""Own Suzhou D sources; no network, models, DB or private reference samples."""
from copy import deepcopy
from io import BytesIO
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct29d as adapter


def payload():
    return dict(applicantName='虚构验收甲', respondentName='虚构验收单位', birthDate='1991-05-09',
                gender='女', idNumber='000000199105090000', phone='00000000000',
                idAddress='虚构地址一号', registeredAddress='虚构单位二号',
                committeeName='虚构仲裁委员会', requests=['请求支付虚构工资100元。'],
                factsReason='仅为软件验收，全部事实与当事人均为虚构。',
                applicationDate='2026-10-29', submitDate='2026-10-29', copyCount=3,
                evidenceCopyCount=2, evidenceList=[dict(name='虚构劳动合同', source='虚构保存',
                purpose='证明虚构劳动关系', originalType='复印件', pageCount='3页')])


class JiangsuOct29DTests(unittest.TestCase):
    def test_each_own_identity_and_capabilities_survive_publication(self):
        for code, name in [('320508', '姑苏区'), ('320506', '吴中区')]:
            g = adapter.parse_capture(name)
            self.assertEqual(g['region_code'], code)
            self.assertEqual(g['source_id'], adapter.digest(g['source_url'])[:24])
            adapted = adapter.with_capabilities(g)
            self.assertEqual(adapted['generation_adapter'], adapter.ADAPTER)
            self.assertEqual(sum(t['can_generate'] for t in adapted['templates']), 2)
            for t in adapted['templates']:
                if t['official_kind'] != 'blank' or t['content_role'] == 'placeholder_heading_only':
                    self.assertFalse(t['can_generate'])
            adapted.update(published=True, publication_status='published', version=200,
                           candidate_web_qa='PASS', warnings=['已完成验收'])
            self.assertEqual(adapter.candidate_contract(adapted)['region_code'], code)
            refreshed = adapter.with_capabilities(adapted)
            self.assertTrue(refreshed['published']); self.assertEqual(refreshed['candidate_web_qa'], 'PASS')
            self.assertEqual(refreshed['source_issues'], g['source_issues'])
            self.assertFalse(any(word in warning for warning in refreshed['warnings']
                                 for word in ['未发布', '候选网页验收', '仅离线']))

    def test_application_birthdate_copy_counts_signature_and_package(self):
        for code in adapter.SUPPORTED:
            g = adapter.parse_capture(code)
            out = BytesIO(); doc = adapter.fill_candidate_document(g, 'application', payload()); doc.save(out)
            body = '\n'.join(p.text for p in doc.paragraphs)
            self.assertIn('1991-05-09', body)
            self.assertIn('本申请书副本3份', body)
            self.assertIn('相关证据2份', body)
            self.assertNotIn('用人单位申请', body)
            self.assertNotIn('申请人（签名）：虚构验收甲', body)
            source = adapter.candidate_contract(g)['documents']['application']
            with ZipFile(ROOT / source['source_file']) as a, ZipFile(out) as b:
                self.assertEqual(a.namelist(), b.namelist())
                self.assertEqual([n for n in a.namelist() if a.read(n) != b.read(n)], ['word/document.xml'])
            data = payload(); data.pop('evidenceCopyCount'); data.pop('copyCount')
            body = '\n'.join(p.text for p in adapter.fill_candidate_document(g, 'application', data).paragraphs)
            self.assertIn('本申请书副本    份', body)
            self.assertIn('相关证据    份', body)

    def test_evidence_six_columns_and_long_input_no_silent_truncation(self):
        for code in adapter.SUPPORTED:
            data = payload()
            data['evidenceList'] = [dict(data['evidenceList'][0], name=f'虚构证据{i}', purpose='虚构长说明' * 50) for i in range(1, 13)]
            doc = adapter.fill_candidate_document(adapter.parse_capture(code), 'evidence', data)
            body = '\n'.join(c.text for table in doc.tables for row in table.rows for c in row.cells)
            self.assertIn('虚构证据12', body)
            self.assertIn('虚构长说明' * 50, body)
            self.assertEqual(len(doc.tables[0].columns), 6)

    def test_partial_optional_application_fields_are_not_dropped(self):
        doc = adapter.fill_candidate_document(adapter.parse_capture('320508'), 'application',
                                               dict(phone='00000000000', gender='女'))
        body = '\n'.join(p.text for p in doc.paragraphs)
        self.assertIn('00000000000', body)
        self.assertNotIn('用人单位申请', body)

    def test_reject_wrong_scope_source_authority_and_task(self):
        for field, value in [('region_code', '320408'), ('district', '江阴市'), ('city', '无锡市'),
                ('source_url', 'https://wxjy.jszwfw.gov.cn/'), ('source_id', 'wrong'),
                ('authority', '常州市人社局'), ('service_code', '002014302002'),
                ('service_name', '劳动人事争议调解申请'), ('province', 'hunan')]:
            g = adapter.parse_capture('320508'); g[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): adapter.candidate_contract(g)
        with self.assertRaises(ValueError): adapter.parse_capture('320281')

    def test_reject_changed_fields_materials_and_capture_binding(self):
        for mutate in [lambda g: g['fields']['实施主体'].update(raw_value='其他机关'),
                       lambda g: g['fields']['办理地点'].update(source_url='https://example.test'),
                       lambda g: g['materials'][3].update(copies='2'),
                       lambda g: g['materials'][1].update(detail_capture_sha256='0' * 64),
                       lambda g: g['scope_identity'].update(webId='40'),
                       lambda g: g['evidence'].update(capture_sha256='0' * 64)]:
            g = adapter.parse_capture('320508'); mutate(g)
            with self.assertRaises(ValueError): adapter.candidate_contract(g)

    def test_reject_sample_placeholder_rebinding_and_annex_mutation(self):
        for field, value in [('official_kind', 'sample'), ('download_status', 'reference_sample_not_distributed'),
                ('sha256', '0' * 64), ('file', 'backend/regional_jiangsu.py'),
                ('material_id', '320506-material-4'), ('download_url', 'https://example.test/a.docx'),
                ('source_url', 'https://wxjy.jszwfw.gov.cn/'), ('annex_id', 'wrong')]:
            g = adapter.parse_capture('320508')
            t = next(t for t in g['templates'] if t['id'] == adapter.SPECS['320508']['application'])
            t[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): adapter.candidate_contract(g)
        g = adapter.parse_capture('320508')
        with self.assertRaises(ValueError): adapter.fill_candidate_document(g, 'identity', payload())
        t = next(t for t in g['templates'] if t['official_kind'] == 'sample')
        with self.assertRaises(ValueError): adapter.blank_binding(g, t)
        g['templates'].append(deepcopy(g['templates'][0]))
        with self.assertRaises(ValueError): adapter.candidate_contract(g)

    def test_public_clean_root_has_no_private_sample_fallback(self):
        source = ROOT / adapter.REPORT
        manifest = json.loads((source / 'SOURCE-MANIFEST.json').read_text(encoding='utf8'))
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp); public = target / adapter.REPORT
            for relative in [*manifest['files'], 'SOURCE-MANIFEST.json', 'PUBLIC-WHITELIST.json']:
                dst = public / relative; dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, dst)
            self.assertFalse([p for p in public.rglob('*') if p.is_file() and 'sample' in p.parts])
            g = adapter.parse_capture('320508', capture_root=public)
            self.assertEqual(adapter.candidate_contract(g, root=target)['region_code'], '320508')
            item = adapter.candidate_contract(g, root=target)['documents']['application']
            path = target / item['source_file']; path.write_bytes(b'corrupt')
            with self.assertRaises(ValueError): adapter.fill_candidate_document(g, 'application', payload(), root=target)
            path.unlink()
            with self.assertRaises(ValueError): adapter.candidate_contract(g, root=target)
            path = public / 'SOURCE-MANIFEST.json'; path.write_text('{}', encoding='utf8')
            with self.assertRaises(ValueError): adapter.parse_capture('320508', capture_root=public)

    def test_public_proof_uses_explicit_public_root_and_never_samples(self):
        source = ROOT / adapter.REPORT
        manifest = json.loads((source / 'SOURCE-MANIFEST.json').read_text(encoding='utf8'))
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as empty:
            root = Path(temp); public = root / adapter.REPORT
            for relative in [*manifest['files'], 'SOURCE-MANIFEST.json', 'PUBLIC-WHITELIST.json']:
                target = public / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, target)
            count = 0
            for code in adapter.SUPPORTED:
                g = adapter.with_capabilities(adapter.parse_capture(code, public), root=root)
                self.assertEqual(adapter.public_evidence(g, root), g['evidence'])
                stripped = deepcopy(g); stripped.pop('evidence')
                self.assertEqual(adapter.public_evidence(stripped, root), g['evidence'])
                self.assertIsNone(adapter.public_evidence(g, None))
                self.assertIsNone(adapter.public_evidence(g, empty))
                for t in g['templates']:
                    approved = adapter.approved_report_attachment(g, t, root)
                    self.assertEqual(approved, t['official_kind'] != 'sample')
                    count += approved
                wrong = deepcopy(g); wrong['materials'][0]['copies'] = '9'
                self.assertIsNone(adapter.public_evidence(wrong, root))
                t = next(t for t in g['templates'] if t['can_generate'])
                wrong = deepcopy(t); wrong['strict_binding']['source_url'] = 'https://czxb.jszwfw.gov.cn/'
                self.assertFalse(adapter.approved_report_attachment(g, wrong, root))
            self.assertEqual(count, 10)
            path = public / 'PUBLIC-WHITELIST.json'; path.write_bytes(b'{}')
            with self.assertRaises(ValueError): adapter.parse_capture('320508', public)
            self.assertIsNone(adapter.public_evidence(g, root))
