"""Final own-source browser/Word receipt, independent from candidate flags."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct30f as own


class FinalFProofTests(unittest.TestCase):
    def test_final_receipt_enables_only_exact_own_attested_projections(self):
        self.assertIsInstance(own.PUBLICATION_SHA256, str, 'Root-reviewed final evidence must be pinned separately')
        from regional_adapters import with_reference_capabilities, checked_reference_adapter
        from regional_public_provenance import public_evidence
        for code in sorted(own.SUPPORTED):
            source = own.parse_capture(code)
            candidate = own.prepare_candidate(code, root=ROOT)
            published = own.with_publication_evidence(candidate, root=ROOT)
            self.assertFalse(with_reference_capabilities(source, ROOT)['can_generate'])
            self.assertTrue(published['published']); self.assertEqual(published['candidate_web_qa'], 'PASS')
            self.assertEqual(published['publication_adapter_evidence']['sha256'], own.PUBLICATION_SHA256)
            self.assertIsNotNone(public_evidence(published, ROOT))
            for kind in ['application', 'evidence']:
                template = next(t for t in published['templates'] if t.get('document_types') == [kind])
                self.assertEqual(checked_reference_adapter(published, template, kind, root=ROOT), own.ADAPTER)
            for mutation in ['missing_final', 'integer_capability', 'foreign_final']:
                bad = deepcopy(published)
                if mutation == 'missing_final': bad.pop('publication_adapter_evidence')
                elif mutation == 'integer_capability': bad['can_generate'] = 1
                else: bad['publication_adapter_evidence']['sha256'] = '0' * 64
                self.assertIsNone(public_evidence(bad, ROOT), mutation)

    def test_cold_explicit_root_needs_every_final_file_and_cannot_fallback(self):
        self.assertIsInstance(own.PUBLICATION_SHA256, str, 'Final approval is required before public-root verification')
        from regional_public_provenance import public_evidence
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            white = json.loads((ROOT / own.REPORT / 'PUBLIC-WHITELIST.json').read_bytes())['files']
            paths = set(white) | {(own.REPORT / 'PUBLIC-WHITELIST.json').as_posix(), own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT}
            for receipt in [own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT]:
                paths.update(r['path'] for r in json.loads((ROOT / receipt).read_bytes())['files'])
            for relative in paths:
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
            candidate = own.prepare_candidate('320582', root=root)
            published = own.with_publication_evidence(candidate, root=root)
            self.assertIsNotNone(public_evidence(published, root))
            for invalid in [None, '', ' ']: self.assertIsNone(public_evidence(published, invalid))
            target = root / own.QA_REPORT / 'browser-word/320582-evidence-1.png'
            target.write_bytes(b'tampered actual browser Word page')
            self.assertIsNone(public_evidence(published, root))
            self.assertIsNotNone(public_evidence(candidate, root), 'Stage permission stays separate from final proof')
            with self.assertRaises(ValueError): own.with_publication_evidence(candidate, root=root)


if __name__ == '__main__':
    unittest.main()
