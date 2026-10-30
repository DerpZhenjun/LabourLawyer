"""Publication projection requires exact own source, stage and browser Word bytes."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_zhejiang_chunan_oct30 as own


class ChunanPublicationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(own, 'with_publication_evidence', None)),
                        'Publication needs its own final browser Word evidence hook')

    def test_published_boolean_and_qa_flags_never_authorize_missing_own_receipt(self):
        g = own.prepare_candidate(root=ROOT)
        g.update(published=True, candidate_web_qa='PASS', publication_status='published')
        t = next(t for t in g['templates'] if t.get('document_types') == ['application'])
        self.assertIsNone(own.public_evidence(g, ROOT))
        with self.assertRaises(ValueError): own.checked_adapter(g, t, 'application')

    def test_final_own_receipt_allows_only_exact_in_memory_publication_projection(self):
        staged = own.prepare_candidate(root=ROOT); staged['version'] = 203
        published = own.with_publication_evidence(staged, root=ROOT)
        self.assertFalse(staged['published'])
        self.assertTrue(published['published']); self.assertEqual(published['version'], 203)
        self.assertEqual(published['candidate_web_qa'], 'PASS')
        self.assertEqual(published['publication_adapter_evidence']['sha256'], own.PUBLICATION_SHA256)
        self.assertIsNotNone(own.public_evidence(published, ROOT))
        for kind in own.BLANKS:
            t = next(t for t in published['templates'] if t.get('document_types') == [kind])
            self.assertEqual(own.checked_adapter(published, t, kind), own.ADAPTER)
        for field in ['source_id', 'source_url', 'region_code']:
            bad = deepcopy(published); bad[field] += '-foreign'
            self.assertIsNone(own.public_evidence(bad, ROOT))
        bad = deepcopy(published); bad['publication_adapter_evidence']['sha256'] = '0' * 64
        self.assertIsNone(own.public_evidence(bad, ROOT))
        bad = deepcopy(published); bad['published'] = 1
        self.assertIsNone(own.public_evidence(bad, ROOT), 'Integer one is not an exact published boolean')
        bad = deepcopy(published)
        nested = next(t for t in bad['templates'] if t.get('document_types') == ['application'])
        nested['can_generate'] = 1
        self.assertIsNone(own.public_evidence(bad, ROOT), 'Nested template booleans retain exact JSON types')
        with self.assertRaises(ValueError): own.checked_adapter(bad, nested, 'application')

    def test_independent_release_root_rejects_changed_actual_browser_page_even_with_qa_pass_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            relative_white = own.REPORT + '/PUBLIC-WHITELIST.json'
            paths = [relative_white, own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT]
            for manifest in [relative_white, own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT]:
                paths.extend(r['path'] for r in json.loads((ROOT / manifest).read_bytes())['files'])
            for relative in paths:
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            published = own.with_publication_evidence(own.prepare_candidate(root=root), root=root)
            self.assertIsNotNone(own.public_evidence(published, root))
            page = root / 'reports/production-readiness-20261030/localities/chunan/browser-generation/word/evidence-1.png'
            page.write_bytes(page.read_bytes() + b'changed')
            self.assertIsNone(own.public_evidence(published, root))
            with self.assertRaises(ValueError):
                own.with_publication_evidence(own.prepare_candidate(root=root), root=root)

    def test_approved_publication_projection_keeps_both_real_source_bound_api_generations(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        from regional_guides import RegionalStore
        from routes import regional_guides as routes
        with tempfile.TemporaryDirectory() as folder:
            store = RegionalStore(Path(folder) / 'review.sqlite')
            projected = own.with_publication_evidence(own.prepare_candidate(root=ROOT), root=ROOT)
            guide = store.put_guide(projected)
            app = FastAPI(); app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for kind in own.BLANKS:
                    template = next(t for t in guide['templates'] if t.get('document_types') == [kind])
                    query = {k: guide[k] for k in ['province', 'city', 'district', 'source_id', 'version']}
                    query.update(template_id=template['id'], kind=kind)
                    result = client.get('/regional/form-contract', params=query)
                    self.assertEqual(result.status_code, 200, result.text)
                    payload = {**query, 'mode': 'blank', 'contract_id': result.json()['contract_id'], 'data': {}}
                    result = client.post('/regional/generate', json=payload)
                    self.assertEqual(result.status_code, 200, result.text if result.status_code != 200 else '')
                    self.assertEqual(result.headers['X-Guide-Source-ID'], guide['source_id'])
                    self.assertEqual(result.headers['X-Document-Origin'], 'official-blank-filled')


if __name__ == '__main__':
    unittest.main()
