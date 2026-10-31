"""Real independently signed K final proof; Temp-only counterfactuals/API."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import test_fujian_oct31k_dispatch as dispatch

ROOT=Path(__file__).resolve().parents[2]
own=dispatch.own
FINAL='3f24c81c617733000c85f1c76b4c2e4bcd0a08e82f34b5323dbeea0b6a7154be'
PROVIDER='fd451372536e65fc122b87f0dde8cc04da2d51ed812c5687faf4e1e419a278bc'


class KPublicationTests(unittest.TestCase):
    def isolated_proofs(self):
        temporary=tempfile.TemporaryDirectory(prefix='k-real-final-proof-');self.addCleanup(temporary.cleanup)
        root=Path(temporary.name).resolve();final=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
        paths=set(own.source_files(ROOT)+[own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT]+[r['path'] for r in final['files']])
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        return root,final

    def test_real_final89_pins_three_partial_sources_four_blanks_and14_metadata_only(self):
        self.assertEqual(own.PUBLICATION_SHA256,FINAL);self.assertEqual(sha256(Path(own.__file__).read_bytes()).hexdigest(),PROVIDER)
        raw=(ROOT/own.PUBLICATION_RECEIPT).read_bytes();self.assertEqual(sha256(raw).hexdigest(),FINAL)
        receipt=json.loads(raw);self.assertEqual(len(receipt['files']),89);self.assertIs(receipt['can_publish'],True)
        self.assertIs(receipt['native_confirmation_download_own_forms'],True);self.assertIs(receipt['database_or_seed_published_by_this_receipt'],False)
        forms=0;metadata=0
        for code,meta in own.REGIONS.items():
            guide=own._published(code,ROOT)
            for key in ['province','city','district','region_code','source_id','source_url','service_code']:self.assertEqual(guide[key],meta[key])
            self.assertEqual(guide['source_version'],meta['manifest_sha256']);self.assertEqual(guide['publication_adapter_evidence']['sha256'],FINAL)
            self.assertTrue(guide['published']);self.assertEqual(guide['publication_status'],'published');self.assertEqual(guide['guide_status'],'partial');self.assertEqual(guide['verification_status'],'partial')
            self.assertIsNone(guide['committee_full_name']);self.assertIsNone(guide['official_version']);self.assertFalse(guide['committee_autofill_allowed'])
            self.assertTrue(all(t['sample_contents_verified'] is False for t in guide['templates']))
            for template in guide['templates']:
                if template['can_generate']:
                    forms+=1;self.assertEqual(template['official_kind'],'blank');self.assertIn(template['material_id'],[t['material_id'] for t in meta['templates'].values()])
                else:
                    metadata+=1;self.assertIsNone(template['file']);self.assertEqual(template['download_status'],'metadata_only');self.assertEqual(template['document_types'],[])
        self.assertEqual((forms,metadata),(4,14))

    def test_none_boolean_wrong_hash_and_unpublished_claims_remain_closed(self):
        staged=own.staged_candidate('350111',root=ROOT);self.assertFalse(staged['published']);self.assertNotIn('publication_adapter_evidence',staged)
        for pin in [None,True,'0'*64]:
            with self.subTest(pin_type=type(pin).__name__),patch.object(own,'PUBLICATION_SHA256',pin):
                with self.assertRaises(ValueError):own.with_publication_evidence(staged,root=ROOT)
                with self.assertRaises(ValueError):own._published('350111',ROOT)
        for g in [own.parse_capture('350111',root=ROOT),own.prepare_candidate('350111',root=ROOT)]:
            with self.assertRaises(ValueError):own.with_publication_evidence(g,root=ROOT)

    def test_missing_final_or_own_root_never_falls_back_to_checkout(self):
        root,_=self.isolated_proofs();(root/own.PUBLICATION_RECEIPT).unlink()
        with self.assertRaises(ValueError):own._published('350111',root)
        with self.assertRaises(ValueError):own._published('350111',root/'missing-root')
        self.assertEqual(own._published('350111',ROOT)['publication_adapter_evidence']['sha256'],FINAL)

    def test_tampered_final_native_contract_source_stage_word_or_leaf_refused(self):
        root,final=self.isolated_proofs()
        paths=[own.PUBLICATION_RECEIPT,own.STAGE_RECEIPT,own.WORD_MANIFEST,
               own.SOURCE_BASE+'/'+own.REGIONS['350121']['folder']+'/NORMALIZED-OWN-SOURCE.json',
               next(row['path'] for row in final['files'] if row['path'].endswith('/NATIVE-CANDIDATE-QA.json')),
               next(row['path'] for row in final['files'] if '/contracts/' in row['path']),
               next(row['path'] for row in final['files'] if '/word/' in row['path'] and row['path'].endswith('.docx'))]
        for name in paths:
            path=root/name;body=path.read_bytes();path.write_bytes(body+b' ')
            with self.subTest(path=name),self.assertRaises(ValueError):own._published('350111',root)
            path.write_bytes(body)
        leaf=root/final['files'][-1]['path'];leaf.unlink()
        with self.assertRaises(ValueError):own._published('350111',root)

    def test_same_application_SHA_cannot_swap_source_region_version_or_material(self):
        guide=own._published('350111',ROOT);other=own._published('350121',ROOT)
        self.assertEqual(own.REGIONS['350111']['templates']['application']['sha256'],own.REGIONS['350121']['templates']['application']['sha256'])
        for key,value in [('source_id',other['source_id']),('district',other['district']),('source_version',other['source_version']),('region_code','350100')]:
            changed=deepcopy(guide);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):own.with_capabilities(changed,root=ROOT)
        template=next(t for t in guide['templates'] if t['can_generate'] and t['document_types']==['application'])
        borrowed=deepcopy(template);borrowed['material_id']=own.REGIONS['350121']['templates']['application']['material_id']
        with self.assertRaises(ValueError):own.checked_adapter(guide,borrowed,'application',root=ROOT)
        for source in [other['source_id'],'3b6dd0535bf4cb4ed328fda4']:
            request=own.envelope('350111','application',{},root=ROOT);request['source_id']=source
            with self.assertRaises(ValueError):own.validate_request(request,root=ROOT)

    def test_actual_published_ASGI_four_fictional_fills_ZIP_headers_and_proof_loss(self):
        case=dispatch.KDispatchTests()
        with case.isolated('published') as (root,store,client):
            metadata=0;forms=0
            for code in own.REGIONS:
                guide=case.guide(store,code);self.assertTrue(guide['published']);self.assertEqual(guide['publication_adapter_evidence']['sha256'],FINAL)
                for kind in own.REGIONS[code]['allowed_kinds']:
                    query=case.query(guide,kind);response=client.get('/regional/form-contract',params=query);self.assertEqual(response.status_code,200,response.text);contract=response.json()
                    data=own.example_data(code,kind,root=root);self.assertIn('虚构',json.dumps(data,ensure_ascii=False))
                    response=client.post('/regional/generate',json={**query,'mode':'blank','contract_id':contract['contract_id'],'data':data});self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
                    expected=own.candidate_fill(own.envelope(code,kind,data,root=root),root=root)
                    with ZipFile(BytesIO(response.content)) as a,ZipFile(BytesIO(expected)) as b:
                        self.assertIsNone(a.testzip());self.assertEqual(a.namelist(),b.namelist())
                        for part in a.namelist():self.assertEqual(a.read(part),b.read(part))
                    for key,value in [('x-guide-source-id',guide['source_id']),('x-guide-version',str(guide['version'])),('x-form-contract-id',contract['contract_id']),('x-document-origin','official-blank-filled'),('cache-control','no-store')]:self.assertEqual(response.headers[key],value)
                    wrong={**query,'mode':'blank','contract_id':contract['contract_id'],'data':data,'version':guide['version']+9};self.assertEqual(client.post('/regional/generate',json=wrong).status_code,409)
                    forms+=1
                for template in guide['templates']:
                    if template['download_status']=='metadata_only':
                        metadata+=1;self.assertEqual(client.get('/regional/form-contract',params={**case.query(guide,'application'),'template_id':template['id']}).status_code,409)
            self.assertEqual((forms,metadata),(4,14));self.assertEqual(list((root/'private-data/generated').iterdir()),[])
            guide=case.guide(store,'350111');(root/own.PUBLICATION_RECEIPT).unlink()
            self.assertEqual(client.get('/regional/form-contract',params=case.query(guide,'application')).status_code,409)


if __name__=='__main__':unittest.main()
