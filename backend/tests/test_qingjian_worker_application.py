from io import BytesIO
import os
from pathlib import Path
from unittest import TestCase, skipUnless
from zipfile import ZipFile

from docx import Document
from pydantic import ValidationError

from regional_qingjian_application import WorkerApplicationRequest, fill_application


PRIVATE = os.getenv("LABOURLAWYER_QINGJIAN_WORKER_LAYOUT")
REQUEST_LINES = (16, 18, 20, 22)
FACT_LINES = tuple(range(24, 34))


class QingjianWorkerApplicationTests(TestCase):
    def test_request_scope_and_line_capacity(self):
        for data in (
            {"requests": ["合成"] * 5}, {"facts": ["合成"] * 11},
            {"requests": ["甲" * 21]}, {"facts": ["换\n行"]},
            {"applicantName": "此处保留手填"},
        ):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                WorkerApplicationRequest.model_validate(data)

    @skipUnless(PRIVATE, "source-derived layout is kept locally")
    def test_fills_only_body_text_and_retains_existing_numbering(self):
        layout = Path(PRIVATE).read_bytes()
        with self.assertRaises(ValueError):
            fill_application(layout + b" ", {})
        source = Document(BytesIO(layout))
        requests = ["合成仲裁请求甲", "合成仲裁请求乙", "", "合成仲裁请求丁"]
        facts = ["合成事实甲", "", "合成事实丙"]
        output = BytesIO()
        fill_application(layout, {"requests": requests, "facts": facts}).save(output)
        result = Document(output)
        self.assertEqual(len(source.paragraphs), len(result.paragraphs))
        changed = dict(zip(REQUEST_LINES, requests))
        changed.update(zip(FACT_LINES, facts))
        for index, original in enumerate(source.paragraphs):
            target = result.paragraphs[index]
            if changed.get(index):
                self.assertEqual(target.text, original.text + changed[index])
            else:
                self.assertEqual(target._p.xml, original._p.xml)
        with ZipFile(BytesIO(layout)) as sample, ZipFile(output) as filled:
            self.assertEqual(sample.namelist(), filled.namelist())
            self.assertTrue(all(sample.read(part) == filled.read(part) for part in sample.namelist()
                                if part != "word/document.xml"))
