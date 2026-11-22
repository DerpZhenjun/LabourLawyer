import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compact_contract_experiment import LocalContractProof
from compact_proof_experiment import SCHEMA
from regional_form_contracts import _contract_id


class LocalContractProofTests(unittest.TestCase):
    def setUp(self):
        scope = TemporaryDirectory()
        self.addCleanup(scope.cleanup)
        self.root = Path(scope.name)
        self.body = b'synthetic local fixture'
        self.original_hash = sha256(self.body).hexdigest()
        self.original = self.root / (self.original_hash + '.docx')
        self.original.write_bytes(self.body)
        self.context = {
            'region_code': '320281', 'source_id': '1' * 24, 'version': 1,
            'kind': 'application', 'template_id': 'fixture-1', 'mode': 'blank',
            'province': 'fixture', 'city': 'fixture', 'district': 'fixture',
            'adapter': 'fixture',
        }
        self.contract = {
            'schema_version': 1, 'context': self.context,
            'fields': [], 'defaults': {}, 'policy': {},
        }
        self.contract['contract_id'] = _contract_id(self.contract)
        self.binding = {
            key: self.context[key]
            for key in ('region_code', 'source_id', 'version', 'kind', 'template_id')
        }
        self.binding.update(original_sha256=self.original_hash, contract_id=self.contract['contract_id'])
        self.capsule_body = json.dumps({'schema': SCHEMA, 'rows': [self.binding]}).encode()

    def proof(self, entries, pinned=None):
        body = json.dumps({'schema': 1, 'contracts': entries}).encode()
        return LocalContractProof(
            self.root, self.capsule_body, sha256(self.capsule_body).hexdigest(),
            body, pinned or sha256(body).hexdigest(),
        )

    def test_returns_exact_isolated_contract_and_original(self):
        proof = self.proof([self.contract])
        contract, original = proof.read(self.binding)
        self.assertEqual(contract, self.contract)
        self.assertEqual(original, self.body)
        contract['context']['district'] = 'modified'
        self.assertEqual(proof.read(self.binding)[0], self.contract)

    def test_wrong_pin_or_partial_inventory_is_rejected(self):
        for args in (([self.contract], '0' * 64), ([], None), ([self.contract] * 2, None)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.proof(*args)

    def test_mutated_contract_and_recomputed_unbound_id_are_rejected(self):
        invalid = {**self.contract, 'defaults': {'extra': ''}}
        with self.assertRaises(ValueError):
            self.proof([invalid])
        invalid['contract_id'] = _contract_id(invalid)
        with self.assertRaises(ValueError):
            self.proof([invalid])

    def test_mismatched_binding_and_tampered_original_are_rejected(self):
        proof = self.proof([self.contract])
        with self.assertRaises(ValueError):
            proof.read(dict(self.binding, version=2))
        self.original.write_bytes(b'modified')
        with self.assertRaises(ValueError):
            proof.read(self.binding)


if __name__ == '__main__':
    unittest.main()
