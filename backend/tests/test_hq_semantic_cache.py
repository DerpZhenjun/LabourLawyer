"""Portable HQ proof-cache regressions; actual proof, Temp mutations, no DB/HTTP."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import os
import shutil
import sys
import tempfile
import unittest

import hq_phase_proof as proof
import hq_word_semantic_cache as cache
import regional_fujian_huian_quangang_nov1 as own

ROOT = Path(__file__).resolve().parents[2]
READ_BYTES = Path.read_bytes
READ_LEDGER = []


def observed_read(path):
    READ_LEDGER.append(path)
    return READ_BYTES(path)


def changed_validator(*args, **kwargs):
    raise ValueError('Changed effective HQ validator must run')


class HQSemanticCacheTests(unittest.TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def clone_proof(self):
        temp = tempfile.TemporaryDirectory(prefix='hq-proof-regression-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        manifest = json.loads((ROOT / own.WORD_MANIFEST).read_bytes())
        names = [*own.source_files(ROOT), own.WORD_MANIFEST,
                 *[own.QA_REPORT + '/' + name for name in manifest['files']],
                 own.STAGE_RECEIPT]
        self.assertEqual(len(names), 99)
        self.assertEqual(len(set(names)), 99)
        for name in names:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        return root

    def test_warm_hit_reads_all98_artifacts_without_repeating_semantics(self):
        # Catches a timestamp-only hit or accidental replay of expensive semantics.
        manifest = json.loads((ROOT / own.WORD_MANIFEST).read_bytes())
        expected = {ROOT / n for n in own.source_files(ROOT)} | {ROOT / own.WORD_MANIFEST}
        expected |= {ROOT / own.QA_REPORT / n for n in manifest['files']}
        self.assertEqual(len(expected), 98)
        semantic_calls = []
        verifier = proof.verify_word.__wrapped__.__code__
        previous_profile = sys.getprofile()

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code is verifier:
                semantic_calls.append(1)

        try:
            sys.setprofile(profile)
            with patch.object(Path, 'read_bytes', observed_read):
                own.word_proof(root=ROOT)
                READ_LEDGER.clear()
                own.word_proof(root=ROOT)
                self.assertTrue(expected <= set(READ_LEDGER))
        finally:
            sys.setprofile(previous_profile)
            READ_LEDGER.clear()
        self.assertEqual(len(semantic_calls), 1)
        self.assertEqual(cache.info()['hits'], 1)

    def test_same_size_restored_mtime_tampering_is_rejected_after_warm(self):
        # Catches trusting a previously validated path/mtime instead of new bytes.
        root = self.clone_proof()
        manifest = own.word_proof(root=root)
        sources = own.source_files(root)
        names = [own.WORD_MANIFEST,
                 next(n for n in sources if n.endswith('safe-table-info.json')),
                 next(n for n in sources if n.endswith('.docx')),
                 *[own.QA_REPORT + '/' + next(n for n in manifest['files'] if predicate(n))
                   for predicate in [lambda n: n.startswith('fixtures/'),
                                     lambda n: n.endswith('.png'),
                                     lambda n: n.endswith('.docx')]],
                 own.QA_REPORT + '/ROOT-WORD-VISUAL-REVIEW.json']
        for name in names:
            with self.subTest(artifact=name):
                path = root / name
                raw, metadata = path.read_bytes(), path.stat()
                tampered = bytearray(raw)
                tampered[len(tampered) // 2] ^= 1
                try:
                    path.write_bytes(tampered)
                    os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
                    self.assertEqual(path.stat().st_size, len(raw))
                    self.assertEqual(path.stat().st_mtime_ns, metadata.st_mtime_ns)
                    with self.assertRaises((ValueError, OSError, KeyError)):
                        own.word_proof(root=root)
                finally:
                    path.write_bytes(raw)
                    os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
                self.assertEqual(own.word_proof(root=root), manifest)

    def test_returned_manifest_is_independent_and_preserves_file_order(self):
        # Catches shared mutable cached dictionaries or sorted reserialization.
        expected = json.loads((ROOT / own.WORD_MANIFEST).read_bytes())
        first = own.word_proof(root=ROOT)
        first['files'].clear()
        first['jobs'][0]['sha256'] = '0' * 64
        second = own.word_proof(root=ROOT)
        self.assertEqual(second, expected)
        self.assertEqual(list(second['files']), list(expected['files']))
        self.assertEqual(own.word_files(ROOT),
                         [own.WORD_MANIFEST, *[own.QA_REPORT + '/' + n for n in expected['files']]])

    def test_changed_callback_helper_and_model_cannot_reuse_semantic_result(self):
        # Catches omitting effective validator/model identities from the key.
        own.word_proof(root=ROOT)
        for target, name, replacement in [
            (own, '_layout_fill', changed_validator),
            (proof, 'parts', changed_validator),
            (own.Application, 'model_validate', classmethod(changed_validator)),
        ]:
            with self.subTest(validator=name), patch.object(target, name, replacement):
                with self.assertRaises(ValueError):
                    own.word_proof(root=ROOT)

    def test_genuine_stage_and_explicit_unbound_publication_are_checked_fresh(self):
        # Catches treating a cached Word result as cached stage/final authority.
        root = self.clone_proof()
        own.word_proof(root=root)
        self.assertTrue(own.staged_candidate('350521', root=root)['can_generate'])
        with patch.object(own, 'STAGE_SHA256', None), self.assertRaises(PermissionError):
            own.staged_candidate('350521', root=root)
        with patch.object(own, 'PUBLICATION_SHA256', None), self.assertRaises(PermissionError):
            own.published_guide('350521', root=root)
        stage = root / own.STAGE_RECEIPT
        raw = stage.read_bytes()
        altered = bytearray(raw)
        altered[len(altered) // 2] ^= 1
        stage.write_bytes(altered)
        with self.assertRaises(ValueError):
            own.staged_candidate('350521', root=root)
        stage.unlink()
        with self.assertRaises((ValueError, OSError)):
            own.staged_candidate('350521', root=root)

    def test_current_supplied_guide_version_is_not_part_of_cached_authority(self):
        # Catches reusing a previous guide/version contract after Word-cache warmup.
        root = self.clone_proof()
        guide = own.staged_candidate('350521', root=root)
        guide['version'] = 1
        old = own.production_contract(guide, 'application', root=root)
        payload = {**old['context'], 'contract_id': old['contract_id'], 'data': old['defaults']}
        updated = deepcopy(guide)
        updated['version'] = 2
        with self.assertRaises(ValueError):
            own.validate_production_request(payload, root=root, guide=updated)
        current = own.production_contract(updated, 'application', root=root)
        self.assertEqual(current['context']['version'], 2)
        self.assertNotEqual(current['contract_id'], old['contract_id'])
        result = own.validate_production_request(
            {**current['context'], 'contract_id': current['contract_id'], 'data': current['defaults']},
            root=root, guide=updated)
        self.assertEqual(result[:2], ('350521', 'application'))

    def test_missing_artifact_and_different_root_cannot_reuse_a_warm_entry(self):
        # Catches a path-independent cache key or bypassed hit-time existence checks.
        first, second = self.clone_proof(), self.clone_proof()
        own.word_proof(root=first)
        own.word_proof(root=second)
        self.assertEqual(cache.info()['misses'], 2)
        (second / own.QA_REPORT / 'ROOT-WORD-VISUAL-REVIEW.json').unlink()
        with self.assertRaises((ValueError, OSError)):
            own.word_proof(root=second)
        self.assertEqual(len(own.word_proof(root=first)['files']), 70)

    def test_distinct_roots_evict_old_entries_with_bounded_serialized_values(self):
        # Catches unbounded retention of per-root proof results.
        roots = [self.clone_proof() for _ in range(5)]
        for root in roots:
            own.word_proof(root=root)
        self.assertEqual(cache.info()['entries'], 4)
        self.assertLessEqual(cache.info()['bytes'], 1024 * 1024)
        before = cache.info()['misses']
        own.word_proof(root=roots[0])
        self.assertEqual(cache.info()['misses'], before + 1)

    def test_concurrent_calls_verify_once_and_return_independent_results(self):
        # Catches unsynchronized miss insertion and shared return objects.
        root = self.clone_proof()
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(lambda _: own.word_proof(root=root), range(4)))
        self.assertEqual((cache.info()['misses'], cache.info()['hits']), (1, 3))
        self.assertTrue(all(row == rows[0] for row in rows))
        rows[0]['files'].clear()
        self.assertTrue(all(len(row['files']) == 70 for row in rows[1:]))


if __name__ == '__main__':
    unittest.main()
