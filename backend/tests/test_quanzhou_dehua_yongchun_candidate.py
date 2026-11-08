"""Candidate API must bind Dehua and Yongchun to their own public originals."""
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
RECEIPT = ROOT / 'reports/overnight-gap-closure-20261030/localities/quanzhou-dehua-yongchun-own-source/WORD-PREFLIGHT.json'
CASES = {
    '350526': ('德化县', '286f2f5801a4ad101b464ff7', '983353486646af7070909393be75730aa7de42a127dec79e464695878f4605da'),
    '350525': ('永春县', 'dce92327ed30b9ea92994e08', 'c535d2d00bb7e8a47dfad8d0c368774e607ac4897bd20cfaf04b55d7c162fb30'),
}


class DehuaYongchunCandidateTests(TestCase):
    def test_own_four_contracts_and_twelve_generation_results(self):
        rows = json.loads(RECEIPT.read_bytes())['records']
        expected = {(r['region_code'], r['kind'], r['case']): r for r in rows}
        contract_ids = set()
        with TemporaryDirectory(prefix='qz-dy-candidate-') as folder:
            store = RegionalStore(Path(folder) / 'guides.sqlite')
            for code in CASES:
                store.put_guide(own.staged_candidate(code, root=ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), patch.dict('os.environ', {'LABOURLAWYER_DATA_DIR': folder}), TestClient(app) as client:
                for code, (district, sid, source_version) in CASES.items():
                    region = {'province': 'fujian', 'city': '泉州市', 'district': district}
                    lookup = client.get('/regional/lookup', params=region)
                    self.assertEqual(lookup.status_code, 200)
                    guide = lookup.json()
                    self.assertEqual(guide['source_id'], sid)
                    self.assertFalse(guide['published'])
                    self.assertIsNone(guide['channel']['entry_url'])
                    self.assertEqual(len(guide['materials']), 3)
                    eligible = {t['eligible_own_kind']: t for t in guide['templates'] if t['can_generate']}
                    self.assertEqual(set(eligible), {'application', 'evidence'})
                    for kind, template in eligible.items():
                        query = {**region, 'source_id': sid, 'version': guide['version'],
                                 'kind': kind, 'template_id': template['id']}
                        response = client.get('/regional/form-contract', params=query)
                        self.assertEqual(response.status_code, 200, response.text)
                        contract = response.json()
                        contract_ids.add(contract['contract_id'])
                        self.assertEqual(len(contract['context']), 15)
                        self.assertEqual(contract['context']['source_version'], source_version)
                        original = expected[code, kind, 'original']
                        self.assertEqual(original['attachment_id'], template['id'])
                        download = client.get(f"/regional/templates/{template['id']}", params=query)
                        self.assertEqual(download.status_code, 200)
                        self.assertEqual(sha256(download.content).hexdigest(), original['sha256'])
                        for case in ('original', 'normal', 'stress'):
                            if case == 'original':
                                data = contract['defaults']
                            else:
                                fixture = ROOT / own.FIXTURES / f'350521-{kind}-{case}.json'
                                data = json.loads(fixture.read_bytes())['data']
                            payload = {**query, 'mode': 'blank', 'data': data, 'contract_id': contract['contract_id']}
                            generation = client.post('/regional/generate', json=payload)
                            self.assertEqual(generation.status_code, 200, generation.text if not generation.is_success else '')
                            self.assertEqual(generation.headers['X-Guide-Source-ID'], sid)
                            self.assertEqual(sha256(generation.content).hexdigest(), expected[code, kind, case]['sha256'])
                        other = next(value for value in CASES.values() if value[1] != sid)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'source_id': other[1]}).status_code, 409)
                        other_code = next(value for value in CASES if value != code)
                        other_id = expected[other_code, kind, 'original']['attachment_id']
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'template_id': other_id}).status_code, 409)
                        missing_contract = {key: value for key, value in payload.items() if key != 'contract_id'}
                        self.assertEqual(client.post('/regional/generate', json=missing_contract).status_code, 409)
                        samples = [t for t in guide['templates'] if t['official_role'] == '示范文本']
                        for sample in samples:
                            self.assertEqual(client.get('/regional/form-contract', params={**query, 'template_id': sample['id']}).status_code, 409)
        self.assertEqual(len(contract_ids), 4)

    def test_no_release_or_fallback_from_old_batch_or_tampered_word_proof(self):
        for code in CASES:
            source = own.production_source(code, root=ROOT)
            self.assertFalse(source['can_generate'])
            with patch.object(own, 'DY_PUBLICATION_SHA256', None), self.assertRaises(ValueError):
                own.published_guide(code, root=ROOT)
            with self.assertRaises(ValueError):
                own.with_capabilities({**source, 'can_generate': True}, root=ROOT)
            staged = own.staged_candidate(code, root=ROOT)
            with self.assertRaises(ValueError):
                own.with_capabilities({**staged, 'published': True}, root=ROOT)
            original_read = own._read
            def tamper(root, name):
                content = original_read(root, name)
                return content + b' ' if name.endswith('/WORD-PREFLIGHT.json') else content
            with patch.object(own, '_read', side_effect=tamper), self.assertRaises(ValueError):
                own.staged_candidate(code, root=ROOT)

    def test_published_guide_requires_its_own_review_and_browser_receipts(self):
        for code, (_, sid, _) in CASES.items():
            with self.subTest(region=code):
                approved = own.published_guide(code, root=ROOT)
                self.assertTrue(approved['published'])
                self.assertEqual(approved['source_id'], sid)
                self.assertEqual(approved['publication_adapter_evidence']['sha256'], own.DY_PUBLICATION_SHA256)
                self.assertEqual(routes.release_capabilities()['locality_publication_receipts'][code],
                                 own.DY_PUBLICATION_SHA256)
                self.assertEqual(sum(t['can_generate'] for t in approved['templates']), 2)
                with patch.object(own, 'DY_PUBLICATION_SHA256', own.PUBLICATION_SHA256), self.assertRaises(ValueError):
                    own.published_guide(code, root=ROOT)
                for name in (own.DY_PUBLICATION_RECEIPT, own.DY_BROWSER_RECEIPT):
                    read = own._read
                    with patch.object(own, '_read', side_effect=lambda root, file: read(root, file) + (b' ' if file == name else b'')):
                        with self.assertRaises(ValueError):
                            own.published_guide(code, root=ROOT)
