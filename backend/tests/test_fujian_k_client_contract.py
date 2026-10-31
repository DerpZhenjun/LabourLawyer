"""Actual K ASGI -> production TypeScript -> ASGI, isolated public test data."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import test_fujian_oct31k_dispatch as dispatch

ROOT = Path(__file__).resolve().parents[2]


class KClientContractTests(unittest.TestCase):
    def node(self, name, data):
        self.assertIn(name, {'test-fujian-k-display.mjs', 'test-fujian-k-wire.mjs'})
        fixture = ROOT / 'backend/tests/fixtures' / name
        result = subprocess.run(
            ['node', str(fixture)], input=json.dumps(data, ensure_ascii=False).encode(),
            capture_output=True, check=True, timeout=40,
        )
        return json.loads(result.stdout)

    def test_own_source_display_uses_real_stored_versions_and_production_TS(self):
        case = dispatch.KDispatchTests()
        with case.isolated('source') as (_, store, _):
            guides = [case.guide(store, code) for code in dispatch.own.REGIONS]
            self.assertEqual([g['version'] for g in guides], [1, 2, 3])
            result = self.node('test-fujian-k-display.mjs', guides)
            self.assertEqual(result['network_requests'], 0)
            self.assertEqual(result['generation_posts'], 0)
            self.assertEqual(len(result['regions']), 3)
            self.assertEqual(len({r['source_id'] for r in result['regions']}), 3)

    def test_four_TS_examples_confirm_through_actual_ASGI_and_clean_outputs(self):
        case = dispatch.KDispatchTests()
        with case.isolated() as (root, store, client):
            with patch.object(dispatch.routes, 'fill_fujian_k_document',
                              side_effect=AssertionError('Reads cannot generate')) as filler:
                wire = case.wire(store, client)
                result = self.node('test-fujian-k-wire.mjs', wire)
                self.assertEqual(filler.call_count, 0)
            self.assertEqual(result['network_requests'], 0)
            self.assertEqual(result['cancel_posts'], 0)
            self.assertEqual(len(result['examples']), 4)
            forms = set()
            for payload in result['examples']:
                guide = store.lookup(payload['province'], payload['city'], payload['district'])
                forms.add((guide['region_code'], payload['kind']))
                self.assertIn('虚构', json.dumps(payload['data'], ensure_ascii=False))
                response = client.post('/regional/generate', json=payload)
                self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else '')
                expected = dispatch.own.candidate_fill(
                    dispatch.own.envelope(guide['region_code'], payload['kind'], payload['data'], root=root),
                    root=root,
                )
                self.assertEqual(response.content, expected)
                self.assertEqual(response.headers['x-guide-source-id'], guide['source_id'])
                self.assertEqual(response.headers['x-guide-version'], str(guide['version']))
                self.assertEqual(response.headers['x-form-contract-id'], payload['contract_id'])
                self.assertEqual(response.headers['cache-control'], 'no-store')
                with ZipFile(BytesIO(response.content)) as actual, ZipFile(BytesIO(expected)) as other:
                    self.assertIsNone(actual.testzip())
                    self.assertEqual(actual.namelist(), other.namelist())
                    for member in actual.namelist():
                        self.assertEqual(sha256(actual.read(member)).digest(), sha256(other.read(member)).digest())
            self.assertEqual(forms, {('350111', 'application'), ('350111', 'evidence'),
                                     ('350121', 'application'), ('350105', 'application')})
            self.assertEqual(list((root / 'private-data/generated').iterdir()), [])
