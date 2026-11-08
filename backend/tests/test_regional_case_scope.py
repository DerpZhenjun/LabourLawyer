"""Ordinary and collective-case surfaces must never share an eligible template."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from routes import regional_guides as routes


class RegionalCaseScopeTests(TestCase):
    def setUp(self):
        work = self.enterContext(TemporaryDirectory())
        self.work = Path(work)
        store = RegionalStore(Path(work) / 'guides.sqlite')
        self.region = {'province': 'guangdong', 'city': '深圳市', 'district': '深圳市罗湖区'}
        source = store.put_guide({
            **self.region, 'region_code': '440303', 'service_name': '劳动人事争议仲裁申请',
            'source_url': 'https://example.gov.cn/local-collective', 'collected_at': '2026-11-08',
            'verified_at': '2026-11-08', 'verification_status': 'partial', 'case_scope': 'collective',
            'fields': {}, 'channel': {}, 'sections': {},
            'materials': [{'name': '集体案专用材料'}],
            'templates': [{'id': 'collective-application', 'case_scope': 'collective', 'can_generate': True,
                           'official_kind': 'blank', 'document_types': ['application'], 'region_code': '440303',
                           'file': 'collective.docx', 'sha256': '1' * 64, 'original_name': 'collective.docx'}],
        })
        self.params = {**self.region, 'source_id': source['source_id'], 'version': source['version'],
                       'template_id': 'collective-application', 'kind': 'application'}
        app = FastAPI()
        app.include_router(routes.router)
        self.enterContext(patch.object(routes, 'store', return_value=store))
        self.client = self.enterContext(TestClient(app, raise_server_exceptions=False))

    def test_lookup_only_projects_collective_materials_after_selection(self):
        ordinary = self.client.get('/lookup', params=self.region)
        self.assertEqual(ordinary.status_code, 200)
        self.assertEqual(ordinary.json()['case_scopes'], ['collective'])
        self.assertEqual(ordinary.json()['materials'], [])
        self.assertEqual(ordinary.json()['templates'], [])
        collective = self.client.get('/lookup', params={**self.region, 'case_scope': 'collective'})
        self.assertEqual(collective.json()['case_scope'], 'collective')
        self.assertEqual([t['id'] for t in collective.json()['templates']], ['collective-application'])
        self.assertEqual(collective.json()['materials'][0]['name'], '集体案专用材料')

    def test_unselected_scope_fails_before_contract_layout_and_generation_access(self):
        with patch.object(routes, 'current_form_contract') as contract, \
                patch.object(routes, 'checked_path') as layout, \
                patch.object(routes, 'validate_generation_request') as generate:
            form = self.client.get('/form-contract', params=self.params)
            self.assertEqual(form.status_code, 409)
            blank = self.client.get('/templates/collective-application', params=self.params)
            self.assertIn(blank.status_code, (404, 409))
            response = self.client.post('/generate', json={**self.params, 'mode': 'blank', 'data': {}})
            self.assertEqual(response.status_code, 409)
            contract.assert_not_called()
            layout.assert_not_called()
            generate.assert_not_called()


    def test_actual_luohu_selected_contract_download_and_generation(self):
        from regional_luohu_collective import staged_guide
        root = Path(__file__).resolve().parents[2]
        store = RegionalStore(self.work / 'luohu.sqlite')
        guide = store.put_guide(staged_guide(root))
        selected = {**self.region, 'case_scope': 'collective'}
        with patch.object(routes, 'ROOT', root), patch.object(routes, 'store', return_value=store):
            result = self.client.get('/lookup', params=selected).json()
            self.assertEqual(len(result['templates']), 2)
            for template in result['templates']:
                kind, = template['document_types']
                query = {**selected, 'source_id': guide['source_id'], 'version': guide['version'],
                         'template_id': template['id'], 'kind': kind}
                response = self.client.get('/form-contract', params=query)
                self.assertEqual(response.status_code, 200, response.text)
                contract = response.json()
                self.assertEqual(contract['context']['case_scope'], 'collective')
                blank = self.client.get('/templates/' + template['id'], params=query)
                self.assertEqual(blank.status_code, 200)
                self.assertEqual(blank.headers['X-Document-Origin'], 'official-blank-converted-layout')
                self.assertEqual(blank.content, (root / template['file']).read_bytes())
                payload = {**query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': contract['defaults']}
                generated = self.client.post('/generate', json=payload)
                self.assertEqual(generated.status_code, 200)
                self.assertEqual(generated.headers['X-Document-Origin'], 'official-blank-converted-filled')
                self.assertEqual(generated.headers['X-Form-Contract-ID'], contract['contract_id'])
                self.assertEqual(self.client.post('/generate', json={k: v for k, v in payload.items()
                                                                    if k != 'case_scope'}).status_code, 409)
                self.assertEqual(self.client.post('/generate', json={**payload, 'district': '福田区'}).status_code, 409)

    def test_actual_directory_row_labels_collective_capability_separately(self):
        from regional_luohu_collective import staged_guide
        root = Path(__file__).resolve().parents[2]
        directory = DirectoryStore(self.work / 'directory.sqlite')
        catalog = json.loads((root / 'data/public-regions/directory.json').read_bytes())
        row = next(item for item in catalog if item['code'] == '440303' and item['provider'] == 'national')
        directory.put_area(row)
        store = RegionalStore(self.work / 'luohu-directory.sqlite')
        guide = store.put_guide(staged_guide(root))
        with patch.object(routes, 'store', return_value=store), patch.object(routes, 'directory_store', return_value=directory):
            response = self.client.get('/areas', params={'province': 'guangdong', 'city': '深圳市'})
            self.assertEqual(response.status_code, 200)
            selected, = response.json()['items']
            self.assertEqual(selected['district'], guide['district'])
            self.assertEqual(selected['source_id'], guide['source_id'])
            self.assertFalse(selected['can_generate'])
            self.assertEqual(selected['case_scopes'], ['collective'])
