"""Exercise the actual mini-program payloads through every enabled API adapter."""
import hashlib
import io
import json
from pathlib import Path
import sys
import subprocess
import unittest

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from document_forms import FORM_SCHEMA
from province_documents import PROVINCE_DOCUMENTS, get_province_document
from routes.province_documents import router
from WenShu.exact_template_fill import all_paragraphs


class DocumentClientContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router, prefix='/api/province-documents')
        cls.client = TestClient(app)
        subprocess.run(['node', str(ROOT / 'scripts/test-document-clients.cjs')], cwd=ROOT, check=True, capture_output=True, timeout=30)
        cls.examples = json.loads((ROOT / 'miniprogram/data/provinces.json').read_text(encoding='utf8'))

    def test_capabilities_match_templates_and_both_client_snapshots(self):
        response = self.client.get('/api/province-documents')
        self.assertEqual(response.status_code, 200)
        records = response.json()['items']
        self.assertEqual(len(records), 31)
        for record in records:
            self.assertTrue(record['region'])
            for kind in record['documents']:
                self.assertTrue(record['forms'][kind + 'Fields'], (record['slug'], kind))
            client = next(p for p in self.examples if p['slug'] == record['slug'])
            self.assertEqual(client['documents'], record['documents'])
            self.assertEqual(client['hasApplication'], bool(record['documents'].get('application')))
            self.assertEqual(client['hasEvidence'], bool(record['documents'].get('evidence')))

    def test_actual_mini_payloads_generate_all_available_word_documents(self):
        payloads = json.loads((ROOT / '.runtime/document-audit/mini-payloads.json').read_text(encoding='utf8'))
        self.assertEqual(len(payloads), 34)
        for item in payloads:
            slug, kind = item['slug'], item['kind']
            with self.subTest(province=slug, kind=kind):
                _, template = get_province_document(slug, kind)
                before = hashlib.sha256(template.read_bytes()).hexdigest()
                response = self.client.post(f'/api/province-documents/{slug}/{kind}/generate', json=item['payload'])
                self.assertEqual(response.status_code, 200, response.text[:200] if response.status_code != 200 else '')
                self.assertTrue(response.content.startswith(b'PK\x03\x04'))
                document = Document(io.BytesIO(response.content))
                text = '\n'.join(p.text for p in all_paragraphs(document))
                if kind == 'application':
                    self.assertIn(item['payload']['applicantName'], text)
                    for claim in item['payload']['requests']:
                        self.assertIn(claim, text)
                    for paragraph in all_paragraphs(document):
                        if '签名' in paragraph.text or '签字' in paragraph.text:
                            self.assertNotIn(item['payload']['applicantName'], paragraph.text)
                else:
                    for evidence in item['payload']['evidenceList']:
                        self.assertIn(evidence['name'], text)
                        self.assertIn(evidence['purpose'], text)
                self.assertEqual(hashlib.sha256(template.read_bytes()).hexdigest(), before)

    def test_missing_templates_do_not_generate_another_province(self):
        for slug, province in PROVINCE_DOCUMENTS.items():
            for kind in ('application', 'evidence'):
                if kind not in province['documents']:
                    self.assertEqual(self.client.post(f'/api/province-documents/{slug}/{kind}/generate', json={}).status_code, 503)
        self.assertEqual(self.client.post('/api/province-documents/invalid/application/generate', json={}).status_code, 404)

    def test_template_capacity_and_incomplete_evidence_return_actionable_errors(self):
        too_many = self.client.post('/api/province-documents/hainan/application/generate', json={'requests': ['请求一', '请求二', '请求三']})
        self.assertEqual(too_many.status_code, 422)
        self.assertIn('2', too_many.json()['detail'])
        too_long = self.client.post('/api/province-documents/guangdong/application/generate', json={'factsReason': '甲' * 701})
        self.assertEqual(too_long.status_code, 422)
        incomplete = self.client.post('/api/province-documents/jiangsu/evidence/generate', json={'evidenceList': [{'purpose': '证明劳动关系'}]})
        self.assertEqual(incomplete.status_code, 422)
        self.assertIn('证据名称', incomplete.json()['detail'])

    def test_explicit_age_reaches_liaoning_template(self):
        response = self.client.post('/api/province-documents/liaoning/application/generate', json={'applicantName': '测试人', 'age': '42', 'birthDate': '1992-08-16', 'applicationDate': '2026-10-06'})
        self.assertEqual(response.status_code, 200)
        text = '\n'.join(p.text for p in all_paragraphs(Document(io.BytesIO(response.content))))
        self.assertIn('42', text)


if __name__ == '__main__':
    unittest.main()
