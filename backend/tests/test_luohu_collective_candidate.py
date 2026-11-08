"""Exact own-source checks and native-layout filling for Luohu collective forms."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from zipfile import ZipFile

from docx import Document


ROOT = Path(__file__).resolve().parents[2]


class LuohuCollectiveCandidateTests(TestCase):
    def test_original_provenance_and_both_generation_layouts(self):
        from regional_luohu_collective import checked_adapter, fill_document, schema_descriptor, staged_guide
        guide = staged_guide(ROOT)
        self.assertEqual((guide['province'], guide['city'], guide['district'], guide['region_code'], guide['case_scope']),
                         ('guangdong', '深圳市', '深圳市罗湖区', '440303', 'collective'))
        fields = schema_descriptor('application', guide['source_version'])['fields']
        respondents = next(field for field in fields if field['key'] == 'respondents')
        self.assertEqual(next(field for field in respondents['fields'] if field['key'] == 'operator')['label'], '实际经营人')
        samples = {'application': {'representatives': '测试代表', 'applicant_count': '12',
                                    'respondents': [{'name': '测试单位'}], 'requests': ['测试请求'],
                                    'fact_lines': ['合成事实'], 'date': '2026-11-08'},
                   'evidence': {'items': [{'name': '测试合同', 'purpose': '测试证明', 'sheet_count': '2'}],
                                'submitter': '测试代表', 'date': '2026-11-08'}}
        for template in guide['templates']:
            kind, = template['document_types']
            self.assertEqual(checked_adapter(guide, template, kind, ROOT), template['adapter'])
            path = ROOT / template['file']
            output = BytesIO()
            fill_document(kind, path, samples[kind]).save(output)
            with ZipFile(path) as source, ZipFile(output) as result:
                self.assertEqual(source.namelist(), result.namelist())
                self.assertTrue(all(source.read(name) == result.read(name) for name in source.namelist()
                                    if name != 'word/document.xml'))
                self.assertIn('测试代表'.encode(), result.read('word/document.xml'))
            rendered = Document(output)
            if kind == 'evidence':
                self.assertEqual([cell.text for cell in rendered.tables[0].rows[1].cells],
                                 ['1', '测试合同', '测试证明', '2'])

    def test_ordinary_or_foreign_sources_do_not_bind(self):
        from regional_luohu_collective import checked_adapter, staged_guide
        g = staged_guide(ROOT)
        t, _ = g['templates']
        for change in ({'district': '福田区'}, {'case_scope': None}, {'source_id': 'fake'},
                       {'source_version': '0'*64}, {'published': True}):
            with self.assertRaises(ValueError):
                checked_adapter({**g, **change}, t, 'application', ROOT)
        bad = deepcopy(t)
        bad.pop('case_scope')
        with self.assertRaises(ValueError):
            checked_adapter(g, bad, 'application', ROOT)
        with self.assertRaises(ValueError):
            checked_adapter(g, t, 'evidence', ROOT)
