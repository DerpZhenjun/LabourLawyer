"""Real providers against a temporary copy containing only approved public files."""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_anhui_oct29 import load_guide
from regional_zhejiang_oct29 import parse_capture as ningbo
from regional_hunan_oct29b import parse_capture as hunan

if importlib.util.find_spec('regional_public_provenance'):
    from regional_public_provenance import public_evidence, approved_report_attachment
else:
    public_evidence = approved_report_attachment = None

REPORTS = {
    'ah': 'reports/nationwide-verification-20261029/anhui',
    'nb': 'reports/nationwide-verification-20261029/zhejiang',
    'hn': 'reports/nationwide-verification-20261029-b/hunan',
}


class PublicProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime = ROOT / '.runtime'; runtime.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=runtime)
        cls.public = Path(cls.temp.name)
        for report in REPORTS.values():
            white_path = ROOT / report / 'PUBLIC-WHITELIST.json'
            white = json.loads(white_path.read_text('utf8'))
            paths = [x['file'] for x in white] if isinstance(white, list) else list(white['files'])
            for relative in paths + [report + '/PUBLIC-WHITELIST.json']:
                if not relative.startswith(report + '/'):
                    continue
                target = cls.public / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
        cls.guides = {
            'yaohai': load_guide('yaohai', root=cls.public),
            'feidong': load_guide('feidong', root=cls.public),
            **{n: ningbo(n, capture_root=cls.public / REPORTS['nb']) for n in ['haishu', 'yinzhou']},
            **{n: hunan(n, capture_root=cls.public / REPORTS['hn']) for n in ['tianxin', 'xiangjiang']},
        }

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def api(self):
        self.assertTrue(callable(public_evidence), 'public_evidence helper is missing')
        self.assertTrue(callable(approved_report_attachment), 'attachment helper is missing')

    @contextmanager
    def changed(self, relative, body=None):
        path = self.public / relative; original = path.read_bytes()
        if body is None: path.unlink()
        else: path.write_bytes(body)
        try: yield
        finally: path.write_bytes(original)

    def test_public_copy_rebuilds_evidence_and_all_own_originals(self):
        self.api()
        self.assertFalse((self.public / 'backend').exists())
        count = 0
        for guide in self.guides.values():
            self.assertEqual(public_evidence(guide, self.public), guide['evidence'])
            for template in guide['templates']:
                self.assertTrue(approved_report_attachment(guide, template, self.public), template['file'])
                count += 1
        self.assertEqual(count, 24)  # AH10 + NB6 + HN8, never neighboring-source substitutions.

    def test_safe_evidence_copy_does_not_echo_caller_data(self):
        self.api(); guide = deepcopy(self.guides['feidong'])
        result = public_evidence(guide, self.public)
        result['基本信息']['capture_file'] = 'untrusted'
        self.assertNotEqual(result, public_evidence(guide, self.public))
        guide['evidence'] = {'cookie': 'forged', 'capture_file': 'private/raw.har'}
        self.assertIsNone(public_evidence(guide, self.public))
        self.assertFalse(approved_report_attachment(guide, guide['templates'][0], self.public))

    def test_store_metadata_and_capability_markers_do_not_change_facts(self):
        self.api()
        for original in self.guides.values():
            guide = deepcopy(original)
            guide.update(source_id='store-metadata', version=7, content_hash='hash', region_id='region', can_generate=True)
            for template in guide['templates']:
                template.update(can_generate=True, document_types=['application'], adapter='marker',
                                content_kind='filled_official_blank', generation_label='填写', region_code=guide['region_code'])
            self.assertEqual(public_evidence(guide, self.public), original['evidence'])
            self.assertTrue(approved_report_attachment(guide, guide['templates'][0], self.public))

    def test_missing_evidence_can_be_reconstructed_but_missing_disk_proof_cannot(self):
        self.api()
        for name, original in self.guides.items():
            guide = deepcopy(original); guide.pop('evidence')
            self.assertEqual(public_evidence(guide, self.public), original['evidence'])
            proof = (original['evidence']['基本信息'] if name in {'feidong', 'yaohai'} else original['evidence'])['capture_file']
            with self.changed(proof):
                self.assertIsNone(public_evidence(original, self.public))
                self.assertFalse(approved_report_attachment(original, original['templates'][0], self.public))
            with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as empty:
                self.assertIsNone(public_evidence(original, Path(empty)))
                self.assertFalse(approved_report_attachment(original, original['templates'][0], Path(empty)))

    def test_changed_public_and_source_manifests_fail_closed(self):
        self.api()
        for name, report, manifest in [('feidong', REPORTS['ah'], 'source-lock.json'),
                                       ('haishu', REPORTS['nb'], 'SOURCE-MANIFEST.json'),
                                       ('tianxin', REPORTS['hn'], 'SOURCE-MANIFEST.json')]:
            guide = self.guides[name]
            for filename in ['PUBLIC-WHITELIST.json', manifest]:
                path = report + '/' + filename
                changed = b'[]' if report == REPORTS['ah'] else b'{"files": {}}'
                if filename == manifest: changed = (self.public / path).read_bytes() + b' '
                with self.changed(path, changed):
                    self.assertIsNone(public_evidence(guide, self.public))
                    self.assertFalse(approved_report_attachment(guide, guide['templates'][0], self.public))

    def test_public_code_only_whitelist_update_does_not_unpin_source_evidence(self):
        self.api()
        for name, report in [('feidong', REPORTS['ah']), ('haishu', REPORTS['nb']), ('tianxin', REPORTS['hn'])]:
            relative = report + '/PUBLIC-WHITELIST.json'
            white = json.loads((self.public / relative).read_text('utf8'))
            if isinstance(white, list):
                white.append({'file': 'backend/new-helper.py', 'sha256': '0' * 64})
            else:
                white['files']['backend/new-helper.py'] = {'sha256': '0' * 64, 'bytes': 10}
            with self.changed(relative, json.dumps(white).encode('utf8')):
                self.assertEqual(public_evidence(self.guides[name], self.public), self.guides[name]['evidence'])

    def test_wrong_scope_facts_and_attachments_are_rejected(self):
        self.api()
        for name in ['feidong', 'haishu', 'tianxin', 'xiangjiang']:
            original = self.guides[name]
            for key, value in [('district', '其他区'), ('authority', '其他机关'), ('source_url', 'https://other.gov.cn'),
                               ('service_code', 'forged'), ('materials', []), ('sections', {}), ('fields', {})]:
                guide = deepcopy(original); guide[key] = value
                self.assertIsNone(public_evidence(guide, self.public), key)
                self.assertFalse(approved_report_attachment(guide, original['templates'][0], self.public), key)
            template = original['templates'][0]
            for key, value in [('file', '../private.docx'), ('sha256', '0' * 64), ('official_kind', 'other'),
                               ('download_url', 'https://untrusted.gov.cn/form.docx'), ('material_id', 'other'), ('region_code', '000000')]:
                changed = deepcopy(template); changed[key] = value
                self.assertFalse(approved_report_attachment(original, changed, self.public), key)
            self.assertFalse(approved_report_attachment(original, self.guides['yaohai']['templates'][0], self.public))
        guide = deepcopy(self.guides['xiangjiang']); guide['scope_identity']['scope'] = '全市通用'
        self.assertIsNone(public_evidence(guide, self.public))

    def test_changed_original_cannot_be_reauthorized_with_forged_metadata(self):
        self.api()
        for name in ['feidong', 'haishu', 'tianxin']:
            guide = deepcopy(self.guides[name]); template = guide['templates'][0]
            relative = template['file']; body = (self.public / relative).read_bytes() + b'changed'
            template.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
            with self.changed(relative, body):
                self.assertIsNone(public_evidence(guide, self.public))
                self.assertFalse(approved_report_attachment(guide, template, self.public))

    def test_hunan_derived_chain_is_bound_to_own_doc_and_public_manifest(self):
        self.api()
        report = REPORTS['hn']
        manifest = json.loads((self.public / report / 'DERIVED-MANIFEST.json').read_text('utf8'))
        for name in ['tianxin', 'xiangjiang']:
            guide = self.guides[name]
            template = next(t for t in guide['templates'] if Path(t['file']).stem == '1624951667887')
            row = next(x for x in manifest['files'] if x['district'] == name and x['file'].endswith('1624951667887.docx'))
            with self.changed(report + '/' + row['file']):
                self.assertFalse(approved_report_attachment(guide, template, self.public))
            with self.changed(report + '/DERIVED-MANIFEST.json', b'{}'):
                self.assertFalse(approved_report_attachment(guide, template, self.public))

    def test_unsupported_regions_and_bad_input_do_not_gain_report_access(self):
        self.api()
        for guide in [None, [], {}, {'province': 'jiangsu', 'region_code': '320281'},
                      {'province': 'guangdong', 'region_code': '440604', 'evidence': {'capture_file': 'reports/anything'}}]:
            self.assertIsNone(public_evidence(guide, self.public))
            self.assertFalse(approved_report_attachment(guide, {}, self.public))
        self.assertIsNone(public_evidence(self.guides['feidong'], None))
        self.assertFalse(approved_report_attachment(self.guides['feidong'], None, self.public))

    def test_symlink_to_original_repository_is_not_public_root_proof(self):
        self.api()
        relative = REPORTS['ah'] + '/source-lock.json'
        path = self.public / relative
        body = path.read_bytes(); path.unlink()
        try:
            try: path.symlink_to(ROOT / relative)
            except OSError as exc: self.skipTest('OS does not permit symlink creation: ' + str(exc))
            guide = self.guides['feidong']
            self.assertIsNone(public_evidence(guide, self.public))
            self.assertFalse(approved_report_attachment(guide, guide['templates'][0], self.public))
        finally:
            if path.is_symlink(): path.unlink()
            path.write_bytes(body)


if __name__ == '__main__': unittest.main()
