"""The Chenggu duplicate sample must stay outside download and generation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class ChengguOwnGuideApiTests(TestCase):
    def test_chenggu_duplicate_application_sample_does_not_register_as_blank(self):
        from regional_chenggu_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide['city'], guide['district'], guide['region_code']), ('汉中市', '城固县', '610722'))
        self.assertTrue(guide['source_url'].startswith('https://zwfw.hanzhong.gov.cn/chengguxian/'))
        self.assertEqual(len(guide['materials']), 3)
        self.assertIn('空表与样表入口返回同一份样本', ' '.join(guide['warnings']))
        self.assertIn('委托书空表已取得', ' '.join(guide['warnings']))
        sample, = guide['templates']
        self.assertEqual(sample['official_kind'], 'sample')
        self.assertEqual(sample['download_status'], 'official_link_only')
        self.assertFalse(sample['can_generate'])
        self.assertFalse(guide['can_generate'])
        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            stored = store.put_guide(guide)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                scope = {key: stored[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
                self.assertEqual(client.get(f"/regional/templates/{sample['id']}", params=scope).status_code, 404)
                query = {**scope, 'template_id': sample['id'], 'kind': 'application'}
                self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                self.assertEqual(client.post('/regional/generate', json={**query, 'mode':'blank', 'data':{}}).status_code, 409)


    def test_verified_county_authorization_exposes_only_official_download_entry(self):
        from regional_chenggu_guides import staged_authorization_guide, staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guides.sqlite')
            previous = store.put_guide(staged_guide(ROOT))
            current = store.put_guide(staged_authorization_guide(ROOT))
            self.assertGreater(current['version'], previous['version'])
            self.assertEqual(current['source_id'], previous['source_id'])
            self.assertEqual(current['templates'][0], previous['templates'][0])
            self.assertEqual(current['materials'], previous['materials'])
            self.assertFalse(current['can_generate'])
            blank, = [template for template in current['templates'] if template['official_kind'] == 'blank']
            self.assertEqual(blank['region_code'], '610722')
            self.assertEqual(blank['source_url'], current['source_url'])
            self.assertEqual(blank['official_sha256'], '4980f6ba4e4eb3ca915ae1ff73a374fbb593cd673eae73bd15bf8b125a597f56')
            self.assertEqual(blank['download_status'], 'official_link_only')
            self.assertFalse(blank['can_generate'])
            self.assertNotIn('file', blank)
            scope = {key: current[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                endpoint = f"/regional/templates/{blank['id']}"
                self.assertEqual(client.get(endpoint, params=scope).status_code, 404)
                self.assertEqual(client.get(endpoint, params={**scope, 'version': previous['version']}).status_code, 409)
                query = {**scope, 'template_id': blank['id'], 'kind': 'application'}
                self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                self.assertEqual(client.post('/regional/generate', json={**query, 'mode': 'blank', 'data': {}}).status_code, 409)
