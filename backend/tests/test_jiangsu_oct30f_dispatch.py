"""Real candidate routes and contracts in isolated stores; no production writes."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct30f as own


class FDispatchTests(unittest.TestCase):
    def test_release_marker_distinguishes_installed_candidate_from_publication(self):
        from routes.regional_guides import release_capabilities
        status = release_capabilities()
        self.assertEqual(status['release_id'], 'oct30night-own-localities-v1')
        self.assertIn(own.ADAPTER, status['adapters'])
        self.assertEqual(status['candidate_stage_receipts'][own.ADAPTER], own.STAGE_SHA256)
        self.assertEqual(status['publication_receipts'][own.ADAPTER], own.PUBLICATION_SHA256)

    def test_adapter_registered_with_strict_field_contract_and_raw_sources_stay_disabled(self):
        from regional_form_contracts import SUPPORTED_ADAPTERS, PUBLIC_PROOF_ADAPTERS
        from regional_adapters import with_reference_capabilities
        self.assertIn(own.ADAPTER, SUPPORTED_ADAPTERS)
        self.assertIn(own.ADAPTER, PUBLIC_PROOF_ADAPTERS)
        for code in sorted(own.SUPPORTED):
            raw = own.parse_capture(code)
            self.assertEqual(with_reference_capabilities(raw, root=ROOT), raw)

    def test_four_own_forms_blank_filled_original_and_negative_requests(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from regional_guides import RegionalStore
        from regional_public_provenance import public_evidence
        from routes import regional_guides as routes
        with tempfile.TemporaryDirectory() as folder:
            store = RegionalStore(Path(folder) / 'candidate.sqlite')
            guides = [store.put_guide(own.prepare_candidate(code, root=ROOT)) for code in sorted(own.SUPPORTED)]
            app = FastAPI(); app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for g in guides:
                    self.assertIsNotNone(public_evidence(g, ROOT))
                    for kind in ['application', 'evidence']:
                        t = next(t for t in g['templates'] if t.get('document_types') == [kind])
                        query = {k: g[k] for k in ['province', 'city', 'district', 'source_id', 'version']}
                        query.update(template_id=t['id'], kind=kind)
                        response = client.get('/regional/form-contract', params=query)
                        self.assertEqual(response.status_code, 200, response.text)
                        contract = response.json()
                        self.assertEqual(len(contract['fields']), 28 if kind == 'application' else 4)
                        self.assertFalse(contract['policy']['capacity_is_official_requirement'])
                        if kind == 'evidence':
                            self.assertEqual(len(contract['defaults']['evidenceList']), 1)
                            self.assertTrue(all(v == '' for v in contract['defaults']['evidenceList'][0].values()))
                        payload = {**query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': {}}
                        data = {'applicantName': '虚构测试劳动者', 'respondentName': '虚构测试单位',
                                'requests': ['仅供测试'], 'factsReason': '全部为虚构。'} if kind == 'application' else {
                                    'evidenceList': [{'name': '虚构测试证据', 'purpose': '仅供版式测试'}]}
                        for draft in [{}, data]:
                            response = client.post('/regional/generate', json={**payload, 'data': draft})
                            self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else '')
                            self.assertEqual(response.headers['X-Document-Origin'], 'official-blank-filled')
                            self.assertEqual(response.headers['X-Guide-Source-ID'], g['source_id'])
                            self.assertEqual(response.headers['X-Form-Contract-ID'], contract['contract_id'])
                            with ZipFile(BytesIO(response.content)) as archive: self.assertIsNone(archive.testzip())
                        foreign = next(v for v in guides if v['source_id'] != g['source_id'])
                        foreign_id = next(t['id'] for t in foreign['templates'] if t.get('document_types') == [kind])
                        for change in [{'source_id': foreign['source_id']}, {'version': g['version'] + 20},
                                       {'template_id': foreign_id}, {'contract_id': '0' * 64}, {'mode': 'reference_adaptation'}]:
                            self.assertEqual(client.post('/regional/generate', json={**payload, **change}).status_code, 409)
                        invalids = [{'unknown': ''}, {'copyCount': True}, {'applicationDate': '2026-02-30'}] if kind == 'application' else [
                            {'evidenceList': [{}] * 41}, {'evidenceList': [{'unknown': ''}]}]
                        for bad in invalids:
                            self.assertEqual(client.post('/regional/generate', json={**payload, 'data': bad}).status_code, 422)
                        original = client.get('/regional/templates/' + t['id'], params={k: g[k] for k in ['province', 'city', 'district', 'source_id', 'version']})
                        self.assertEqual(original.status_code, 200, original.text if original.status_code != 200 else '')
                        self.assertEqual(sha256(original.content).hexdigest(), t['sha256'])
                    sample = next(t for t in g['templates'] if t['official_kind'] == 'sample')
                    self.assertEqual(client.post('/regional/generate', json={**payload, 'template_id': sample['id']}).status_code, 409)

    def test_explicit_public_root_requires_complete_own_and_stage_proofs(self):
        from regional_public_provenance import public_evidence
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = ROOT / own.REPORT
            white = json.loads((report / 'PUBLIC-WHITELIST.json').read_bytes())['files']
            paths = list(white) + [(own.REPORT / 'PUBLIC-WHITELIST.json').as_posix(), own.STAGE_RECEIPT]
            paths += [r['path'] for r in json.loads((ROOT / own.STAGE_RECEIPT).read_bytes())['files']]
            for relative in paths:
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
            g = own.prepare_candidate('320581', root=root)
            self.assertIsNotNone(public_evidence(g, root))
            for invalid in [None, '', ' ']: self.assertIsNone(public_evidence(g, invalid))
            with self.assertRaises(ValueError): own.with_publication_evidence(g, root=root)
            (root / own.STAGE_RECEIPT).write_bytes(b'{"visual_review":"PASS"}')
            self.assertIsNone(public_evidence(g, root))
            with self.assertRaises(ValueError): own.prepare_candidate('320581', root=root)


if __name__ == '__main__':
    unittest.main()
