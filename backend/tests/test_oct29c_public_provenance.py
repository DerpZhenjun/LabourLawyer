"""C4 public-only provenance, independent of private samples and the source checkout."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_hunan_oct29c as hn
import regional_jiangsu_oct29c as js
from regional_public_provenance import public_evidence, approved_report_attachment


class Oct29CPublicProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.public = Path(cls.temp.name)
        for report in [str(hn.REPORT), js.REPORT.as_posix(), hn.ADAPTATION]:
            white = json.loads((ROOT / report / 'PUBLIC-WHITELIST.json').read_text('utf8'))
            for relative in [*white['files'], report + '/PUBLIC-WHITELIST.json']:
                if not relative.startswith(report + '/'):
                    continue
                if report == hn.ADAPTATION and '/derived/' not in relative and not relative.endswith(('DERIVED-MANIFEST.json', 'PUBLIC-WHITELIST.json')):
                    continue
                dst = cls.public / relative; dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, dst)
        cls.guides = {n: hn.parse_capture(n, cls.public / hn.REPORT) for n in hn.SPECS}
        cls.guides.update({code: js.parse_capture(code, cls.public / js.REPORT) for code in sorted(js.SUPPORTED)})

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    @contextmanager
    def changed(self, relative, content=None):
        p = self.public / relative; original = p.read_bytes()
        if content is None: p.unlink()
        else: p.write_bytes(content)
        try: yield
        finally: p.write_bytes(original)

    def test_canonical_public_only_evidence_and_exact_originals(self):
        approved = 0; denied_samples = 0
        for name, g in self.guides.items():
            self.assertEqual(public_evidence(g, self.public), g['evidence'], name)
            for t in g['templates']:
                if g['province'] == 'jiangsu' and t['official_kind'] == 'sample':
                    self.assertFalse(approved_report_attachment(g, t, self.public)); denied_samples += 1
                else:
                    self.assertTrue(approved_report_attachment(g, t, self.public), t['file']); approved += 1
        self.assertEqual(approved, 18)
        self.assertEqual(denied_samples, 8)
        self.assertFalse((self.public / 'backend').exists())
        self.assertFalse([p for p in (self.public / js.REPORT).rglob('*') if p.is_file() and 'sample' in p.parts])

    def test_precise_capability_markers_survive_publishing(self):
        for name, raw in self.guides.items():
            g = hn.with_capabilities(raw, root=self.public) if raw['province'] == 'hunan' else js.with_capabilities(raw, root=self.public)
            if raw['province'] == 'jiangsu':
                for t in g['templates']:
                    if t['can_generate']:
                        t.update(adapter=js.ADAPTER, content_kind='filled_official_blank', generation_label='依据本区自身官方空白表格填写')
            g.update(published=True, publication_status='published', candidate_web_qa='PASS', version=201, warnings=['平台说明'])
            self.assertEqual(public_evidence(g, self.public), raw['evidence'], name)
            for t in g['templates']:
                if t['can_generate']:
                    self.assertTrue(approved_report_attachment(g, t, self.public))
            wrong = deepcopy(g); wrong['templates'][0]['generation_adapter'] = 'foreign-region-adapter'
            self.assertIsNone(public_evidence(wrong, self.public))
            generated = next(t for t in g['templates'] if t['can_generate'])
            for key, value in [('content_kind', 'arbitrary'), ('render_status', 'NOT_RUN')]:
                wrong = deepcopy(g); t = next(t for t in wrong['templates'] if t['id'] == generated['id']); t[key] = value
                self.assertIsNone(public_evidence(wrong, self.public), key)

    def test_identity_facts_materials_and_source_id_are_not_markers(self):
        for raw in self.guides.values():
            for field, value in [('region_code', '000000'), ('source_id', 'wrong'), ('source_url', 'https://other.gov.cn'),
                                 ('authority', '其他机关'), ('materials', []), ('fields', {}), ('sections', {})]:
                g = deepcopy(raw); g[field] = value
                self.assertIsNone(public_evidence(g, self.public), field)
                self.assertFalse(approved_report_attachment(g, raw['templates'][0], self.public))
            g = deepcopy(raw); g['evidence'] = {'capture_file': 'reports/arbitrary/file'}
            self.assertIsNone(public_evidence(g, self.public))

    def test_attachment_paths_hashes_kinds_and_derived_substitution_rejected(self):
        for raw in self.guides.values():
            t = raw['templates'][0]
            for key, value in [('file', 'reports/arbitrary/form.docx'), ('sha256', '0' * 64),
                               ('official_kind', 'blank' if t['official_kind'] != 'blank' else 'sample'),
                               ('material_id', 'wrong'), ('download_status', 'downloaded_elsewhere')]:
                changed = deepcopy(t); changed[key] = value
                self.assertFalse(approved_report_attachment(raw, changed, self.public), key)
            with self.changed(t['file'], b'changed'):
                self.assertIsNone(public_evidence(raw, self.public))
                self.assertFalse(approved_report_attachment(raw, t, self.public))

    def test_hunan_own_conversion_chain_required_even_for_public_evidence(self):
        rows = json.loads((self.public / hn.ADAPTATION / 'DERIVED-MANIFEST.json').read_text('utf8'))['files']
        for name in hn.SPECS:
            g = self.guides[name]; row = next(r for r in rows if r['district'] == name)
            for relative in [row['source'], row['file'], hn.ADAPTATION + '/DERIVED-MANIFEST.json']:
                with self.changed(relative):
                    self.assertIsNone(public_evidence(g, self.public), relative)
                    self.assertFalse(approved_report_attachment(g, g['templates'][0], self.public))

    def test_no_empty_root_or_private_repository_fallback(self):
        for g in self.guides.values():
            with tempfile.TemporaryDirectory() as empty:
                self.assertIsNone(public_evidence(g, empty))
                self.assertFalse(approved_report_attachment(g, g['templates'][0], empty))
            self.assertIsNone(public_evidence(g, None))
        g = self.guides['320411']
        manifest = js.REPORT.as_posix() + '/SOURCE-MANIFEST.json'
        with self.changed(manifest, b'{}'):
            self.assertIsNone(public_evidence(g, self.public))
        for unknown in [None, {}, {'province': 'jiangsu', 'region_code': []}, {'province': 'jiangsu', 'region_code': '320408'},
                        {'province': 'hunan', 'region_code': '430104', 'evidence': {'capture_file': 'reports/anything'}}]:
            self.assertIsNone(public_evidence(unknown, self.public))
            self.assertFalse(approved_report_attachment(unknown, {}, self.public))

    def test_sample_bytes_on_disk_do_not_override_not_distributed_status(self):
        g = self.guides['320411']; t = next(t for t in g['templates'] if t['official_kind'] == 'sample')
        path = self.public / t['file']; path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(b'synthetic fake reference sample')
            self.assertFalse(approved_report_attachment(g, t, self.public))
            changed = deepcopy(t); changed['download_status'] = 'downloaded'
            self.assertFalse(approved_report_attachment(g, changed, self.public))
        finally: path.unlink()

    def test_original_repository_symlink_is_not_proof_inside_public_root(self):
        g = self.guides['320411']; relative = g['templates'][0]['file']; path = self.public / relative
        original = path.read_bytes(); path.unlink()
        try:
            try: path.symlink_to(ROOT / relative)
            except OSError as exc: self.skipTest('Windows symlink permission unavailable: ' + str(exc))
            self.assertIsNone(public_evidence(g, self.public))
            self.assertFalse(approved_report_attachment(g, g['templates'][0], self.public))
        finally:
            if path.is_symlink(): path.unlink()
            path.write_bytes(original)
