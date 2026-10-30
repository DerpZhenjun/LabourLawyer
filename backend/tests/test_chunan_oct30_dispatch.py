"""Source/receipt/contract-bound candidate routes, using an isolated SQLite store."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import sys
import json
import shutil
from hashlib import sha256
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_zhejiang_chunan_oct30 as own


class ChunanDispatchTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(own, 'prepare_candidate', None)),
                        'Chunan needs explicit own QA receipt staging before route integration')

    def test_sealed_source_does_not_enable_generation_and_boolean_markers_cannot_bypass_receipt(self):
        from regional_adapters import with_reference_capabilities, checked_reference_adapter
        raw = own.parse_capture(root=ROOT)
        self.assertFalse(any(t['can_generate'] for t in with_reference_capabilities(raw)['templates']))
        staged = own.prepare_candidate(root=ROOT)
        self.assertFalse(staged['published'])
        for kind in own.BLANKS:
            t = next(t for t in staged['templates'] if t.get('document_types') == [kind])
            self.assertEqual(checked_reference_adapter(staged, t, kind), own.ADAPTER)
            bad = deepcopy(staged); bad.pop('candidate_adapter_evidence')
            with self.assertRaises(ValueError): checked_reference_adapter(bad, t, kind)
            bad = deepcopy(staged); bad['candidate_adapter_evidence']['sha256'] = '0' * 64
            with self.assertRaises(ValueError): checked_reference_adapter(bad, t, kind)

    def test_actual_candidate_contract_generate_original_routes_and_cross_source_rejections(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from regional_guides import RegionalStore
        from regional_public_provenance import public_evidence
        from routes import regional_guides as routes
        with tempfile.TemporaryDirectory() as folder:
            store = RegionalStore(Path(folder) / 'candidate.sqlite')
            staged = store.put_guide(own.prepare_candidate(root=ROOT))
            self.assertIsNotNone(public_evidence(staged, ROOT))
            app = FastAPI(); app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for kind, spec in own.BLANKS.items():
                    t = next(t for t in staged['templates'] if t.get('document_types') == [kind])
                    query = {k: staged[k] for k in ['province', 'city', 'district', 'source_id', 'version']}
                    query.update(template_id=t['id'], kind=kind)
                    response = client.get('/regional/form-contract', params=query)
                    self.assertEqual(response.status_code, 200, response.text)
                    contract = response.json()
                    expected = 23 if kind == 'application' else 5
                    self.assertEqual(len(contract['fields']), expected)
                    payload = {**query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': {}}
                    response = client.post('/regional/generate', json=payload)
                    self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else '')
                    self.assertEqual(response.headers['X-Document-Origin'], 'official-blank-filled')
                    self.assertEqual(response.headers['X-Guide-Source-ID'], staged['source_id'])
                    self.assertEqual(response.headers['X-Form-Contract-ID'], contract['contract_id'])
                    with ZipFile(BytesIO(response.content)) as archive: self.assertIsNone(archive.testzip())
                    for change in [{'source_id': 'foreign'}, {'version': staged['version'] + 1},
                                   {'contract_id': '0' * 64}, {'template_id': 'foreign'}]:
                        wrong = deepcopy(payload); wrong.update(change)
                        self.assertEqual(client.post('/regional/generate', json=wrong).status_code, 409)
                    for data in [{'unknown': ''}, {'copyCount': True}]:
                        wrong = deepcopy(payload); wrong['data'] = data
                        self.assertEqual(client.post('/regional/generate', json=wrong).status_code, 422)
                    original = client.get('/regional/templates/' + t['id'], params={k: staged[k] for k in ['province', 'city', 'district', 'source_id', 'version']})
                    self.assertEqual(original.status_code, 200)
                    self.assertEqual(original.content, (ROOT / t['file']).read_bytes())

    def test_explicit_release_root_bootstraps_only_with_complete_own_and_stage_evidence(self):
        from public_seed import bootstrap_public_data
        from regional_public_provenance import public_evidence
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source_white = own.REPORT + '/PUBLIC-WHITELIST.json'
            paths = [source_white, own.STAGE_RECEIPT]
            paths += [r['path'] for r in json.loads((ROOT / source_white).read_bytes())['files']]
            paths += [r['path'] for r in json.loads((ROOT / own.STAGE_RECEIPT).read_bytes())['files']]
            for relative in paths:
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            staged = own.prepare_candidate(root=root)
            public = root / 'data/public-regions'; public.mkdir(parents=True)
            files = {}
            for filename, records in [('guides.json', [staged]), ('directory.json', [])]:
                body = json.dumps(records, ensure_ascii=False).encode()
                (public / filename).write_bytes(body); files[filename] = sha256(body).hexdigest()
            (public / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'files': files}), encoding='utf8')
            outcome = bootstrap_public_data(root)
            self.assertEqual(outcome['guides_imported'], 1)
            self.assertEqual(outcome['missing_attachments'], [])
            self.assertIsNotNone(public_evidence(staged, root))
            for invalid in [None, '', ' ']:
                self.assertIsNone(public_evidence(staged, invalid))
            (root / own.STAGE_RECEIPT).write_bytes(b'{"visual_review":"PASS","can_generate":true}')
            self.assertIsNone(public_evidence(staged, root))
            with self.assertRaises(ValueError): own.prepare_candidate(root=root)


if __name__ == '__main__':
    unittest.main()
