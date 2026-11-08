"""Baoji worker applications preserve the county's form and manual signature."""
import importlib
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from zipfile import ZipFile

from docx import Document
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / 'templates/_docx/_regional/shaanxi'


class BaojiCountyApplicationTests(TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('regional_baoji_county_application')
        self.assertIsNotNone(spec, 'Baoji county application renderer not registered')
        self.adapter = importlib.import_module(spec.name)

    def test_each_layout_keeps_its_label_and_manual_signature(self):
        for code in ('610323', '610326', '610327'):
            with self.subTest(county=code):
                raw = (LAYOUT / f'baoji-{code}-worker-application.docx').read_bytes()
                out = BytesIO()
                doc = self.adapter.fill_application(code, raw, {
                    'applicant_name': '测试劳动者', 'respondent_name': '测试用人单位',
                    'requests': ['请求核对测试工资'], 'facts': '用于版式核验，不用于提交。',
                })
                doc.save(out)
                text = '\n'.join(p.text for p in Document(out).paragraphs)
                self.assertIn('测试劳动者', text)
                self.assertIn('测试用人单位', text)
                self.assertIn('请求核对测试工资', text)
                self.assertIn('用于版式核验，不用于提交。', text)
                if code == '610326':
                    self.assertIn('眉县劳动争议仲裁委员会', text)
                else:
                    self.assertNotIn('眉县劳动争议仲裁委员会', text)
                self.assertNotIn('申请人：测试劳动者', text.splitlines()[-3:])
                with ZipFile(BytesIO(raw)) as old, ZipFile(out) as new:
                    self.assertEqual(old.namelist(), new.namelist())
                    for name in old.namelist():
                        if name != 'word/document.xml':
                            self.assertEqual(old.read(name), new.read(name))

    def test_wrong_layout_and_signature_field_are_rejected(self):
        raw = (LAYOUT / 'baoji-610326-worker-application.docx').read_bytes()
        with self.assertRaises(ValueError):
            self.adapter.fill_application('610323', raw, {})
        with self.assertRaises(ValidationError):
            self.adapter.fill_application('610326', raw, {'signature': '测试'})
        with self.assertRaises(ValueError):
            self.adapter.fill_application('610330', raw, {})
