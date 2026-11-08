"""Verify Lianyungang municipal forms and keep district sources separate."""
from copy import deepcopy
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

import regional_blank_documents as forms
from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from routes import regional_guides as routes

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'reports/overnight-gap-closure-20261030/localities/lianyungang-municipal-own-source'
REGION = {'province': 'jiangsu', 'city': '连云港市', 'district': '市本级'}
SOURCE_ID = '798345f56be3804472dc90b1'
IDS = {
    'application': 'bcc67aa2-7b47-4cc2-92e6-3aaf581aa901',
    'evidence': 'eb850eb4-d57a-47e3-9fc9-45f719d582be',
}


class LianyungangMunicipalCandidateTests(TestCase):
    def test_scope_and_source_only_record_do_not_grant_generation(self):
        original = json.loads((SOURCE / 'GUIDE.json').read_bytes())
        own = next(t for t in original['templates'] if t['id'] == IDS['application'])
        self.assertIsNone(forms.blank_binding(original, own))
        staged = forms.staged_lianyungang_municipal(ROOT)
        own = next(t for t in staged['templates'] if t['id'] == IDS['application'])
        self.assertFalse(staged['published'])
        self.assertEqual(forms.blank_binding(staged, own), 'application')
        for key, value in (
            ('district', '海州区'), ('region_code', '320706'), ('published', True),
            ('source_version', '0' * 64), ('scope_level', 'district'),
        ):
            with self.subTest(key=key):
                self.assertIsNone(forms.blank_binding({**staged, key: value}, own))
        for t in staged['templates']:
            if t['id'] not in IDS.values():
                self.assertIsNone(forms.blank_binding(staged, t))

    def test_city_option_and_native_form_api_use_exact_municipal_source(self):
        directory_rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        city_row = next(r for r in directory_rows if r['code'] == '320700' and r['level'] == 3)
        with TemporaryDirectory(prefix='lianyungang-candidate-') as temp:
            store = RegionalStore(Path(temp) / 'guides.sqlite')
            directory = DirectoryStore(Path(temp) / 'directory.sqlite')
            directory.put_area(city_row)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.object(routes, 'directory_store', return_value=directory), TestClient(app) as client:
                city = {k: REGION[k] for k in ('province', 'city')}
                self.assertEqual(client.get('/regional/areas', params=city).json()['items'], [])
                store.put_guide(forms.staged_lianyungang_municipal(ROOT))
                choice, = client.get('/regional/areas', params=city).json()['items']
                self.assertEqual((choice['district'], choice['region_code'], choice['source_id']),
                                 ('市本级', '320700', SOURCE_ID))
                for district in ('', '海州区'):
                    other = client.get('/regional/lookup', params={**city, 'district': district}).json()
                    self.assertIsNone(other['source_id'])
                    self.assertFalse(any(t['can_generate'] for t in other['templates']))
                guide = client.get('/regional/lookup', params=REGION).json()
                self.assertEqual({t['id'] for t in guide['templates'] if t['can_generate']}, set(IDS.values()))
                for kind, annex in IDS.items():
                    with self.subTest(kind=kind):
                        query = {**REGION, 'source_id': SOURCE_ID, 'version': guide['version'],
                                 'kind': kind, 'template_id': annex}
                        form = client.get('/regional/form-contract', params=query)
                        self.assertEqual(form.status_code, 200, form.text)
                        contract = form.json()
                        original = client.get(f'/regional/templates/{annex}', params=query)
                        self.assertEqual(original.status_code, 200)
                        template = next(t for t in guide['templates'] if t['id'] == annex)
                        self.assertEqual(sha256(original.content).hexdigest(), template['sha256'])
                        data = deepcopy(contract['defaults'])
                        if kind == 'application':
                            data['applicantName'] = '连云港虚构申请人'
                        else:
                            data['evidenceList'] = [{'name': '虚构测试合同', 'source': '本人保存',
                                'purpose': '版式核验', 'pageCount': '3页', 'originalType': '复印件'}]
                        payload = {**query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': data}
                        result = client.post('/regional/generate', json=payload)
                        self.assertEqual(result.status_code, 200, result.text if not result.is_success else '')
                        self.assertEqual(result.headers['X-Guide-Source-ID'], SOURCE_ID)
                        self.assertEqual(result.headers['X-Document-Origin'], 'official-blank-filled')
                        generated = Document(BytesIO(result.content))
                        if kind == 'application':
                            self.assertTrue(any('连云港虚构申请人' in p.text for p in generated.paragraphs))
                        else:
                            self.assertEqual(generated.tables[0].rows[1].cells[1].text, '虚构测试合同')
                        bad = client.post('/regional/generate', json={**payload, 'district': '海州区'})
                        self.assertEqual(bad.status_code, 409)
