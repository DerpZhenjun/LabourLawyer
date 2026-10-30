"""Only Temp seed copies; real Root J stage/final receipts and proof leaves."""
from hashlib import sha256
from copy import deepcopy
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
import regional_fujian_oct31j as own


class FujianJSeedPublicationTests(unittest.TestCase):
    def setUp(self):
        source=ROOT/'scripts/publish-approved-fujian-j-seed.py'
        self.assertTrue(source.is_file(),'Need exact six-own-J seed publisher')
        spec=importlib.util.spec_from_file_location('j_seed_test',source)
        self.p=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.p)

    def copy(self,proof=True):
        if proof and (self.p.FINAL_SHA256 is None or not (ROOT/own.PUBLICATION_RECEIPT).exists()):
            self.skipTest('Waiting for actual independently issued Root final receipt')
        temporary=tempfile.TemporaryDirectory(prefix='j-seed-');self.addCleanup(temporary.cleanup);root=Path(temporary.name).resolve()
        paths={'data/public-regions/'+name for name in ['guides.json','manifest.json','directory.json']}
        if proof:
            paths.update(own.source_files(ROOT));paths.update([own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT])
            for name in [own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT]:
                paths.update(row['path'] for row in json.loads((ROOT/name).read_bytes())['files'])
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        public=root/'data/public-regions';rows=json.loads((public/'guides.json').read_bytes())[:209]
        body=self.p.encoded(rows);self.assertEqual(sha256(body).hexdigest(),self.p.BASE_GUIDES_SHA256)
        (public/'guides.json').write_bytes(body)
        manifest=json.loads((public/'manifest.json').read_bytes());manifest.update(guides=209,generatable_localities=192)
        manifest['exported_at']='2026-10-30T20:17:36.953173+00:00';manifest['files']['guides.json']=self.p.BASE_GUIDES_SHA256
        self.assertEqual(sha256(self.p.encoded(manifest)).hexdigest(),self.p.BASE_MANIFEST_SHA256)
        (public/'manifest.json').write_bytes(self.p.encoded(manifest))
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

    def test_dryrun_six_exact_own_rows_prefix_directory_and_exact_idempotence(self):
        root=self.copy();before=self.snapshot(root)
        self.assertEqual(self.run_publish(root)['status'],'dry_run');self.assertEqual(self.snapshot(root),before)
        self.assertFalse((root/'.runtime').exists())
        with patch.object(own,'ROOT',root/'absent-checkout'):result=self.run_publish(root,execute=True)
        self.assertEqual((result['guides_after'],result['generatable_localities_after']),(215,198))
        after=self.snapshot(root);rows=json.loads(after['guides.json'])
        self.assertEqual(self.p.encoded(rows[:209]),before['guides.json']);self.assertEqual(after['directory.json'],before['directory.json'])
        self.assertEqual([g['region_code'] for g in rows[-6:]],['350122','350123','350124','350125','350181','350182'])
        self.assertEqual(len({g['source_id'] for g in rows[-6:]}),6)
        self.assertEqual(sum(len(t.get('document_types',[])) for g in rows for t in g['templates'] if t.get('can_generate') is True),389)
        for g in rows[-6:]:
            self.assertEqual(g['verification_status'],'partial');self.assertIs(g['published'],True)
            self.assertIsNone(g['committee_full_name']);self.assertIs(g['sample_contents_verified'],False)
            self.assertEqual(sum(t['can_generate'] is True for t in g['templates']),1 if g['region_code']=='350125' else 2)
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
            if path.name=='manifest.json.fujian-j-next':raise OSError('second replacement failure')
            return replace(path,target)
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        self.assertFalse(list((root/'data/public-regions').glob('*.fujian-j-next')))
        self.assertFalse((root/own.QA_REPORT/'PUBLISHED-GUIDES.json').exists())

    def test_report_failure_rolls_back_and_removes_only_own_new_reports(self):
        root=self.copy();before=self.snapshot(root);open_=Path.open
        def fail(path,*args,**kwargs):
            if path.name=='PUBLICATION.json' and args and args[0]=='xb':raise OSError('publication report failure')
            return open_(path,*args,**kwargs)
        with patch.object(Path,'open',fail),self.assertRaises(OSError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)
        for name in ['PUBLISHED-GUIDES.json','PUBLICATION.json']:self.assertFalse((root/own.QA_REPORT/name).exists())

    def test_partial_reordered_or_tampered_completion_refuses(self):
        for mutation in ['partial','reverse','tamper']:
            root=self.copy();self.run_publish(root,execute=True);rows=json.loads(self.snapshot(root)['guides.json'])
            if mutation=='partial':rows.pop()
            elif mutation=='reverse':rows[-6:]=list(reversed(rows[-6:]))
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

    def test_actual_own_batch_projection_index_tamper_refuses(self):
        root=self.copy();(root/own.SOURCE_BASE/'BATCH-PROJECTION-INDEX.json').write_bytes(b'tampered');before=self.snapshot(root)
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
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
        for relative in ['data/public-regions/guides.json.fujian-j-next',own.QA_REPORT+'/PUBLICATION.json',self.p.BACKUP+'/guides.json']:
            root=self.copy();path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'KEEP');before=self.snapshot(root)
            with self.subTest(path=relative),self.assertRaises(ValueError):self.run_publish(root,execute=True)
            self.assertEqual(path.read_bytes(),b'KEEP');self.assertEqual(self.snapshot(root),before)

    def test_invalid_execute_flags_and_j_only_paths(self):
        root=self.copy(False);before=self.snapshot(root)
        for flag in [1,'true',None]:
            with self.assertRaises(ValueError):self.run_publish(root,execute=flag)
        self.assertEqual(self.snapshot(root),before)
        self.assertIn('fujian-j',self.p.BACKUP);self.assertNotIn('gulou-h',self.p.BACKUP)
        with self.assertRaises(ValueError):own.path_at(root,'../escape')

    def test_exact_baseline_manifest_and_reordered_old_prefix_cannot_be_rehashed(self):
        root=self.copy();public=root/'data/public-regions';before=self.snapshot(root)
        manifest=json.loads(before['manifest.json']);manifest['exported_at']='different'
        (public/'manifest.json').write_bytes(self.p.encoded(manifest));changed=self.snapshot(root)
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),changed)
        (public/'manifest.json').write_bytes(before['manifest.json'])
        rows=json.loads(before['guides.json']);rows[0],rows[1]=rows[1],rows[0];self.rehash(root,rows);changed=self.snapshot(root)
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),changed)

    def test_second_backup_failure_preserves_seed_and_existing_backup(self):
        root=self.copy();before=self.snapshot(root);open_=Path.open
        def fail(path,*args,**kwargs):
            if path==root/self.p.BACKUP/'manifest.json' and args and args[0]=='xb':raise OSError('backup failure')
            return open_(path,*args,**kwargs)
        with patch.object(Path,'open',fail),self.assertRaises(OSError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before);self.assertEqual((root/self.p.BACKUP/'guides.json').read_bytes(),before['guides.json'])
        self.assertFalse(list((root/'data/public-regions').glob('*.fujian-j-next')))

    def test_own_projection_guards_reject_cross_i_source_yongtai_evidence_and_inherited_material(self):
        root=self.copy();self.run_publish(root,execute=True);actual=json.loads(self.snapshot(root)['guides.json'])[-6:];cases=[]
        bad=deepcopy(actual);bad[3]['templates'].append(deepcopy(next(t for t in bad[0]['templates'] if t.get('document_types')==['evidence'])));cases.append(bad)
        bad=deepcopy(actual);bad[0].update(region_code='350103',district='台江区',source_id='dcf9b71dee1c1cb61a3af637');cases.append(bad)
        bad=deepcopy(actual);bad[5]['source_version']=actual[0]['source_version'];cases.append(bad)
        bad=deepcopy(actual);next(t for t in bad[0]['templates'] if t.get('document_types')==['application'])['material_id']=own.REGIONS['350123']['templates']['application']['material_id'];cases.append(bad)
        bad=deepcopy(actual);next(t for t in bad[5]['templates'] if t.get('document_types')==['evidence'])['id']=own.REGIONS['350122']['templates']['evidence']['file_id'];cases.append(bad)
        bad=deepcopy(actual);next(t for t in bad[0]['templates'] if t['official_kind']=='sample')['can_generate']=True;cases.append(bad)
        for n,bad in enumerate(cases):
            # Negative projection unit: actual receipts remain untouched. The
            # constructor is replaced only to inject disallowed output.
            with self.subTest(case=n),patch.object(own,'_published',side_effect=bad),self.assertRaises(ValueError):self.p.approved_guides(root)

    def test_existing_complete_seed_requires_exact_publication_metadata(self):
        root=self.copy();self.run_publish(root,execute=True);before=self.snapshot(root);receipt=root/self.p.REPORT/'PUBLICATION.json';raw=receipt.read_bytes()
        receipt.unlink()
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
        receipt.write_bytes(raw);value=json.loads(raw);value['live_database_written']=0;receipt.write_bytes(self.p.encoded(value))
        with self.assertRaises(ValueError):self.run_publish(root,execute=True)
        self.assertEqual(self.snapshot(root),before)


if __name__=='__main__':unittest.main()
