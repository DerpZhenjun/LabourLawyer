"""Release mutation tests use only temporary SQLite databases and files."""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import reviewed_oct29_release as release
from candidate_review import prepare as prepare_candidate,extend_hunan
from regional_guides import RegionalStore
from regional_directory import DirectoryStore


class ReviewedReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace=tempfile.TemporaryDirectory(dir=ROOT/'.runtime')
        cls.input_root=Path(cls.workspace.name)/'isolated-input'
        baseline=ROOT/'data/public-regions/history/20261028-181'
        (cls.input_root/'data/public-regions').mkdir(parents=True)
        for name in ['guides.json','directory.json','manifest.json']:
            shutil.copy2(baseline/name,cls.input_root/'data/public-regions'/name)
        (cls.input_root/'config').mkdir()
        shutil.copy2(ROOT/'config/history/regional_candidates-20261029-before-publication.json',cls.input_root/'config/regional_candidates.json')
        needed=set(release.SOURCE_FILES+release.HUNAN_FILES+release.RECEIPTS)
        # Only explicit public files. No recursive report copies, raw browser
        # artifacts, live stores, downloads directory, or running candidate DB.
        for relative in ['reports/nationwide-verification-20261029/zhejiang/PUBLIC-WHITELIST.json','reports/nationwide-verification-20261029/anhui/PUBLIC-WHITELIST.json','reports/nationwide-verification-20261029-b/hunan/PUBLIC-WHITELIST.json']:
            white=json.loads((ROOT/relative).read_text('utf8'));needed.add(relative)
            if isinstance(white,list):needed.update(row['file'] for row in white)
            elif isinstance(white['files'],dict):needed.update(white['files'])
            else:needed.update(row.get('path',row.get('file')) for row in white['files'])
        for relative in [release.RECEIPTS[3],release.RECEIPTS[6]]:
            needed.update(row['file'] for row in json.loads((ROOT/relative).read_text('utf8'))['files'])
        for relative in needed:
            source=release._contained(ROOT,relative);target=release._contained(cls.input_root,relative)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        candidate=cls.input_root/'.runtime/candidate-review-20261029-a'
        prepare_candidate(cls.input_root,candidate);extend_hunan(cls.input_root,candidate)
        cls.prepared=cls.input_root/'.runtime/prepared'
        cls.plan=release.prepare(cls.input_root,cls.prepared)
        cls.additions=json.loads((cls.prepared/'additions.json').read_text('utf8'))

    @classmethod
    def tearDownClass(cls):cls.workspace.cleanup()

    def fixture(self):
        temp=tempfile.TemporaryDirectory(dir=ROOT/'.runtime');self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        shutil.copytree(self.input_root/'data/public-regions',root/'data/public-regions')
        (root/'config').mkdir();shutil.copy2(self.input_root/'config/regional_candidates.json',root/'config/regional_candidates.json')
        store=RegionalStore(root/'backend/data/regional-guides.sqlite')
        for g in json.loads((root/'data/public-regions/guides.json').read_text('utf8')):store.put_guide(g)
        with store.connection() as db:
            old=db.execute('SELECT region_id,source_id,province,city,district,payload FROM regional_guides LIMIT 1').fetchone()
            db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',tuple(old[:2])+('retained-old-history',)+tuple(old[2:]))
        directory=DirectoryStore(root/'backend/data/regional-directory.sqlite')
        with directory.connection() as db:
            db.executemany('INSERT INTO discovery_jobs(id,kind,payload,state,updated_at) VALUES(?,?,?,?,?)',[(str(i),'preserved-discovery',json.dumps({'synthetic_job':i}),'pending','synthetic-time') for i in range(4294)])
        output=root/'.runtime/prepared';shutil.copytree(self.prepared,output)
        return root,output,store,directory

    def test_prepare_is_prospective_safe_and_preserves_own_capabilities(self):
        self.assertEqual((self.plan['guides'],self.plan['generatable_localities']),(190,173))
        self.assertEqual(self.plan['new_capabilities'],{'localities':7,'documents':11})
        self.assertEqual(len({g['source_id'] for g in self.additions}),9)
        self.assertTrue(all(g['published'] is True for g in self.additions))
        for g in self.additions:
            for t in g['templates']:
                self.assertEqual(t['region_code'],g['region_code'])
            if g['province']=='jiangsu':
                self.assertEqual(sum(t['download_status']=='downloaded' for t in g['templates']),2)
            if g['province'] in {'anhui','zhejiang','hunan'}:self.assertIn('evidence',g)
            self.assertFalse(any('候选网页未验收' in w or '验收NOT_RUN' in w for w in g.get('warnings',[])))
        hn=[g for g in self.additions if g['province']=='hunan']
        self.assertTrue(all(any('not_found_in_checked_sources' in w for w in g['warnings']) for g in hn))
        self.assertEqual((self.input_root/'data/public-regions/guides.json').read_bytes(),(self.prepared/'base/guides.json').read_bytes())
        self.assertEqual(release.verify_prepared(self.input_root,self.prepared)['release_id'],release.RELEASE_ID)

    def test_missing_wrong_or_redirected_marker_cannot_apply(self):
        root,output,store,_=self.fixture();before=release.file_sha(store.path)
        with patch.object(release,'verify_prepared',return_value=self.plan),patch.object(release,'_read_marker',return_value={}):
            with self.assertRaisesRegex(ValueError,'marker'):release.apply(root,output)
        self.assertEqual(release.file_sha(store.path),before)
        for marker in [{**release.expected_marker(),'release_id':'old'}, {**release.expected_marker(),'source_bound':False}, {**release.expected_marker(),'regional_store':'alternate'}]:
            with patch.object(release,'_read_marker',return_value=marker):
                with self.assertRaisesRegex(ValueError,'marker'):release.check_main_marker()
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def geturl(self):return 'http://127.0.0.1:8001/api/regional-guides/release-capabilities'
            def read(self,*args):return json.dumps(release.expected_marker()).encode()
        with patch.object(release,'urlopen',return_value=Response()):
            with self.assertRaisesRegex(ValueError,'main API'):release._read_marker()

    def test_append_preserves_history_jobs_directory_and_other_candidate_metadata(self):
        root,output,store,directory=self.fixture();old_cfg=json.loads((root/'config/regional_candidates.json').read_text('utf8'))
        directory_before=release.file_sha(directory.path)
        with patch.object(release,'verify_prepared',return_value=self.plan),patch.object(release,'_read_marker',return_value=release.expected_marker()):result=release.apply(root,output)
        self.assertEqual(result['guides_after'],190);self.assertEqual(result['inserted'],9)
        self.assertEqual(result['discovery_jobs_before'],4294);self.assertEqual(result['discovery_jobs_after'],4294)
        self.assertEqual(release.file_sha(directory.path),directory_before)
        with closing(sqlite3.connect(store.path)) as db:self.assertEqual(db.execute('SELECT count(*) FROM regional_guides').fetchone()[0],191)
        new_cfg=json.loads((root/'config/regional_candidates.json').read_text('utf8'))
        self.assertEqual(len(new_cfg),24)
        expected=[g for g in old_cfg if release.scope(g) not in {release.scope(a) for a in self.additions}]
        self.assertEqual(new_cfg,expected)
        rollback=Path(result['rollback_directory']);self.assertTrue((rollback/'rollback-manifest.json').is_file())
        with patch.object(release,'verify_prepared',return_value=self.plan),patch.object(release,'_read_marker',return_value=release.expected_marker()):
            with self.assertRaises(ValueError):release.apply(root,output)

    def test_existing_same_scope_is_never_overwritten(self):
        root,output,store,_=self.fixture();store.put_guide(deepcopy(self.additions[0]));before=release.file_sha(store.path)
        with patch.object(release,'verify_prepared',return_value=self.plan),patch.object(release,'_read_marker',return_value=release.expected_marker()):
            with self.assertRaisesRegex(ValueError,'scope|baseline'):release.apply(root,output)
        self.assertEqual(release.file_sha(store.path),before)

    def test_changed_main_facts_and_historical_scope_conflicts_are_rejected(self):
        for field in ['authority','materials','fields']:
            root,output,store,_=self.fixture();g=store.inventory()[0]
            if field=='authority':g[field]=g.get(field,'')+' changed after baseline'
            elif field=='materials':g[field]=g.get(field,[])+[{'name':'unreviewed changed material'}]
            else:g[field]={**g.get(field,{}),'unreviewed_changed_field':{'raw_value':'changed'}}
            store.put_guide(g)
            with patch.object(release,'verify_prepared',return_value=self.plan),patch.object(release,'_read_marker',return_value=release.expected_marker()):
                with self.assertRaisesRegex(ValueError,'baseline facts'):release.apply(root,output)
        root,output,store,_=self.fixture();g=self.additions[0]
        with store.connection() as db:
            db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',('orphan-history',g['source_id'],'old-candidate-history',*release.scope(g),json.dumps(g)))
        with patch.object(release,'verify_prepared',return_value=self.plan),patch.object(release,'_read_marker',return_value=release.expected_marker()):
            with self.assertRaisesRegex(ValueError,'scope/source history'):release.apply(root,output)

    def test_file_install_failure_rolls_back_sqlite_and_every_changed_file(self):
        root,output,store,directory=self.fixture()
        files=[root/'data/public-regions'/n for n in ['guides.json','manifest.json','directory.json']]+[root/'config/regional_candidates.json']
        before={str(p):p.read_bytes() for p in files};history=release.sqlite_count(store.path,'regional_guides')
        original=release._atomic_write;calls=[]
        def fail_second(path,body):
            calls.append(path)
            if len(calls)==2:raise OSError('simulated file install failure')
            return original(path,body)
        with patch.object(release,'verify_prepared',return_value=self.plan),patch.object(release,'_read_marker',return_value=release.expected_marker()),patch.object(release,'_atomic_write',side_effect=fail_second):
            with self.assertRaisesRegex(OSError,'simulated'):release.apply(root,output)
        self.assertEqual(release.sqlite_count(store.path,'regional_current'),181)
        self.assertEqual(release.sqlite_count(store.path,'regional_guides'),history)
        self.assertEqual(release.sqlite_count(directory.path,'discovery_jobs'),4294)
        for p in files:self.assertEqual(p.read_bytes(),before[str(p)])

    def test_prepared_output_tampering_and_missing_receipt_are_rejected(self):
        changed=self.input_root/'.runtime/tampered';shutil.copytree(self.prepared,changed)
        (changed/'additions.json').write_text('[]',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'prepared'):release.verify_prepared(self.input_root,changed)
        with patch.object(release,'_json',side_effect=FileNotFoundError('missing receipt')):
            with self.assertRaises(FileNotFoundError):release.verify_receipts(self.input_root,[])

    def test_prepared_input_paths_are_exact_and_contained(self):
        for index,extra in enumerate(['../outside-secret','C:/outside-secret','config/unapproved.json']):
            changed=self.input_root/'.runtime'/('bad-path-'+str(index));shutil.copytree(self.prepared,changed)
            receipt=json.loads((changed/'prepare-receipt.json').read_text('utf8'));receipt['input_sha256'][extra]='0'*64
            (changed/'prepare-receipt.json').write_text(json.dumps(receipt),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'allowlist'):release.verify_prepared(self.input_root,changed)

    def test_failed_real_receipt_is_rejected_without_writing(self):
        original=release._json
        def rejected(path):
            value=original(path)
            if Path(path)==self.input_root/release.RECEIPTS[1]:value['acceptance_passed']=False
            return value
        with patch.object(release,'_json',side_effect=rejected):
            with self.assertRaisesRegex(ValueError,'receipt is not PASS'):release.verify_receipts(self.input_root,[])

    def test_all_eleven_projected_documents_generate_in_temporary_store(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes import regional_guides as routes
        import io
        import zipfile
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as folder:
            store=RegionalStore(Path(folder)/'projected.sqlite')
            guides=[store.put_guide(g) for g in self.additions]
            app=FastAPI();app.include_router(routes.router,prefix='/regional');generated=0;localities=set()
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                for g in guides:
                    for t in g['templates']:
                        for kind in t.get('document_types',[]) if t.get('can_generate') else []:
                            data={'applicantName':'虚构发布验收','requests':['请求支付虚构工资。'],'factsReason':'仅用于临时库软件验证。'}
                            if kind=='evidence':data={'evidenceList':[{'name':'虚构独立证据','source':'虚构来源','purpose':'虚构证明事项','pageCount':'2'}]}
                            if g['region_code']=='340122':data={'applicant_lines':['虚构发布验收劳动者'],'respondent_lines':['虚构单位'],'requests':['请求支付虚构工资。'],'facts':'仅用于临时库软件验证。'}
                            payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=t['id'],kind=kind,mode='blank',data=data)
                            r=client.post('/regional/generate',json=payload)
                            self.assertEqual(r.status_code,200,r.text[:200] if r.status_code!=200 else '')
                            self.assertEqual(r.headers['X-Guide-Source-ID'],g['source_id'])
                            with zipfile.ZipFile(io.BytesIO(r.content)) as z:self.assertIsNone(z.testzip());self.assertIn('word/document.xml',z.namelist())
                            generated+=1;localities.add(release.scope(g))
                            payload['source_id']=next(other['source_id'] for other in guides if other['source_id']!=g['source_id'])
                            self.assertEqual(client.post('/regional/generate',json=payload).status_code,409)
            self.assertEqual((len(localities),generated),(7,11))


if __name__=='__main__':unittest.main()
