"""Actual shared H contracts/routes in temporary stores; no live stage approval."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
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
import regional_fujian_oct31h as own


class HDispatchTests(unittest.TestCase):
    @contextmanager
    def isolated(self,stage=True):
        from regional_guides import RegionalStore
        from routes import regional_guides as routes
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=json.loads((ROOT/own.WORD_MANIFEST).read_bytes())
            paths=own.source_files(ROOT)+[own.SOURCE_FREEZE,own.OFFLINE_REVIEW,own.WORD_MANIFEST]+[r['path'] for r in manifest['files']]
            for relative in paths:
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,target)
            receipt={**own.approval_requirements(), 'files':manifest['files'],'synthetic_test_fixture_only':True}
            raw=json.dumps(receipt,ensure_ascii=False).encode();(root/own.STAGE_RECEIPT).write_bytes(raw)
            pin=sha256(raw).hexdigest() if stage else None
            with patch.object(own,'STAGE_SHA256',pin),patch.object(own,'PUBLICATION_SHA256',None),patch.object(own,'ROOT',root),patch.object(routes,'ROOT',root):
                guide=own.prepare_candidate(root=root) if stage else own.parse_capture(root=root)
                store=RegionalStore(root/'test-only.sqlite');g=store.put_guide(guide)
                app=FastAPI();app.include_router(routes.router,prefix='/regional')
                with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                    yield root,store,g,client

    def test_registry_marker_source_only_and_model_selection(self):
        from regional_adapters import with_reference_capabilities
        from regional_public_provenance import public_evidence
        from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
        from routes import regional_guides as routes
        import regional_jiangsu_oct30f as f
        import regional_jiangsu_oct31g as g
        self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
        marker=routes.release_capabilities();self.assertEqual(marker['release_id'],'oct30night-own-localities-v1')
        for module in [f,g,own]:
            self.assertIn(module.ADAPTER,marker['adapters'])
            self.assertEqual(marker['candidate_stage_receipts'][module.ADAPTER],module.STAGE_SHA256)
            self.assertEqual(marker['publication_receipts'][module.ADAPTER],module.PUBLICATION_SHA256)
        self.assertIs(routes.generation_request_model(own.ADAPTER,'application'),own.ApplicationRequest)
        self.assertIs(routes.generation_request_model(own.ADAPTER,'evidence'),own.EvidenceRequest)
        with self.isolated(False) as (root,store,g,client):
            self.assertFalse(with_reference_capabilities(g,root)['can_generate'])
            self.assertIsNotNone(public_evidence(g,root))
            t=next(t for t in g['templates'] if t['id']==own.ANNEX['application'])
            query={k:g[k] for k in ['province','city','district','source_id','version']}
            self.assertEqual(client.get('/regional/form-contract',params={**query,'template_id':t['id'],'kind':'application'}).status_code,409)
            self.assertEqual(client.post('/regional/generate',json={**query,'template_id':t['id'],'kind':'application','mode':'blank','data':{}}).status_code,409)
            self.assertEqual(client.get('/regional/templates/'+t['id'],params=query).content,(root/t['file']).read_bytes())

    def test_actual_routes_contracts_originals_blank_filled_and_context_negatives(self):
        from regional_form_contracts import validate_contract_data
        with self.isolated() as (root,store,g,client):
            forms=[]
            for kind in ['application','evidence']:
                t=next(t for t in g['templates'] if t.get('document_types')==[kind])
                query={k:g[k] for k in ['province','city','district','source_id','version']};query.update(template_id=t['id'],kind=kind)
                response=client.get('/regional/form-contract',params=query);self.assertEqual(response.status_code,200,response.text)
                contract=response.json();forms.append(contract)
                self.assertEqual(contract['fields'],own.form_fields(kind));self.assertEqual(contract['defaults'],own.defaults(kind))
                self.assertFalse(contract['policy']['capacity_is_official_requirement'])
                self.assertEqual(contract['policy']['text_controls'],'newline_only')
                if kind=='evidence':self.assertEqual(len(contract['defaults']['evidenceList']),1)
                payload={**query,'mode':'blank','contract_id':contract['contract_id'],'data':{}}
                original=(root/t['file']).read_bytes()
                for data in [{},contract['defaults'],own.example_data(kind),own.example_data(kind,True)]:
                    response=client.post('/regional/generate',json={**payload,'data':data})
                    self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
                    self.assertEqual(response.headers['X-Document-Origin'],'official-blank-filled')
                    self.assertEqual(response.headers['X-Guide-Source-ID'],g['source_id'])
                    self.assertEqual(response.headers['X-Guide-Version'],str(g['version']))
                    self.assertEqual(response.headers['X-Form-Contract-ID'],contract['contract_id'])
                    with ZipFile(BytesIO(response.content)) as archive:self.assertIsNone(archive.testzip())
                    expected=BytesIO();own.fill_offline(kind,data,root=root).save(expected)
                    self.assertEqual(response.content,expected.getvalue())
                    if data in [{},contract['defaults']]:self.assertEqual(response.content,original)
                download=client.get('/regional/templates/'+t['id'],params={k:g[k] for k in ['province','city','district','source_id','version']})
                self.assertEqual(download.status_code,200);self.assertEqual(sha256(download.content).hexdigest(),t['sha256'])
                for change in [{'source_id':'foreign'},{'version':g['version']+1},{'district':'台江区'},
                               {'template_id':'other'},{'contract_id':'0'*64},{'mode':'reference_adaptation'},
                               {'kind':'evidence' if kind=='application' else 'application'}]:
                    self.assertEqual(client.post('/regional/generate',json={**payload,**change}).status_code,409,change)
                for version in [True,'1',1.0,0,-1]:
                    self.assertEqual(client.post('/regional/generate',json={**payload,'version':version}).status_code,422)
                for change in [{'kind':'unknown'},{'contract_id':'bad'}]:
                    self.assertEqual(client.post('/regional/generate',json={**payload,**change}).status_code,422)
                invalid=[{'extra':''},{'schema_version':2},{'signature':'auto'},{'applicationDate':'2026-02-30'},{'submitDate':'2026-10-31'},{'copyCount':4},{'evidenceCopyCount':2}]
                invalid+=([{'requests':['x']*4},{'factsReason':'x'*2401},{'applicantName':'a\tb'}] if kind=='application' else [
                    {'evidenceList':[{}]*16},{'evidenceList':[{'pageCount':True}]},{'evidenceList':[{'pageCount':2}]},
                    {'evidenceList':[{'pageCount':'0'}]},{'evidenceList':[{'pageCount':'10000'}]},
                    {'evidenceList':[{'originalType':'automatic'}]},{'evidenceList':[{'signature':'auto'}]}])
                for data in invalid:
                    for legacy in [False,True]:
                        req={**payload,'data':data}
                        if legacy:req.pop('contract_id')
                        self.assertEqual(client.post('/regional/generate',json=req).status_code,422,data)
                wrong=deepcopy(contract);wrong['schema_version']=2
                with self.assertRaises(ValueError):validate_contract_data(wrong,{})
            # Real client functions, fixed Node program, JSON wire data only.
            wire={'mode':'wire','lookup':client.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']}).json(),
                  'inventory':client.get('/regional/inventory').json(),'forms':forms}
            result=subprocess.run(['node',str(ROOT/'scripts/test-gulou-guide-wire.mjs')],cwd=ROOT,input=json.dumps(wire,ensure_ascii=False),encoding='utf-8',capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            generated=json.loads(result.stdout.splitlines()[-1])
            for kind,request in generated['examples'].items():
                if kind=='evidence':self.assertEqual(len(request['data']['evidenceList']),1)
                self.assertIn('虚构',json.dumps(request['data'],ensure_ascii=False))
                self.assertEqual(client.post('/regional/generate',json=request).status_code,200)
            for t in g['templates']:
                if t['official_kind']=='sample' or t['content_role']=='scanning_instructions_only':
                    self.assertEqual(client.post('/regional/generate',json={**payload,'template_id':t['id']}).status_code,409)

    def test_template_and_complete_public_proof_tamper_fail_closed(self):
        from routes import regional_guides as routes
        with self.isolated() as (root,store,g,client):
            t=next(t for t in g['templates'] if t.get('document_types')==['application'])
            query={k:g[k] for k in ['province','city','district','source_id','version']};query.update(template_id=t['id'],kind='application')
            for field,value in [('sha256','0'*64),('official_kind','sample'),('region_code','350103')]:
                bad=deepcopy(g);next(t for t in bad['templates'] if t['id']==query['template_id'])[field]=value
                with patch.object(store,'lookup',return_value=bad):self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
            (root/own.WORD_MANIFEST).write_bytes(b'{}')
            self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)

if __name__=='__main__':unittest.main()
