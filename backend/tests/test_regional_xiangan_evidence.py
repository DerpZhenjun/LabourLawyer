from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

import regional_quanzhou_next4 as provider
import regional_xiangan_evidence as evidence
from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'reports/overnight-gap-closure-20261030/localities/xiamen-xiangan-legacy-evidence'
DATA = {
    'submissionNumber': '2', 'copyType': '副本', 'caseNumber': '虚构仲案[2026]7号',
    'applicantName': '虚构申请人', 'respondentName': '虚构用人单位', 'thirdParty': '虚构第三人',
    'submitterRole': '申请人', 'submitDate': '2026-11-08',
    'evidenceList': [
        {'name': f'虚构证据{i}', 'source': '自存', 'pageRange': '1-2',
         'purpose': '证明虚构关系', 'originalType': '复印件'} for i in range(1, 11)
    ],
}


class XianganLegacyEvidenceTests(TestCase):
    def test_fill_preserves_converted_blank_and_uses_the_own_ten_row_layout(self):
        layout = (FIXTURE / 'evidence-layout-converted.docx').read_bytes()
        self.assertEqual(evidence.fill_layout(layout, {}), layout)
        filled = evidence.fill_layout(layout, DATA)
        doc = Document(BytesIO(filled))
        self.assertEqual(len(doc.tables[0].rows), 11)
        self.assertEqual([c.text for c in doc.tables[0].rows[10].cells],
                         ['10', '虚构证据10', '自存', '1-2', '证明虚构关系', '复印件'])
        self.assertEqual(doc.paragraphs[2].text, '案号：虚构仲案[2026]7号')
        self.assertIn('☑副本', doc.paragraphs[1].text)
        self.assertIn('☑申请人', doc.paragraphs[7].text)
        self.assertEqual(doc.paragraphs[8].text, '举证人（签名或盖章）：')
        self.assertEqual(doc.paragraphs[9].text, '提交日期：2026-11-08')
        with ZipFile(BytesIO(layout)) as original, ZipFile(BytesIO(filled)) as output:
            self.assertEqual(original.namelist(), output.namelist())
            for member in original.namelist():
                if member != 'word/document.xml':
                    self.assertEqual(original.read(member), output.read(member))

    def test_rejects_overflow_unknown_fields_and_invalid_dates(self):
        bad_values = [
            {'evidenceList': [{}] * 11}, {'evidenceList': [{'source': '伪造的很长来源'}]},
            {'evidenceList': [{'itemCount': '1'}]}, {'submitDate': '2026-02-30'},
            {'copyType': '照片'}, {'signature': '虚构签名'}, {'applicantName': 'a\nb'},
        ]
        for data in bad_values:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                evidence.XianganEvidenceRequest.model_validate(data)

    def test_real_contract_download_and_filled_response_are_exact_scope(self):
        scope = {'province': 'fujian', 'city': '厦门市', 'district': '翔安区'}
        guide = provider.staged_candidate('350213', root=ROOT)
        template, = [t for t in guide['templates'] if t['can_generate'] and t['document_types'] == ['evidence']]
        self.assertEqual(template['id'], 'A637EF6EAD573C2578CA358269DED78A')
        with TemporaryDirectory(prefix='xiangan-review-') as folder:
            store = RegionalStore(Path(folder) / 'guides.sqlite')
            store.put_guide(guide)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store),                     patch.dict('os.environ', {'LABOURLAWYER_DATA_DIR': folder}), TestClient(app) as client:
                guide = client.get('/regional/lookup', params=scope).json()
                query = {**scope, 'source_id': guide['source_id'], 'version': guide['version'],
                         'kind': 'evidence', 'template_id': template['id']}
                contract = client.get('/regional/form-contract', params=query)
                self.assertEqual(contract.status_code, 200, contract.text)
                contract = contract.json()
                rows, = [f for f in contract['fields'] if f['key'] == 'evidenceList']
                self.assertEqual(rows['maxItems'], 10)
                self.assertEqual(contract['policy']['text_controls'], 'newline_only')
                self.assertIn('source', {f['key'] for f in rows['fields']})
                result = client.get(f"/regional/templates/{template['id']}", params=query)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(sha256(result.content).hexdigest(), evidence.ORIGINAL_SHA256)
                payload = {**query, 'mode': 'blank', 'data': DATA, 'contract_id': contract['contract_id']}
                result = client.post('/regional/generate', json=payload)
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.headers['X-Document-Origin'], 'official-blank-converted-filled')
                self.assertEqual(result.headers['X-Form-Contract-ID'], contract['contract_id'])
                self.assertEqual(Document(BytesIO(result.content)).tables[0].rows[10].cells[2].text, '自存')
                self.assertEqual(client.post('/regional/generate', json={**payload, 'contract_id': None}).status_code, 409)
                self.assertEqual(client.post('/regional/generate', json={**payload, 'district': '同安区'}).status_code, 409)
