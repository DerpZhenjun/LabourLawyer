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


    def test_linyou_preserves_its_own_fields_recipient_and_manual_signature(self):
        code = '610329'
        raw = (LAYOUT / f'baoji-{code}-worker-application.docx').read_bytes()
        out = BytesIO()
        self.adapter.fill_application(code, raw, {
            'applicant_name': '测试劳动者', 'gender': '测试', 'birth_text': '测试年月',
            'nationality': '测试民族', 'applicant_work_unit': '测试工作单位',
            'address': '测试地址', 'phone': '测试电话', 'applicant_postcode': '测试邮编',
            'respondent_name': '测试用人单位', 'representative': '测试代表',
            'representative_role': '测试职务', 'respondent_address': '测试单位通信地址',
            'respondent_phone': '测试单位电话', 'respondent_postcode': '测试单位邮编',
            'requests': ['请求核对测试工资', '请求核对测试记录'], 'facts': '测试第一段\n测试第二段',
        }).save(out)
        paragraphs = [p.text for p in Document(out).paragraphs]
        for index, value in {
            1: '测试劳动者', 2: '测试年月', 3: '测试工作单位', 4: '测试邮编',
            7: '测试单位通信地址', 8: '测试单位邮编', 9: '请求核对测试工资',
            10: '请求核对测试记录', 12: '测试第一段\n测试第二段',
            14: '麟游县劳动人事争议仲裁委员会', 15: '申请书一式三份', 16: '证据资料一式三份',
        }.items():
            self.assertIn(value, paragraphs[index])
        self.assertNotIn('测试劳动者', paragraphs[17])
        self.assertEqual(paragraphs[13].strip(), '此致')
        self.assertIn('（签名）', paragraphs[17])
        with self.assertRaises(ValidationError):
            self.adapter.fill_application(code, raw, {'id_number': '非本县表单栏位'})
        with ZipFile(BytesIO(raw)) as old, ZipFile(out) as new:
            self.assertTrue(all(old.read(name) == new.read(name)
                                for name in old.namelist() if name != 'word/document.xml'))
