"""Actual isolated K stage/final API phases; no public seed or real service."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import regional_fujian_oct31k as own
from regional_guides import RegionalStore
from routes import regional_guides as routes


class KDispatchTests(unittest.TestCase):
    @contextmanager
    def isolated(self,phase='stage'):
        with tempfile.TemporaryDirectory(prefix='fujian-k-dispatch-') as folder:
            root=Path(folder);word=json.loads((ROOT/own.WORD_MANIFEST).read_bytes())
            paths=set(own.source_files(ROOT)+[own.WORD_MANIFEST,own.STAGE_RECEIPT]+[r['path'] for r in word['files']])
            if phase=='published':
                final=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
                paths.update([own.PUBLICATION_RECEIPT,*[r['path'] for r in final['files']]])
            for name in paths:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
            store=RegionalStore(root/'candidate.sqlite')
            prepare={'stage':own.staged_candidate,'source':own.parse_capture,'offline':own.prepare_candidate,'published':own._published}[phase]
            for code in own.REGIONS:store.put_guide(prepare(code,root=root))
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            with patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private-data')}),patch.object(routes,'ROOT',root),patch.object(routes,'store',return_value=store),TestClient(app) as client:
                yield root,store,client

    def guide(self,store,code):return store.lookup('fujian','福州市',own.REGIONS[code]['district'])
    def query(self,g,kind):return {**{k:g[k] for k in ['province','city','district','source_id','version']},'template_id':own.REGIONS[g['region_code']]['templates'][kind]['file_id'],'kind':kind}

    def wire(self,store,client):
        rows=[]
        for code in own.REGIONS:
            g=self.guide(store,code);lookup=client.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']})
            self.assertEqual(lookup.status_code,200)
            forms=[]
            for kind in own.REGIONS[code]['allowed_kinds']:
                response=client.get('/regional/form-contract',params=self.query(g,kind));self.assertEqual(response.status_code,200,response.text);forms.append(response.json())
            rows.append({'lookup':lookup.json(),'forms':forms})
        return {'regions':rows,'inventory':client.get('/regional/inventory').json()}

    def test_exact_registry_marker_models_and_root_stage_only(self):
        from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
        self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
        marker=routes.release_capabilities();self.assertIn(own.ADAPTER,marker['adapters'])
        self.assertEqual(marker['candidate_stage_receipts'][own.ADAPTER],own.STAGE_SHA256)
        self.assertEqual(marker['publication_receipts'][own.ADAPTER],own.PUBLICATION_SHA256);self.assertFalse(marker['models_required'])
        for kind in ['application','evidence']:
            model=routes.generation_request_model(own.ADAPTER,kind)
            self.assertIsNot(model,routes.FujianJApplicationRequest if kind=='application' else routes.FujianJEvidenceRequest)
            self.assertIsNot(model,routes.FujianIApplicationRequest if kind=='application' else routes.FujianIEvidenceRequest)
        evidence=routes.generation_request_model(own.ADAPTER,'evidence').model_validate({})
        self.assertEqual(len(evidence.evidenceList),1)
        with self.assertRaises(ValueError):routes.generation_request_model(own.ADAPTER,'evidence').model_validate({'evidenceList':[{}]*10})

    def test_actual_four_forms_originals_filled_ZIP_headers_and_cleanup(self):
        with self.isolated() as (root,store,client):
            ids=[]
            for code,meta in own.REGIONS.items():
                g=self.guide(store,code);self.assertFalse(g['published']);self.assertIsNone(g['committee_full_name'])
                for kind in meta['allowed_kinds']:
                    query=self.query(g,kind);response=client.get('/regional/form-contract',params=query);self.assertEqual(response.status_code,200,response.text)
                    contract=response.json();descriptor=own.schema_descriptor(code,kind);ids.append(contract['contract_id'])
                    for key in ['fields','defaults','policy']:self.assertEqual(contract[key],descriptor[key])
                    self.assertEqual(contract['context']['source_version'],meta['manifest_sha256'])
                    self.assertEqual(contract['context']['version'],g['version'])
                    if kind=='evidence':self.assertEqual(contract['fields'][0]['maxItems'],9);self.assertEqual(len(contract['defaults']['evidenceList']),1)
                    original=own.template_path(code,kind,root=root).read_bytes()
                    for data in [contract['defaults'],own.example_data(code,kind,root=root)]:
                        before=deepcopy(data);response=client.post('/regional/generate',json={**query,'mode':'blank','contract_id':contract['contract_id'],'data':data})
                        self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
                        self.assertEqual(data,before);self.assertEqual(response.content,own.candidate_fill(own.envelope(code,kind,data,root=root),root=root))
                        for key,value in [('x-guide-source-id',g['source_id']),('x-guide-version',str(g['version'])),('x-form-contract-id',contract['contract_id']),('x-document-origin','official-blank-filled'),('cache-control','no-store')]:self.assertEqual(response.headers[key],value)
                        with ZipFile(BytesIO(original)) as a,ZipFile(BytesIO(response.content)) as b:
                            self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist())
                            for part in a.namelist():
                                if part!='word/document.xml':self.assertEqual(a.read(part),b.read(part))
                    download=client.get('/regional/templates/'+query['template_id'],params=query)
                    self.assertEqual(download.status_code,200);self.assertEqual(download.content,original)
                    self.assertEqual(download.headers['x-template-sha256'],sha256(original).hexdigest());self.assertEqual(download.headers['x-guide-source-id'],g['source_id'])
            self.assertEqual(len(set(ids)),4)
            self.assertEqual(list((root/'private-data/generated').iterdir()),[])

    def test_counterfactual_context_canonical_Minhou_version_types_and_14_metadata_only_attachments(self):
        with self.isolated() as (root,store,client):
            guides=[self.guide(store,c) for c in own.REGIONS];blocked=0
            for i,g in enumerate(guides):
                other=guides[(i+1)%3];query=self.query(g,'application');form=client.get('/regional/form-contract',params=query)
                self.assertEqual(form.status_code,200,form.text);contract=form.json()['contract_id'];payload={**query,'mode':'blank','contract_id':contract,'data':{}}
                for change in [{'province':'jiangsu'},{'district':other['district']},{'source_id':other['source_id']},{'source_id':'3b6dd0535bf4cb4ed328fda4'},{'version':g['version']+20},{'contract_id':'0'*64},{'mode':'reference_adaptation'},{'template_id':'missing'}]:
                    self.assertEqual(client.post('/regional/generate',json={**payload,**change}).status_code,409,change)
                for version in [True,'1',1.0,0,-1]:self.assertEqual(client.post('/regional/generate',json={**payload,'version':version}).status_code,422,version)
                crossed={**self.query(other,'application'),'mode':'blank','contract_id':contract,'data':{}}
                self.assertEqual(client.post('/regional/generate',json=crossed).status_code,409)
                for t in g['templates']:
                    if t['download_status']=='metadata_only':
                        blocked+=1
                        self.assertFalse(t['can_generate']);self.assertEqual(t['document_types'],[])
                        self.assertEqual(client.get('/regional/form-contract',params={**query,'template_id':t['id']}).status_code,409)
                        self.assertEqual(client.post('/regional/generate',json={**payload,'template_id':t['id']}).status_code,409)
                        self.assertEqual(client.get('/regional/templates/'+t['id'],params=query).status_code,409)
                if g['region_code']!='350111':self.assertEqual(client.get('/regional/form-contract',params={**query,'kind':'evidence'}).status_code,409)
            self.assertEqual(blocked,14)

    def test_source_offline_missing_stage_tamper_and_wrong_phase_do_not_gain_permission(self):
        for phase in ['source','offline']:
            with self.subTest(phase=phase),self.isolated(phase) as (_,store,client):
                g=self.guide(store,'350111');query=self.query(g,'application')
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
        with self.isolated() as (root,store,client):
            g=self.guide(store,'350121');query=self.query(g,'application')
            for value in [None,True,'0'*64]:
                with patch.object(own,'STAGE_SHA256',value):self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
            for name in [own.STAGE_RECEIPT,own.WORD_MANIFEST,own.SOURCE_BASE+'/'+own.REGIONS['350121']['folder']+'/SOURCE-PROJECTION-MANIFEST.json']:
                path=root/name;original=path.read_bytes();path.write_bytes(b'{}')
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409);path.write_bytes(original)
            receipt_path=root/own.STAGE_RECEIPT;receipt=json.loads(receipt_path.read_bytes());receipt['can_publish']=True
            body=json.dumps(receipt,ensure_ascii=False).encode();receipt_path.write_bytes(body)
            with patch.object(own,'STAGE_SHA256',sha256(body).hexdigest()):
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
            self.assertEqual(own.PUBLICATION_SHA256,'3f24c81c617733000c85f1c76b4c2e4bcd0a08e82f34b5323dbeea0b6a7154be')
            with self.assertRaises(ValueError):own.with_publication_evidence(g,root=root)

    def test_strict_independent_models_and_legacy_path_reject_bad_values(self):
        with self.isolated() as (root,store,client):
            for code,kind in [('350121','application'),('350111','evidence')]:
                g=self.guide(store,code);query=self.query(g,kind);response=client.get('/regional/form-contract',params=query);self.assertEqual(response.status_code,200,response.text)
                payload={**query,'mode':'blank','contract_id':response.json()['contract_id'],'data':{}}
                invalid=[{'extra':''},{'committeeName':'自动填名'},{'copyCount':2}]
                invalid+=([{'applicantName':True},{'agentName':1},{'requests':['x']*4},{'factsReason':'x'*2401},{'factsReason':'\t'}] if kind=='application' else [{'evidenceList':[{}]*10},{'evidenceList':[{'name':'x'*61}]},{'evidenceList':[{'originalType':'自动'}]},*[{'evidenceList':[{'pageCount':v}]} for v in [True,2,'0','01','-1','1.0']]])
                model=routes.generation_request_model(own.ADAPTER,kind)
                for data in invalid:
                    with self.subTest(kind=kind,data=data),self.assertRaises(ValueError):model.model_validate(data)
                for data in invalid[:3]+invalid[-2:]:
                    for legacy in [False,True]:
                        request={**payload,'data':data}
                        if legacy:request.pop('contract_id')
                        self.assertEqual(client.post('/regional/generate',json=request).status_code,422,(kind,data,legacy))

    def test_read_cancel_wire_uses_real_store_and_never_calls_filler(self):
        with self.isolated() as (_,store,client):
            self.assertTrue(hasattr(routes,'fill_fujian_k_document'),'K dispatch must be explicit')
            with patch.object(routes,'fill_fujian_k_document',side_effect=AssertionError('Reads/cancel cannot fill')) as filler:
                wire=self.wire(store,client);self.assertEqual(filler.call_count,0)
                self.assertEqual(len(wire['regions']),3);self.assertEqual(sum(len(r['forms']) for r in wire['regions']),4)
                for row in wire['regions']:
                    g=row['lookup'];self.assertFalse(g['published']);self.assertTrue(g['can_generate']);self.assertGreater(g['version'],0)
                    self.assertEqual([m['original_copy'] for m in g['materials']],['原件','原件','复印件'])


if __name__=='__main__':unittest.main(verbosity=2)
