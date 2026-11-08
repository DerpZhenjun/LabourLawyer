"""The three own-source applications cannot borrow a county or an evidence template."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class BaojiCountyApplicationAPITests(TestCase):
    def test_generation_and_download_are_source_bound(self):
        from regional_baoji_county_application import staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            guides = {code: store.put_guide(staged_guide(code, ROOT)) for code in ('610323', '610326', '610327')}
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, guide in guides.items():
                    with self.subTest(code=code):
                        template, = guide['templates']
                        query = {key: guide[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
                        query.update(template_id=template['id'], kind='application')
                        contract = client.get('/regional/form-contract', params=query)
                        self.assertEqual(contract.status_code, 200, contract.text)
                        self.assertEqual(contract.json()['policy']['signature_field'], 'manual_only')
                        blank = client.get(f"/regional/templates/{template['id']}", params=query)
                        self.assertEqual(blank.status_code, 200)
                        self.assertEqual(blank.headers['X-Template-SHA256'], template['sha256'])
                        payload = {**query, 'mode': 'blank', 'contract_id': contract.json()['contract_id'],
                                   'data': {'applicant_name': '测试劳动者'}}
                        response = client.post('/regional/generate', json=payload)
                        self.assertEqual(response.status_code, 200, response.text if not response.is_success else '')
                        self.assertEqual(response.headers['X-Document-Origin'], 'official-blank-filled')
                        self.assertIn('测试劳动者', ''.join(p.text for p in Document(BytesIO(response.content)).paragraphs))
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'kind': 'evidence'}).status_code, 409)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'contract_id': None}).status_code, 409)
                wrong = guides['610327']
                self.assertIn(client.get('/regional/templates/baoji-610323-worker-application', params={
                    'province': wrong['province'], 'city': wrong['city'], 'district': wrong['district'],
                    'source_id': wrong['source_id'], 'version': wrong['version'],
                }).status_code, (404, 409))
