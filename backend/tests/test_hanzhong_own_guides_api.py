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


ROOT = Path(__file__).resolve().parents[2]
BASE = {'province': 'shaanxi', 'city': '汉中市'}
MATERIALS = ['劳动人事争议仲裁申请书', '授权委托书', '劳动（人事）关系证明材料', '身份证']


class HanzhongOwnGuidesApiTests(TestCase):
    def test_exact_sources_keep_municipal_and_district_materials_separate(self):
        from regional_hanzhong_guides import staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            directory = DirectoryStore(Path(work) / 'directory.sqlite')
            rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
            for row in rows:
                if row['code'] in {'610700', '610702', '610703'}:
                    directory.put_area(row)

            municipal = store.put_guide(staged_guide('610700', ROOT))
            district = store.put_guide(staged_guide('610702', ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), patch.object(
                routes, 'directory_store', return_value=directory,
            ), TestClient(app) as client:
                areas = client.get('/regional/areas', params=BASE).json()['items']
                self.assertEqual(areas[0]['district'], '市本级')
                self.assertEqual(areas[0]['source_id'], municipal['source_id'])
                neighboring_area = next(row for row in areas if row['district'] == '南郑区')
                self.assertIsNone(neighboring_area['source_id'])

                for draft, method, certain, copies, phone, online in [
                    (municipal, '网上办理', '非必要', '复印件1份', '0916-2626620', 'unverified'),
                    (district, '窗口办理', '必要', '复印件2份', '0916-2214767', 'unavailable'),
                ]:
                    scope = {**BASE, 'district': draft['district']}
                    guide = client.get('/regional/lookup', params=scope).json()
                    self.assertEqual(guide['source_id'], draft['source_id'])
                    self.assertEqual(guide['fields']['办理形式'], method)
                    self.assertEqual(guide['fields']['咨询方式'], phone)
                    self.assertEqual(guide['channel']['online_status'], online)
                    self.assertFalse(guide['channel']['submission_verified'])
                    self.assertEqual([material['name'] for material in guide['materials']], MATERIALS)
                    self.assertEqual(guide['materials'][1]['required'], certain)
                    self.assertEqual(guide['materials'][3]['copies'], copies)
                    self.assertTrue(all(
                        (m['region_code'], m['source_url']) == (guide['region_code'], guide['source_url'])
                        for m in guide['materials']
                    ))
                    self.assertFalse(guide['can_generate'])
                    self.assertEqual(
                        [template['official_kind'] for template in guide['templates']],
                        ['sample', 'sample', 'blank'],
                    )
                    versioned = {**scope, 'source_id': guide['source_id'], 'version': guide['version']}
                    for template in guide['templates']:
                        self.assertEqual(template['source_url'], guide['source_url'])
                        self.assertEqual(template['region_code'], guide['region_code'])
                        self.assertFalse(template['can_generate'])
                        self.assertNotIn('file', template)
                        self.assertEqual(client.get(
                            f"/regional/templates/{template['id']}", params=versioned,
                        ).status_code, 404)
                    query = {**versioned, 'kind': 'application', 'template_id': guide['templates'][0]['id']}
                    self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                    self.assertEqual(client.post(
                        '/regional/generate', json={**query, 'mode': 'blank', 'data': {}},
                    ).status_code, 409)

                self.assertNotEqual(municipal['source_id'], district['source_id'])
                self.assertNotEqual(
                    municipal['templates'][-1]['official_sha256'], district['templates'][-1]['official_sha256'],
                )
                neighboring = client.get('/regional/lookup', params={**BASE, 'district': '南郑区'}).json()
                self.assertIsNone(neighboring['source_id'])
                self.assertEqual(neighboring['materials'], [])
                store.put_guide({**municipal, 'source_version': '0' * 64})
                areas = client.get('/regional/areas', params=BASE).json()['items']
                self.assertNotIn('市本级', [row['district'] for row in areas])
