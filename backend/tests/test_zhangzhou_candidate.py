"""Zhangzhou candidates generate only from separately observed local files."""
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
LOCALITIES = ROOT / 'reports/overnight-gap-closure-20261030/localities'


class _ZhangzhouCandidateChecks:
    def test_candidate_contracts_and_downloads_use_exact_local_lineage(self):
        source = own.production_source(self.code, root=ROOT)
        self.assertEqual(source['source_id'], self.source_id)
        self.assertEqual(source['source_version'], self.source_version)
        self.assertEqual(source['authority'], self.authority)
        self.assertEqual(source['channel']['handling_form_raw'], '窗口办，网上办，邮寄办')
        self.assertEqual(source['channel']['depth_raw'], '材料预审（Ⅱ级）')
        self.assertIsNone(source['channel']['entry_url'])
        self.assertFalse(source['can_generate'])

        receipt = json.loads((LOCALITIES / self.source_folder / 'WORD-PREFLIGHT.json').read_bytes())['records']
        expected = {(row['kind'], row['case']): row for row in receipt}
        candidate = own.staged_candidate(self.code, root=ROOT)
        with TemporaryDirectory(prefix='zz-candidate-') as folder:
            store = RegionalStore(Path(folder) / 'guides.sqlite')
            store.put_guide(candidate)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.dict('os.environ', {'LABOURLAWYER_DATA_DIR': folder}), TestClient(app) as client:
                response = client.get('/regional/lookup', params=self.region)
                self.assertEqual(response.status_code, 200)
                guide = response.json()
                self.assertFalse(guide['published'])
                self.assertEqual(len(guide['materials']), 3)
                self.assertEqual(len(guide['templates']), 6)
                eligible = {t['eligible_own_kind']: t for t in guide['templates'] if t['can_generate']}
                self.assertEqual(set(eligible), {'application', 'evidence'})
                for kind, template in eligible.items():
                    with self.subTest(kind=kind):
                        query = {**self.region, 'source_id': self.source_id, 'version': guide['version'],
                                 'kind': kind, 'template_id': template['id']}
                        response = client.get('/regional/form-contract', params=query)
                        self.assertEqual(response.status_code, 200, response.text)
                        contract = response.json()
                        self.assertEqual(contract['context']['source_version'], self.source_version)
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
                            self.assertEqual(response.headers['X-Guide-Source-ID'], self.source_id)
                            self.assertEqual(sha256(response.content).hexdigest(), expected[kind, case]['sha256'])
                        other = own.staged_candidate(self.foreign_code, root=ROOT)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'source_id': other['source_id']}).status_code, 409)
                        foreign = next(t['id'] for t in other['templates'] if t['eligible_own_kind'] == kind)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'template_id': foreign}).status_code, 409)
                        for sample in (t for t in guide['templates'] if not t['can_generate']):
                            bad = {**query, 'template_id': sample['id']}
                            self.assertEqual(client.get('/regional/form-contract', params=bad).status_code, 409)

    def test_previous_publication_and_tampered_preflight_do_not_authorize_local_candidate(self):
        staged = own.staged_candidate(self.code, root=ROOT)
        self.assertTrue(staged['can_generate'])
        self.assertFalse(staged['published'])
        with self.assertRaises(ValueError):
            own.published_guide(self.code, root=ROOT)
        dehua = own.published_guide('350526', root=ROOT)
        forged = {**staged, 'published': True, 'publication_adapter_evidence': dehua['publication_adapter_evidence']}
        with self.assertRaises(ValueError):
            own.with_capabilities(forged, root=ROOT)

        read = own._read
        def tampered(root, name):
            value = read(root, name)
            return value + b' ' if name == f'{own.LOCALITIES}/{self.source_folder}/WORD-PREFLIGHT.json' else value

        with patch.object(own, '_read', side_effect=tampered), self.assertRaises(ValueError):
            own.staged_candidate(self.code, root=ROOT)


class XiangchengCandidateTests(_ZhangzhouCandidateChecks, TestCase):
    code = '350602'
    source_id = 'f8e8351e86b1c41530f16dec'
    source_version = 'f00f84d5e6ed1a90e7d064760966c36735950d2e734c2fa6493db2186956ab41'
    authority = '漳州市芗城区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '芗城区'}
    source_folder = 'zhangzhou-own-source'
    foreign_code = '350526'


class LonghaiCandidateTests(_ZhangzhouCandidateChecks, TestCase):
    code = '350681'
    source_id = 'ed191bcdf82538767ff7bc25'
    source_version = '60cb15eedb5f3d3fa70c2cd38037c93ab972e3866f530cf9fb65f6c6251bdafc'
    authority = '龙海区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '龙海区'}
    source_folder = 'zhangzhou-longhai-own-source'
    foreign_code = '350602'
