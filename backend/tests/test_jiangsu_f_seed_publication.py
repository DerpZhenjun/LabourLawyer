"""Run the F leaf publisher only against complete isolated release copies."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct30f as own


class FSeedPublicationTests(unittest.TestCase):
    def setUp(self):
        script = ROOT / 'scripts/publish-approved-jiangsu-f-seed.py'
        self.assertTrue(script.is_file(), 'Need a precise two-guide append-only F publisher')
        spec = importlib.util.spec_from_file_location('f_seed_publication', script)
        self.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)

    def release_copy(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        white = (own.REPORT / 'PUBLIC-WHITELIST.json').as_posix()
        paths = set(json.loads((ROOT / white).read_bytes())['files'])
        paths.update([white, own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT])
        for receipt in [own.STAGE_RECEIPT, own.PUBLICATION_RECEIPT]:
            paths.update(r['path'] for r in json.loads((ROOT / receipt).read_bytes())['files'])
        paths.update('data/public-regions/' + n for n in ['guides.json', 'manifest.json', 'directory.json'])
        for name in paths:
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / name, target)
        # Keep testing the exact historical baseline after ROOT later executes
        # this approved append. Future append-only releases retain these203.
        public = root / 'data/public-regions'
        previous = json.loads((public / 'guides.json').read_bytes())[:203]
        body = self.module.encoded(previous)
        self.assertEqual(sha256(body).hexdigest(), self.module.BASE_GUIDES_SHA256)
        (public / 'guides.json').write_bytes(body)
        manifest = json.loads((public / 'manifest.json').read_bytes())
        manifest.update(guides=203, generatable_localities=186)
        manifest['files']['guides.json'] = sha256(body).hexdigest()
        (public / 'manifest.json').write_bytes(self.module.encoded(manifest))
        return root

    def snapshot(self, root):
        return {n: (root / 'data/public-regions' / n).read_bytes() for n in ['guides.json', 'manifest.json', 'directory.json']}

    def test_dry_run_then_exact_append_old203_encoded_records_directory_and_idempotency(self):
        root = self.release_copy(); before = self.snapshot(root)
        self.assertEqual(self.module.publish(root)['status'], 'dry_run')
        self.assertEqual(self.snapshot(root), before)
        self.assertFalse((root / '.runtime').exists())
        result = self.module.publish(root, execute=True)
        self.assertEqual((result['guides_after'], result['generatable_localities_after']), (205, 188))
        after = self.snapshot(root); guides = json.loads(after['guides.json'])
        self.assertEqual(self.module.encoded(guides[:203]), before['guides.json'])
        self.assertEqual(after['directory.json'], before['directory.json'])
        self.assertEqual([g['source_id'] for g in guides[-2:]], ['9a24af792c956feb67bd37c6', '95e826085ed0fec9f410cc86'])
        self.assertTrue(all(g['published'] is True and own.public_evidence(g, root) for g in guides[-2:]))
        backup = root / self.module.BACKUP
        self.assertEqual((backup / 'guides.json').read_bytes(), before['guides.json'])
        self.assertEqual((backup / 'manifest.json').read_bytes(), before['manifest.json'])
        self.assertEqual(self.module.publish(root, execute=True)['status'], 'already_published_exact')
        self.assertEqual(self.snapshot(root), after)
        self.assertFalse((root / 'backend/data').exists())

    def test_rehashed_changed_old_record_is_not_rebuilt_or_overwritten(self):
        root = self.release_copy(); public = root / 'data/public-regions'
        rows = json.loads((public / 'guides.json').read_bytes()); rows[0]['authority'] = 'unexpected replacement'
        body = self.module.encoded(rows); (public / 'guides.json').write_bytes(body)
        manifest = json.loads((public / 'manifest.json').read_bytes()); manifest['files']['guides.json'] = sha256(body).hexdigest()
        (public / 'manifest.json').write_bytes(self.module.encoded(manifest)); before = self.snapshot(root)
        with self.assertRaises(ValueError): self.module.publish(root, execute=True)
        self.assertEqual(self.snapshot(root), before)

    def test_missing_or_tampered_final_proof_never_uses_checkout_fallback(self):
        for relative in [own.PUBLICATION_RECEIPT, own.QA_REPORT + '/browser-word/320582-evidence-1.png']:
            root = self.release_copy(); before = self.snapshot(root)
            (root / relative).write_bytes(b'tampered or unavailable public evidence')
            with self.subTest(relative=relative), self.assertRaises((ValueError, OSError)):
                self.module.publish(root, execute=True)
            self.assertEqual(self.snapshot(root), before)
            self.assertFalse((root / '.runtime').exists())

    def test_second_file_commit_failure_rolls_back_both_public_files(self):
        root = self.release_copy(); before = self.snapshot(root)
        original_replace = Path.replace
        def fail_manifest(path, target):
            if path.name == 'manifest.json.jiangsu-f-next': raise OSError('injected second-file commit failure')
            return original_replace(path, target)
        with patch.object(Path, 'replace', fail_manifest), self.assertRaises(OSError):
            self.module.publish(root, execute=True)
        self.assertEqual(self.snapshot(root), before)
        self.assertFalse(list((root / 'data/public-regions').glob('*.jiangsu-f-next')))
        self.assertFalse((root / 'backend/data').exists())

    def test_unexpected_existing_f_projection_and_foreign_pending_file_are_preserved(self):
        root = self.release_copy(); self.module.publish(root, execute=True)
        public = root / 'data/public-regions'
        rows = json.loads((public / 'guides.json').read_bytes()); rows[-1]['can_generate'] = 1
        body = self.module.encoded(rows); (public / 'guides.json').write_bytes(body)
        manifest = json.loads((public / 'manifest.json').read_bytes()); manifest['files']['guides.json'] = sha256(body).hexdigest()
        (public / 'manifest.json').write_bytes(self.module.encoded(manifest)); before = self.snapshot(root)
        with self.assertRaises(ValueError): self.module.publish(root, execute=True)
        self.assertEqual(self.snapshot(root), before)
        root = self.release_copy(); pending = root / 'data/public-regions/guides.json.jiangsu-f-next'
        pending.write_bytes(b'preserve another prepared operation'); before = self.snapshot(root)
        with self.assertRaises(ValueError): self.module.publish(root, execute=True)
        self.assertEqual(pending.read_bytes(), b'preserve another prepared operation')
        self.assertEqual(self.snapshot(root), before)


if __name__ == '__main__':
    unittest.main()
