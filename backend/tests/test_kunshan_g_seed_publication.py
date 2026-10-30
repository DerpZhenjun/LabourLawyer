"""Approved G append tests use complete cold release copies, never the real seed."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import regional_jiangsu_oct31g as own


class KunshanGSeedPublicationTests(unittest.TestCase):
    def setUp(self):
        script=ROOT/'scripts/publish-approved-kunshan-g-seed.py'
        self.assertTrue(script.is_file(),'Need an exact one-guide G append publisher')
        spec=importlib.util.spec_from_file_location('kunshan_g_seed_publication',script)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)

    def release_copy(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        paths=set(own.source_files(ROOT))|{own.SOURCE_FREEZE,own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT}
        paths.update(r['path'] for r in json.loads((ROOT/own.WORD_MANIFEST).read_bytes())['files'])
        for receipt in [own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT]:
            paths.update(r['path'] for r in json.loads((ROOT/receipt).read_bytes())['files'])
        paths.update('data/public-regions/'+name for name in ['guides.json','manifest.json','directory.json'])
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        public=root/'data/public-regions'
        previous=json.loads((public/'guides.json').read_bytes())[:205]
        body=self.module.encoded(previous)
        self.assertEqual(sha256(body).hexdigest(),self.module.BASE_GUIDES_SHA256)
        (public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes())
        manifest.update(guides=205,generatable_localities=188)
        manifest['files']['guides.json']=sha256(body).hexdigest()
        (public/'manifest.json').write_bytes(self.module.encoded(manifest))
        return root

    def publish(self,root,**kwargs):
        with patch('sqlite3.connect',side_effect=AssertionError('Seed publisher must never open a DB')):
            return self.module.publish(root,**kwargs)

    def snapshot(self,root):
        return {name:(root/'data/public-regions'/name).read_bytes() for name in ['guides.json','manifest.json','directory.json']}

    def rehash(self,root,rows):
        public=root/'data/public-regions';body=self.module.encoded(rows);(public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes())
        manifest['files']['guides.json']=sha256(body).hexdigest()
        (public/'manifest.json').write_bytes(self.module.encoded(manifest))

    def test_dry_run_append_exact205_directory_backup_and_idempotence(self):
        root=self.release_copy();before=self.snapshot(root)
        self.assertEqual(self.publish(root)['status'],'dry_run')
        self.assertEqual(self.snapshot(root),before);self.assertFalse((root/'.runtime').exists())
        with patch.object(own,'ROOT',root/'checkout-not-available'):
            result=self.publish(root,execute=True)
        self.assertEqual((result['guides_after'],result['generatable_localities_after']),(206,189))
        after=self.snapshot(root);rows=json.loads(after['guides.json'])
        self.assertEqual(self.module.encoded(rows[:205]),before['guides.json'])
        self.assertEqual(after['directory.json'],before['directory.json'])
        self.assertEqual(rows[-1]['source_id'],'d39444ab7f4bcaea2ea91473')
        self.assertIs(rows[-1]['published'],True);self.assertIsNotNone(own.public_evidence(rows[-1],root))
        backup=root/self.module.BACKUP
        for name in ['guides.json','manifest.json']:self.assertEqual((backup/name).read_bytes(),before[name])
        self.assertEqual(self.publish(root,execute=True)['status'],'already_published_exact')
        self.assertEqual(self.snapshot(root),after);self.assertFalse(list(root.rglob('*.sqlite')))
        self.assertFalse((root/'backend/data').exists())

    def test_rehashed_changed_old205_is_never_replaced(self):
        root=self.release_copy();rows=json.loads(self.snapshot(root)['guides.json'])
        rows[0]['authority']='unexpected';self.rehash(root,rows);before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before);self.assertFalse((root/'.runtime').exists())

    def test_approval_pins_and_missing_final_evidence_fail_without_checkout_fallback(self):
        final=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
        for relative in [own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT,final['files'][-1]['path']]:
            root=self.release_copy();before=self.snapshot(root);(root/relative).write_bytes(b'tampered')
            with self.subTest(path=relative),self.assertRaises((ValueError,OSError)):
                self.publish(root,execute=True)
            self.assertEqual(self.snapshot(root),before);self.assertFalse((root/'.runtime').exists())
        root=self.release_copy();before=self.snapshot(root)
        for bad in [None,'0'*64]:
            with patch.object(own,'PUBLICATION_SHA256',bad),self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_second_file_commit_failure_rolls_back_both_files(self):
        root=self.release_copy();before=self.snapshot(root);original=Path.replace
        def fail_manifest(path,target):
            if path.name=='manifest.json.kunshan-g-next':raise OSError('second commit injected')
            return original(path,target)
        with patch.object(Path,'replace',fail_manifest),self.assertRaises(OSError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        self.assertFalse(list((root/'data/public-regions').glob('*.kunshan-g-next')))
        self.assertFalse((root/own.QA_REPORT/'PUBLISHED-GUIDE.json').exists())
        self.assertEqual((root/self.module.BACKUP/'guides.json').read_bytes(),before['guides.json'])

    def test_publication_report_failure_rolls_back_and_removes_only_owned_reports(self):
        root=self.release_copy();before=self.snapshot(root);original=Path.open
        def fail_report(path,*args,**kwargs):
            if path.name=='PUBLICATION.json' and args and args[0]=='xb':raise OSError('report write injected')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',fail_report),self.assertRaises(OSError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        self.assertFalse((root/own.QA_REPORT/'PUBLISHED-GUIDE.json').exists())
        self.assertFalse((root/own.QA_REPORT/'PUBLICATION.json').exists())

    def test_existing_g_tamper_and_noncanonical_completed_bytes_are_refused(self):
        root=self.release_copy();self.publish(root,execute=True)
        rows=json.loads(self.snapshot(root)['guides.json']);rows[-1]['can_generate']=1
        self.rehash(root,rows);before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        root=self.release_copy();self.publish(root,execute=True);public=root/'data/public-regions'
        rows=json.loads((public/'guides.json').read_bytes());body=(json.dumps(rows,ensure_ascii=False,indent=1)+'\n').encode()
        (public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes());manifest['files']['guides.json']=sha256(body).hexdigest()
        (public/'manifest.json').write_bytes(self.module.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_foreign_pending_report_and_backup_are_preserved(self):
        for relative in ['data/public-regions/guides.json.kunshan-g-next',
                         (own.QA_REPORT/'PUBLICATION.json').as_posix(),self.module.BACKUP+'/guides.json']:
            root=self.release_copy();target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(b'foreign operation: preserve');before=self.snapshot(root)
            with self.subTest(path=relative),self.assertRaises(ValueError):self.publish(root,execute=True)
            self.assertEqual(target.read_bytes(),b'foreign operation: preserve');self.assertEqual(self.snapshot(root),before)

    def test_directory_rehashed_tamper_and_typed_manifest_counts_are_refused(self):
        root=self.release_copy();public=root/'data/public-regions'
        directory=(public/'directory.json').read_bytes()+b' ';(public/'directory.json').write_bytes(directory)
        manifest=json.loads((public/'manifest.json').read_bytes());manifest['files']['directory.json']=sha256(directory).hexdigest()
        (public/'manifest.json').write_bytes(self.module.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        root=self.release_copy();public=root/'data/public-regions';manifest=json.loads((public/'manifest.json').read_bytes())
        manifest['guides']=True;(public/'manifest.json').write_bytes(self.module.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_explicit_root_execution_types_and_g_only_paths(self):
        for absent in [None,'',' ']:
            with self.assertRaises(ValueError):self.publish(absent)
        root=self.release_copy();before=self.snapshot(root)
        for flag in [1,'true',None]:
            with self.assertRaises(ValueError):self.publish(root,execute=flag)
        self.assertEqual(self.snapshot(root),before)
        self.assertIn('kunshan-g',self.module.BACKUP)
        self.assertIn('kunshan',str(self.module.REPORT))
        self.assertNotIn('jiangsu-f',self.module.BACKUP)
        with self.assertRaises(ValueError):own.path_at(root,'../escape')


if __name__=='__main__':unittest.main()
