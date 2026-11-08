"""Exact district/functional-area candidates must not inherit city sources."""
from copy import deepcopy
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
CITY = {'province': 'jiangsu', 'city': '淮安市'}
AREAS = {
    '320804': ('淮阴区', 'huaiyin', 'af10b6358a0cea5389de88b7', '320804',
               'eca65f46-5178-4c29-a6f5-cea523aa5595', '857d0650-f222-465d-9687-54459d9e3bb0'),
    '320813': ('洪泽区', 'hongze', '353f307d6c7fc7e41924a8cf', '320829',
               'db154c19-9478-4644-9120-2a9bf727c70b', '70b69cb8-9011-464c-b31c-15bc6339e391'),
    '320871': ('经济开发区', 'huaian-edz', 'd80293457ba981b81997c7f9', '320871',
               'e3661b6a-1991-4fa4-9471-4f5975d7586a', '2d24580f-7c60-4ac0-880d-fc3437ba71be'),
}


class HuaianOwnCandidatesTests(TestCase):
    def test_hongze_current_code_keeps_legacy_provider_value(self):
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        legacy = next(r for r in rows if r['code'] == '320829' and r['district'] == '洪泽区')
        with TemporaryDirectory(prefix='hongze-directory-') as tmp:
            directory = DirectoryStore(Path(tmp) / 'directory.sqlite')
            directory.put_area(legacy)
            row, = directory.areas('jiangsu', '淮安市')
            self.assertEqual((row['code'], row['provider_code'], row['district']),
                             ('320813', '320829', '洪泽区'))
            with directory.connection() as db:
                stored = json.loads(db.execute('SELECT payload FROM directory_areas').fetchone()['payload'])
            self.assertEqual(stored['code'], '320829')

    def test_exact_local_originals_contracts_and_downloads(self):
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        with TemporaryDirectory(prefix='huaian-own-candidates-') as tmp:
            store = RegionalStore(Path(tmp) / 'guides.sqlite')
            directory = DirectoryStore(Path(tmp) / 'directory.sqlite')
            directory.put_area(next(r for r in rows if r['code'] == '320800' and r['level'] == 3))
            store.put_guide(forms.staged_jiangsu_municipal(ROOT, '320800'))
            for code, (district, slug, source, provider, app_id, evidence_id) in AREAS.items():
                directory.put_area(next(r for r in rows if r['code'] == provider and r['district'] == district))
                base = ROOT / f'reports/overnight-gap-closure-20261030/localities/{slug}-own-source'
                only_source = json.loads((base / 'GUIDE.json').read_bytes())
                app_original = next(t for t in only_source['templates'] if t['id'] == app_id)
                self.assertIsNone(forms.blank_binding(only_source, app_original))
                candidate = forms.staged_jiangsu_locality(ROOT, code)
                self.assertFalse(candidate['published'])
                self.assertEqual(candidate['source_id'], source)
                self.assertIsNone(forms.blank_binding({**candidate, 'district': '市本级'}, app_original))
                self.assertIsNone(forms.blank_binding({**candidate, 'scope_level': 'municipal'}, app_original))
                store.put_guide(candidate)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.object(routes, 'directory_store', return_value=directory), TestClient(app) as client:
                options = client.get('/regional/areas', params=CITY).json()['items']
                for code, (district, _, source, _, app_id, evidence_id) in AREAS.items():
                    with self.subTest(district=district):
                        option, = (row for row in options if row['district'] == district)
                        self.assertEqual((option['code'], option['source_id']), (code, source))
                        scope = {**CITY, 'district': district}
                        guide = client.get('/regional/lookup', params=scope).json()
                        for kind, annex in (('application', app_id), ('evidence', evidence_id)):
                            q = {**scope, 'source_id': source, 'version': guide['version'],
                                 'kind': kind, 'template_id': annex}
                            response = client.get('/regional/form-contract', params=q)
                            self.assertEqual(response.status_code, 200, response.text)
                            contract = response.json()
                            original = client.get(f'/regional/templates/{annex}', params=q)
                            self.assertEqual(original.status_code, 200)
                            template = next(t for t in guide['templates'] if t['id'] == annex)
                            self.assertEqual(original.content, (ROOT / template['file']).read_bytes())
                            data = deepcopy(contract['defaults'])
                            label = f'{district}虚构验证'
                            if kind == 'application':
                                data['applicantName'] = label
                            else:
                                data['evidenceList'] = [{'name': label, 'source': '本人保存', 'purpose': '核验',
                                                        'pageCount': '3页', 'originalType': '复印件'}]
                            payload = {**q, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': data}
                            result = client.post('/regional/generate', json=payload)
                            self.assertEqual(result.status_code, 200, result.text if not result.is_success else '')
                            self.assertEqual(result.headers['X-Guide-Source-ID'], source)
                            document = Document(BytesIO(result.content))
                            if kind == 'application':
                                self.assertTrue(any(label in p.text for p in document.paragraphs))
                            else:
                                self.assertEqual(document.tables[0].rows[1].cells[1].text, label)
                            for wrong in ('市本级', '清江浦区', ''):
                                mismatch = client.post('/regional/generate', json={**payload, 'district': wrong})
                                self.assertEqual(mismatch.status_code, 409)
