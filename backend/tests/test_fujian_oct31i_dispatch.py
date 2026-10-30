"""Real staged I shared routes/contracts, private Temp stores, no publication."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import regional_fujian_oct31i as own
from regional_guides import RegionalStore
from routes import regional_guides as routes


class IDispatchTests(unittest.TestCase):
    @contextmanager
    def isolated(self,phase='stage'):
        with tempfile.TemporaryDirectory(prefix='fujian-i-dispatch-') as temporary:
            root=Path(temporary).resolve();manifest=json.loads((ROOT/own.WORD_MANIFEST).read_bytes())
            paths=set(own.source_files(ROOT)+[own.WORD_MANIFEST,own.STAGE_RECEIPT]+[r['path'] for r in manifest['files']])
            for relative in paths:
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,target)
            store=RegionalStore(root/'candidate.sqlite')
            for code in own.REGIONS:
                guide=(own.staged_candidate if phase=='stage' else own.prepare_candidate if phase=='offline' else own.parse_capture)(code,root=root)
                store.put_guide(guide)
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            with patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private-data')}),patch.object(routes,'ROOT',root),\
                 patch.object(routes,'store',return_value=store),patch.object(own,'ROOT',root/'absent-checkout'),TestClient(app) as client:
                yield root,store,client

    def guide(self,store,code):return store.lookup('fujian','福州市',own.REGIONS[code]['district'])
    def query(self,g,kind):
        return {**{k:g[k] for k in ('province','city','district','source_id','version')},'template_id':own.SPECS[kind]['id'],'kind':kind}

    def test_registry_real_stage_marker_and_independent_i_models(self):
        from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
        from regional_adapters import with_reference_capabilities
        from regional_public_provenance import public_evidence
        self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
        marker=routes.release_capabilities();self.assertEqual(marker['release_id'],'oct30night-own-localities-v1')
        self.assertIn(own.ADAPTER,marker['adapters'])
        self.assertEqual(marker['candidate_stage_receipts'][own.ADAPTER],own.STAGE_SHA256)
        self.assertEqual(marker['publication_receipts'][own.ADAPTER],own.PUBLICATION_SHA256);self.assertFalse(marker['models_required'])
        self.assertIsNot(routes.generation_request_model(own.ADAPTER,'application'),routes.GulouApplicationRequest)
        self.assertIsNot(routes.generation_request_model(own.ADAPTER,'evidence'),routes.GulouEvidenceRequest)
        with self.isolated('source') as (root,store,client):
            for code in own.REGIONS:
                g=self.guide(store,code);self.assertFalse(with_reference_capabilities(g,root)['can_generate'])
                self.assertIsNotNone(public_evidence(g,root));query=self.query(g,'application')
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
                self.assertEqual(client.post('/regional/generate',json={**query,'mode':'blank','data':{}}).status_code,409)
                original=client.get('/regional/templates/'+query['template_id'],params=query)
                self.assertEqual(original.status_code,200);self.assertEqual(sha256(original.content).hexdigest(),own.SPECS['application']['sha256'])

    def test_four_forms_actual_contracts_originals_and_exact_blank_filled_bytes(self):
        with self.isolated() as (root,store,client):
            all_ids=[]
            for code,meta in own.REGIONS.items():
                g=self.guide(store,code);self.assertIsNone(g['committee_full_name']);self.assertFalse(g['published'])
                self.assertEqual([m['copies'] for m in g['materials']],[meta['copies']]*3)
                self.assertEqual(g['channel']['online_status'],'auth_required');self.assertIsNone(g['channel']['entry_url'])
                for kind in own.KINDS:
                    query=self.query(g,kind);response=client.get('/regional/form-contract',params=query)
                    self.assertEqual(response.status_code,200,response.text)
                    form=response.json();descriptor=own.schema_descriptor(code,kind);all_ids.append(form['contract_id'])
                    self.assertEqual(form['fields'],descriptor['fields']);self.assertEqual(form['defaults'],descriptor['defaults'])
                    self.assertEqual(form['policy'],descriptor['policy'])
                    self.assertEqual(form['context']['schema_id'],descriptor['schema_id'])
                    self.assertEqual(form['context']['source_version'],meta['manifest_sha256'])
                    self.assertEqual(form['context']['template_sha256'],own.SPECS[kind]['sha256'])
                    if kind=='evidence':self.assertEqual(len(form['defaults']['evidenceList']),1)
                    original=own.template_path(code,kind,root=root).read_bytes()
                    payload={**query,'mode':'blank','contract_id':form['contract_id']}
                    for data in ({},form['defaults'],own.example_data(code,kind,root=root),own.example_data(code,kind,True,root=root)):
                        before=deepcopy(data);response=client.post('/regional/generate',json={**payload,'data':data})
                        self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
                        self.assertEqual(data,before)
                        self.assertEqual(response.headers['x-guide-source-id'],g['source_id'])
                        self.assertEqual(response.headers['x-guide-version'],str(g['version']))
                        self.assertEqual(response.headers['x-document-origin'],'official-blank-filled')
                        self.assertEqual(response.headers['x-form-contract-id'],form['contract_id'])
                        self.assertEqual(response.headers['cache-control'],'no-store')
                        expected=own.candidate_fill(own.envelope(code,kind,data,root=root),root=root)
                        self.assertEqual(response.content,expected)
                        if data in ({},form['defaults']):self.assertEqual(response.content,original)
                        with ZipFile(BytesIO(original)) as source,ZipFile(BytesIO(response.content)) as output:
                            self.assertEqual(source.namelist(),output.namelist())
                            for part in source.namelist():
                                if part!='word/document.xml':self.assertEqual(source.read(part),output.read(part))
                    download=client.get('/regional/templates/'+query['template_id'],params=query)
                    self.assertEqual(download.status_code,200);self.assertEqual(download.content,original)
                    self.assertEqual(download.headers['x-template-sha256'],sha256(original).hexdigest())
                    self.assertEqual(download.headers['x-guide-source-id'],g['source_id'])
                    self.assertEqual(own.template_path(code,kind,root=root).read_bytes(),original)
            self.assertEqual(len(set(all_ids)),4)
            self.assertEqual(list((root/'private-data/generated').iterdir()),[])

    def test_wrong_context_stale_source_version_cross_i_and_sample_scan_are_closed(self):
        with self.isolated() as (root,store,client):
            guides=[self.guide(store,c) for c in own.REGIONS]
            for index,g in enumerate(guides):
                other=guides[1-index];self.assertNotEqual(g['source_id'],other['source_id'])
                query=self.query(g,'application');form=client.get('/regional/form-contract',params=query).json()
                payload={**query,'mode':'blank','contract_id':form['contract_id'],'data':{}}
                for change in ({'province':'jiangsu'},{'district':other['district']},{'source_id':other['source_id']},
                    {'source_id':'old-source'},{'version':g['version']+10},{'template_id':'missing'},{'kind':'evidence'},
                    {'contract_id':'0'*64},{'mode':'reference_adaptation'}):
                    self.assertEqual(client.post('/regional/generate',json={**payload,**change}).status_code,409,change)
                crossed={**self.query(other,'application'),'mode':'blank','contract_id':form['contract_id'],'data':{}}
                self.assertEqual(client.post('/regional/generate',json=crossed).status_code,409)
                for version in (True,'1',1.0,0,-1):
                    self.assertEqual(client.post('/regional/generate',json={**payload,'version':version}).status_code,422,version)
                bad=deepcopy(g);bad['templates']=deepcopy(other['templates'])
                with patch.object(store,'lookup',return_value=bad):
                    self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
                for template in g['templates']:
                    if template['official_kind']=='sample' or template['content_role']=='scanning_instructions_only':
                        self.assertEqual(client.post('/regional/generate',json={**payload,'template_id':template['id']}).status_code,409)

    def test_strict_own_slots_and_page_count_reject_in_contract_and_legacy_paths(self):
        with self.isolated() as (root,store,client):
            for code in own.REGIONS:
                g=self.guide(store,code)
                for kind in own.KINDS:
                    query=self.query(g,kind);form=client.get('/regional/form-contract',params=query).json()
                    payload={**query,'mode':'blank','data':{},'contract_id':form['contract_id']}
                    invalid=[{'committeeName':'虚构错误自动填'},{'signature':'自动'},{'copyCount':2},{'extra':''},{'schema_version':2}]
                    invalid+=([{'applicantName':1},{'requests':['x']*4},{'factsReason':'x'*2401},{'agentName':'x\t'}] if kind=='application' else [
                        {'evidenceList':[{}]*16},{'evidenceList':[{'name':'x'*61}]},{'evidenceList':[{'purpose':'x'*81}]},
                        *[{'evidenceList':[{'pageCount':v}]} for v in (True,2,'0','01','10000','-1','1.0')],
                        {'evidenceList':[{'originalType':'自动'}]},{'evidenceList':[{'signature':'自动'}]}])
                    for data in invalid:
                        for legacy in (False,True):
                            request={**payload,'data':data}
                            if legacy:request.pop('contract_id')
                            self.assertEqual(client.post('/regional/generate',json=request).status_code,422,(code,kind,data,legacy))

    def test_actual_typescript_wire_display_examples_and_cancel_reads_have_zero_generation(self):
        with self.isolated() as (root,store,client):
            wire=[]
            with patch.object(routes,'fill_fujian_i_document',side_effect=AssertionError('Read/cancel must not generate')) as filler:
                for code in own.REGIONS:
                    g=self.guide(store,code);lookup=client.get('/regional/lookup',params={k:g[k] for k in ('province','city','district')})
                    forms=[client.get('/regional/form-contract',params=self.query(g,k)).json() for k in own.KINDS]
                    wire.append({'lookup':lookup.json(),'forms':forms})
                inventory=client.get('/regional/inventory').json();self.assertEqual(filler.call_count,0)
            result=subprocess.run(['node',str(ROOT/'backend/tests/fixtures/test-fujian-i-wire.mjs')],input=json.dumps({'regions':wire,'inventory':inventory},ensure_ascii=False),
                encoding='utf-8',capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.assertEqual(result.returncode,0,result.stderr)
            examples=json.loads(result.stdout.splitlines()[-1])['examples'];self.assertEqual(len(examples),4)
            for request in examples:self.assertEqual(client.post('/regional/generate',json=request).status_code,200)

    def test_offline_candidate_missing_stage_and_tampered_cold_root_never_borrow_checkout(self):
        with self.isolated('offline') as (root,store,client):
            g=self.guide(store,'350103');query=self.query(g,'application')
            self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
        with self.isolated() as (root,store,client):
            g=self.guide(store,'350104');query=self.query(g,'application')
            for relative in (own.STAGE_RECEIPT,own.WORD_MANIFEST,own.SOURCE_BASE+'/'+own.REGIONS['350104']['folder']+'/SOURCE-PROJECTION-MANIFEST.json'):
                path=root/relative;original=path.read_bytes();path.write_bytes(b'{}')
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
                path.write_bytes(original)
            own.template_path('350104','application',root=root).unlink()
            self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
            self.assertEqual(client.get('/regional/templates/'+query['template_id'],params=query).status_code,409)


if __name__=='__main__':unittest.main()
