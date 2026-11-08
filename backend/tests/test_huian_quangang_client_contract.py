"""Actual own two-district ASGI -> production TypeScript -> actual ASGI Word."""
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import unittest
import test_huian_quangang_dispatch as dispatch

ROOT = Path(__file__).resolve().parents[2]


class HQClientTests(unittest.TestCase):
    def test_actual_four_contracts_shared_clients_and_own_word_roundtrip(self):
        case = dispatch.HQDispatchTests()
        with case.isolated() as (root, store, client):
            cases = []
            with patch.object(dispatch.routes, 'fill_hq_document', side_effect=AssertionError('Reading must not generate')) as filler:
                for guide in case.guides(store):
                    response = client.get('/regional/lookup', params={k: guide[k] for k in ['province', 'city', 'district']})
                    self.assertEqual(response.status_code, 200)
                    cases.append({'guide': response.json(), 'forms': [case.contract(client, guide, kind) for kind in ['application', 'evidence']]})
                process = subprocess.run(['node', str(ROOT / 'backend/tests/fixtures/test-huian-quangang-wire.mjs')], input=json.dumps({'cases': cases}, ensure_ascii=False).encode(), capture_output=True, timeout=45)
                self.assertEqual(process.returncode, 0, process.stderr.decode('utf8', errors='replace'))
                replay = json.loads(process.stdout)
                self.assertEqual(replay['fetch_calls'], 0)
                self.assertEqual(filler.call_count, 0)
            self.assertEqual(replay['rejected_contexts'], 60)
            self.assertEqual(len(set(replay['sources'])), 2)
            self.assertEqual(len(replay['examples']), 4)
            for payload in replay['examples']:
                guide = next(row['guide'] for row in cases if row['guide']['source_id'] == payload['source_id'])
                response = client.post('/regional/generate', json=payload)
                self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else '')
                original_envelope = dispatch.own.envelope(guide['region_code'], payload['kind'], payload['data'], version=guide['version'], root=root)
                expected = dispatch.own.candidate_fill(original_envelope, root=root, private_review=True)
                self.assertEqual(response.content, expected)
                self.assertEqual(response.headers['x-form-contract-id'], payload['contract_id'])
            self.assertEqual(list((root / 'private/generated').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
