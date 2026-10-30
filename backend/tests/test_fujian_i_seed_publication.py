"""Only Temp seed copies; real Root I stage/final receipts and proof leaves."""
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
import regional_fujian_oct31i as own


class FujianISeedPublicationTests(unittest.TestCase):
    def setUp(self):
        source=ROOT/'scripts/publish-approved-fujian-i-seed.py'
        self.assertTrue(source.is_file(),'Need exact two-own-I seed publisher')
        spec=importlib.util.spec_from_file_location('i_seed_test',source)
        self.p=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.p)

    def copy(self,proof=True):
        if proof and (self.p.FINAL_SHA256 is None or not (ROOT/own.PUBLICATION_RECEIPT).exists()):
            self.skipTest('Waiting for actual independently issued Root final receipt')
        temporary=tempfile.TemporaryDirectory(prefix='i-seed-');self.addCleanup(temporary.cleanup);root=Path(temporary.name).resolve()
        paths={'data/public-regions/'+name for name in ['guides.json','manifest.json','directory.json']}
        if proof:
            paths.update(own.source_files(ROOT));paths.update([own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT])
            for name in [own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT]:
                paths.update(row['path'] for row in json.loads((ROOT/name).read_bytes())['files'])
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        public=root/'data/public-regions';rows=json.loads((public/'guides.json').read_bytes())[:207]
        body=self.p.encoded(rows);self.assertEqual(sha256(body).hexdigest(),self.p.BASE_GUIDES_SHA256)
        (public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes());manifest.update(guides=207,generatable_localities=190)
        manifest['files']['guides.json']=self.p.BASE_GUIDES_SHA256;(public/'manifest.json').write_bytes(self.p.encoded(manifest))
        return root

    def run_publish(self,root,**options):
        with patch('sqlite3.connect',side_effect=AssertionError('Seed publisher must not open DB')):
            return self.p.publish(root,**options)

    def snapshot(self,root):return {n:(root/'data/public-regions'/n).read_bytes() for n in ['guides.json','manifest.json','directory.json']}

    def rehash(self,root,rows):
        public=root/'data/public-regions';body=self.p.encoded(rows);(public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes());manifest.update(guides=len(rows),generatable_localities=self.p.generating(rows))
        manifest['files']['guides.json']=sha256(body).hexdigest();(public/'manifest.json').write_bytes(self.p.encoded(manifest))

    def test_global_unpinned_final_and_missing_root_refuse_without_seed_write(self):
        root=self.copy(False);before=self.snapshot(root)
        with patch.object(own,'PUBLICATION_SHA256',None),self.assertRaises(ValueError):self.run_publish(root,execute=True)
        with patch.object(self.p,'FINAL_SHA256',None),self.assertRaises(ValueError):self.run_publish(root,execute=True)
        for absent in [None,'',' ']:
            with self.assertRaises((ValueError,OSError)):self.run_publish(absent)
        self.assertEqual(self.snapshot(root),before);self.assertFalse((root/'.runtime').exists())

    def test_dryrun_two_exact_own_rows_prefix_directory_and_exact_idempotence(self):
        root=self.copy();before=self.snapshot(root)
        self.assertEqual(self.run_publish(root)['status'],'dry_run');self.assertEqual(self.snapshot(root),before)
        self.assertFalse((root/'.runtime').exists())
        with patch.object(own,'ROOT',root/'absent-checkout'):result=self.run_publish(root,execute=True)
        self.assertEqual((result['guides_after'],result['generatable_localities_after']),(209,192))
        after=self.snapshot(root);rows=json.loads(after['guides.json'])
        self.assertEqual(self.p.encoded(rows[:207]),before['guides.json']);self.assertEqual(after['directory.json'],before['directory.json'])
        self.assertEqual([g['region_code'] for g in rows[-2:]],['350103','350104'])
        self.assertEqual(len({g['source_id'] for g in rows[-2:]}),2)
        for g in rows[-2:]:
            self.assertEqual(g['verification_status'],'partial');self.assertIs(g['published'],True)
            self.assertIsNone(g['committee_full_name']);self.assertIs(g['sample_contents_verified'],False)
            self.assertEqual(sum(t['can_generate'] is True for t in g['templates']),2)
            self.assertTrue(all(t['download_status']=='downloaded' and t['sample_contents_verified'] is False and not t['can_generate'] for t in g['templates'] if t['official_kind']=='sample'))
            self.assertTrue(all(not t['can_generate'] for t in g['templates'] if t['content_role']=='scanning_instructions_only'))
        for name in ['guides.json','manifest.json']:self.assertEqual((root/self.p.BACKUP/name).read_bytes(),before[name])
        self.assertEqual(self.run_publish(root,execute=True)['status'],'already_published_exact');self.assertEqual(self.snapshot(root),after)

    def test_rehashed_old_prefix_tamper_refuses_without_rebuild(self):
        root=self.copy();rows=json.loads(self.snapshot(root)['guides.json']);rows[0]['authority']='changed';self.rehash(root,rows);before=self.snapshot(root)
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_second_file_replace_failure_rolls_back_pair_and_keeps_backup(self):
        root=self.copy();before=self.snapshot(root);replace=Path.replace
        def fail(path,target):
            if path.name=='manifest.json.fujian-i-next':raise OSError('second replacement failure')
            return replace(path,target)
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        self.assertFalse(list((root/'data/public-regions').glob('*.fujian-i-next')))
        self.assertFalse((root/own.QA_REPORT/'PUBLISHED-GUIDES.json').exists())

    def test_report_failure_rolls_back_and_removes_only_own_new_reports(self):
        root=self.copy();before=self.snapshot(root);open_=Path.open
        def fail(path,*args,**kwargs):
            if path.name=='PUBLICATION.json' and args and args[0]=='xb':raise OSError('publication report failure')
            return open_(path,*args,**kwargs)
        with patch.object(Path,'open',fail),self.assertRaises(OSError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        for name in ['PUBLISHED-GUIDES.json','PUBLICATION.json']:self.assertFalse((root/own.QA_REPORT/name).exists())

    def test_one_row_partial_reordered_or_tampered_completion_refuses(self):
        for mutation in ['partial','reverse','tamper']:
            root=self.copy();self.run_publish(root,execute=True);rows=json.loads(self.snapshot(root)['guides.json'])
            if mutation=='partial':rows.pop()
            elif mutation=='reverse':rows[-2:]=list(reversed(rows[-2:]))
            else:rows[-1]['can_generate']=1
            self.rehash(root,rows);before=self.snapshot(root)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.run_publish(root,execute=True)
            self.assertEqual(self.snapshot(root),before)

    def test_actual_stage_final_and_leaf_tamper_fail_without_checkout_fallback(self):
        final=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes()) if self.p.FINAL_SHA256 else None
        if final is None:self.skipTest('Waiting for Root final')
        for relative in [own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT,final['files'][-1]['path']]:
            root=self.copy();(root/relative).write_bytes(b'tampered');before=self.snapshot(root)
            with self.subTest(path=relative),self.assertRaises((ValueError,OSError)):self.run_publish(root,execute=True)
            self.assertEqual(self.snapshot(root),before)

    def test_wrong_provider_stage_final_and_canonical_source_refuse(self):
        root=self.copy();before=self.snapshot(root)
        for name,value in [('STAGE_SHA256','0'*64),('PUBLICATION_SHA256',None),('PUBLICATION_SHA256','0'*64)]:
            with patch.object(own,name,value),self.assertRaises(ValueError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_directory_and_typed_manifest_counts_refuse(self):
        root=self.copy();public=root/'data/public-regions';(public/'directory.json').write_bytes(self.snapshot(root)['directory.json']+b' ')
        manifest=json.loads((public/'manifest.json').read_bytes());manifest['files']['directory.json']=sha256((public/'directory.json').read_bytes()).hexdigest()
        (public/'manifest.json').write_bytes(self.p.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        root=self.copy();public=root/'data/public-regions';manifest=json.loads((public/'manifest.json').read_bytes());manifest['guides']=True
        (public/'manifest.json').write_bytes(self.p.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_existing_pending_report_backup_are_never_overwritten(self):
        for relative in ['data/public-regions/guides.json.fujian-i-next',own.QA_REPORT+'/PUBLICATION.json',self.p.BACKUP+'/guides.json']:
            root=self.copy();path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'KEEP');before=self.snapshot(root)
            with self.subTest(path=relative),self.assertRaises(ValueError):self.run_publish(root,execute=True)
            self.assertEqual(path.read_bytes(),b'KEEP');self.assertEqual(self.snapshot(root),before)

    def test_invalid_execute_flags_and_i_only_paths(self):
        root=self.copy(False);before=self.snapshot(root)
        for flag in [1,'true',None]:
            with self.assertRaises(ValueError):self.run_publish(root,execute=flag)
        self.assertEqual(self.snapshot(root),before)
        self.assertIn('fujian-i',self.p.BACKUP);self.assertNotIn('gulou-h',self.p.BACKUP)
        with self.assertRaises(ValueError):own.path_at(root,'../escape')


if __name__=='__main__':unittest.main()
