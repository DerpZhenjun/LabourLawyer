"""Baoji evidence is available only for the pinned municipal guide and template."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / 'reports/overnight-gap-closure-20261030/localities/baoji-municipal-own-source/GUIDE.json'
CITY = {'province': 'shaanxi', 'city': '宝鸡市'}
SCOPE = {**CITY, 'district': '市本级'}
ADAPTER = 'shaanxi_baoji_municipal_evidence_v1'
TEMPLATE = 'baoji-municipal-evidence'
SAMPLE = 'baoji-municipal-application-sample'


class BaojiEvidenceApiTests(TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        guide_store = RegionalStore(root / 'guide.sqlite')
        directory = DirectoryStore(root / 'directory.sqlite')
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        for row in rows:
            if row['code'] in {'610300', '610303'}:
                directory.put_area(row)
        raw = GUIDE.read_bytes()
        guide = json.loads(raw)
        guide['source_version'] = sha256(raw).hexdigest()
        guide['templates'][0].update(can_generate=True, adapter=ADAPTER)
        stored = guide_store.put_guide(guide)
        self.query = {**SCOPE, 'source_id': stored['source_id'], 'version': stored['version'],
                      'kind': 'evidence', 'template_id': TEMPLATE}
        app = FastAPI()
        app.include_router(routes.router, prefix='/regional')
        self.enterContext(patch.object(routes, 'ROOT', ROOT))
        self.enterContext(patch.object(routes, 'store', return_value=guide_store))
        self.enterContext(patch.object(routes, 'directory_store', return_value=directory))
        self.client = self.enterContext(TestClient(app))

    def test_only_exact_city_entry_exposes_catalog(self):
        areas = self.client.get('/regional/areas', params=CITY).json()['items']
        self.assertEqual([(row['district'], row['can_generate']) for row in areas],
                         [('市本级', True), ('金台区', False)])
        response = self.client.get(f'/regional/templates/{TEMPLATE}', params=self.query)
        self.assertEqual(response.status_code, 200, response.text if not response.is_success else '')
        self.assertEqual(response.headers['X-Document-Origin'], 'official-blank-metadata-sanitized-layout')
        self.assertEqual(response.headers['X-Template-SHA256'], sha256(response.content).hexdigest())
        self.assertEqual(self.client.get(f'/regional/templates/{SAMPLE}', params=self.query).status_code, 404)

    def test_contract_fills_evidence_and_rejects_application_and_cross_district(self):
        result = self.client.get('/regional/form-contract', params=self.query)
        self.assertEqual(result.status_code, 200, result.text)
        contract = result.json()
        self.assertEqual(contract['policy']['signature_field'], 'manual_only')
        data = {'items': [{'name': '测试材料', 'purpose': '用于填写测试', 'page_range': '1-2'}]}
        payload = {**self.query, 'contract_id': contract['contract_id'], 'mode': 'blank', 'data': data}
        filled = self.client.post('/regional/generate', json=payload)
        self.assertEqual(filled.status_code, 200, filled.text if not filled.is_success else '')
        self.assertEqual(filled.headers['X-Document-Origin'], 'official-blank-filled')
        self.assertEqual([c.text.strip() for c in Document(BytesIO(filled.content)).tables[0].rows[2].cells],
                         ['1', '测试材料', '用于填写测试', '1-2'])
        for changes in ({'district': '金台区'}, {'contract_id': None}, {'contract_id': '0'*64},
                        {'kind': 'application'}, {'template_id': SAMPLE, 'kind': 'application'},
                        {'mode': 'reference_adaptation'}):
            self.assertEqual(self.client.post('/regional/generate', json={**payload, **changes}).status_code, 409)
