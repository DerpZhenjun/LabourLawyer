from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from province_documents import PROVINCE_DOCUMENTS, get_province_document
from WenShu.generic_template_fill import generate_application, generate_evidence


def document_text(document) -> str:
    values = [paragraph.text for paragraph in document.paragraphs]
    values.extend(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    return "\n".join(values)


class AllProvinceDocumentTests(unittest.TestCase):
    application_payload = {
        "committeeName": "测试市劳动人事争议仲裁委员会",
        "applicantName": "王晨",
        "birthDate": "1992-08-16",
        "gender": "男",
        "nationality": "汉族",
        "idNumber": "110101199208160015",
        "phone": "13800001234",
        "householdType": "本省非农业户口",
        "idAddress": "测试市人民路88号",
        "applicantMailingAddress": "测试市人民路88号",
        "respondentName": "测试启明科技有限公司",
        "socialCreditCode": "91320100MA2B12345X",
        "registeredAddress": "测试市创新大道120号",
        "mailingAddress": "测试市创新大道120号",
        "workAddress": "测试市创新大道120号8层",
        "legalRepName": "张明",
        "legalRepPosition": "执行董事",
        "companyContactPhone": "13900005678",
        "requests": ["请求支付拖欠工资24000元。", "请求支付经济补偿16000元。"],
        "factsReason": "申请人正常提供劳动，被申请人拖欠工资并解除劳动关系。",
        "copyCount": 2,
        "applicationDate": "2026-09-23",
    }
    evidence_payload = {
        "committeeName": "测试市劳动人事争议仲裁委员会",
        "copyCount": 2,
        "submitterName": "王晨",
        "submitDate": "2026-09-23",
        "evidenceList": [
            {"name": "劳动合同", "pageCount": "5页", "source": "本人保存", "purpose": "证明劳动关系和工资约定。"},
            {"name": "银行工资流水", "pageCount": "3页", "source": "银行下载", "purpose": "证明工资支付和拖欠情况。"},
        ],
    }

    def test_catalog_covers_all_31_province_level_regions(self):
        self.assertEqual(len(PROVINCE_DOCUMENTS), 31)
        enabled = [item for item in PROVINCE_DOCUMENTS.values() if item["documents"]]
        self.assertEqual(len(enabled), 21)
        for item in PROVINCE_DOCUMENTS.values():
            self.assertTrue(item["source_url"])
            self.assertTrue(item["authority"])
            self.assertTrue(item["scope"])

    def test_every_enabled_application_uses_and_preserves_its_official_file(self):
        failures = []
        for slug, item in PROVINCE_DOCUMENTS.items():
            if "application" not in item["documents"] or slug in {"zhejiang", "guangdong"}:
                continue
            _, path = get_province_document(slug, "application")
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                generated = generate_application(self.application_payload, path)
                text = document_text(generated)
                self.assertTrue("王晨" in text or "测试启明科技有限公司" in text, slug)
                self.assertTrue("24000" in text or "正常提供劳动" in text, slug)
            except Exception as exc:  # collect every province in one test run
                failures.append(f"{slug}: {exc}")
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest(), slug)
        self.assertEqual(failures, [])

    def test_every_enabled_evidence_template_accepts_case_items(self):
        failures = []
        for slug, item in PROVINCE_DOCUMENTS.items():
            if "evidence" not in item["documents"] or slug in {"zhejiang", "guangdong"}:
                continue
            _, path = get_province_document(slug, "evidence")
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                generated = generate_evidence(self.evidence_payload, path)
                text = document_text(generated)
                self.assertIn("劳动合同", text, slug)
                self.assertIn("证明劳动关系", text, slug)
            except Exception as exc:
                failures.append(f"{slug}: {exc}")
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest(), slug)
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
