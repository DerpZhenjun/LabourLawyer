from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from docx import Document
from pydantic import ValidationError


class XixiangReferenceApplicationTests(TestCase):
    def test_candidate_rejects_missing_or_substituted_private_reference(self):
        from regional_hanzhong_guides import YANGXIAN_XIXIANG_PROOF
        from regional_xixiang_reference import LAYOUT, staged_reference_candidate

        with TemporaryDirectory() as work:
            root = Path(work)
            proof = root / YANGXIAN_XIXIANG_PROOF
            proof.parent.mkdir(parents=True)
            existing = Path(__file__).resolve().parents[2] / YANGXIAN_XIXIANG_PROOF
            proof.write_bytes(existing.read_bytes())
            for wrong_source in (None, b'placeholder from another county'):
                with self.subTest(wrong_source=wrong_source):
                    if wrong_source:
                        path = root / LAYOUT
                        path.parent.mkdir(parents=True)
                        path.write_bytes(wrong_source)
                    with self.assertRaisesRegex(ValueError, '西乡县'):
                        staged_reference_candidate(root)

    def test_source_hash_is_required_before_opening_document(self):
        from regional_xixiang_reference import fill_application

        with self.assertRaisesRegex(ValueError, '西乡县'):
            fill_application(b'foreign document', {})

    def test_synthetic_slot_fill_and_handwritten_signature(self):
        from hashlib import sha256
        from regional_xixiang_reference import fill_application

        doc = Document()
        for index in range(29):
            text = {0: '劳动仲裁申请书', 24: '西乡县劳动人事争议仲裁委员会',
                    27: '申请人：    (签名按手印)', 28: '二O  年  月  日'}.get(index, '演示空位')
            doc.add_paragraph(text)
        raw = BytesIO()
        doc.save(raw)
        source = raw.getvalue()
        with patch('regional_xixiang_reference.REFERENCE_SHA256', sha256(source).hexdigest()):
            result = fill_application(source, {
                'applicant_name': '虚构甲', 'birth_date': '1990-01-02', 'ethnicity': '示例',
                'respondent_name': '虚构乙公司', 'third_party_name': '虚构丙',
                'requests': ['虚构请求一', '虚构请求二'], 'facts': '虚构事实',
                'application_copies': '2', 'evidence_copies': '1',
            })
        texts = [p.text for p in result.paragraphs]
        self.assertIn('虚构甲', texts[1])
        self.assertIn('1990年1月2日', texts[2])
        self.assertIn('虚构丙', texts[13])
        self.assertEqual(texts[18:20], ['1. 虚构请求一', '2. 虚构请求二'])
        self.assertEqual(texts[22], '事实和理由：虚构事实')
        self.assertEqual(texts[24], '西乡县劳动人事争议仲裁委员会')
        self.assertEqual(texts[27:29], ['申请人：    (签名按手印)', '二O  年  月  日'])
        self.assertNotIn('定稿', ''.join(texts))
        output = BytesIO()
        result.save(output)
        with ZipFile(output) as package:
            self.assertFalse(any(key.startswith('customXml/') for key in package.namelist()))

    def test_draft_rejects_non_source_fields_and_invalid_values(self):
        from regional_xixiang_reference import XixiangReferenceRequest

        for values in ({'committee_name': '外地机构'}, {'signature': '虚构签字'},
                       {'requests': ['事项'] * 5}, {'birth_date': '2026-02-30'},
                       {'phone': '123\n456'}, {'facts': '错误\x00文本'}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                XixiangReferenceRequest.model_validate(values)
