"""The investment zone must only generate from its separately observed files."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes
import regional_quanzhou_next4 as own


ROOT = Path(__file__).resolve().parents[2]
CODE = '350599'
SOURCE_ID = 'cf089c0b9ee9b764b564e269'
REGION = {'province': 'fujian', 'city': '泉州市', 'district': '台商投资区'}
SOURCE = ROOT / 'reports/overnight-gap-closure-20261030/localities/quanzhou-investment-zone-own-source'
SOURCE_VERSION = '297b56b936b8c43d5598c4fc115c26b881936d21fcd3da08722523ca74319fc2'


class InvestmentCandidateTests(TestCase):
    def test_candidate_contracts_and_downloads_use_exact_investment_zone_lineage(self):
        source = own.production_source(CODE, root=ROOT)
        self.assertEqual(source['source_id'], SOURCE_ID)
        self.assertEqual(source['source_version'], SOURCE_VERSION)
        self.assertEqual(source['authority'], '泉州台商投资区管理委员会民生保障局')
        self.assertEqual(source['channel']['handling_form_raw'], '窗口办，网上办，邮寄办')
        self.assertEqual(source['channel']['depth_raw'], '材料预审（Ⅱ级）')
        self.assertIsNone(source['channel']['entry_url'])
        self.assertFalse(source['can_generate'])

        receipt = json.loads((SOURCE / 'WORD-PREFLIGHT.json').read_bytes())['records']
        expected = {(row['kind'], row['case']): row for row in receipt}
        candidate = own.staged_candidate(CODE, root=ROOT)
        with TemporaryDirectory(prefix='qz-investment-candidate-') as folder:
            store = RegionalStore(Path(folder) / 'guides.sqlite')
            store.put_guide(candidate)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.dict('os.environ', {'LABOURLAWYER_DATA_DIR': folder}), TestClient(app) as client:
                response = client.get('/regional/lookup', params=REGION)
                self.assertEqual(response.status_code, 200)
                guide = response.json()
                self.assertFalse(guide['published'])
                self.assertEqual(len(guide['materials']), 3)
                self.assertEqual(len(guide['templates']), 6)
                eligible = {t['eligible_own_kind']: t for t in guide['templates'] if t['can_generate']}
                self.assertEqual(set(eligible), {'application', 'evidence'})
                for kind, template in eligible.items():
                    with self.subTest(kind=kind):
                        query = {**REGION, 'source_id': SOURCE_ID, 'version': guide['version'],
                                 'kind': kind, 'template_id': template['id']}
                        response = client.get('/regional/form-contract', params=query)
                        self.assertEqual(response.status_code, 200, response.text)
                        contract = response.json()
                        self.assertEqual(contract['context']['source_version'], SOURCE_VERSION)
                        self.assertEqual(template['id'], expected[kind, 'original']['attachment_id'])
                        response = client.get(f"/regional/templates/{template['id']}", params=query)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(sha256(response.content).hexdigest(), expected[kind, 'original']['sha256'])
                        for case in ('original', 'normal', 'stress'):
                            fixture = ROOT / own.FIXTURES / f'350521-{kind}-{case}.json'
                            data = contract['defaults'] if case == 'original' else json.loads(fixture.read_bytes())['data']
                            payload = {**query, 'mode': 'blank', 'data': data, 'contract_id': contract['contract_id']}
                            response = client.post('/regional/generate', json=payload)
                            self.assertEqual(response.status_code, 200, response.text if not response.is_success else '')
                            self.assertEqual(response.headers['X-Guide-Source-ID'], SOURCE_ID)
                            self.assertEqual(sha256(response.content).hexdigest(), expected[kind, case]['sha256'])
                        other = own.staged_candidate('350526', root=ROOT)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'source_id': other['source_id']}).status_code, 409)
                        foreign = next(t['id'] for t in other['templates'] if t['eligible_own_kind'] == kind)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'template_id': foreign}).status_code, 409)
                        for sample in (t for t in guide['templates'] if not t['can_generate']):
                            bad = {**query, 'template_id': sample['id']}
                            self.assertEqual(client.get('/regional/form-contract', params=bad).status_code, 409)

    def test_previous_publication_and_tampered_preflight_do_not_authorize_investment_zone(self):
        staged = own.staged_candidate(CODE, root=ROOT)
        self.assertTrue(staged['can_generate'])
        self.assertFalse(staged['published'])
        with self.assertRaises(ValueError):
            own.published_guide(CODE, root=ROOT)
        dehua = own.published_guide('350526', root=ROOT)
        forged = {**staged, 'published': True, 'publication_adapter_evidence': dehua['publication_adapter_evidence']}
        with self.assertRaises(ValueError):
            own.with_capabilities(forged, root=ROOT)

        read = own._read
        def tampered(root, name):
            value = read(root, name)
            return value + b' ' if 'investment-zone' in name and name.endswith('/WORD-PREFLIGHT.json') else value

        with patch.object(own, '_read', side_effect=tampered), self.assertRaises(ValueError):
            own.staged_candidate(CODE, root=ROOT)

    def test_economic_zone_stays_unverified_without_an_own_source(self):
        with self.assertRaises(ValueError):
            own.production_source('350598', root=ROOT)
        with self.assertRaises(ValueError):
            own.staged_candidate('350598', root=ROOT)
