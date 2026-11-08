"""Own Huian/Quangang sources through real isolated ASGI routes; no live data."""
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import json
import os
import shutil
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
import regional_fujian_huian_quangang_nov1 as own
from regional_guides import RegionalStore
from routes import regional_guides as routes

ROOT = Path(__file__).resolve().parents[2]
IDENTITIES = [
    ('350521', '惠安县', '5a2049b6dd7a240d496c29d7'),
    ('350505', '泉港区', '4f9f8144ec2ae19a7f2e70cf'),
]


class HQDispatchTests(unittest.TestCase):
    @contextmanager
    def isolated(self, stage=True):
        with tempfile.TemporaryDirectory(prefix='own-hq-asgi-') as temp:
            root = Path(temp)
            names = set(own.source_files(ROOT))
            if stage:
                names.update(own.approval_files(ROOT))
            for name in names:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            provider = own.staged_candidate if stage else own.prepare_candidate
            store = RegionalStore(root / 'candidate.sqlite')
            for code, _, _ in IDENTITIES:
                store.put_guide(provider(code, root=root))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.dict(os.environ, {'LABOURLAWYER_DATA_DIR': str(root / 'private')}), patch.object(routes, 'ROOT', root), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                yield root, store, client

    def guides(self, store):
        return [store.lookup('fujian', '泉州市', district) for _, district, _ in IDENTITIES]

    def query(self, guide, kind):
        template = next(t for t in guide['templates'] if t['eligible_own_kind'] == kind)
        return {**{k: guide[k] for k in ['province', 'city', 'district', 'source_id', 'version']}, 'template_id': template['id'], 'kind': kind}

    def contract(self, client, guide, kind):
        response = client.get('/regional/form-contract', params=self.query(guide, kind))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_registry_uses_own_request_models_and_real_stage_marker(self):
        from regional_form_contracts import SUPPORTED_ADAPTERS, PUBLIC_PROOF_ADAPTERS
        self.assertIn(own.ADAPTER, SUPPORTED_ADAPTERS)
        self.assertIn(own.ADAPTER, PUBLIC_PROOF_ADAPTERS)
        marker = routes.release_capabilities()
        self.assertEqual(marker['candidate_stage_receipts'][own.ADAPTER], own.STAGE_SHA256)
        self.assertEqual(marker['publication_receipts'][own.ADAPTER], own.PUBLICATION_SHA256)
        self.assertFalse(marker['models_required'])
        for kind in ['application', 'evidence']:
            self.assertEqual(routes.generation_request_model(own.ADAPTER, kind).__module__, 'regional_huian_quangang_request')

    def test_own_sources_and_four_contracts_retain_real_ids_and_version(self):
        with self.isolated() as (_, store, client):
            ids = []
            for guide, (code, district, sid) in zip(self.guides(store), IDENTITIES):
                self.assertEqual((guide['region_code'], guide['district'], guide['source_id']), (code, district, sid))
                self.assertEqual(guide['official_version'], '1')
                self.assertFalse(guide['published'])
                self.assertIsNone(guide['committee_full_name'])
                self.assertFalse(guide['committee_autofill_allowed'])
                self.assertEqual(len(guide['materials']), 3)
                self.assertTrue(all(m['official_material_id'] for m in guide['materials']))
                self.assertEqual(sum(t['can_generate'] for t in guide['templates']), 2)
                self.assertEqual(guide['channel']['raw_value'], '窗口办，网上办，邮寄办')
                self.assertEqual(guide['channel']['online_depth_raw'], '材料预审（Ⅱ级）')
                for kind in ['application', 'evidence']:
                    contract = self.contract(client, guide, kind)
                    ids.append(contract['contract_id'])
                    self.assertEqual(len(contract['context']), 15)
                    self.assertEqual(contract['context']['region_code'], code)
                    self.assertEqual(contract['context']['source_id'], sid)
                    self.assertTrue(all(field['label'] for field in contract['fields']))
                    self.assertFalse(contract['policy']['capacity_is_official_requirement'])
                    if kind == 'evidence':
                        self.assertEqual(len(contract['defaults']['evidenceList']), 1)
            self.assertEqual(len(set(ids)), 4)

    def test_real_routes_return_eight_exact_reviewed_word_files_and_four_originals(self):
        with self.isolated() as (root, store, client):
            for guide in self.guides(store):
                for kind in ['application', 'evidence']:
                    query = self.query(guide, kind)
                    contract = self.contract(client, guide, kind)
                    original = own.original_bytes(guide['region_code'], kind, root=root)
                    fixture = json.loads((root / own.QA_REPORT / 'fixtures' / f"{guide['region_code']}-{kind}-normal.json").read_bytes())
                    filled = (root / own.QA_REPORT / 'word' / f"{guide['region_code']}-{kind}-normal.docx").read_bytes()
                    for data, expected in [(contract['defaults'], original), (fixture['data'], filled)]:
                        response = client.post('/regional/generate', json={**query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': data})
                        self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else '')
                        self.assertEqual(response.content, expected)
                        self.assertEqual(response.headers['x-guide-source-id'], guide['source_id'])
                        self.assertEqual(response.headers['x-guide-version'], str(guide['version']))
                        self.assertEqual(response.headers['x-form-contract-id'], contract['contract_id'])
                        self.assertEqual(response.headers['cache-control'], 'no-store')
                        with ZipFile(BytesIO(response.content)) as actual, ZipFile(BytesIO(expected)) as reference:
                            self.assertIsNone(actual.testzip())
                            self.assertEqual(actual.namelist(), reference.namelist())
                            self.assertTrue(all(actual.read(n) == reference.read(n) for n in reference.namelist()))
                    response = client.get('/regional/templates/' + query['template_id'], params=query)
                    self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else '')
                    self.assertEqual(response.content, original)
                    self.assertEqual(response.headers['x-template-sha256'], sha256(original).hexdigest())
            self.assertEqual(list((root / 'private/generated').iterdir()), [])

    def test_source_only_and_unknown_locality_cannot_inherit_templates(self):
        with self.isolated(stage=False) as (_, store, client):
            for guide in self.guides(store):
                self.assertFalse(guide['can_generate'])
                self.assertFalse(guide['published'])
                self.assertEqual(client.get('/regional/form-contract', params=self.query(guide, 'application')).status_code, 409)
            for city, district in [('泉州市', '虚构未核验区'), ('福州市', '惠安县'), ('莆田市', '泉港区')]:
                response = client.get('/regional/lookup', params={'province': 'fujian', 'city': city, 'district': district})
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.json()['source_id'])
                self.assertEqual(response.json()['templates'], [])

    def test_cross_district_stale_and_metadata_requests_fail_closed(self):
        with self.isolated() as (_, store, client):
            guides = self.guides(store)
            forms = [self.contract(client, g, 'application') for g in guides]
            for index, guide in enumerate(guides):
                query = self.query(guide, 'application')
                payload = {**query, 'mode': 'blank', 'contract_id': forms[index]['contract_id'], 'data': {}}
                for change in [{'source_id': guides[1-index]['source_id']}, {'contract_id': forms[1-index]['contract_id']}, {'city': '福州市'}, {'version': guide['version'] + 1}, {'mode': 'reference_adaptation'}]:
                    response = client.post('/regional/generate', json={**payload, **change})
                    self.assertEqual(response.status_code, 409, change)
                for template in guide['templates']:
                    if template['eligible_own_kind'] is None:
                        self.assertFalse(template['can_generate'])
                        query_bad = {**query, 'template_id': template['id']}
                        self.assertEqual(client.get('/regional/form-contract', params=query_bad).status_code, 409)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'template_id': template['id']}).status_code, 409)

    def test_strict_validation_unknown_fields_xml_and_capacity(self):
        with self.isolated() as (_, store, client):
            for guide in self.guides(store):
                for kind in ['application', 'evidence']:
                    query = self.query(guide, kind)
                    contract = self.contract(client, guide, kind)
                    payload = {**query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': {}}
                    for version in [True, False, None, '1', 1.0, 0, -1]:
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'version': version}).status_code, 422)
                    for extra in ['signature', 'committeeName', 'unrecognized']:
                        self.assertEqual(client.post('/regional/generate', json={**payload, extra: '禁止'}).status_code, 422)
                    bad_data = ([{'signature': '禁止'}, {'committeeName': '不推定'}, {'factsReason': '\x00'}, {'requests': ['虚构'] * 4}] if kind == 'application' else [{'evidenceList': [{}] * 10}, {'evidenceList': [{'pageCount': True}]}, {'evidenceList': [{'pageCount': 1}]}, {'evidenceList': [{'pageCount': '01'}]}, {'evidenceList': [{'name': '\x01'}]}, {'evidenceList': [{'signature': '禁止'}]}])
                    for data in bad_data:
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'data': data}).status_code, 422, data)


if __name__ == '__main__':
    unittest.main()
