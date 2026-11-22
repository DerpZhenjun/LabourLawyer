"""Measurement contracts: first-source attempts cannot masquerade as coverage."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
import zipfile

from first_source_measurement import aggregate, original_fingerprint, verify_files


def fixture():
    cohort = {'frozen_at': '2026-11-22T00:00:00+00:00',
              'regions': [{'code': '100001'}, {'code': '100002'}]}
    records = []
    for code in ['100001', '100002']:
        records.append({'region_code': code, 'completed_at': '2026-11-22T01:00:00+00:00',
                        'work_seconds': 300, 'censored': True, 'sources': [], 'templates': [],
                        'coverage': {'own_source_found': True, 'own_guide_verified': False,
                                     'materials_verified': False, 'blank_original_acquired': False,
                                     'generation_ready': False},
                        'root_review': {'own_scope_verified': False, 'hashes_verified': True}})
    return cohort, records


class FirstSourceMeasurementTests(unittest.TestCase):
    def test_exact_frozen_cohort_rejects_duplicates_and_replacements(self):
        c, rows = fixture()
        for codes in [['100001', '100001'], ['100001', '999999'], ['100001']]:
            bad = [deepcopy(rows[0]) for _ in codes]
            for row, code in zip(bad, codes): row['region_code'] = code
            with self.assertRaises(ValueError): aggregate(c, bad, set())

    def test_source_only_and_censored_attempts_have_no_finite_completion_eta(self):
        c, rows = fixture(); result = aggregate(c, rows, set())
        self.assertEqual(result['counts']['own_source_found'], 2)
        self.assertEqual(result['counts']['generation_ready'], 0)
        self.assertEqual(result['censored_regions'], 2)
        self.assertIsNone(result['full_completion_eta_seconds'])
        self.assertIsNone(result['templates']['new_unique_ratio'])
        self.assertEqual(result['research_wall_seconds'], 3600)
        self.assertEqual(result['attempts_per_wall_hour'], 2)

    def test_wrong_jurisdiction_does_not_pass_guide_review(self):
        c, rows = fixture(); rows[0]['coverage']['own_guide_verified'] = True
        with self.assertRaisesRegex(ValueError, 'scope'): aggregate(c, rows, set())

    def test_materials_blank_and_generation_are_independent_gates(self):
        c, rows = fixture(); rows[0]['root_review']['own_scope_verified'] = True
        rows[0]['coverage']['own_guide_verified'] = True
        result = aggregate(c, rows, set())
        self.assertEqual(result['counts']['own_guide_verified'], 1)
        self.assertEqual(result['counts']['materials_verified'], 0)
        self.assertEqual(result['counts']['generation_ready'], 0)
        rows[0]['coverage']['generation_ready'] = True
        with self.assertRaisesRegex(ValueError, 'acceptance'): aggregate(c, rows, set())

    def test_samples_unknown_and_unreviewed_blanks_are_not_denominators(self):
        c, rows = fixture()
        rows[0]['templates'] = [{'classification': x, 'sha256': x, 'root_blank_verified': False}
                               for x in ['sample', 'instruction', 'unknown', 'blank']]
        result = aggregate(c, rows, set())
        self.assertEqual(result['templates']['qualified_blank_bindings'], 0)
        self.assertIsNone(result['templates']['new_binding_ratio'])

    def test_raw_byte_novelty_preserves_each_regional_binding(self):
        c, rows = fixture()
        rows[0]['templates'] = [{'classification': 'blank', 'sha256': s,
                                 'root_blank_verified': True} for s in ['old', 'new']]
        rows[1]['templates'] = [{'classification': 'blank', 'sha256': 'new',
                                 'root_blank_verified': True}]
        result = aggregate(c, rows, {'old'})['templates']
        self.assertEqual(result['qualified_blank_bindings'], 3)
        self.assertEqual(result['unique_originals'], 2)
        self.assertEqual(result['new_unique_originals'], 1)
        self.assertAlmostEqual(result['new_unique_ratio'], .5)
        self.assertAlmostEqual(result['new_binding_ratio'], 2/3)

    def test_zip_container_metadata_only_reuse_does_not_ignore_xml_changes(self):
        with tempfile.TemporaryDirectory() as d:
            files = [Path(d)/str(i) for i in range(3)]
            for i, p in enumerate(files):
                with zipfile.ZipFile(p, 'w') as z:
                    entry = zipfile.ZipInfo('word/document.xml', (2020+i, 1, 1, 0, 0, 0))
                    z.writestr(entry, 'same' if i < 2 else 'changed')
                    z.writestr('docProps/core.xml', 'all members matter')
            a, b, c = map(original_fingerprint, files)
            self.assertNotEqual(a['sha256'], b['sha256'])
            self.assertEqual(a['member_sha256'], b['member_sha256'])
            self.assertNotEqual(a['member_sha256'], c['member_sha256'])

    def test_two_urls_same_local_blank_do_not_inflate_regional_bindings(self):
        c, rows = fixture()
        rows[0]['templates'] = [{'classification': 'blank', 'sha256': 'same',
                                 'root_blank_verified': True, 'url': url}
                                for url in ['blank-url', 'mislabelled-example-url']]
        result = aggregate(c, rows, set())['templates']
        self.assertEqual(result['qualified_blank_url_bindings'], 2)
        self.assertEqual(result['qualified_blank_bindings'], 1)

    def test_binary_document_with_embedded_zip_is_not_treated_as_docx(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'legacy.doc'
            path.write_bytes(bytes.fromhex('d0cf11e0a1b11ae1') + b'legacy word body')
            with zipfile.ZipFile(path, 'a') as archive:
                archive.writestr('word/document.xml', 'embedded payload')
            self.assertTrue(zipfile.is_zipfile(path))
            result = original_fingerprint(path)
            self.assertIsNone(result['member_sha256'])
            self.assertEqual(result['identity'], 'raw_bytes')

    def test_archive_hashes_and_workspace_boundary_are_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'one').write_bytes(b'one')
            self.assertEqual(verify_files(root,[{'relative_path':'one','sha256':sha256(b'one').hexdigest()}]),1)
            with self.assertRaises(ValueError): verify_files(root,[{'relative_path':'one','sha256':'wrong'}])
            with self.assertRaises(ValueError): verify_files(root,[{'relative_path':'../escape','sha256':'wrong'}])

    def test_followup_and_incomplete_timing_never_become_full_completion_mean(self):
        c, rows=fixture(); rows[0]['timing_incomplete']=True
        rows[0]['followup_work_seconds']=125
        result=aggregate(c, rows, set())
        self.assertEqual(result['recorded_region_dwell_seconds'],725)
        self.assertEqual(result['timing_incomplete_regions'],['100001'])
        self.assertIsNone(result['full_completion_eta_seconds'])


if __name__ == '__main__': unittest.main()
