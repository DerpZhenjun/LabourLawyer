"""Exercise the four independently bound candidate guides through the real API."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import shutil

from fastapi import FastAPI
from fastapi.testclient import TestClient

import regional_quanzhou_next4 as own
from public_seed import bootstrap_public_data
from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class QuanzhouCandidateTests(TestCase):
    def test_reviewed_documents_use_own_contract_and_original(self):
        qa = ROOT / own.REVIEW_RECEIPT
        reviewed = json.loads(qa.read_bytes())['records']
        contract_ids = set()
        with TemporaryDirectory(prefix='qz-own-candidate-') as directory:
            store = RegionalStore(Path(directory) / 'guides.sqlite')
            for code in own.REGIONS:
                store.put_guide(own.staged_candidate(code, root=ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), patch.dict('os.environ', {'LABOURLAWYER_DATA_DIR': directory}), TestClient(app) as client:
                for code, profile in own.REGIONS.items():
                    region = {'province': 'fujian', 'city': '泉州市', 'district': profile['district']}
                    lookup = client.get('/regional/lookup', params=region)
                    self.assertEqual(lookup.status_code, 200)
                    guide = lookup.json()
                    self.assertIsInstance(guide['sections'], dict)
                    self.assertIsNone(guide['channel']['entry_url'])
                    self.assertFalse(guide['published'])
                    templates = [t for t in guide['templates'] if t['can_generate']]
                    self.assertEqual({t['eligible_own_kind'] for t in templates}, set(profile['original_kinds']))
                    for template in templates:
                        kind = template['eligible_own_kind']
                        records = {row['case']: row for row in reviewed if row['source']['region_code'] == code and row['source']['kind'] == kind}
                        self.assertEqual(set(records), {'original', 'normal', 'stress'})
                        self.assertEqual(records['original']['source']['attachment_id'], template['id'])
                        query = {k: guide[k] for k in ('province', 'city', 'district', 'source_id', 'version')}
                        query.update(kind=kind, template_id=template['id'])
                        response = client.get('/regional/form-contract', params=query)
                        self.assertEqual(response.status_code, 200, response.text)
                        contract = response.json()
                        self.assertEqual(len(contract['context']), 15)
                        self.assertEqual(contract['context']['source_version'], profile['source_manifest_sha256'])
                        contract_ids.add(contract['contract_id'])
                        original = client.get(f"/regional/templates/{template['id']}", params=query)
                        self.assertEqual(original.status_code, 200)
                        self.assertEqual(sha256(original.content).hexdigest(), records['original']['sha256'])
                        for case, row in records.items():
                            if case == 'original':
                                data = contract['defaults']
                            else:
                                sample = ROOT / own.FIXTURES / f'350521-{kind}-{case}.json'
                                data = json.loads(sample.read_bytes())['data']
                            payload = {**query, 'mode': 'blank', 'data': data, 'contract_id': contract['contract_id']}
                            result = client.post('/regional/generate', json=payload)
                            self.assertEqual(result.status_code, 200, result.text if result.status_code != 200 else '')
                            self.assertEqual(sha256(result.content).hexdigest(), row['sha256'])
                        foreign = {**payload, 'source_id': own.REGIONS['350581' if code != '350581' else '350582']['source_id']}
                        self.assertEqual(client.post('/regional/generate', json=foreign).status_code, 409)
                        without_contract = {key: value for key, value in payload.items() if key != 'contract_id'}
                        self.assertEqual(client.post('/regional/generate', json=without_contract).status_code, 409)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'contract_id': '0' * 64}).status_code, 409)
                    if code == '350581':
                        ambiguous = next(t for t in guide['templates'] if t['classification'] == 'FORMAT_SLOT_SAMPLE_NAME_CONFLICT')
                        query = {k: guide[k] for k in ('province', 'city', 'district', 'source_id', 'version')}
                        query.update(kind='evidence', template_id=ambiguous['id'])
                        self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
        self.assertEqual(len(contract_ids), 7)

    def test_source_only_forged_stage_and_published_flag_are_refused(self):
        source = own.production_source('350582', root=ROOT)
        self.assertFalse(source['can_generate'])
        self.assertFalse(own.with_capabilities(source, root=ROOT)['can_generate'])
        for flag in ('published', 'can_generate'):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                own.with_capabilities({**source, flag: True}, root=ROOT)
        stage = own.staged_candidate('350582', root=ROOT)
        with self.assertRaises(ValueError):
            own.with_capabilities({**stage, 'published': True}, root=ROOT)
        with self.assertRaises(ValueError):
            own.with_capabilities({**stage, 'source_id': own.REGIONS['350581']['source_id']}, root=ROOT)

    def test_stage_receipt_must_exist_at_the_supplied_root_and_match(self):
        code = '350581'
        manifest = ROOT / own.BASE / code / 'SOURCE-PROJECTION-MANIFEST.json'
        members = json.loads(manifest.read_bytes())['files']
        with TemporaryDirectory(prefix='qz-missing-review-') as directory:
            root = Path(directory).resolve()
            folder = root / own.BASE / code
            folder.mkdir(parents=True)
            shutil.copyfile(manifest, folder / manifest.name)
            for member in members:
                shutil.copyfile(manifest.parent / member, folder / member)
            self.assertFalse(own.production_source(code, root=root)['can_generate'])
            with self.assertRaises(ValueError):
                own.staged_candidate(code, root=root)
            receipt = root / own.REVIEW_RECEIPT
            receipt.parent.mkdir()
            receipt.write_bytes((ROOT / own.REVIEW_RECEIPT).read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                own.staged_candidate(code, root=root)

    def test_public_bootstrap_refuses_candidate_before_database_creation(self):
        with TemporaryDirectory(prefix='qz-public-seed-') as directory:
            root = Path(directory)
            folder = root / 'data/public-regions'
            folder.mkdir(parents=True)
            snapshot = {'guides.json': [own.staged_candidate('350582', root=ROOT)], 'directory.json': []}
            pins = {}
            for name, value in snapshot.items():
                raw = json.dumps(value, ensure_ascii=False).encode('utf8')
                (folder / name).write_bytes(raw)
                pins[name] = sha256(raw).hexdigest()
            (folder / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'files': pins}), encoding='utf8')
            dest = root / 'isolated-db'
            with self.assertRaisesRegex(ValueError, 'Candidate guide'):
                bootstrap_public_data(root=root, data_dir=dest)
            self.assertFalse(dest.exists())

    def test_published_guide_requires_exact_separate_browser_and_word_approval(self):
        code = '350581'
        approved = own.published_guide(code, root=ROOT)
        self.assertTrue(approved['published'])
        self.assertEqual(approved['publication_status'], 'published')
        self.assertEqual(approved['publication_adapter_evidence']['sha256'], own.PUBLICATION_SHA256)
        original = next(t for t in approved['templates'] if t['can_generate'])
        self.assertEqual(original['document_types'], ['application'])
        self.assertEqual(own.checked_adapter(approved, original, 'application', root=ROOT), own.ADAPTER)
        with self.assertRaises(ValueError):
            own.checked_adapter(approved, original, 'evidence', root=ROOT)
        with patch.object(own, 'PUBLICATION_SHA256', None), self.assertRaises(ValueError):
            own.published_guide(code, root=ROOT)
        for rejected_path in (own.PUBLICATION_RECEIPT, own.BROWSER_RECEIPT):
            read = own._read
            with self.subTest(path=rejected_path), patch.object(own, '_read', side_effect=lambda root, name: read(root, name) + (b' ' if name == rejected_path else b'')):
                with self.assertRaises(ValueError):
                    own.published_guide(code, root=ROOT)
