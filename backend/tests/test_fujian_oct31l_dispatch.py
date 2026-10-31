"""Pingtan source-bound API regression, temporary stores and fictional data only."""
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import json, os, shutil, tempfile, unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import regional_fujian_oct31l as own
from regional_guides import RegionalStore
from routes import regional_guides as routes
ROOT=Path(__file__).resolve().parents[2]

class LDispatchTests(unittest.TestCase):
 @contextmanager
 def isolated(self,phase='stage'):
  with tempfile.TemporaryDirectory(prefix='pingtan-own-api-') as folder:
   root=Path(folder);paths=set(own.source_files(ROOT))
   if phase in ['stage','published']:
    word=json.loads((ROOT/own.WORD_MANIFEST).read_bytes())
    paths.update([own.WORD_MANIFEST,own.STAGE_RECEIPT,*[r['path'] for r in word['files']]])
   if phase=='published':
    final=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
    paths.update([own.PUBLICATION_RECEIPT,*[r['path'] for r in final['files']]])
   for name in paths:
    dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
   store=RegionalStore(root/'candidate.sqlite')
   prepare={'stage':own.staged_candidate,'published':own._published,'source':own.parse_capture}[phase]
   store.put_guide(prepare('350128',root=root))
   app=FastAPI();app.include_router(routes.router,prefix='/regional')
   with patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private')}),patch.object(routes,'ROOT',root),patch.object(routes,'store',return_value=store),TestClient(app) as client:
    yield root,store,client
 def guide(self,store):return store.lookup('fujian','平潭综合实验区','平潭综合实验区')
 def query(self,g,kind):return {**{k:g[k] for k in ['province','city','district','source_id','version']},'template_id':own.TEMPLATES[kind]['file_id'],'kind':kind}
 def test_registry_marker_and_independent_strict_own_models(self):
  from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
  self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
  marker=routes.release_capabilities();self.assertIn(own.ADAPTER,marker['adapters'])
  self.assertEqual(marker['candidate_stage_receipts'][own.ADAPTER],own.STAGE_SHA256)
  self.assertEqual(marker['publication_receipts'][own.ADAPTER],own.PUBLICATION_SHA256)
  self.assertFalse(marker['models_required'])
  for kind in ['application','evidence']:
   model=routes.generation_request_model(own.ADAPTER,kind)
   self.assertIsNot(model,routes.generation_request_model(routes.FUJIAN_K_ADAPTER,kind))
   with self.assertRaises(ValueError):model.model_validate({'signature':'不代签'})
  model=routes.generation_request_model(own.ADAPTER,'evidence')
  self.assertEqual(len(model.model_validate({}).evidenceList),1)
  for data in [{'evidenceList':[{}]*10},{'evidenceList':[{'pageCount':True}]},{'evidenceList':[{'pageCount':'01'}]}]:
   with self.subTest(data=data),self.assertRaises(ValueError):model.model_validate(data)
 def test_source_only_has_no_generation_and_city_is_not_fuzhou(self):
  with self.isolated('source') as (_,store,client):
   g=self.guide(store);q=self.query(g,'application')
   self.assertEqual(client.get('/regional/form-contract',params=q).status_code,409)
   unknown=store.lookup('fujian','福州市','平潭县')
   self.assertIsNone(unknown['source_id']);self.assertEqual(unknown['verification_status'],'unverified');self.assertEqual(unknown['templates'],[])
   response=client.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']})
   self.assertEqual(response.status_code,200);self.assertFalse(response.json()['can_generate'])
 def test_two_own_forms_default_filled_original_and_all_unrelated_parts(self):
  with self.isolated() as (root,store,client):
   g=self.guide(store);ids=[]
   for kind in ['application','evidence']:
    q=self.query(g,kind);response=client.get('/regional/form-contract',params=q)
    self.assertEqual(response.status_code,200,response.text);form=response.json();ids.append(form['contract_id'])
    self.assertEqual(form['context']['source_version'],own.SOURCE_SHA)
    for key in ['fields','defaults','policy']:self.assertEqual(form[key],own.schema_descriptor('350128',kind)[key])
    original=own.original_bytes('350128',kind,root=root)
    for data in [form['defaults'],own.example_data('350128',kind,root=root)]:
     payload={**q,'mode':'blank','contract_id':form['contract_id'],'data':data}
     response=client.post('/regional/generate',json=payload)
     self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
     self.assertEqual(response.content,own.candidate_fill(own.envelope('350128',kind,data,root=root),root=root))
     self.assertEqual(response.headers['x-guide-source-id'],own.SOURCE_ID)
     self.assertEqual(response.headers['x-form-contract-id'],form['contract_id'])
     self.assertEqual(response.headers['cache-control'],'no-store')
     with ZipFile(BytesIO(original)) as a,ZipFile(BytesIO(response.content)) as b:
      self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist())
      for name in a.namelist():
       if name!='word/document.xml':self.assertEqual(a.read(name),b.read(name))
    download=client.get('/regional/templates/'+q['template_id'],params=q)
    self.assertEqual(download.status_code,200);self.assertEqual(download.content,original)
   self.assertEqual(len(set(ids)),2);self.assertEqual(list((root/'private/generated').iterdir()),[])
 def test_cross_context_sample_and_missing_proof_fail_closed(self):
  with self.isolated() as (root,store,client):
   g=self.guide(store);q=self.query(g,'application');form=client.get('/regional/form-contract',params=q).json()
   payload={**q,'mode':'blank','contract_id':form['contract_id'],'data':{}}
   for change in [{'city':'福州市'},{'district':'平潭县'},{'source_id':'09dcedf106cd2fd411a09546'},{'version':g['version']+1},{'contract_id':'0'*64},{'mode':'reference_adaptation'},{'template_id':own.TEMPLATES['evidence']['file_id']}]:
    self.assertEqual(client.post('/regional/generate',json={**payload,**change}).status_code,409,change)
   for v in [True,'1',1.0,0,-1]:self.assertEqual(client.post('/regional/generate',json={**payload,'version':v}).status_code,422)
   samples=[t for t in g['templates'] if t['download_status']=='metadata_only'];self.assertEqual(len(samples),4)
   self.assertEqual(client.get('/regional/form-contract',params={**q,'source_id':'09dcedf106cd2fd411a09546'}).status_code,409)
   self.assertEqual(client.get('/regional/form-contract',params={**q,'city':'福州市'}).status_code,404)
   for t in samples:
    self.assertFalse(t['can_generate']);self.assertEqual(t['document_types'],[])
    self.assertEqual(client.get('/regional/form-contract',params={**q,'template_id':t['id']}).status_code,409)
   for name in [own.STAGE_RECEIPT,own.WORD_MANIFEST]:
    file=root/name;old=file.read_bytes();file.write_bytes(b'{}')
    self.assertEqual(client.get('/regional/form-contract',params=q).status_code,409);file.write_bytes(old)
if __name__=='__main__':unittest.main()
