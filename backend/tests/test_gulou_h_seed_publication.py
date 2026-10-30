"""H seed append tests write only cold temporary copies with real root proof."""
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
import regional_fujian_oct31h as own


class GulouHSeedPublicationTests(unittest.TestCase):
    def setUp(self):
        script=ROOT/'scripts/publish-approved-gulou-h-seed.py'
        self.assertTrue(script.is_file(),'Need an exact own Gulou H append publisher')
        spec=importlib.util.spec_from_file_location('gulou_h_seed_publication',script)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.final_roots=set()
        self.assertIn(own.PUBLICATION_SHA256,(None,self.module.FINAL_SHA256),'Provider phase pin must be absent or exactly root-approved')

    def release_copy(self,*,evidence=True):
        if evidence and (self.module.FINAL_SHA256 is None or not (ROOT/own.PUBLICATION_RECEIPT).is_file()):
            self.skipTest('Independent actual H final approval is not pinned yet')
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        paths={'data/public-regions/'+name for name in ['guides.json','manifest.json','directory.json']}
        if evidence:
            paths.update(own.source_files(ROOT));paths.update([own.SOURCE_FREEZE,own.OFFLINE_REVIEW,own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT])
            paths.update(r['path'] for r in json.loads((ROOT/own.WORD_MANIFEST).read_bytes())['files'])
            for receipt in [own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT]:
                paths.update(r['path'] for r in json.loads((ROOT/receipt).read_bytes())['files'])
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        public=root/'data/public-regions';old=json.loads((public/'guides.json').read_bytes())[:206]
        body=self.module.encoded(old);self.assertEqual(sha256(body).hexdigest(),self.module.BASE_GUIDES_SHA256)
        (public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes());manifest.update(guides=206,generatable_localities=189)
        manifest['files']['guides.json']=sha256(body).hexdigest();(public/'manifest.json').write_bytes(self.module.encoded(manifest))
        if evidence:self.final_roots.add(root.resolve())
        return root

    def publish(self,root,*,patch_final=True,**kwargs):
        with patch('sqlite3.connect',side_effect=AssertionError('Seed append must never open a DB')):
            # Before root activates the provider's actual publication phase,
            # test the real separately pinned final receipt in this temp only.
            if patch_final and isinstance(root,(str,Path)) and str(root).strip() and Path(root).resolve() in self.final_roots:
                self.assertNotEqual(Path(root).resolve(),ROOT)
                with patch.object(own,'PUBLICATION_SHA256',self.module.FINAL_SHA256):
                    return self.module.publish(root,**kwargs)
            return self.module.publish(root,**kwargs)

    def snapshot(self,root):
        return {name:(root/'data/public-regions'/name).read_bytes() for name in ['guides.json','manifest.json','directory.json']}

    def rehash(self,root,rows):
        public=root/'data/public-regions';body=self.module.encoded(rows);(public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes());manifest['files']['guides.json']=sha256(body).hexdigest()
        (public/'manifest.json').write_bytes(self.module.encoded(manifest))

    def test_unpinned_final_is_always_closed_even_if_provider_pin_is_also_none(self):
        root=self.release_copy(evidence=False);before=self.snapshot(root)
        with patch.object(self.module,'FINAL_SHA256',None),patch.object(own,'PUBLICATION_SHA256',None):
            with self.assertRaises(ValueError):self.publish(root,execute=True)
        with patch.object(own,'PUBLICATION_SHA256',None):
            with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before);self.assertFalse((root/'.runtime').exists())

    def test_dry_run_exact_append_partial_status_old206_backup_and_idempotency(self):
        root=self.release_copy();before=self.snapshot(root)
        self.assertEqual(self.publish(root)['status'],'dry_run');self.assertEqual(self.snapshot(root),before)
        self.assertFalse((root/'.runtime').exists())
        with patch.object(own,'ROOT',root/'no-checkout'):
            result=self.publish(root,execute=True)
        self.assertEqual((result['guides_after'],result['generatable_localities_after']),(207,190))
        after=self.snapshot(root);rows=json.loads(after['guides.json']);guide=rows[-1]
        self.assertEqual(self.module.encoded(rows[:206]),before['guides.json']);self.assertEqual(after['directory.json'],before['directory.json'])
        self.assertEqual(guide['source_id'],'3e2246aa2a534d2b37f6c6c5');self.assertIs(guide['published'],True)
        self.assertEqual(guide['verification_status'],'partial');self.assertFalse(guide['sample_contents_verified'])
        self.assertEqual(sum(t['can_generate'] is True for t in guide['templates']),2)
        self.assertTrue(all(not t['can_generate'] and not t['document_types'] and t['download_status']=='unverified' for t in guide['templates'] if t['official_kind']=='sample'))
        self.assertTrue(all(not t['can_generate'] for t in guide['templates'] if t['content_role']=='scanning_instructions_only'))
        with patch.object(own,'PUBLICATION_SHA256',self.module.FINAL_SHA256):
            self.assertIsNotNone(own.public_evidence(guide,root))
        for name in ['guides.json','manifest.json']:self.assertEqual((root/self.module.BACKUP/name).read_bytes(),before[name])
        self.assertEqual(self.publish(root,execute=True)['status'],'already_published_exact');self.assertEqual(self.snapshot(root),after)
        self.assertFalse(list(root.rglob('*.sqlite')));self.assertFalse((root/'backend/data').exists())

    def test_rehashed_old206_tamper_is_never_rebuilt(self):
        root=self.release_copy();rows=json.loads(self.snapshot(root)['guides.json']);rows[0]['authority']='unexpected'
        self.rehash(root,rows);before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before);self.assertFalse((root/'.runtime').exists())

    def test_stage_final_pins_and_missing_final_leaf_refuse_without_checkout(self):
        root=self.release_copy();final=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
        for relative in [own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT,final['files'][-1]['path']]:
            root=self.release_copy();before=self.snapshot(root);(root/relative).write_bytes(b'tampered')
            with self.subTest(path=relative),self.assertRaises((ValueError,OSError)):self.publish(root,execute=True)
            self.assertEqual(self.snapshot(root),before);self.assertFalse((root/'.runtime').exists())
        root=self.release_copy();before=self.snapshot(root)
        with patch.object(own,'PUBLICATION_SHA256',self.module.FINAL_SHA256):
            for field in ['STAGE_SHA256','PUBLICATION_SHA256']:
                for pin in [None,'0'*64]:
                    with patch.object(own,field,pin),self.assertRaises(ValueError):self.publish(root,execute=True,patch_final=False)
        self.assertEqual(self.snapshot(root),before)

    def test_second_file_commit_failure_restores_both_files(self):
        root=self.release_copy();before=self.snapshot(root);replace=Path.replace
        def fail_manifest(path,target):
            if path.name=='manifest.json.gulou-h-next':raise OSError('second commit injected')
            return replace(path,target)
        with patch.object(Path,'replace',fail_manifest),self.assertRaises(OSError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before);self.assertFalse(list((root/'data/public-regions').glob('*.gulou-h-next')))
        self.assertFalse((root/own.QA_REPORT/'PUBLISHED-GUIDE.json').exists())

    def test_report_failure_rolls_back_and_removes_only_owned_reports(self):
        root=self.release_copy();before=self.snapshot(root);open_=Path.open
        def fail_report(path,*args,**kwargs):
            if path.name=='PUBLICATION.json' and args and args[0]=='xb':raise OSError('report write injected')
            return open_(path,*args,**kwargs)
        with patch.object(Path,'open',fail_report),self.assertRaises(OSError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        self.assertFalse((root/own.QA_REPORT/'PUBLISHED-GUIDE.json').exists());self.assertFalse((root/own.QA_REPORT/'PUBLICATION.json').exists())

    def test_existing_h_projection_and_completed_encoding_tamper_refused(self):
        root=self.release_copy();self.publish(root,execute=True);rows=json.loads(self.snapshot(root)['guides.json'])
        rows[-1]['can_generate']=1;self.rehash(root,rows);before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        root=self.release_copy();self.publish(root,execute=True);public=root/'data/public-regions'
        rows=json.loads((public/'guides.json').read_bytes());body=(json.dumps(rows,ensure_ascii=False,indent=1)+'\n').encode()
        (public/'guides.json').write_bytes(body);manifest=json.loads((public/'manifest.json').read_bytes())
        manifest['files']['guides.json']=sha256(body).hexdigest();(public/'manifest.json').write_bytes(self.module.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_foreign_pending_report_backup_preserved(self):
        for relative in ['data/public-regions/guides.json.gulou-h-next',own.QA_REPORT+'/PUBLICATION.json',self.module.BACKUP+'/guides.json']:
            root=self.release_copy();path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'preserve foreign file')
            before=self.snapshot(root)
            with self.subTest(path=relative),self.assertRaises(ValueError):self.publish(root,execute=True)
            self.assertEqual(path.read_bytes(),b'preserve foreign file');self.assertEqual(self.snapshot(root),before)

    def test_directory_and_typed_manifest_counts_refused(self):
        root=self.release_copy();public=root/'data/public-regions';directory=(public/'directory.json').read_bytes()+b' '
        (public/'directory.json').write_bytes(directory);manifest=json.loads((public/'manifest.json').read_bytes())
        manifest['files']['directory.json']=sha256(directory).hexdigest();(public/'manifest.json').write_bytes(self.module.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        root=self.release_copy();public=root/'data/public-regions';manifest=json.loads((public/'manifest.json').read_bytes())
        manifest['guides']=True;(public/'manifest.json').write_bytes(self.module.encoded(manifest));before=self.snapshot(root)
        with self.assertRaises(ValueError):self.publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)

    def test_explicit_root_boolean_flag_and_h_only_paths(self):
        for absent in [None,'',' ']:
            with self.assertRaises(ValueError):self.publish(absent)
        root=self.release_copy(evidence=False);before=self.snapshot(root)
        for flag in [1,'true',None]:
            with self.assertRaises(ValueError):self.publish(root,execute=flag)
        self.assertEqual(self.snapshot(root),before);self.assertIn('gulou-h',self.module.BACKUP)
        self.assertIn('fujian-h',str(self.module.REPORT));self.assertNotIn('kunshan-g',self.module.BACKUP)
        with self.assertRaises(ValueError):own.path_at(root,'../escape')


if __name__=='__main__':unittest.main()
