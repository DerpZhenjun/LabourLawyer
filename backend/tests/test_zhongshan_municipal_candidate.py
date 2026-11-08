"""The municipal legacy layout is available only against its own exact source."""
import json
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

from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from routes import regional_guides as routes

ROOT = Path(__file__).resolve().parents[2]
CITY = {'province': 'guangdong', 'city': '中山市'}
SCOPE = {**CITY, 'district': '市本级'}
TEMPLATE = 'zhongshan-municipal-application'
SOURCE = 'https://hrss.zs.gov.cn/zcy/zczn/sqzc/content/post_1899769.html'
ORIGINAL = 'https://hrss.zs.gov.cn/attachment/0/536/536012/1899769.doc'
ORIGINAL_SHA256 = '674dae021de29fa3caff11d63d25acdd04d114501a9590b8f8db62d3ccb71a6a'
PRIVATE_PROPERTIES = {'docProps/core.xml', 'docProps/custom.xml', 'docProps/app.xml'}


class ZhongshanMunicipalCandidateTests(TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = RegionalStore(Path(tmp.name) / 'guide.sqlite')
        directory = DirectoryStore(Path(tmp.name) / 'directory.sqlite')
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        directory.put_area(next(row for row in rows if row['code'] == '442000' and row['level'] == 3))
        app = FastAPI()
        app.include_router(routes.router, prefix='/regional')
        self.enterContext(patch.object(routes, 'ROOT', ROOT))
        self.enterContext(patch.object(routes, 'store', return_value=self.store))
        self.enterContext(patch.object(routes, 'directory_store', return_value=directory))
        self.client = self.enterContext(TestClient(app))
        from regional_zhongshan_municipal import staged_guide
        self.guide = self.store.put_guide(staged_guide(ROOT))
        self.query = {**SCOPE, 'source_id': self.guide['source_id'], 'version': self.guide['version'],
                      'kind': 'application', 'template_id': TEMPLATE}

    def test_city_scope_and_download_provenance(self):
        choice, = self.client.get('/regional/areas', params=CITY).json()['items']
        self.assertEqual((choice['district'], choice['region_code'], choice['can_generate']),
                         ('市本级', '442000', True))
        self.assertEqual(self.guide['source_url'], SOURCE)
        template, = self.guide['templates']
        self.assertEqual((template['source_url'], template['official_sha256']),
                         (ORIGINAL, ORIGINAL_SHA256))
        download = self.client.get(f'/regional/templates/{TEMPLATE}', params=self.query)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.headers['X-Document-Origin'], 'official-blank-converted-layout')
        self.assertEqual(download.headers['X-Template-SHA256'], sha256(download.content).hexdigest())
        with ZipFile(BytesIO(download.content)) as pack:
            for name in PRIVATE_PROPERTIES:
                self.assertNotIn(b'</', pack.read(name))
        for district in ('', '三乡镇', '火炬开发区'):
            params = {**self.query, 'district': district}
            self.assertIsNone(self.client.get('/regional/lookup', params=params).json()['source_id'])
            self.assertIn(self.client.get(f'/regional/templates/{TEMPLATE}', params=params).status_code, (404, 409))

    def test_application_generation_only_with_own_current_contract(self):
        form = self.client.get('/regional/form-contract', params=self.query)
        self.assertEqual(form.status_code, 200, form.text)
        contract = form.json()
        self.assertEqual(contract['policy']['signature_field'], 'manual_only')
        data = {'applicant_name': '测试劳动者', 'requests': ['请求支付测试工资'],
                'reason_1': ['用于核验版式']}
        payload = {**self.query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': data}
        result = self.client.post('/regional/generate', json=payload)
        self.assertEqual(result.status_code, 200, result.text if not result.is_success else '')
        self.assertEqual(result.headers['X-Document-Origin'], 'official-blank-converted-filled')
        table = Document(BytesIO(result.content)).tables[0]
        self.assertEqual(table.rows[0].cells[3].text, data['applicant_name'])
        self.assertIn(data['requests'][0], table.rows[8].cells[2].text)
        self.assertIn(data['reason_1'][0], table.rows[17].cells[2].text)
        for changes in ({'contract_id': None}, {'contract_id': '0'*64}, {'kind': 'evidence'},
                        {'mode': 'reference_adaptation'}, {'district': '三乡镇'}, {'version': self.guide['version']+1}):
            self.assertEqual(self.client.post('/regional/generate', json={**payload, **changes}).status_code, 409)
        for invalid in ({'signed': True}, {'reason_1': ['字'*23]}, {'requests': ['字'*21]}, {'phone': '测试文字'}):
            self.assertEqual(self.client.post('/regional/generate', json={**payload, 'data': invalid}).status_code, 422)

    def test_mutated_source_or_layout_identity_cannot_generate(self):
        from regional_zhongshan_municipal import checked_adapter, exact_municipal
        template, = self.guide['templates']
        for changes in ({'source_version': '0'*64}, {'district': '三乡镇'},
                        {'source_url': ORIGINAL}, {'scope_level': 'district'}):
            guide = {**self.guide, **changes}
            self.assertFalse(exact_municipal(guide))
            with self.assertRaises(ValueError):
                checked_adapter(guide, template, 'application', root=ROOT)
        for changes in ({'source_url': ORIGINAL.replace('536012', '536013')}, {'sha256': '0'*64}):
            with self.assertRaises(ValueError):
                checked_adapter(self.guide, {**template, **changes}, 'application', root=ROOT)
