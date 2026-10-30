"""Approved Chunan seed append preserves all previous records and directory bytes."""
import importlib.util
import json
from hashlib import sha256
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_zhejiang_chunan_oct30 as own


class ChunanSeedPublicationTests(unittest.TestCase):
    def setUp(self):
        script = ROOT / 'scripts/publish-approved-chunan-seed.py'
        self.assertTrue(script.is_file(), 'Need an exact append-only Chunan public seed operation')
        spec = importlib.util.spec_from_file_location('chunan_seed_publication', script)
        self.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)

    def release_copy(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        white = own.REPORT + '/PUBLIC-WHITELIST.json'
        paths = [white, own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT]
        for manifest in [white, own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT]:
            paths.extend(r['path'] for r in json.loads((ROOT / manifest).read_bytes())['files'])
        paths.append('data/public-regions/directory.json')
        for relative in paths:
            target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        public = root / 'data/public-regions'
        # Reconstruct the exact approved historical prefix, not "everything
        # except F": later append-only releases legitimately add other places.
        historical = json.loads((ROOT / 'data/public-regions/guides.json').read_bytes())[:203]
        historical_bytes = (json.dumps(historical, ensure_ascii=False, indent=2) + '\n').encode()
        self.assertEqual(len(historical), 203)
        self.assertEqual(sha256(historical_bytes).hexdigest(), '58f42da0707a1a85a9923c212c36a4cc57aa0794a046ca8e3769f6801af8bc4c', 'Historical Chunan publication fixture must retain the exact approved203 prefix')
        guides = [g for g in historical if g['region_code'] != '330127']
        raw = (json.dumps(guides, ensure_ascii=False, indent=2) + '\n').encode()
        self.assertEqual(sha256(raw).hexdigest(), self.module.BASE_GUIDES_SHA256)
        (public / 'guides.json').write_bytes(raw)
        manifest = json.loads((ROOT / 'data/public-regions/manifest.json').read_bytes())
        manifest.update(guides=202, generatable_localities=185)
        manifest['files']['guides.json'] = sha256(raw).hexdigest()
        (public / 'manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        return root, guides

    def test_only_approved_own_record_appended_previous202_and_directory_unchanged_idempotent(self):
        root, before = self.release_copy(); public = root / 'data/public-regions'
        directory = (public / 'directory.json').read_bytes()
        result = self.module.publish(root)
        self.assertEqual((result['guides_after'], result['generatable_localities_after']), (203, 186))
        after = json.loads((public / 'guides.json').read_bytes())
        self.assertEqual(after[:202], before)
        self.assertEqual((public / 'directory.json').read_bytes(), directory)
        self.assertTrue(after[-1]['published']); self.assertEqual(after[-1]['source_id'], '3fb683d473fe253a3a117d46')
        self.assertIsNotNone(own.public_evidence(after[-1], root))
        checksum = sha256((public / 'guides.json').read_bytes()).hexdigest()
        self.assertEqual(self.module.publish(root)['status'], 'already_published_exact')
        self.assertEqual(sha256((public / 'guides.json').read_bytes()).hexdigest(), checksum)

    def test_changed_previous_guide_is_never_rebuilt_or_overwritten_even_if_manifest_rehashed(self):
        root, _ = self.release_copy(); public = root / 'data/public-regions'
        guides = json.loads((public / 'guides.json').read_bytes()); guides[0]['authority'] = 'changed'
        raw = json.dumps(guides).encode(); (public / 'guides.json').write_bytes(raw)
        manifest = json.loads((public / 'manifest.json').read_bytes()); manifest['files']['guides.json'] = sha256(raw).hexdigest()
        (public / 'manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        with self.assertRaises(ValueError): self.module.publish(root)
        self.assertEqual((public / 'guides.json').read_bytes(), raw)

    def test_missing_final_browser_receipt_never_updates_either_public_file(self):
        root, _ = self.release_copy(); public = root / 'data/public-regions'
        before = {n: (public / n).read_bytes() for n in ['guides.json', 'manifest.json']}
        (root / own.PUBLICATION_RECEIPT).unlink()
        with self.assertRaises((ValueError, OSError)): self.module.publish(root)
        self.assertTrue(all((public / n).read_bytes() == body for n, body in before.items()))

    def test_loaded_code_marker_identifies_chunan_and_exact_publication_receipt(self):
        from routes.regional_guides import release_capabilities
        marker = release_capabilities()
        self.assertEqual(marker['release_id'], 'oct30night-own-localities-v1')
        self.assertIn(own.ADAPTER, marker['adapters'])
        self.assertEqual(marker['publication_receipts'][own.ADAPTER], own.PUBLICATION_SHA256)
        self.assertIn('jiangsu_own_blank_oct30f_v1', marker['adapters'])
        self.assertEqual(marker['candidate_stage_receipts']['jiangsu_own_blank_oct30f_v1'], '1c9bcc069f4b659f55225a988852f81e7888ab66b6e0c46ad4d0a78fbdf38c88')
        self.assertEqual(marker['publication_receipts']['jiangsu_own_blank_oct30f_v1'], 'b37cabc422b4a315e22a5762553269636b821dd8d9b0b3fc46f03602af6febe6')


if __name__ == '__main__':
    unittest.main()
