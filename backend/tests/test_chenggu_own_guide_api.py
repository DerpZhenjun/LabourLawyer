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
