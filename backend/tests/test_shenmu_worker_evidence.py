from io import BytesIO
import os
from pathlib import Path
from unittest import TestCase, skipUnless
from zipfile import ZipFile

from docx import Document
from pydantic import ValidationError

from regional_shenmu_evidence import EvidenceRequest, fill_evidence


LAYOUT = os.environ.get("LABOURLAWYER_SHENMU_EVIDENCE_LAYOUT")


class ShenmuEvidenceTests(TestCase):
    def test_rejects_overflow_and_non_cell_fields(self):
        for payload in (
            {"items": [{"name": "合成证据"}] * 11},
            {"items": [{"name": "换\n行"}]},
            {"items": [{"name": "甲" * 25}]},
            {"items": [{"name": "", "purpose": "缺少名称"}]},
            {"items": [{"name": "合成证据", "page_count": "2-3"}]},
            {"items": [{"name": "合成证据", "page_count": 2}]},
            {"items": [{"name": "合成证据", "notes": "额外栏"}]},
            {"items": [], "submitter": "签名留在原表"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                EvidenceRequest.model_validate(payload)

    @skipUnless(LAYOUT, "verified Shenmu blank layout is kept locally")
    def test_uses_only_the_verified_ten_row_sheet(self):
        original = Path(LAYOUT).read_bytes()
        with self.assertRaises(ValueError):
            fill_evidence(original + b" ", {"items": []})
        official = Document(BytesIO(original))
        for count in (0, 1, 10):
            payload = {"items": [
                {"name": f"合成材料{index}", "purpose": "核对合成事实", "page_count": "2"}
                for index in range(1, count + 1)
            ]}
            rendered = BytesIO()
            fill_evidence(original, payload).save(rendered)
            result = Document(rendered)
            self.assertEqual([p.text for p in official.paragraphs], [p.text for p in result.paragraphs])
            table, = result.tables
            self.assertEqual(len(table.rows), 11)
            self.assertEqual(["".join(c.text.split()) for c in table.rows[0].cells], ["序号", "名称", "证明内容", "页数"])
            for index, row in enumerate(table.rows[1:], 1):
                expected = [str(index), f"合成材料{index}", "核对合成事实", "2"] if index <= count else [""] * 4
                self.assertEqual([cell.text.strip() for cell in row.cells], expected)
            with ZipFile(BytesIO(original)) as source, ZipFile(rendered) as output:
                self.assertEqual(source.namelist(), output.namelist())
                self.assertTrue(all(source.read(name) == output.read(name)
                                    for name in source.namelist() if name != "word/document.xml"))
