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
    def test_official_wide_space_directory_labels_reach_verified_county_guides(self):
        from regional_hanzhong_guides import staged_guide

        with TemporaryDirectory() as work:
            directory = DirectoryStore(Path(work) / 'directory.sqlite')
            store = RegionalStore(Path(work) / 'guides.sqlite')
            entries = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
            for row in entries:
                if row['code'] in {'610723', '610725'}:
                    directory.put_area(row)
                    store.put_guide(staged_guide(row['code'], ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'store', return_value=store), patch.object(
                routes, 'directory_store', return_value=directory,
            ), TestClient(app) as client:
                items = client.get('/regional/areas', params=BASE).json()['items']
                expected = {'610723': ('洋县', '洋　县'), '610725': ('勉县', '勉　县')}
                self.assertEqual(len(items), len(expected))
                for item in items:
                    district, original = expected[item['code']]
                    self.assertEqual((item['district'], item['official_name']), (district, original))
                    self.assertEqual(item['raw_record']['regionName'], original)
                    self.assertIsNotNone(item['source_id'])
                    guide = client.get('/regional/lookup', params={**BASE, 'district': item['district']}).json()
                    self.assertEqual(guide['source_id'], item['source_id'])
                    self.assertEqual(guide['region_code'], item['code'])

    def test_ningqiang_and_lueyang_keep_their_own_materials_and_sample_modes(self):
        from regional_hanzhong_guides import staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            store.put_guide(staged_guide('610700', ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, county, names, copies, period, phone in [
                    ('610726', '宁强县', [MATERIALS[0], MATERIALS[3], MATERIALS[1]], '原件1份', '2 工作日', '0916-4221648'),
                    ('610727', '略阳县', [MATERIALS[0], MATERIALS[3], MATERIALS[2], MATERIALS[1], '外国人就业证'],
                     '原件2份\xa0 复印件2份', '5 工作日', '0916-4827378'),
                ]:
                    guide = store.put_guide(staged_guide(code, ROOT))
                    scope = {**BASE, 'district': county}
                    fetched = client.get('/regional/lookup', params=scope).json()
                    self.assertEqual(fetched['source_id'], guide['source_id'])
                    self.assertEqual(fetched['fields']['承诺办结时限'], period)
                    self.assertEqual(fetched['fields']['咨询方式'], phone)
                    self.assertEqual([item['name'] for item in fetched['materials']], names)
                    self.assertEqual(fetched['materials'][0]['copies'], copies)
                    self.assertTrue(all(item['region_code'] == code for item in fetched['materials']))
                    self.assertFalse(fetched['can_generate'])
                    self.assertEqual(
                        [template['official_kind'] for template in fetched['templates']],
                        ['sample', 'sample'] if code == '610726' else ['unverified', 'unverified'],
                    )
                    for template in fetched['templates']:
                        self.assertEqual(template['source_url'], guide['source_url'])
                        self.assertEqual(template['region_code'], code)
                        self.assertFalse(template['can_generate'])
                        self.assertEqual('official_sha256' in template, code == '610726')
                        binding = {**scope, 'source_id': guide['source_id'], 'version': guide['version']}
                        self.assertEqual(client.get(
                            f"/regional/templates/{template['id']}", params=binding,
                        ).status_code, 404)
                neighbor = client.get('/regional/lookup', params={**BASE, 'district': '镇巴县'}).json()
                self.assertIsNone(neighbor['source_id'])
                self.assertEqual(neighbor['templates'], [])

    def test_yangxian_and_xixiang_preserve_separate_sample_and_guide_sources(self):
        from regional_hanzhong_guides import staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, county, method_limit, phone, application_copies, file_type in [
                    ('610723', '洋县', '1 工作日', '0916-2938727', '原件1份\xa0 复印件2份', 'jpg'),
                    ('610724', '西乡县', '0 工作日', '0916-6217683', '原件2份', 'docx'),
                ]:
                    stored = store.put_guide(staged_guide(code, ROOT))
                    scope = {**BASE, 'district': county}
                    guide = client.get('/regional/lookup', params=scope).json()
                    self.assertEqual(guide['source_id'], stored['source_id'])
                    self.assertEqual(guide['fields']['承诺办结时限'], method_limit)
                    self.assertEqual(guide['fields']['咨询方式'], phone)
                    self.assertEqual(len(guide['materials']), 5)
                    self.assertEqual(guide['materials'][0]['copies'], application_copies)
                    self.assertEqual(guide['materials'][0]['region_code'], code)
                    self.assertEqual([t['official_kind'] for t in guide['templates']], ['sample', 'sample'])
                    application = guide['templates'][0]
                    self.assertEqual(application['file_type'], file_type)
                    self.assertEqual(application['source_url'], guide['source_url'])
                    self.assertEqual(application['region_code'], code)
                    self.assertFalse(application['can_generate'])
                    query = {**scope, 'source_id': guide['source_id'], 'version': guide['version'],
                             'kind': 'application', 'template_id': application['id']}
                    self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                neighbor = client.get('/regional/lookup', params={**BASE, 'district': '宁强县'}).json()
                self.assertIsNone(neighbor['source_id'])
                self.assertEqual(neighbor['templates'], [])

    def test_nanzheng_and_mianxian_use_their_own_attachment_and_material_bindings(self):
        from regional_hanzhong_guides import staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            store.put_guide(staged_guide('610700', ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, district, names, period, method in [
                    ('610703', '南郑区', [MATERIALS[0], MATERIALS[3], MATERIALS[1]], '1 工作日', '窗口办理'),
                    ('610725', '勉县', ['外国人就业证', MATERIALS[3], MATERIALS[1], MATERIALS[2], MATERIALS[0]],
                     '5 工作日', '网上办理'),
                ]:
                    stored = store.put_guide(staged_guide(code, ROOT))
                    scope = {**BASE, 'district': district}
                    guide = client.get('/regional/lookup', params=scope).json()
                    self.assertEqual(guide['source_id'], stored['source_id'])
                    self.assertEqual(guide['fields']['承诺办结时限'], period)
                    self.assertEqual(guide['fields']['办理形式'], method)
                    self.assertEqual([row['name'] for row in guide['materials']], names)
                    self.assertTrue(all(row['region_code'] == code for row in guide['materials']))
                    expected_kinds = ['sample', 'blank'] if code == '610703' else ['sample']
                    self.assertEqual([template['official_kind'] for template in guide['templates']], expected_kinds)
                    self.assertTrue(all(template['download_status'] == 'official_link_only' for template in guide['templates']))
                    application = guide['templates'][0]
                    self.assertEqual(application['official_kind'], 'sample')
                    self.assertEqual(application['source_url'], guide['source_url'])
                    self.assertEqual(application['region_code'], code)
                    self.assertFalse(guide['can_generate'])
                    self.assertFalse(application['can_generate'])
                    query = {**scope, 'source_id': guide['source_id'], 'version': guide['version'],
                             'kind': 'application', 'template_id': application['id']}
                    self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                neighbor = client.get('/regional/lookup', params={**BASE, 'district': '西乡县'}).json()
                self.assertIsNone(neighbor['source_id'])
                self.assertEqual(neighbor['templates'], [])

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
