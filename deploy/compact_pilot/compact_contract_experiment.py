"""Private admission test for current form definitions and official originals."""

from copy import deepcopy
from hashlib import sha256
import json

from compact_proof_experiment import Capsule, object_without_duplicates
from regional_form_contracts import _contract_id


_SCOPE_FIELDS = ('region_code', 'kind', 'source_id', 'template_id', 'version')
_CONTRACT_FIELDS = {'schema_version', 'context', 'fields', 'defaults', 'policy', 'contract_id'}


class LocalContractProof:
    def __init__(self, root, capsule_body, capsule_pin, contract_body, contract_pin):
        self._root = root
        self._capsule = Capsule(capsule_body, capsule_pin)
        if not isinstance(contract_body, bytes) or sha256(contract_body).hexdigest() != contract_pin:
            raise ValueError('Unexpected contract bundle digest')
        bundle = json.loads(contract_body, object_pairs_hook=object_without_duplicates)
        if (not isinstance(bundle, dict) or bundle.keys() != {'schema', 'contracts'}
                or type(bundle['schema']) is not int or bundle['schema'] != 1
                or not isinstance(bundle['contracts'], list)):
            raise ValueError('Unexpected contract bundle schema')
        self._contracts = {}
        for contract in bundle['contracts']:
            if (not isinstance(contract, dict) or contract.keys() != _CONTRACT_FIELDS
                    or not isinstance(contract['context'], dict)):
                raise ValueError('Unexpected contract definition')
            context = contract['context']
            key = (context.get('region_code'), context.get('kind'))
            if any(not isinstance(part, str) for part in key):
                raise ValueError('Invalid contract scope')
            binding = self._capsule.rows.get(key)
            if (binding is None or key in self._contracts or context.get('mode') != 'blank'
                    or type(context.get('version')) is not int
                    or any(context.get(field) != binding[field] for field in _SCOPE_FIELDS)
                    or _contract_id(contract) != contract['contract_id']
                    or binding['contract_id'] != contract['contract_id']):
                raise ValueError('Contract differs from the pinned binding')
            self._contracts[key] = contract
        if self._contracts.keys() != self._capsule.rows.keys():
            raise ValueError('Contract bundle does not cover the pinned inventory')

    def read(self, request):
        original = self._capsule.resolve(self._root, request)
        scope = (request['region_code'], request['kind'])
        return deepcopy(self._contracts[scope]), original
