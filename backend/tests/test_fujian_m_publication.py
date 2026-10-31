"""Real Root M final, cold-only published contracts and strict source binding."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient
import test_fujian_oct31m_dispatch as d

ROOT=d.ROOT
own=d.own
FINAL='7a9a65f57253d24588014dd254471f039ac40099cad319706f2ea10afb98c813'


@contextmanager
def isolated_final():
    """Copy only exact public source/real approval closure, never a global DB."""
    with tempfile.TemporaryDirectory(prefix='M-final-cold-') as folder:
        root=Path(folder)
        receipt=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
        names=set(own.source_files(ROOT))|{own.WORD_MANIFEST,own.STAGE_RECEIPT,own.PUBLICATION_RECEIPT}
        names.update(row['path'] for row in receipt['files'])
        for name in names:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target)
        store=d.RegionalStore(root/'public.sqlite')
        for code in own.REGIONS:store.put_guide(own._published(code,root))
        app=FastAPI();app.include_router(d.routes.router,prefix='/regional')
        with patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private')}),patch.object(d.routes,'ROOT',root),patch.object(d.routes,'store',return_value=store),TestClient(app) as client:
            yield root,store,client


class MPublicationTests(unittest.TestCase):
    def test_actual_final_78_leaves_two_sources_four_own_blank_forms(self):
        self.assertEqual(own.PUBLICATION_SHA256,FINAL)
        self.assertEqual(sha256((ROOT/own.PUBLICATION_RECEIPT).read_bytes()).hexdigest(),FINAL)
        self.assertEqual(sha256(Path(own.__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),'f0f509f6552f8cb25efd8bd50bf36d9bd87deb5b4ae36cab918acd7c47aea535')
        receipt=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
        self.assertEqual(len(receipt['files']),78)
        self.assertTrue(receipt['native_confirmation_download_own_forms'])
        self.assertEqual(receipt['eligible_originals'],4)
        for row in receipt['files']:
            body=(ROOT/row['path']).read_bytes()
            self.assertEqual((len(body),sha256(body).hexdigest()),(row['bytes'],row['sha256']))
        self.assertEqual(len(own.source_files(ROOT)),18)
        sources=[]
        for code in own.REGIONS:
            guide=own._published(code,ROOT);sources.append(guide['source_id'])
            self.assertTrue(guide['published']);self.assertTrue(guide['can_generate'])
            self.assertEqual(guide['guide_status'],'partial')
            self.assertEqual(sum(t['can_generate'] is True for t in guide['templates']),2)
            self.assertIsNone(guide['official_version']);self.assertIsNone(guide['committee_full_name'])
            self.assertIsNone(guide['channel']['entry_url']);self.assertIsNone(guide['online_entry'])
            self.assertEqual(guide['channel']['online_status'],'auth_required')
            self.assertTrue(all(t['material_id'] is None for t in guide['templates']))
        self.assertEqual(len(set(sources)),2)

    def test_real_cold_published_ASGI_four_contracts_Word_original_headers_cleanup(self):
        case=d.MDispatchTests()
        with isolated_final() as (root,store,client):
            contracts=[]
            for guide in case.guides(store):
                self.assertTrue(guide['published'])
                for kind in ['application','evidence']:
                    query=case.query(guide,kind);response=client.get('/regional/form-contract',params=query)
                    self.assertEqual(response.status_code,200,response.text);contract=response.json();contracts.append(contract['contract_id'])
                    self.assertEqual(len(contract['context']),15)
                    self.assertEqual(contract['context']['source_version'],own.SOURCE_SHAS[guide['region_code']])
                    original=own.original_bytes(guide['region_code'],kind,root=root)
                    for data in [contract['defaults'],own.example_data(guide['region_code'],kind,root=root)]:
                        response=client.post('/regional/generate',json={**query,'mode':'blank','contract_id':contract['contract_id'],'data':data})
                        self.assertEqual(response.status_code,200)
                        self.assertEqual(response.content,own.candidate_fill(own.envelope(guide['region_code'],kind,data,root=root),root=root))
                        self.assertEqual(response.headers['x-guide-source-id'],guide['source_id'])
                        self.assertEqual(response.headers['x-guide-version'],str(guide['version']))
                        self.assertEqual(response.headers['x-form-contract-id'],contract['contract_id'])
                        self.assertEqual(response.headers['x-document-origin'],'official-blank-filled')
                        with ZipFile(BytesIO(original)) as before,ZipFile(BytesIO(response.content)) as after:
                            self.assertIsNone(after.testzip());self.assertEqual(before.namelist(),after.namelist())
                            self.assertTrue(all(before.read(name)==after.read(name) for name in before.namelist() if name!='word/document.xml'))
                    response=client.get('/regional/templates/'+query['template_id'],params=query)
                    self.assertEqual(response.status_code,200);self.assertEqual(response.content,original)
            self.assertEqual(len(set(contracts)),4)
            self.assertEqual(list((root/'private/generated').iterdir()),[])

    def test_None_boolean_and_wrong_hash_cannot_approve(self):
        for pin in [None,True,False,'0'*64]:
            with self.subTest(pin=pin),patch.object(own,'PUBLICATION_SHA256',pin):
                with self.assertRaises(ValueError):own._published('350302',ROOT)
        for key in ['STAGE_SHA256','WORD_SHA']:
            with self.subTest(key=key),patch.object(own,key,None):
                with self.assertRaises(ValueError):own._published('350303',ROOT)

    def test_missing_or_tampered_real_final_leaves_and_no_ROOT_fallback(self):
        case=d.MDispatchTests()
        with isolated_final() as (root,store,client):
            guide=case.guides(store)[0];query=case.query(guide,'application')
            final=json.loads((root/own.PUBLICATION_RECEIPT).read_bytes())
            targets=[own.PUBLICATION_RECEIPT,own.STAGE_RECEIPT,own.WORD_MANIFEST,final['files'][-1]['path'],own.source_files(root)[-1]]
            for name in targets:
                path=root/name;body=path.read_bytes();path.unlink()
                with self.subTest(name=name),self.assertRaises(ValueError):own._published('350302',root)
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
                path.write_bytes(body+b' ')
                with self.subTest(tamper=name),self.assertRaises(ValueError):own._published('350302',root)
                path.write_bytes(body)
            self.assertTrue(own._published('350302',root)['published'])

    def test_same_template_SHA_never_authorizes_cross_M_source_or_adapter(self):
        first=own._published('350302',ROOT);other=own._published('350303',ROOT)
        for guide,foreign in [(first,other),(other,first)]:
            template=next(t for t in guide['templates'] if t['can_generate'] and t['document_types']==['application'])
            self.assertEqual(template['sha256'],next(t for t in foreign['templates'] if t['document_types']==['application'])['sha256'])
            for key in ['source_id','source_version','district','service_code','authority']:
                changed=deepcopy(guide);changed[key]=foreign[key]
                with self.subTest(key=key),self.assertRaises(ValueError):own.with_capabilities(changed,root=ROOT)
            for key,value in [('material_id','INVENTED'),('adapter','fujian_pingtan_own_blank_oct31l_v1'),('local_material_key',foreign['source_id']+':dom-material:1')]:
                changed=deepcopy(template);changed[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):own.checked_adapter(guide,changed,'application',root=ROOT)

    def test_all_four_metadata_only_samples_and_scanning_references_stay_blocked(self):
        for code in own.REGIONS:
            guide=own._published(code,ROOT)
            for template in guide['templates']:
                if template['can_generate'] is True:continue
                self.assertEqual(template['document_types'],[])
                self.assertIsNone(template['file']);self.assertIsNone(template['local_original'])
                changed=deepcopy(template);changed.update(can_generate=True,document_types=['application'],adapter=own.ADAPTER,official_kind='blank')
                with self.subTest(code=code,id=template['id']),self.assertRaises(ValueError):own.checked_adapter(guide,changed,'application',root=ROOT)


if __name__=='__main__':unittest.main()
