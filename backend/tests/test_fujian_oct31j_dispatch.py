"""Real staged J shared routes/contracts, private Temp stores, no publication."""
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
import regional_fujian_oct31j as own
from regional_guides import RegionalStore
from routes import regional_guides as routes


class JDispatchTests(unittest.TestCase):
    @contextmanager
    def isolated(self,phase='stage'):
        with tempfile.TemporaryDirectory(prefix='fujian-j-dispatch-') as temporary:
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
        return {**{k:g[k] for k in ('province','city','district','source_id','version')},'template_id':own.REGIONS[g['region_code']]['templates'][kind]['file_id'],'kind':kind}

    def test_registry_real_stage_marker_and_independent_j_models(self):
        from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
        from regional_adapters import with_reference_capabilities
        from regional_public_provenance import public_evidence
        self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
        marker=routes.release_capabilities();self.assertEqual(marker['release_id'],'oct30night-own-localities-v1')
        self.assertIn(own.ADAPTER,marker['adapters'])
        self.assertEqual(marker['candidate_stage_receipts'][own.ADAPTER],own.STAGE_SHA256)
        self.assertEqual(marker['publication_receipts'][own.ADAPTER],own.PUBLICATION_SHA256);self.assertFalse(marker['models_required'])
        self.assertIsNot(routes.generation_request_model(own.ADAPTER,'application'),routes.GulouApplicationRequest)
        self.assertIsNot(routes.generation_request_model(own.ADAPTER,'application'),routes.FujianIApplicationRequest)
        self.assertIsNot(routes.generation_request_model(own.ADAPTER,'evidence'),routes.GulouEvidenceRequest)
        self.assertIsNot(routes.generation_request_model(own.ADAPTER,'evidence'),routes.FujianIEvidenceRequest)
        with self.isolated('source') as (root,store,client):
            for code in own.REGIONS:
                g=self.guide(store,code);self.assertFalse(with_reference_capabilities(g,root)['can_generate'])
                self.assertIsNotNone(public_evidence(g,root));query=self.query(g,'application')
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
                self.assertEqual(client.post('/regional/generate',json={**query,'mode':'blank','data':{}}).status_code,409)
                original=client.get('/regional/templates/'+query['template_id'],params=query)
                self.assertEqual(original.status_code,200);self.assertEqual(sha256(original.content).hexdigest(),own.REGIONS[code]['templates']['application']['sha256'])

    def test_eleven_forms_actual_contracts_originals_and_exact_blank_filled_bytes(self):
        with self.isolated() as (root,store,client):
            all_ids=[]
            for code,meta in own.REGIONS.items():
                g=self.guide(store,code);self.assertIsNone(g['committee_full_name']);self.assertFalse(g['published'])
                self.assertEqual([m['copies'] for m in g['materials']],[2,2,2])
                self.assertEqual(g['channel']['online_status'],'auth_required');self.assertIsNone(g['channel']['entry_url'])
                for kind in own.REGIONS[code]['allowed_kinds']:
                    query=self.query(g,kind);response=client.get('/regional/form-contract',params=query)
                    self.assertEqual(response.status_code,200,response.text)
                    form=response.json();descriptor=own.schema_descriptor(code,kind);all_ids.append(form['contract_id'])
                    self.assertEqual(form['fields'],descriptor['fields']);self.assertEqual(form['defaults'],descriptor['defaults'])
                    self.assertEqual(form['policy'],descriptor['policy'])
                    self.assertEqual(form['context']['schema_id'],descriptor['schema_id'])
                    self.assertEqual(form['context']['source_version'],meta['manifest_sha256'])
                    self.assertEqual(form['context']['template_sha256'],meta['templates'][kind]['sha256'])
                    if kind=='evidence':self.assertEqual(len(form['defaults']['evidenceList']),1)
                    original=own.template_path(code,kind,root=root).read_bytes()
                    payload={**query,'mode':'blank','contract_id':form['contract_id']}
                    # Every own route gets one exact blank and one reviewed
                    # filled fixture; provider QA separately covers all stress ZIPs.
                    for data in (form['defaults'],own.example_data(code,kind,root=root)):
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
            self.assertEqual(len(set(all_ids)),11)
            self.assertEqual(list((root/'private-data/generated').iterdir()),[])

    def test_wrong_context_stale_source_version_cross_j_and_sample_scan_are_closed(self):
        with self.isolated() as (root,store,client):
            guides=[self.guide(store,c) for c in own.REGIONS]
            for index,g in enumerate(guides):
                other=guides[(index+1)%len(guides)];self.assertNotEqual(g['source_id'],other['source_id'])
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
                    if template['official_kind']=='sample' or template['content_role'] in {'scanning_instructions_only','official_format_contains_filled_sample_no_generation'}:
                        self.assertEqual(client.post('/regional/generate',json={**payload,'template_id':template['id']}).status_code,409)

    def test_strict_own_slots_and_page_count_reject_in_contract_and_legacy_paths(self):
        with self.isolated() as (root,store,client):
            # J has two independent technical request models. Test their full
            # invalid-value matrix once; six-source context isolation is tested
            # separately with actual routes, rather than re-reading 124 proofs
            # for every identical model input at every locality.
            for code,kind in [('350122','application'),('350182','evidence')]:
                g=self.guide(store,code)
                query=self.query(g,kind);form=client.get('/regional/form-contract',params=query).json()
                payload={**query,'mode':'blank','data':{},'contract_id':form['contract_id']}
                invalid=[{'committeeName':'虚构错误自动填'},{'signature':'自动'},{'copyCount':2},{'extra':''},{'schema_version':2}]
                invalid+=([{'applicantName':1},{'requests':['x']*4},{'factsReason':'x'*2401},{'agentName':'x\t'}] if kind=='application' else [
                    {'evidenceList':[{}]*16},{'evidenceList':[{'name':'x'*61}]},{'evidenceList':[{'purpose':'x'*81}]},
                    *[{'evidenceList':[{'pageCount':v}]} for v in (True,2,'0','01','10000','-1','1.0')],
                    {'evidenceList':[{'originalType':'自动'}]},{'evidenceList':[{'signature':'自动'}]}])
                model=routes.generation_request_model(own.ADAPTER,kind)
                for data in invalid:
                    with self.subTest(kind=kind,data=data),self.assertRaises(ValueError):model.model_validate(data)
                selected=invalid[:3]+([{'applicantName':1},{'agentName':'x\t'},{'requests':['x']*4}] if kind=='application' else [
                    {'evidenceList':[{'pageCount':True}]},{'evidenceList':[{'pageCount':'01'}]},{'evidenceList':[{'pageCount':2}]}])
                for data in selected:
                    for legacy in (False,True):
                        request={**payload,'data':data}
                        if legacy:request.pop('contract_id')
                        self.assertEqual(client.post('/regional/generate',json=request).status_code,422,(code,kind,data,legacy))

    def test_actual_typescript_wire_display_examples_and_cancel_reads_have_zero_generation(self):
        with self.isolated() as (root,store,client):
            wire=[]
            with patch.object(routes,'fill_fujian_j_document',side_effect=AssertionError('Read/cancel must not generate')) as filler:
                for code in own.REGIONS:
                    g=self.guide(store,code);lookup=client.get('/regional/lookup',params={k:g[k] for k in ('province','city','district')})
                    forms=[client.get('/regional/form-contract',params=self.query(g,k)).json() for k in own.REGIONS[code]['allowed_kinds']]
                    wire.append({'lookup':lookup.json(),'forms':forms})
                inventory=client.get('/regional/inventory').json();self.assertEqual(filler.call_count,0)
            result=subprocess.run(['node',str(ROOT/'backend/tests/fixtures/test-fujian-j-wire.mjs')],input=json.dumps({'regions':wire,'inventory':inventory},ensure_ascii=False),
                encoding='utf-8',capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.assertEqual(result.returncode,0,result.stderr)
            examples=json.loads(result.stdout.splitlines()[-1])['examples'];self.assertEqual(len(examples),11)
            for request in examples:self.assertEqual(client.post('/regional/generate',json=request).status_code,200)

    def test_offline_candidate_missing_stage_and_tampered_cold_root_never_borrow_checkout(self):
        with self.isolated('offline') as (root,store,client):
            g=self.guide(store,'350122');query=self.query(g,'application')
            self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
        with self.isolated() as (root,store,client):
            g=self.guide(store,'350123');query=self.query(g,'application')
            for relative in (own.STAGE_RECEIPT,own.WORD_MANIFEST,own.SOURCE_BASE+'/'+own.REGIONS['350123']['folder']+'/SOURCE-PROJECTION-MANIFEST.json'):
                path=root/relative;original=path.read_bytes();path.write_bytes(b'{}')
                self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
                path.write_bytes(original)
            own.template_path('350123','application',root=root).unlink()
            self.assertEqual(client.get('/regional/form-contract',params=query).status_code,409)
            self.assertEqual(client.get('/regional/templates/'+query['template_id'],params=query).status_code,409)


    def test_actual_source_offline_stage_typescript_parser_projection(self):
        with self.isolated('source') as (root,store,client):
            guides=[]
            for prepare in (own.parse_capture,own.prepare_candidate,own.staged_candidate):
                for code,meta in own.REGIONS.items():
                    store.put_guide(prepare(code,root=root))
                    response=client.get('/regional/lookup',params={k:meta[k] for k in ('province','city','district')})
                    self.assertEqual(response.status_code,200);guides.append(response.json())
            result=subprocess.run(['node',str(ROOT/'scripts/test-fujian-j-guide-wire.mjs')],input=json.dumps(guides,ensure_ascii=False),
                encoding='utf-8',capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_cross_i_and_j_equal_app_bytes_never_share_source_or_contract(self):
        import regional_fujian_oct31i as other
        with self.isolated() as (root,store,client):
            paths=set(other.source_files(ROOT)+[other.WORD_MANIFEST,other.STAGE_RECEIPT,other.PUBLICATION_RECEIPT])
            for receipt in (other.WORD_MANIFEST,other.STAGE_RECEIPT,other.PUBLICATION_RECEIPT):
                paths.update(r['path'] for r in json.loads((ROOT/receipt).read_bytes())['files'])
            for relative in paths:
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,target)
            i_guide=store.put_guide(other.with_publication_evidence(other.staged_candidate('350103',root=root),root=root))
            i_query={**{k:i_guide[k] for k in ('province','city','district','source_id','version')},'template_id':other.SPECS['application']['id'],'kind':'application'}
            i_form=client.get('/regional/form-contract',params=i_query)
            self.assertEqual(i_form.status_code,200,i_form.text)
            for code in own.REGIONS:
                g=self.guide(store,code);query=self.query(g,'application');form=client.get('/regional/form-contract',params=query).json()
                self.assertEqual(form['context']['template_sha256'],i_form.json()['context']['template_sha256'])
                self.assertNotEqual(form['context']['source_id'],i_form.json()['context']['source_id'])
                self.assertNotEqual(form['context']['schema_id'],i_form.json()['context']['schema_id'])
                for context,foreign_contract in ((query,i_form.json()['contract_id']),(i_query,form['contract_id'])):
                    response=client.post('/regional/generate',json={**context,'mode':'blank','contract_id':foreign_contract,'data':{}})
                    self.assertEqual(response.status_code,409)
            changle=self.guide(store,'350182');query=self.query(changle,'evidence')
            form=client.get('/regional/form-contract',params=query).json()
            common=own.REGIONS['350122']['templates']['evidence']['file_id']
            self.assertEqual(client.post('/regional/generate',json={**query,'template_id':common,'mode':'blank','contract_id':form['contract_id'],'data':{}}).status_code,409)
            yongtai=self.guide(store,'350125');query=self.query(yongtai,'application')
            self.assertEqual(client.get('/regional/form-contract',params={**query,'kind':'evidence'}).status_code,409)

    def test_explicit_temp_candidate_append_adds_six_capabilities_without_old_mutation(self):
        seed_path=ROOT/'data/public-regions/guides.json';seed_bytes=seed_path.read_bytes()
        published=json.loads(seed_bytes);manifest=json.loads((ROOT/'data/public-regions/manifest.json').read_bytes())
        self.assertEqual(len(published),manifest['guides'])
        self.assertEqual(sum(any(t.get('can_generate') for t in g['templates']) for g in published),manifest['generatable_localities'])
        # Keep this fixture valid after a separately approved J publication.
        # Only this new Temp DB omits J before explicitly staging the six rows.
        snapshot=[g for g in published if g['region_code'] not in own.REGIONS]
        active=[g for g in snapshot if any(t.get('can_generate') for t in g['templates'])]
        previous_pairs=sum(len(t['document_types']) for g in active for t in g['templates'] if t.get('can_generate'))
        with self.isolated() as (root,_,client):
            store=RegionalStore(root/'explicit-matrix.sqlite')
            for g in snapshot:store.put_guide(g)
            with store.connection() as db:
                before=[tuple(r) for r in db.execute('SELECT * FROM regional_guides ORDER BY sequence')]
                pointers=[tuple(r) for r in db.execute('SELECT * FROM regional_current ORDER BY region_id')]
            for code in own.REGIONS:store.put_guide(own.staged_candidate(code,root=root))
            with store.connection() as db:
                after=[tuple(r) for r in db.execute('SELECT * FROM regional_guides WHERE sequence<=? ORDER BY sequence',(len(snapshot),))]
                self.assertEqual(after,before)
                self.assertTrue(all(tuple(r) in [tuple(v) for v in db.execute('SELECT * FROM regional_current')] for r in pointers))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM collection_outbox').fetchone()[0],0)
            inventory=store.inventory();generatable=[g for g in inventory if any(t.get('can_generate') for t in g['templates'])]
            self.assertEqual((len(inventory),len(generatable)),(len(snapshot)+6,len(active)+6))
            self.assertEqual(sum(len(t['document_types']) for g in generatable for t in g['templates'] if t.get('can_generate')),previous_pairs+11)
            with patch.object(routes,'store',return_value=store):
                for code,meta in own.REGIONS.items():
                    for kind in meta['allowed_kinds']:
                        response=client.get('/regional/form-contract',params=self.query(self.guide(store,code),kind))
                        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(seed_path.read_bytes(),seed_bytes)

    def test_actual_directory_code_350182_selects_lookup_and_two_own_contracts(self):
        from regional_directory import DirectoryStore
        raw=(ROOT/'data/public-regions/directory.json').read_bytes()
        self.assertEqual(sha256(raw).hexdigest(),'913daa7dd7bcbec570945fd7cc8ed08ae55b15c50665e5f8f4d967b62fc85ba8')
        rows=json.loads(raw);self.assertEqual(len(rows),3974)
        actual=[r for r in rows if r['code']=='350182']
        self.assertEqual(len(actual),1)
        self.assertEqual((actual[0]['province'],actual[0]['city'],actual[0]['district'],actual[0]['official_name']),('fujian','福州市','长乐区','长乐区'))
        with self.isolated() as (root,store,client):
            directory=DirectoryStore(root/'actual-directory.sqlite')
            for row in rows:
                if row['province']=='fujian' and row['city']=='福州市' and row['level']==4:directory.put_area(row)
            with patch.object(routes,'directory_store',return_value=directory):
                areas=client.get('/regional/areas',params={'province':'fujian','city':'福州市'})
                self.assertEqual(areas.status_code,200)
                selected=next(r for r in areas.json()['items'] if r['code']=='350182')
                self.assertEqual(selected['district'],'长乐区');self.assertEqual(selected['source_id'],own.REGIONS['350182']['source_id'])
                self.assertTrue(selected['can_generate'])
                region={k:selected[k] for k in ('province','city','district')}
                response=client.get('/regional/lookup',params=region);self.assertEqual(response.status_code,200)
                guide=response.json();self.assertEqual(guide['source_id'],selected['source_id'])
                self.assertEqual((guide['region_code'],guide['district']),('350182','长乐区'))
                for kind in ('application','evidence'):
                    query=self.query(guide,kind);form=client.get('/regional/form-contract',params=query)
                    self.assertEqual(form.status_code,200,form.text)
                    self.assertEqual(form.json()['context']['district'],selected['district'])
                    self.assertEqual(form.json()['context']['schema_id'],f'fujian-j-350182-{kind}-v1')
                    if kind=='evidence':self.assertEqual(form.json()['context']['template_sha256'],'511d213073af6e25b0f9f8ed2b914b7b31ee47bf6cef2fbb85a0422e3d6a4f56')
                    for wrong in ('福州市长乐区','福州市福州市长乐区','长乐市'):
                        missing=client.get('/regional/lookup',params={**region,'district':wrong}).json()
                        self.assertIsNone(missing['source_id'])
                        self.assertEqual(client.get('/regional/form-contract',params={**query,'district':wrong}).status_code,404)
                    self.assertEqual(client.get('/regional/form-contract',params={**query,'district':'连江县'}).status_code,409)
        self.assertEqual((ROOT/'data/public-regions/directory.json').read_bytes(),raw)


if __name__=='__main__':unittest.main()
