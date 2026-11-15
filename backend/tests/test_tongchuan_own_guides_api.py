"""Exact Tongchuan worker guides must keep their own materials and sample status."""
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


class TongchuanOwnGuidesApiTests(TestCase):
    def test_districts_keep_distinct_material_lists_and_sample_links(self):
        from regional_tongchuan_guides import staged_guide

        for code in ('610200', '610222', '610302'):
            with self.assertRaises(ValueError):
                staged_guide(code, ROOT)

        cases = {
            '610202': ('王益区', '689dd51baa349bf71db04b138d3ef7b3', 5),
            '610203': ('印台区', '5e6d7905330bbcd63f2b56d1d613028d', 4),
            '610204': ('耀州区', '6bec09fd771fc7977881001a14bb7c0a', 2),
        }
        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, (district, source_code, material_count) in cases.items():
                    with self.subTest(district=district):
                        stored = store.put_guide(staged_guide(code, ROOT))
                        scope = {'province': 'shaanxi', 'city': '铜川市', 'district': district}
                        response = client.get('/regional/lookup', params=scope)
                        self.assertEqual(response.status_code, 200)
                        guide = response.json()
                        self.assertEqual(guide['region_code'], code)
                        self.assertIn(source_code, guide['source_url'])
                        self.assertFalse(guide['can_generate'])
                        if code == '610203':
                            self.assertIn('第二十八条', ' '.join(guide['warnings']))
                        if code == '610204':
                            self.assertIn('内容和版式仍在核验', ' '.join(guide['warnings']))
                        self.assertEqual(len(guide['materials']), material_count)
                        self.assertTrue(all(
                            material['region_code'] == code and material['source_url'] == guide['source_url']
                            for material in guide['materials']
                        ))
                        template, = guide['templates']
                        self.assertEqual(template['official_kind'], 'sample')
                        self.assertEqual(template['download_status'], 'official_link_only')
                        self.assertEqual(template['source_url'], guide['source_url'])
                        for district_query in (scope, {**scope, 'district': '市本级'}, {**scope, 'district': '渭滨区'}):
                            url = f"/regional/templates/{template['id']}"
                            self.assertEqual(client.get(url, params=district_query).status_code, 404)
                        scope.update(source_id=stored['source_id'], version=stored['version'], template_id=template['id'])
                        for kind in ('application', 'evidence'):
                            query = {**scope, 'kind': kind}
                            self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                            self.assertEqual(client.post('/regional/generate', json={**query, 'mode': 'blank', 'data': {}}).status_code, 409)


    def test_yaozhou_blank_authorization_preserves_official_source_without_enabling_generation(self):
        from regional_tongchuan_guides import staged_guide, staged_yaozhou_authorization_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            previous = store.put_guide(staged_guide('610204', ROOT))
            current = store.put_guide(staged_yaozhou_authorization_guide(ROOT))
            self.assertGreater(current['version'], previous['version'])
            self.assertEqual(current['source_id'], previous['source_id'])
            self.assertEqual(current['templates'][0], previous['templates'][0])
            self.assertEqual(current['materials'], previous['materials'])
            self.assertNotIn('内容和版式仍在核验', ' '.join(current['warnings']))
            template, = [item for item in current['templates'] if item['official_kind'] == 'blank']
            self.assertEqual(template['region_code'], '610204')
            self.assertEqual(template['source_url'], current['source_url'])
            self.assertEqual(template['official_attachment_entry'], 'material_tab')
            self.assertEqual(template['download_status'], 'official_link_only')
            self.assertEqual(template['official_sha256'], '128837098459c5677e2ecb0929ab833645224946264344218f9ffb2a19e923fd')
            self.assertNotIn('file', template)
            self.assertFalse(template['can_generate'])
            self.assertFalse(current['can_generate'])
            scope = {key: current[key] for key in ('province', 'city', 'district')}
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                valid = {**scope, 'source_id': current['source_id'], 'version': current['version']}
                route = f"/regional/templates/{template['id']}"
                self.assertEqual(client.get(route, params=valid).status_code, 404)
                self.assertEqual(client.get(route, params={**valid, 'version': previous['version']}).status_code, 409)
                self.assertEqual(client.get(route, params={**scope, 'district': '印台区'}).status_code, 404)
                query = {**valid, 'template_id': template['id'], 'kind': 'application'}
                self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                self.assertEqual(client.post('/regional/generate', json={**query, 'mode':'blank', 'data':{}}).status_code, 409)


    def test_municipal_source_exposes_only_the_city_selection_and_preserves_county_boundaries(self):
        from regional_tongchuan_guides import staged_municipal_guide

        scope = {'province': 'shaanxi', 'city': '铜川市'}
        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            directory = DirectoryStore(Path(work) / 'directory.sqlite')
            rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
            for row in rows:
                if row['code'] in {'610200', '610222'}:
                    directory.put_area(row)
            guide = store.put_guide(staged_municipal_guide(ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), patch.object(
                routes, 'directory_store', return_value=directory
            ), TestClient(app) as client:
                areas = client.get('/regional/areas', params=scope).json()['items']
                self.assertEqual([(row['district'], row['can_generate']) for row in areas], [('市本级', False), ('宜君县', False)])
                retrieved = client.get('/regional/lookup', params={**scope, 'district': '市本级'}).json()
                self.assertEqual(retrieved['source_id'], guide['source_id'])
                self.assertEqual(retrieved['fields']['咨询方式'], '0919-3185664')
                self.assertEqual(len(retrieved['materials']), 4)
                self.assertTrue(all(row['region_code'] == '610200' for row in retrieved['materials']))
                self.assertEqual(retrieved['templates'], [])
                self.assertNotIn('宜君县', json.dumps(retrieved, ensure_ascii=False))
                county = client.get('/regional/lookup', params={**scope, 'district': '宜君县'}).json()
                self.assertIsNone(county['source_id'])
                self.assertEqual(county['materials'], [])
                query = {**scope, 'district':'市本级', 'source_id':guide['source_id'], 'version':guide['version'],
                         'template_id':'unverified', 'kind':'application'}
                self.assertEqual(client.post('/regional/generate', json={**query, 'mode':'blank', 'data':{}}).status_code, 409)
                store.put_guide({**guide, 'source_version': '0' * 64})
                altered = client.get('/regional/areas', params=scope).json()['items']
                self.assertEqual([row['district'] for row in altered], ['宜君县'])
