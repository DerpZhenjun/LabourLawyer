"""Warm catalogues stay untouched; any initialization retains the cold proof gate."""
from contextlib import closing, ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import public_seed
from regional_directory import DirectoryStore
from regional_guides import RegionalStore
import test_public_seed as fixtures


class PublicSeedWarmStartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='public-seed-warm-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'release'
        self.seed, self.guide = fixtures.PublicSeedTests().bundle(self.root)
        self.data = Path(self.temp.name) / 'persistent'
        self.guide_path = self.data / 'regional-guides.sqlite'
        self.directory_path = self.data / 'regional-directory.sqlite'

    def fill(self, *, guides=True, areas=True):
        if guides:
            store = RegionalStore(self.guide_path)
            for revision in ['first', 'current']:
                guide = deepcopy(self.guide)
                guide['fields'] = {'synthetic_revision': revision}
                store.put_guide(guide)
            acknowledged = store.record_event({'id': 'synthetic-ack', 'type': 'GUIDE_PAGE_UNAVAILABLE'})
            store.acknowledge([acknowledged['id']], {'ok': True, 'accepted_event_ids': [acknowledged['id']], 'synthetic_only': True})
            store.record_event({'id': 'synthetic-pending', 'type': 'GUIDE_PAGE_UNAVAILABLE'})
        if areas:
            directory = DirectoryStore(self.directory_path)
            directory.put_area({'provider': 'synthetic', 'code': '510199000000', 'province': 'sichuan',
                'city': '成都市', 'district': '既有测试区', 'level': 4,
                'source_url': self.guide['source_url'], 'collected_at': '2026-10-28'})
            directory.enqueue('synthetic', {'state': 'first'})
            directory.claim()
            directory.enqueue('synthetic', {'state': 'pending'})

    def snapshot(self):
        result = {}
        for path in [self.guide_path, self.directory_path]:
            if not path.exists():
                result[path.name] = None
                continue
            with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                rows = tuple(db.iterdump())
            result[path.name] = (path.read_bytes(), rows,
                {suffix: (Path(str(path) + suffix).read_bytes() if Path(str(path) + suffix).exists() else None)
                 for suffix in ['-wal', '-shm', '-journal']})
        return result

    def replace_payload(self, filename, value):
        path = self.seed / filename
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf8')
        manifest = json.loads((self.seed / 'manifest.json').read_text('utf8'))
        manifest['files'][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.seed / 'manifest.json').write_text(json.dumps(manifest), encoding='utf8')

    def forbid_heavy(self, stack):
        return [stack.enter_context(patch.object(public_seed, name,
                    side_effect=AssertionError('warm path reached ' + name)))
                for name in ['public_evidence', 'approved_report_attachment',
                             'oct29_jiangsu_binding', 'checked_reference_adapter']]

    def forbid_stores(self, stack):
        return [stack.enter_context(patch.object(public_seed, name,
                    side_effect=AssertionError('unexpected constructor: ' + name)))
                for name in ['RegionalStore', 'DirectoryStore']]

    def test_repeated_warm_calls_skip_all_heavy_checks_and_preserve_bytes_history_outboxes_and_jobs(self):
        self.fill()
        before = self.snapshot()
        with ExitStack() as stack:
            checks = self.forbid_heavy(stack)
            stores = self.forbid_stores(stack)
            for _ in range(3):
                result = public_seed.bootstrap_public_data(self.root, data_dir=self.data)
                self.assertEqual(result, {'guides_imported': 0, 'directory_imported': 0,
                    'missing_attachments': [], 'state': 'existing_preserved'})
                self.assertEqual(self.snapshot(), before)
            for called in checks + stores:
                called.assert_not_called()
        self.assertFalse((self.root / 'backend/data').exists())

    def test_warm_probe_connects_only_in_read_only_mode_without_creating_other_files(self):
        self.fill()
        before = set(self.data.iterdir())
        real_connect = sqlite3.connect
        connections = []

        def connect(database, *args, **kwargs):
            self.assertTrue(kwargs.get('uri'))
            self.assertIn('?mode=ro', database)
            connections.append(database)
            return real_connect(database, *args, **kwargs)

        with ExitStack() as stack:
            self.forbid_heavy(stack)
            self.forbid_stores(stack)
            stack.enter_context(patch.object(public_seed.sqlite3, 'connect', side_effect=connect))
            public_seed.bootstrap_public_data(self.root, data_dir=self.data)
        self.assertEqual(len(connections), 2)
        self.assertEqual(set(self.data.iterdir()), before)

    def test_warm_path_still_rejects_bad_hash_manifest_schema_and_nonlist_payloads(self):
        self.fill()
        before = self.snapshot()
        originals = {name: (self.seed / name).read_bytes()
                     for name in ['manifest.json', 'guides.json', 'directory.json']}
        for variant in ['guides_hash', 'directory_hash', 'schema', 'manifest_json', 'guides_shape', 'directory_shape']:
            with self.subTest(variant=variant):
                for name, body in originals.items():
                    (self.seed / name).write_bytes(body)
                if variant.endswith('_hash'):
                    (self.seed / (variant.removesuffix('_hash') + '.json')).write_bytes(b'[]')
                elif variant == 'schema':
                    manifest = json.loads(originals['manifest.json'])
                    manifest['schema_version'] = 2
                    (self.seed / 'manifest.json').write_text(json.dumps(manifest), encoding='utf8')
                elif variant == 'manifest_json':
                    (self.seed / 'manifest.json').write_bytes(b'{')
                else:
                    self.replace_payload(variant.removesuffix('_shape') + '.json', {'not': 'a list'})
                with ExitStack() as stack:
                    self.forbid_heavy(stack)
                    self.forbid_stores(stack)
                    with self.assertRaises(ValueError):
                        public_seed.bootstrap_public_data(self.root, data_dir=self.data)
                self.assertEqual(self.snapshot(), before)

    def test_invalid_seed_source_or_adapter_never_rewrites_existing_catalogues(self):
        self.fill()
        before = self.snapshot()
        for change in ['source', 'foreign_template', 'invalid_adapter']:
            with self.subTest(change=change):
                guide = deepcopy(self.guide)
                if change == 'source':
                    guide['source_url'] = 'https://not-official.example/invalid'
                elif change == 'foreign_template':
                    guide['templates'][0]['region_code'] = 'other-region'
                else:
                    guide['templates'][0]['adapter'] = 'unapproved-synthetic-adapter'
                self.replace_payload('guides.json', [guide])
                with ExitStack() as stack:
                    self.forbid_heavy(stack)
                    self.forbid_stores(stack)
                    try:
                        result = public_seed.bootstrap_public_data(self.root, data_dir=self.data)
                    except ValueError as exc:
                        self.fail('Warm existing catalogues must not import or validate seed source records: ' + str(exc))
                self.assertEqual(result['state'], 'existing_preserved')
                self.assertEqual(result['missing_attachments'], [])
                self.assertEqual(self.snapshot(), before)

    def test_existing_unexpected_schema_is_rejected_read_only_before_heavy_checks(self):
        self.fill()
        for path, table in [(self.guide_path, 'regional_guides'), (self.directory_path, 'directory_areas')]:
            with self.subTest(table=table):
                original = path.read_bytes()
                path.unlink()
                with closing(sqlite3.connect(path)) as db:
                    with db:
                        db.execute('CREATE TABLE unexpected(value)')
                        db.execute('INSERT INTO unexpected VALUES(1)')
                before = self.snapshot()
                with ExitStack() as stack:
                    self.forbid_heavy(stack)
                    self.forbid_stores(stack)
                    with self.assertRaisesRegex(ValueError, 'unexpected schema'):
                        public_seed.bootstrap_public_data(self.root, data_dir=self.data)
                self.assertEqual(self.snapshot(), before)
                path.write_bytes(original)

    def test_corrupt_existing_database_is_not_replaced_or_repaired(self):
        self.fill()
        self.directory_path.write_bytes(b'SYNTHETIC CORRUPT SQLITE')
        before = {p.name: p.read_bytes() for p in self.data.iterdir()}
        with ExitStack() as stack:
            self.forbid_heavy(stack)
            self.forbid_stores(stack)
            with self.assertRaises(sqlite3.DatabaseError):
                public_seed.bootstrap_public_data(self.root, data_dir=self.data)
        self.assertEqual({p.name: p.read_bytes() for p in self.data.iterdir()}, before)

    def test_invalid_destination_is_rejected_before_heavy_checks_without_modification(self):
        self.data.write_bytes(b'SYNTHETIC FILE NOT DIRECTORY')
        with ExitStack() as stack:
            self.forbid_heavy(stack)
            self.forbid_stores(stack)
            with self.assertRaisesRegex(ValueError, 'destination must be a directory'):
                public_seed.bootstrap_public_data(self.root, data_dir=self.data)
        self.assertEqual(self.data.read_bytes(), b'SYNTHETIC FILE NOT DIRECTORY')

    def test_missing_or_empty_either_catalogue_cannot_skip_complete_proof_before_construction(self):
        for present in ['guide_only', 'directory_only', 'guide_empty', 'directory_empty', 'both_empty', 'both_missing']:
            with self.subTest(present=present), tempfile.TemporaryDirectory() as folder:
                data = Path(folder) / 'data'
                self.data = data
                self.guide_path = data / 'regional-guides.sqlite'
                self.directory_path = data / 'regional-directory.sqlite'
                self.fill(guides=present in {'guide_only', 'directory_empty'},
                          areas=present in {'directory_only', 'guide_empty'})
                if present in {'guide_empty', 'both_empty'}:
                    RegionalStore(self.guide_path)
                if present in {'directory_empty', 'both_empty'}:
                    DirectoryStore(self.directory_path)
                before = self.snapshot()
                with ExitStack() as stack:
                    stack.enter_context(patch.object(public_seed, 'public_evidence',
                        side_effect=ValueError('synthetic full proof rejected')))
                    self.forbid_stores(stack)
                    with self.assertRaisesRegex(ValueError, 'full proof rejected'):
                        public_seed.bootstrap_public_data(self.root, data_dir=data)
                self.assertEqual(self.snapshot(), before)

    def test_cold_attachment_and_adapter_checks_finish_before_any_store_constructor(self):
        template = self.root / self.guide['templates'][0]['file']
        template.parent.mkdir(parents=True)
        template.write_bytes(b'SYNTHETIC UNIT BYTES; NOT OFFICIAL EVIDENCE OR DOCX')
        guide = deepcopy(self.guide)
        guide['templates'][0]['sha256'] = hashlib.sha256(template.read_bytes()).hexdigest()
        self.replace_payload('guides.json', [guide])
        order = []

        def record(name, result):
            def called(*args, **kwargs):
                order.append(name)
                return result(*args, **kwargs) if callable(result) else result
            return called

        with patch.object(public_seed, 'public_evidence', side_effect=record('proof', {})), \
             patch.object(public_seed, 'approved_report_attachment', side_effect=record('attachment', True)), \
             patch.object(public_seed, 'oct29_jiangsu_binding', return_value=None), \
             patch.object(public_seed, 'checked_reference_adapter', side_effect=record('adapter', 'synthetic')), \
             patch.object(public_seed, 'RegionalStore', side_effect=record('guide_store', RegionalStore)), \
             patch.object(public_seed, 'DirectoryStore', side_effect=record('directory_store', DirectoryStore)):
            result = public_seed.bootstrap_public_data(self.root, data_dir=self.data)
        self.assertEqual(order, ['proof', 'attachment', 'adapter', 'guide_store', 'directory_store'])
        self.assertEqual((result['guides_imported'], result['directory_imported']), (1, 1))

    def test_cold_invalid_source_or_foreign_template_cannot_create_stores(self):
        for change in ['source', 'template_region']:
            with self.subTest(change=change):
                guide = deepcopy(self.guide)
                if change == 'source':
                    guide['source_id'] = 'not-the-source-digest'
                else:
                    guide['templates'][0]['region_code'] = 'foreign'
                self.replace_payload('guides.json', [guide])
                with patch.object(public_seed, 'public_evidence', return_value=None), ExitStack() as stack:
                    self.forbid_stores(stack)
                    with self.assertRaises(ValueError):
                        public_seed.bootstrap_public_data(self.root, data_dir=self.data)
                self.assertFalse(self.data.exists())

    def test_cold_real_missing_attachment_still_disables_generation(self):
        result = public_seed.bootstrap_public_data(self.root, data_dir=self.data)
        self.assertEqual((result['guides_imported'], result['directory_imported']), (1, 1))
        stored = RegionalStore(self.guide_path).inventory()[0]
        self.assertFalse(stored['templates'][0]['can_generate'])
        self.assertEqual(stored['templates'][0]['download_status'], 'local_copy_unavailable')
        self.assertEqual(result['missing_attachments'], [self.guide['templates'][0]['file']])


if __name__ == '__main__':
    unittest.main()
