"""Two exact Putian sources -> isolated actual ASGI; fictional data only."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import json,os,shutil,tempfile,unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import regional_fujian_oct31m as own
from regional_guides import RegionalStore
from routes import regional_guides as routes
ROOT=Path(__file__).resolve().parents[2]
class MDispatchTests(unittest.TestCase):
 @contextmanager
 def isolated(self,phase='stage'):
  with tempfile.TemporaryDirectory(prefix='putian-own-api-') as temp:
   root=Path(temp);names=set(own.source_files(ROOT))
   if phase=='stage':
    word=json.loads((ROOT/own.WORD_MANIFEST).read_bytes());names.update([own.WORD_MANIFEST,own.STAGE_RECEIPT,*[r['path'] for r in word['files']]])
   for name in names:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
   store=RegionalStore(root/'candidate.sqlite');prepare=own.staged_candidate if phase=='stage' else own.parse_capture
   for code in own.REGIONS:store.put_guide(prepare(code,root=root))
   app=FastAPI();app.include_router(routes.router,prefix='/regional')
   with patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private')}),patch.object(routes,'ROOT',root),patch.object(routes,'store',return_value=store),TestClient(app) as client:
    yield root,store,client
 def guides(self,store):return [store.lookup(m['province'],m['city'],m['district']) for m in own.REGIONS.values()]
 def query(self,g,kind):return {**{k:g[k] for k in ['province','city','district','source_id','version']},'template_id':own.TEMPLATES[kind]['file_id'],'kind':kind}
 def test_registry_marker_and_independent_strict_own_models(self):
  from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
  self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
  m=routes.release_capabilities();self.assertEqual(m['candidate_stage_receipts'][own.ADAPTER],own.STAGE_SHA256);self.assertEqual(m['publication_receipts'][own.ADAPTER],own.PUBLICATION_SHA256);self.assertFalse(m['models_required'])
  for kind in ['application','evidence']:
   model=routes.generation_request_model(own.ADAPTER,kind);self.assertEqual(model.__module__,'regional_putian_request')
   for data in [{'signature':'禁止代签'},{'committeeName':'不推定'},{'unknown':'x'}]:
    with self.assertRaises(ValueError):model.model_validate(data)
  model=routes.generation_request_model(own.ADAPTER,'evidence');self.assertEqual(len(model.model_validate({}).evidenceList),1)
  for d in [{'evidenceList':[{}]*10},{'evidenceList':[{'pageCount':True}]},{'evidenceList':[{'pageCount':'01'}]},{'evidenceList':[{'pageCount':'1.2'}]}]:
   with self.assertRaises(ValueError):model.model_validate(d)
 def test_source_only_and_unknown_regions_never_inherit_forms(self):
  with self.isolated('source') as (_,store,c):
   for g in self.guides(store):
    self.assertEqual(c.get('/regional/form-contract',params=self.query(g,'application')).status_code,409)
    self.assertFalse(c.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']}).json()['can_generate'])
   for region in [('福州市','城厢区'),('莆田市','仅虚构待核验区')]:
    g=c.get('/regional/lookup',params={'province':'fujian','city':region[0],'district':region[1]}).json()
    self.assertIsNone(g['source_id']);self.assertEqual(g['templates'],[])
 def test_two_own_sources_four_forms_filled_blank_original_headers_and_ZIP(self):
  with self.isolated() as (root,store,c):
   contracts=[]
   for g in self.guides(store):
    self.assertIsNone(g['committee_full_name'])
    for kind in ['application','evidence']:
     q=self.query(g,kind);r=c.get('/regional/form-contract',params=q);self.assertEqual(r.status_code,200,r.text);f=r.json();contracts.append(f['contract_id'])
     self.assertEqual(len(f['context']),15);self.assertEqual(f['context']['source_version'],own.SOURCE_SHAS[g['region_code']])
     for key in ['fields','defaults','policy']:self.assertEqual(f[key],own.schema_descriptor(g['region_code'],kind)[key])
     original=own.original_bytes(g['region_code'],kind,root=root)
     for data in [f['defaults'],own.example_data(g['region_code'],kind,root=root)]:
      payload={**q,'mode':'blank','contract_id':f['contract_id'],'data':data};r=c.post('/regional/generate',json=payload)
      self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '')
      self.assertEqual(r.content,own.candidate_fill(own.envelope(g['region_code'],kind,data,root=root),root=root))
      self.assertEqual(r.headers['x-guide-source-id'],g['source_id']);self.assertEqual(r.headers['x-guide-version'],str(g['version']))
      self.assertEqual(r.headers['x-form-contract-id'],f['contract_id']);self.assertEqual(r.headers['cache-control'],'no-store')
      self.assertEqual(r.headers['x-document-origin'],'official-blank-filled')
      with ZipFile(BytesIO(original)) as a,ZipFile(BytesIO(r.content)) as b:
       self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist())
       for name in a.namelist():
        if name!='word/document.xml':self.assertEqual(a.read(name),b.read(name))
     r=c.get('/regional/templates/'+q['template_id'],params=q);self.assertEqual(r.status_code,200);self.assertEqual(r.content,original)
   self.assertEqual(len(set(contracts)),4);self.assertEqual(list((root/'private/generated').iterdir()),[])
 def test_equal_SHA_different_source_contract_versions_and_metadata_fail_closed(self):
  with self.isolated() as (_,store,c):
   a,b=self.guides(store);qa=self.query(a,'application');qb=self.query(b,'application')
   fa=c.get('/regional/form-contract',params=qa);fb=c.get('/regional/form-contract',params=qb)
   self.assertEqual((fa.status_code,fb.status_code),(200,200))
   self.assertEqual(fa.json()['context']['template_sha256'],fb.json()['context']['template_sha256']);self.assertNotEqual(fa.json()['contract_id'],fb.json()['contract_id'])
   for g in [a,b]:
    q=self.query(g,'application');f=c.get('/regional/form-contract',params=q).json();base={**q,'mode':'blank','contract_id':f['contract_id'],'data':{}}
    other=b if g['source_id']==a['source_id'] else a
    for change in [{'source_id':other['source_id']},{'version':g['version']+9},{'contract_id':fb.json()['contract_id'] if g==a else fa.json()['contract_id']},{'mode':'reference_adaptation'},{'template_id':own.TEMPLATES['evidence']['file_id']},{'city':'福州市'}]:
     self.assertEqual(c.post('/regional/generate',json={**base,**change}).status_code,409,change)
    for value in [True,False,'1',1.0,0,-1]:
     self.assertEqual(c.post('/regional/generate',json={**base,'version':value}).status_code,422,value)
    for t in g['templates']:
     self.assertIsNone(t['material_id'])
     if t['download_status']=='metadata_only':
      self.assertEqual(c.get('/regional/form-contract',params={**q,'template_id':t['id']}).status_code,409)
      self.assertEqual(c.get('/regional/templates/'+t['id'],params=q).status_code,409)
 def test_unknown_signature_XML_page_types_and_capacity_refused(self):
  with self.isolated() as (_,store,c):
   for g in self.guides(store):
    for kind in ['application','evidence']:
     q=self.query(g,kind);r=c.get('/regional/form-contract',params=q);self.assertEqual(r.status_code,200);f=r.json()
     base={**q,'mode':'blank','contract_id':f['contract_id'],'data':{}}
     for data in ([{'signature':'禁止'},{'factsReason':'虚构'+chr(0)},{'requests':['虚构']*4},{'committeeName':'不推定'}] if kind=='application' else [{'evidenceList':[{}]*10},{'evidenceList':[{'pageCount':True}]},{'evidenceList':[{'pageCount':'01'}]},{'evidenceList':[{'unknown':'x'}]}]):
      self.assertEqual(c.post('/regional/generate',json={**base,'data':data}).status_code,422,data)
     self.assertEqual(c.post('/regional/generate',json={**base,'signature':'禁止额外代签'}).status_code,422)
 def test_missing_own_proof_refuses_actual_contract(self):
  with self.isolated() as (root,store,c):
   g=self.guides(store)[0];q=self.query(g,'application')
   self.assertEqual(c.get('/regional/form-contract',params=q).status_code,200)
   file=root/own.STAGE_RECEIPT;file.write_bytes(b'{}')
   self.assertEqual(c.get('/regional/form-contract',params=q).status_code,409)
if __name__=='__main__':unittest.main()
