"""Baoji uses its exact four-column evidence catalog and leaves signature to the filer."""
import importlib
from io import BytesIO
from pathlib import Path
import unittest
from zipfile import ZipFile

from docx import Document
from pydantic import ValidationError


class BaojiEvidenceTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.layout = root / 'templates/_docx/_regional/shaanxi/baoji-municipal-evidence.docx'
        spec = importlib.util.find_spec('regional_baoji_evidence')
        self.assertIsNotNone(spec, 'Baoji evidence renderer is not registered')
        self.adapter = importlib.import_module(spec.name)

    def test_keeps_catalog_columns_and_manual_signature(self):
        items = [{'name': 'LABOR RECORD', 'purpose': 'PAY PERIOD', 'page_range': '1-2'}] * 9
        out = BytesIO()
        self.adapter.fill_evidence(self.layout.read_bytes(), {'items': items}).save(out)
        with ZipFile(self.layout) as original, ZipFile(out) as filled:
            self.assertEqual(original.namelist(), filled.namelist())
            for entry in original.namelist():
                if entry != 'word/document.xml':
                    self.assertEqual(original.read(entry), filled.read(entry))
        doc = Document(out)
        table = doc.tables[0]
        self.assertEqual(len(table.rows), 12)
        self.assertFalse(table.autofit)
        self.assertEqual(table.rows[10].cells[2].paragraphs[0].paragraph_format.line_spacing.pt, 13)
        self.assertEqual([cell.text.strip() for cell in table.rows[10].cells],
                         ['9', 'LABOR RECORD', 'PAY PERIOD', '1-2'])
        self.assertIn('\u7b7e\u5b57\u6216\u76d6\u7ae0', table.rows[11].cells[0].text)
        self.assertNotIn('\u9ad8\u4eae', table.rows[11].cells[0].text)

    def test_rejects_signatures_and_beyond_form_capacity(self):
        form = self.adapter.BaojiEvidenceRequest
        for payload in ({'signature': 'name'}, {'items': [{}] * 10},
                        {'items': [{'page_range': '3-1'}]},
                        {'items': [{'name': 'one\ntwo'}]}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    form.model_validate(payload)
