"""Genuine Root-sealed O publication tests; no synthetic receipt or skip path.

Root must fill APPROVED_FINAL_SHA256 only after explicitly sealing the actual
receipt. The private proposal deliberately keeps this literal unbound.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json,os,shutil,tempfile,unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import regional_fujian_oct31o as own
from regional_guides import RegionalStore
from routes import regional_guides as routes
ROOT=Path(__file__).resolve().parents[2]
APPROVED_FINAL_SHA256 = '7c34b021e636e62d709d1ae1ab622447b12b48ff38c9470657836eefa6db17d8'

@contextmanager
def real_closure():
    """Only actual immutable source/approval files, copied to a fresh Temp root."""
    names=set(own.source_files(ROOT))|set(own.publication_files(ROOT))
    if len(names)!=100:raise ValueError('Exact own O100 sealed closure required')
    with tempfile.TemporaryDirectory(prefix='O-real-sealed-final-') as folder:
        root=Path(folder)
        for name in names:
            destination=root/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,destination)
        yield root

class OPublicationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsInstance(APPROVED_FINAL_SHA256,str,'Root must seal the real receipt and bind the reviewed expected SHA; this template never skips')
        self.assertRegex(APPROVED_FINAL_SHA256,r'^[a-f0-9]{64}$')
        self.assertEqual(own.PUBLICATION_SHA256,APPROVED_FINAL_SHA256)
        self.assertEqual(sha256((ROOT/own.PUBLICATION_RECEIPT).read_bytes()).hexdigest(),APPROVED_FINAL_SHA256)

    def test_actual_final100_own_native6_and_raw_source_never_promoted(self):
        names=set(own.source_files(ROOT))|set(own.publication_files(ROOT));self.assertEqual(len(names),100)
        self.assertEqual(len(own.source_files(ROOT)),19);self.assertEqual(len(own.publication_files(ROOT)),81)
        receipt=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes());self.assertTrue(receipt['can_publish']);self.assertEqual(receipt['scope'],'OWN_O_FINAL_PUBLICATION');self.assertEqual(len(receipt['files']),78)
        for leaf in receipt['files']:
            body=(ROOT/leaf['path']).read_bytes();self.assertEqual((len(body),sha256(body).hexdigest()),(leaf['bytes'],leaf['sha256']))
        native={leaf['path'] for leaf in receipt['files']}-{leaf['path'] for leaf in json.loads((ROOT/own.WORD_MANIFEST).read_bytes())['files']}
        expected={own.QA_REPORT+'/'+name for name in ['BROWSER-RESULT.json','ROOT-NATIVE-REVIEW.json',*[f'{code}-{kind}-CONTRACT.json' for code in ['350322','350502'] for kind in ['application','evidence']]]};self.assertEqual(native,expected)
        sources=[]
        for code,source in [('350322','6918d8e34e1206673434fbc9'),('350502','c95aa7b9d6cf3798036de103')]:
            raw=own.parse_capture(code,root=ROOT);self.assertFalse(raw['can_generate']);self.assertFalse(raw['published']);self.assertFalse(own.with_capabilities(raw,root=ROOT)['can_generate'])
            with self.assertRaises(ValueError):own.with_publication_evidence(raw,root=ROOT)
            stage=own.staged_candidate(code,root=ROOT);self.assertFalse(stage['published'])
            published=own.published_guide(code,root=ROOT);sources.append(published['source_id']);self.assertEqual(published['source_id'],source);self.assertTrue(published['published']);self.assertTrue(published['can_generate']);self.assertEqual(published['publication_adapter_evidence']['sha256'],APPROVED_FINAL_SHA256)
            self.assertEqual(published['verification_status'],'partial');self.assertIsNone(published['committee_full_name']);self.assertIsNone(published['official_version']);self.assertEqual(sum(t['can_generate'] is True for t in published['templates']),2)
            self.assertEqual(published['channel']['online_status'],'auth_required');self.assertIsNone(published['channel']['entry_url']);self.assertFalse(published['channel']['submission_verified'])
        self.assertEqual(len(set(sources)),2)

    def test_actual_cold2_published_guides_four_full_contracts_and_foreign_source_refused(self):
        from public_seed import bootstrap_public_data
        with real_closure() as root:
            guides=[own.published_guide(code,root=root) for code in ['350322','350502']]
            directory=[r for r in json.loads((ROOT/'data/public-regions/directory.json').read_bytes()) if r['province']=='fujian' and r['level']==4 and r['code'] in {'350322','350502'}]
            self.assertEqual({r['code'] for r in directory},{'350322','350502'})
            folder=root/'data/public-regions';folder.mkdir(parents=True)
            for name,value in [('guides.json',guides),('directory.json',directory)]:
                (folder/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
            (folder/'manifest.json').write_text(json.dumps({'schema_version':1,'files':{n:sha256((folder/n).read_bytes()).hexdigest() for n in ['guides.json','directory.json']}}),encoding='utf8')
            result=bootstrap_public_data(root,data_dir=root/'cold-db');self.assertEqual((result['guides_imported'],result['directory_imported'],result['missing_attachments']),(2,2,[]))
            store=RegionalStore(root/'cold-db/regional-guides.sqlite');self.assertEqual(len(store.inventory()),2)
            app=FastAPI();app.include_router(routes.router,prefix='/regional');ids=[];template_hashes=[]
            with patch.object(routes,'ROOT',root),patch.object(routes,'store',return_value=store),patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private')}),TestClient(app) as client:
                for guide in guides:
                    current=store.lookup('fujian',guide['city'],guide['district']);self.assertTrue(current['published']);self.assertTrue(current['can_generate']);self.assertEqual(current['evidence'],own.public_evidence(current,root))
                    for kind in ['application','evidence']:
                        query={k:current[k] for k in ['province','city','district','source_id','version']};query.update(kind=kind,template_id=own.KINDS[kind][1])
                        response=client.get('/regional/form-contract',params=query);self.assertEqual(response.status_code,200,response.text);contract=response.json();schema=own.production_schema_descriptor(current['region_code'],kind)
                        expected={k:current[k] for k in ['province','city','district','region_code','source_id','version']};expected.update(template_id=own.KINDS[kind][1],kind=kind,mode='blank',adapter=own.ADAPTER,schema_id=schema['schema_id'],schema_version=1,source_version=own.SOURCE_VERSIONS[current['region_code']],template_sha256=own.KINDS[kind][2],template_version='sha256:'+own.KINDS[kind][2]);self.assertEqual(contract['context'],expected);self.assertEqual(len(expected),15)
                        for key in ['fields','defaults','policy']:self.assertEqual(contract[key],schema[key])
                        body={key:contract[key] for key in ['schema_version','context','fields','defaults','policy']};self.assertEqual(contract['contract_id'],sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest());ids.append(contract['contract_id']);template_hashes.append(contract['context']['template_sha256'])
                        foreign=next(g for g in guides if g['source_id']!=current['source_id']);self.assertEqual(client.get('/regional/form-contract',params={**query,'source_id':foreign['source_id']}).status_code,409)
                self.assertEqual(len(set(ids)),4);self.assertEqual(len(set(template_hashes)),2)
                self.assertFalse((root/'private/generated').exists())

    def test_real_final_proof_missing_tampered_and_empty_root_never_falls_back(self):
        with real_closure() as root:
            targets=[own.PUBLICATION_RECEIPT,own.STAGE_RECEIPT,own.WORD_MANIFEST,own.QA_REPORT+'/BROWSER-RESULT.json',own.QA_REPORT+'/ROOT-NATIVE-REVIEW.json',own.QA_REPORT+'/350322-application-CONTRACT.json',next(n for n in own.source_files(root) if n.endswith('own-guide.json'))]
            for name in targets:
                path=root/name;body=path.read_bytes();path.unlink()
                with self.subTest(missing=name),self.assertRaises(ValueError):own.published_guide('350322',root=root)
                path.write_bytes(body+b' changed')
                with self.subTest(tampered=name),self.assertRaises(ValueError):own.published_guide('350322',root=root)
                path.write_bytes(body)
            empty=root/'empty';empty.mkdir()
            with self.assertRaises(ValueError):own.published_guide('350502',root=empty)
            self.assertTrue(own.published_guide('350502',root=root)['published'])

    def test_invalidated_publication_Word_or_stage_pins_cannot_keep_real_permission(self):
        for bad in [None,True,False,'0'*64]:
            with self.subTest(pin=bad),patch.object(own,'PUBLICATION_SHA256',bad),self.assertRaises(ValueError):own.published_guide('350322',root=ROOT)
        for name in ['WORD_SHA256','STAGE_SHA256']:
            with self.subTest(pin=name),patch.object(own,name,None),self.assertRaises(ValueError):own.published_guide('350502',root=ROOT)

if __name__=='__main__':unittest.main()
