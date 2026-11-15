"""Exact Tongchuan worker guides must keep their own materials and sample status."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
