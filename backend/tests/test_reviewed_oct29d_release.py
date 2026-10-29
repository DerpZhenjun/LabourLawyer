"""D4 release safety tests: every input and SQLite database is synthetic/temp."""
from contextlib import closing
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import candidate_review as candidate
from regional_guides import RegionalStore,digest
from regional_directory import DirectoryStore


class DReleaseTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('reviewed_oct29d_release'),'D4 release module is required')
        import reviewed_oct29d_release as release
        self.r=release
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.output=self.root/'.runtime/prepared'
        self.candidate=self.root/'.runtime/candidate-review-20261029-a'
        self.candidate.mkdir(parents=True)
        self.base=[]
        for n in range(194):
            self.base.append(self.guide('baseline',str(n),str(n),n<177))
        store=RegionalStore(self.candidate/'regional-guides.sqlite')
        for g in self.base:store.put_guide(g)
        DirectoryStore(self.candidate/'regional-directory.sqlite')
        source_files={}
        for index,p in enumerate(candidate.SOURCE_FILES+candidate.HUNAN_FILES+candidate.C_FILES):
            self.write(p,{'preserved':'A9-'+str(index)});source_files[p]=release.file_sha(self.root/p)
        manifest={'scope':'isolated-public-candidate-review-only','published':False,'candidate_guides':13,'guides':194,'generatable_localities':177,'source_files':source_files,'candidate_source_ids':['A'+str(i) for i in range(13)],'database_files':{n:release.file_sha(self.candidate/n) for n in ['regional-guides.sqlite','regional-directory.sqlite']}}
        (self.candidate/'manifest.json').write_bytes(release._bytes(manifest))
        self.additions=[]
        for relative,profile in zip(candidate.D_FILES,release.PROFILES):
            code,province,city,district=profile
            g=self.guide(province,city,district,True);g['region_code']=code
            g['source_url']=release.SOURCE_URLS[code]
            g['templates']=[{'id':code+'-'+k,'region_code':code,'can_generate':True,'document_types':[k],'official_kind':'blank','adapter':'fixture'} for k in (['application'] if code=='330112' else ['application','evidence'])]
            g['published']=False;g['publication_status']='unpublished';g['candidate_web_qa']='NOT_RUN'
            self.write(relative,g);self.additions.append(g)
        self.write('data/public-regions/guides.json',self.base);self.write('data/public-regions/directory.json',[{'preserved':'directory'}])
        self.write('data/public-regions/manifest.json',{'guides':194,'generatable_localities':177,'files':{n:release.file_sha(self.root/'data/public-regions'/n) for n in ['guides.json','directory.json']},'old_metadata':'preserved'})
        queue=[{'province':g['province'],'city':g['city'],'district':g['district'],'meta':{'preserved':True}} for g in self.additions]
        queue.extend({'province':'pending','city':'pending','district':str(i),'meta':i} for i in range(24))
        self.write('config/regional_candidates.json',queue)
        main=RegionalStore(self.root/'backend/data/regional-guides.sqlite')
        for g in self.base:main.put_guide(g)
        with main.connection() as db:
            row=db.execute('SELECT region_id,source_id,province,city,district,payload FROM regional_guides LIMIT 1').fetchone()
            for i in range(8):db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',tuple(row[:2])+('history-'+str(i),)+tuple(row[2:]))
        directory=DirectoryStore(self.root/'backend/data/regional-directory.sqlite')
        with directory.connection() as db:db.executemany('INSERT INTO discovery_jobs(id,kind,payload,state,updated_at) VALUES(?,?,?,?,?)',[(str(i),'preserved','{}','pending','fixture') for i in range(4294)])
        self.cap=patch.object(candidate,'with_reference_capabilities',side_effect=lambda g,**kwargs:deepcopy(g));self.cap.start();self.addCleanup(self.cap.stop)
        self.rcap=patch.object(release,'with_reference_capabilities',side_effect=lambda g,**kwargs:deepcopy(g));self.rcap.start();self.addCleanup(self.rcap.stop)
        self.check=patch.object(release,'checked_reference_adapter',side_effect=lambda g,t,k,**kwargs:release.EXPECTED_ADAPTERS[g['province']]);self.check.start();self.addCleanup(self.check.stop)
        self.public=patch.object(release,'_public',side_effect=lambda g,root:deepcopy(g));self.public.start();self.addCleanup(self.public.stop)
        self.proof=patch.object(release,'public_evidence',return_value={'fixture':True});self.proof.start();self.addCleanup(self.proof.stop)
        self.marker=patch.object(release,'expected_marker',return_value={'release_id':release.RELEASE_ID,'adapters':['fixture-hunan','fixture-jiangsu'],'source_bound':True,'models_required':False,'regional_store':'main_default'});self.marker.start();self.addCleanup(self.marker.stop)
        import regional_zhejiang_oct29d as zj
        import regional_jiangsu_oct29d as js
        def parsed_js(code,capture_root=None):
            self.assertEqual(Path(capture_root),self.root/js.REPORT)
            value=deepcopy(next(g for g in self.additions if g['region_code']==code))
            value['canonical_parser_derived']={'own_region':value['region_code']}
            return value
        def parsed_zj(name,root=None):
            self.assertEqual(Path(root),self.root)
            code={'xiaoshan':'330109','linan':'330112'}[name]
            value=deepcopy(next(g for g in self.additions if g['region_code']==code))
            value['canonical_parser_derived']={'own_region':value['region_code']}
            return value
        for provider,parser_fn in [(js,parsed_js),(zj,parsed_zj)]:
            parser=patch.object(provider,'parse_capture',side_effect=parser_fn);parser.start();self.addCleanup(parser.stop)

    @staticmethod
    def png():
        import struct,zlib
        def chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
        return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\xff\xff'))+chunk(b'IEND',b'')

    def guide(self,p,c,d,generate):
        return {'province':p,'city':c,'district':d,'region_code':d,'source_url':'https://fixture.gov.cn/'+p+'/'+c+'/'+d,'service_name':'劳动人事争议仲裁申请','collected_at':'fixture','verified_at':'fixture','verification_status':'partial','authority':'immutable authority','templates':[{'id':d,'can_generate':generate,'document_types':[]}]}

    def write(self,path,value):
        target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')

    def receipts(self):
        rows=self.r._current(self.candidate/'regional-guides.sqlite');by_code={g['region_code']:g for g in rows}
        regions={code:{'source_id':by_code[code]['source_id'],'version':by_code[code]['version']} for code,*_ in self.r.PROFILES}
        self.write(self.r.RECEIPTS[0],{'status':'PASS','candidate_acceptance':True,'checks':[{'passed':True} for _ in range(4)],'regions':regions})
        records=[]
        for code,kind in sorted(self.r.EXPECTED_PAIRS):
            prefix='reports/nationwide-verification-20261029-d/acceptance/'+code+'-'+kind
            document=self.root/(prefix+'.docx');document.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(document,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
            page=self.root/(prefix+'.png');page.write_bytes(self.png())
            records.append({'region_code':code,'kind':kind,'template_id':code+'-'+kind,'candidate_source_context':regions[code],'native_ui_generation':True,'api_replay_used':False,'http_status':200,'zip_integrity':'PASS','document_xml_parse':'PASS','file':prefix+'.docx','sha256':self.r.file_sha(document),'visual_qa':{'status':'PASS','pages':[{'file':prefix+'.png','sha256':self.r.file_sha(page),'visual_status':'PASS'}]}})
        self.write(self.r.RECEIPTS[1],{'status':'PASS','completed':7,'records':records})

    def prepare(self):
        candidate.append_d(self.root,self.candidate);self.receipts();return self.r.prepare(self.root,self.output)

    def test_append_preserves_c13_snapshot_and_rejects_repeat(self):
        before=(self.candidate/'manifest.json').read_bytes();directory=self.r.file_sha(self.candidate/'regional-directory.sqlite')
        result=candidate.append_d(self.root,self.candidate)
        self.assertEqual((result['guides'],result['generatable_localities'],result['candidate_guides']),(198,181,17))
        backup=self.candidate/'before-d-extension'
        self.assertEqual((backup/'manifest.json').read_bytes(),before)
        self.assertEqual(self.r.sqlite_count(backup/'regional-guides.sqlite','regional_current'),194)
        self.assertEqual(self.r.file_sha(self.candidate/'regional-directory.sqlite'),directory)
        self.assertEqual(candidate.verify(self.root,self.candidate),result)
        with self.assertRaises(ValueError):candidate.append_d(self.root,self.candidate)

    def test_d_loader_and_append_use_canonical_parsers_without_rewriting_raw_sources(self):
        self.assertTrue(callable(getattr(candidate,'load_d_guides',None)),'D4 must rebuild through own canonical parsers')
        originals={p:(self.root/p).read_bytes() for p in candidate.D_FILES}
        loaded=candidate.load_d_guides(self.root)
        self.assertEqual([g['canonical_parser_derived']['own_region'] for g in loaded],[p[0] for p in self.r.PROFILES])
        candidate.append_d(self.root,self.candidate);self.receipts();self.r.prepare(self.root,self.output)
        added=json.loads((self.output/'additions.json').read_text('utf8'))
        self.assertEqual([g['canonical_parser_derived']['own_region'] for g in added],[p[0] for p in self.r.PROFILES])
        for path,body in originals.items():self.assertEqual((self.root/path).read_bytes(),body)

    def test_append_failure_restores_original_manifest_and_db(self):
        before=(self.candidate/'manifest.json').read_bytes()
        with patch.object(candidate,'_atomic_write',side_effect=OSError('simulated manifest failure')):
            with self.assertRaisesRegex(OSError,'simulated'):candidate.append_d(self.root,self.candidate)
        self.assertEqual((self.candidate/'manifest.json').read_bytes(),before)
        self.assertEqual(self.r.sqlite_count(self.candidate/'regional-guides.sqlite','regional_current'),194)

    def test_prepare_missing_receipt_never_creates_output(self):
        candidate.append_d(self.root,self.candidate)
        with self.assertRaises((ValueError,FileNotFoundError)):self.r.prepare(self.root,self.output)
        self.assertFalse(self.output.exists())

    def test_strict_receipts_bind_exact_sources_documents_and_artifact_bytes(self):
        candidate.append_d(self.root,self.candidate);self.receipts()
        guides=[g for g in self.r._current(self.candidate/'regional-guides.sqlite') if g['region_code'] in {p[0] for p in self.r.PROFILES}]
        self.r.verify_receipts(self.root,guides)
        path=self.root/self.r.RECEIPTS[1];original=path.read_bytes()
        for field,value in [('native_ui_generation',False),('api_replay_used',True),('template_id','other-template'),('sha256','0'*64)]:
            receipt=json.loads(original);receipt['records'][0][field]=value;path.write_bytes(self.r._bytes(receipt))
            with self.assertRaises(ValueError):self.r.verify_receipts(self.root,guides)
        path.write_bytes(original);receipt=json.loads(original);receipt['records'][0]['candidate_source_context']['source_id']='wrong';path.write_bytes(self.r._bytes(receipt))
        with self.assertRaises(ValueError):self.r.verify_receipts(self.root,guides)

    def test_prepare_and_apply_preserve_baseline_history_jobs_and_queue_metadata(self):
        plan=self.prepare();self.assertEqual(plan['new_capabilities'],{'localities':4,'documents':7})
        self.assertEqual(self.r.verify_prepared(self.root,self.output),plan)
        main=self.root/'backend/data/regional-guides.sqlite';directory=self.root/'backend/data/regional-directory.sqlite';before=self.r.file_sha(directory)
        with patch.object(self.r,'_read_marker',return_value=self.r.expected_marker()):result=self.r.apply(self.root,self.output)
        self.assertEqual((result['guides_after'],result['history_rows_after'],result['candidate_queue_after']),(198,206,24))
        self.assertEqual((result['discovery_jobs_before'],result['discovery_jobs_after']),(4294,4294));self.assertEqual(before,self.r.file_sha(directory))
        published=json.loads((self.root/'data/public-regions/guides.json').read_text('utf8'));self.assertEqual(published[:194],self.base)
        queue=json.loads((self.root/'config/regional_candidates.json').read_text('utf8'));self.assertEqual([x['meta'] for x in queue],list(range(24)))
        self.assertEqual(self.r.sqlite_count(Path(result['rollback_directory'])/'regional-guides.sqlite','regional_guides'),202)

    def test_apply_changed_baseline_facts_and_existing_history_source_refused(self):
        self.prepare();main=self.root/'backend/data/regional-guides.sqlite'
        with closing(sqlite3.connect(main)) as db:
            payload=json.loads(db.execute('SELECT payload FROM regional_guides WHERE sequence=1').fetchone()[0]);payload['authority']='changed';db.execute('UPDATE regional_guides SET payload=? WHERE sequence=1',(json.dumps(payload),));db.commit()
        with patch.object(self.r,'_read_marker',return_value=self.r.expected_marker()):
            with self.assertRaisesRegex(ValueError,'facts'):self.r.apply(self.root,self.output)
        self.assertEqual(self.r.sqlite_count(main,'regional_guides'),202)
        with closing(sqlite3.connect(main)) as db:
            payload['authority']='immutable authority';db.execute('UPDATE regional_guides SET payload=? WHERE sequence=1',(json.dumps(payload),))
            db.execute('UPDATE regional_guides SET source_id=? WHERE sequence=195',(digest(self.additions[0]['source_url'])[:24],));db.commit()
        with patch.object(self.r,'_read_marker',return_value=self.r.expected_marker()):
            with self.assertRaisesRegex(ValueError,'scope/source history'):self.r.apply(self.root,self.output)
        self.assertEqual(self.r.sqlite_count(main,'regional_current'),194)

    def test_prepared_and_input_tampering_never_authorize_apply(self):
        self.prepare();plan=json.loads((self.output/'prepare-receipt.json').read_text('utf8'))
        receipt=self.output/'prepare-receipt.json'
        for extra in ['../outside','C:/outside','config/not-approved.json']:
            bad=deepcopy(plan);bad['input_sha256'][extra]='0'*64;receipt.write_bytes(self.r._bytes(bad))
            with self.assertRaisesRegex(ValueError,'allowlist'):self.r.verify_prepared(self.root,self.output)
        receipt.write_bytes(self.r._bytes(plan));addition=self.output/'additions.json';original=addition.read_bytes();addition.write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError,'file changed'):self.r.verify_prepared(self.root,self.output)
        addition.write_bytes(original)
        docx=next((self.root/'reports/nationwide-verification-20261029-d/acceptance').glob('*.docx'));docx.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'artifact'):self.r.verify_prepared(self.root,self.output)

    def test_wrong_prepared_counts_or_publication_claim_are_rejected(self):
        self.prepare();path=self.output/'prepare-receipt.json';original=path.read_bytes()
        for key,value in [('guides',195),('generatable_localities',178),('main_modified',True),('snapshot_modified',True),('candidate_queue_after',23),('source_ids',['other-source'])]:
            plan=json.loads(original);plan[key]=value;path.write_bytes(self.r._bytes(plan))
            with self.assertRaisesRegex(ValueError,'identity'):self.r.verify_prepared(self.root,self.output)

    def test_own_source_identity_and_payload_changes_are_rejected(self):
        wrong=deepcopy(self.additions);wrong[0]['source_url']=self.additions[1]['source_url']
        with self.assertRaisesRegex(ValueError,'source identity'):self.r.validate_sources(wrong)
        candidate.append_d(self.root,self.candidate);self.receipts()
        path=self.candidate/'regional-guides.sqlite'
        with closing(sqlite3.connect(path)) as db:
            row=db.execute('SELECT sequence,payload FROM regional_guides WHERE sequence=195').fetchone();payload=json.loads(row[1]);payload['authority']='unreviewed facts';db.execute('UPDATE regional_guides SET payload=? WHERE sequence=?',(json.dumps(payload),row[0]));db.commit()
        manifest=json.loads((self.candidate/'manifest.json').read_text('utf8'));manifest['database_files']['regional-guides.sqlite']=self.r.file_sha(path);(self.candidate/'manifest.json').write_bytes(self.r._bytes(manifest))
        with self.assertRaisesRegex(ValueError,'payload differs'):self.r.prepare(self.root,self.output)
        self.assertFalse(self.output.exists())

    def test_apply_install_failure_rolls_back_every_file_and_sqlite(self):
        self.prepare();targets=[self.root/p for p in self.r.TARGETS];saved={p:p.read_bytes() for p in targets};original=self.r._atomic_write;calls=[]
        def fail(path,body):
            calls.append(path)
            if len(calls)==2:raise OSError('simulated install failure')
            original(path,body)
        with patch.object(self.r,'_read_marker',return_value=self.r.expected_marker()),patch.object(self.r,'_atomic_write',side_effect=fail):
            with self.assertRaisesRegex(OSError,'simulated'):self.r.apply(self.root,self.output)
        self.assertEqual(self.r.sqlite_count(self.root/'backend/data/regional-guides.sqlite','regional_guides'),202)
        for p,body in saved.items():self.assertEqual(p.read_bytes(),body)

    def test_alternate_or_stale_marker_cannot_authorize_main(self):
        for field,value in [('regional_store','alternate'),('release_id','oct29-own-localities-v1'),('source_bound',False),('models_required',True)]:
            with patch.object(self.r,'_read_marker',return_value={**self.r.expected_marker(),field:value}):
                with self.assertRaisesRegex(ValueError,'marker'):self.r.check_main_marker()
        self.assertEqual(self.r.MAIN_MARKER_URL,'http://127.0.0.1:8000/api/regional-guides/release-capabilities')


    def test_receipts_reject_fake_png_even_with_matching_sha(self):
        candidate.append_d(self.root,self.candidate);self.receipts()
        path=self.root/self.r.RECEIPTS[1];receipt=json.loads(path.read_text('utf8'))
        page=receipt['records'][0]['visual_qa']['pages'][0];(self.root/page['file']).write_bytes(b'not a PNG')
        page['sha256']=self.r.file_sha(self.root/page['file']);self.write(self.r.RECEIPTS[1],receipt)
        with self.assertRaisesRegex(ValueError,'PNG'):self.r.prepare(self.root,self.output)
        self.assertFalse(self.output.exists())

    def test_candidate_and_main_exact_versions(self):
        self.prepare()
        versions=[g['version'] for g in self.r._current(self.candidate/'regional-guides.sqlite') if g['region_code'] in {p[0] for p in self.r.PROFILES}]
        self.assertEqual(versions,[195,196,197,198])
        with patch.object(self.r,'_read_marker',return_value=self.r.expected_marker()):result=self.r.apply(self.root,self.output)
        self.assertEqual([row['version'] for row in result['versions']],[203,204,205,206])

    def test_post_commit_receipt_failure_restores_database_and_public_files(self):
        self.prepare();saved={p:(self.root/p).read_bytes() for p in self.r.TARGETS}
        original=self.r._backup_db
        def fail_after_commit(source,target):
            if Path(target).name=='after-guides.sqlite':raise OSError('simulated after-commit failure')
            return original(source,target)
        with patch.object(self.r,'_read_marker',return_value=self.r.expected_marker()),patch.object(self.r,'_backup_db',side_effect=fail_after_commit):
            with self.assertRaisesRegex(OSError,'after-commit'):self.r.apply(self.root,self.output)
        self.assertEqual(self.r.sqlite_count(self.root/'backend/data/regional-guides.sqlite','regional_guides'),202)
        for path,body in saved.items():self.assertEqual((self.root/path).read_bytes(),body)

    def test_candidate_sequence_jump_refused_without_replacing_history(self):
        with closing(sqlite3.connect(self.candidate/'regional-guides.sqlite')) as db:
            db.execute("UPDATE sqlite_sequence SET seq=300 WHERE name='regional_guides'");db.commit()
        manifest=json.loads((self.candidate/'manifest.json').read_text('utf8'))
        manifest['database_files']['regional-guides.sqlite']=self.r.file_sha(self.candidate/'regional-guides.sqlite')
        (self.candidate/'manifest.json').write_bytes(self.r._bytes(manifest))
        with self.assertRaisesRegex(ValueError,'version|sequence|history'):candidate.append_d(self.root,self.candidate)
        self.assertEqual(self.r.sqlite_count(self.candidate/'regional-guides.sqlite','regional_guides'),194)

    def test_verify17_requires_exact_capability_count_and_both_database_hashes(self):
        candidate.append_d(self.root,self.candidate);path=self.candidate/'manifest.json';original=path.read_bytes()
        for key,value in [('generatable_localities',180),('database_files',{}),('candidate_source_ids',[])]:
            changed=json.loads(original);changed[key]=value;path.write_bytes(self.r._bytes(changed))
            with self.assertRaises(ValueError,msg=key):candidate.verify(self.root,self.candidate)
        path.write_bytes(original)

    def test_append_failure_restores_verifiable_database_hash(self):
        original=(self.candidate/'manifest.json').read_bytes()
        with patch.object(candidate,'_atomic_write',side_effect=OSError('simulated manifest failure')):
            with self.assertRaises(OSError):candidate.append_d(self.root,self.candidate)
        self.assertEqual(candidate.verify(self.root,self.candidate),json.loads(original))

    def test_png_crc_alone_does_not_authorize_invalid_image_pixels(self):
        import struct,zlib
        png=self.png();start=png.index(b'IDAT')-4;length=struct.unpack('>I',png[start:start+4])[0]
        bad=b'invalid zlib stream';chunk=struct.pack('>I',len(bad))+b'IDAT'+bad+struct.pack('>I',zlib.crc32(b'IDAT'+bad)&0xffffffff)
        path=self.root/'fake.png';path.write_bytes(png[:start]+chunk+png[start+12+length:])
        with self.assertRaisesRegex(ValueError,'PNG'):self.r._verify_png(path)

    def test_root_forwarded_through_d_loader_projection_and_adapter_checks(self):
        self.prepare()
        for name in ['with_reference_capabilities','checked_reference_adapter']:
            calls=getattr(self.r,name).call_args_list
            self.assertTrue(calls)
            self.assertTrue(all(c.kwargs.get('root')==self.root for c in calls),name)
        self.assertTrue(all(c.kwargs.get('root')==self.root for c in candidate.with_reference_capabilities.call_args_list))

if __name__=='__main__':unittest.main()
