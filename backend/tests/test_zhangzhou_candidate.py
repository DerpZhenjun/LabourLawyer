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


class PingheCandidateTests(_ZhangzhouCandidateChecks, TestCase):
    code = '350628'
    source_id = '1c435a8e909867d2119efe16'
    source_version = '798eba503cadb717fb74727aaff074c1389a69feed03c577f63642325f36c70d'
    authority = '平和县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '平和县'}
    source_folder = 'zhangzhou-four-own-source/350628'
    foreign_code = '350625'


class ChangtaiCandidateTests(_ZhangzhouCandidateChecks, TestCase):
    code = '350625'
    source_id = '2ea92c5adb81421b892f2994'
    source_version = '74786aec7221088ada6a7923a38e13b9d74cb9ba042ac877db57211e35f3ae50'
    authority = '漳州市长泰区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '长泰区'}
    source_folder = 'zhangzhou-four-own-source/350625'
    foreign_code = '350628'


class ZhangpuCandidateTests(_ZhangzhouCandidateChecks, TestCase):
    code = '350623'
    source_id = '48e65b2c27fc105366706caa'
    source_version = 'de8110bb1a971d508bffb8d94c8545d5bef504dee090b55955736105f7ac91ac'
    authority = '漳浦县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '漳浦县'}
    source_folder = 'zhangzhou-four-own-source/350623'
    foreign_code = '350628'


class HuaanCandidateTests(_ZhangzhouCandidateChecks, TestCase):
    code = '350629'
    source_id = 'd61089df6a682a0affd5d18c'
    source_version = 'd21b0110552ff1568fe6a7b7049faf9df6939f55f651d24191f8b472d1f3dc44'
    authority = '华安县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '华安县'}
    source_folder = 'zhangzhou-four-own-source/350629'
    foreign_code = '350628'
