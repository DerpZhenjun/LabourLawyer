"""Known Baoji county guides remain source-only until their own templates are verified."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / 'reports/overnight-gap-closure-20261030/localities/baoji-eight-county-source/GUIDES.json'


class BaojiCountySourceTests(TestCase):
    def test_counties_have_distinct_sources_and_never_enable_generation(self):
        self.assertTrue(CANDIDATE.is_file(), 'Missing own-source guide batch')
        guides = json.loads(CANDIDATE.read_bytes())
        self.assertEqual({guide['region_code'] for guide in guides}, {
            '610323', '610324', '610326', '610327', '610328', '610329', '610330', '610331',
        })
        self.assertEqual(len({guide['source_url'] for guide in guides}), len(guides))
        directory = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        identities = {row['code']: row['district'] for row in directory if row.get('city') == '宝鸡市'}
        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            stored = [store.put_guide(guide) for guide in guides]
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for guide in stored:
                    with self.subTest(county=guide['district']):
                        code = guide['region_code']
                        self.assertEqual(guide['district'], identities[code])
                        self.assertEqual(guide['authority'], guide['district'].replace('　', '') + '人力资源和社会保障局')
                        self.assertTrue(all(item['region_code'] == code and item['source_url'] == guide['source_url']
                                            for item in guide['materials']))
                        self.assertFalse(guide['published'])
                        self.assertFalse(guide['can_generate'])
                        self.assertEqual(guide['templates'], [])
                        params = {key: guide[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
                        response = client.get('/regional/lookup', params=params)
                        self.assertEqual(response.json()['source_id'], guide['source_id'])
                        response = client.get('/regional/form-contract', params={
                            **params, 'kind': 'application', 'template_id': 'unverified',
                        })
                        self.assertIn(response.status_code, (404, 409))
                missing = client.get('/regional/lookup', params={
                    'province': 'shaanxi', 'city': '宝鸡市', 'district': '市本级',
                })
                self.assertIsNone(missing.json()['source_id'])
