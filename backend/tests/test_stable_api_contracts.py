"""Stable schema export must never start services or touch application databases."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class StableAPIContracts(unittest.TestCase):
    def test_export_is_offline_and_reproducible(self):
        from export_api_contracts import stable_openapi
        with patch('sqlite3.connect', side_effect=AssertionError('database access')), \
             patch('httpx.AsyncClient', side_effect=AssertionError('network access')):
            first = stable_openapi()
            self.assertEqual(first, stable_openapi())
        self.assertEqual(len(first['paths']), 11)
        self.assertIn('/api/services',first['paths'])
        self.assertNotIn('/api/regional-guides/form-contract', first['paths'])
        self.assertIn('QuestionRequest', first['components']['schemas'])

    def test_catalog_response_preserves_every_existing_value(self):
        from api_contracts import ProvinceCatalogResponse
        from routes.province_documents import list_province_documents
        raw = list_province_documents()
        self.assertEqual(ProvinceCatalogResponse.model_validate(raw).model_dump(exclude_unset=True), raw)
        self.assertEqual(len(raw['items']), 31)

    def test_ai_boundaries_and_legacy_alias(self):
        from api_contracts import QuestionRequest
        from routes.ai import QuestionRequest as LegacyRequest
        from pydantic import ValidationError
        self.assertIs(QuestionRequest, LegacyRequest)
        self.assertEqual(QuestionRequest(question='虚构测试').history, [])
        self.assertEqual(len(QuestionRequest(question='😀' * 8000).question), 8000)
        for raw in [{'question': '😀' * 8001}, {'question': 'x', 'history': [{'role': 'user', 'content': 'x'}] * 13}]:
            with self.assertRaises(ValidationError):
                QuestionRequest.model_validate(raw)

    def test_schema_tracks_live_request_constraints_and_binary_responses(self):
        from export_api_contracts import stable_openapi
        schema = stable_openapi()
        request = schema['components']['schemas']['QuestionRequest']['properties']
        self.assertEqual(request['question']['maxLength'], 8000)
        self.assertEqual(request['history']['maxItems'], 12)
        path = schema['paths']['/api/province-documents/{slug}/application/generate']['post']
        self.assertIn('application/vnd.openxmlformats-officedocument.wordprocessingml.document', path['responses']['200']['content'])


if __name__ == '__main__':
    unittest.main()
