"""Two independently pinned P districts: real Temp ASGI and bootstrap only."""
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
import regional_fujian_oct31p as own
from regional_guides import RegionalStore
from routes import regional_guides as routes
ROOT=Path(__file__).resolve().parents[2]
IDENTITIES=[('350503','泉州市','丰泽区','89a6739d1a513a7c5a77717a'),('350504','泉州市','洛江区','4a34ce0e167250f122410ffc')]
class PDispatchTests(unittest.TestCase):
 @contextmanager
 def isolated(self,phase='stage',bootstrap=False):
  with tempfile.TemporaryDirectory(prefix='own-p-asgi-') as temp,patch.object(own,'PUBLICATION_SHA256',None):
   root=Path(temp);names=set(own.source_files(ROOT))
   if phase=='stage':names.update(own.approval_files(ROOT))
   for name in names:
    file=root/name;file.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,file)
   rows=[(own.staged_candidate if phase=='stage' else own.parse_capture)(code,root=root) for code,*_ in IDENTITIES]
   if bootstrap:
    from public_seed import bootstrap_public_data
    folder=root/'data/public-regions';folder.mkdir(parents=True)
    directory=[row for row in json.loads((ROOT/'data/public-regions/directory.json').read_bytes()) if row['code'] in {'350503','350504'}]
    self.assertEqual({row['code'] for row in directory},{'350503','350504'})
    for filename,value in [('guides.json',rows),('directory.json',directory)]:
     (folder/filename).write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
    (folder/'manifest.json').write_text(json.dumps({'schema_version':1,'files':{n:sha256((folder/n).read_bytes()).hexdigest() for n in ['guides.json','directory.json']}}),encoding='utf8')
    state=bootstrap_public_data(root,data_dir=root/'public-db')
    self.assertEqual((state['guides_imported'],state['directory_imported'],state['missing_attachments']),(2,2,[]))
    store=RegionalStore(root/'public-db/regional-guides.sqlite')
   else:
    store=RegionalStore(root/'candidate.sqlite')
    for row in rows:store.put_guide(row)
   app=FastAPI();app.include_router(routes.router,prefix='/regional')
   with patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private')}),patch.object(routes,'ROOT',root),patch.object(routes,'store',return_value=store),TestClient(app) as client:
    yield root,store,client
 def guides(self,store):return [store.lookup('fujian',city,district) for _,city,district,_ in IDENTITIES]
 def query(self,g,kind):return {**{k:g[k] for k in ['province','city','district','source_id','version']},'template_id':own.KINDS[kind][1],'kind':kind}
 def contract(self,c,g,kind):
  r=c.get('/regional/form-contract',params=self.query(g,kind));self.assertEqual(r.status_code,200,r.text);return r.json()
 def test_exact_P_registry_stage_only_marker_and_independent_models(self):
  from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
  self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
  caps=routes.release_capabilities();self.assertEqual(caps['candidate_stage_receipts'][own.ADAPTER],own.STAGE_SHA256)
  self.assertEqual(caps['publication_receipts'][own.ADAPTER],own.PUBLICATION_SHA256);self.assertEqual(routes.FUJIAN_P_PUBLICATION_SHA256,own.PUBLICATION_SHA256);self.assertFalse(caps['models_required'])
  for kind in own.KINDS:self.assertEqual(routes.generation_request_model(own.ADAPTER,kind).__module__,'regional_fujian_p_request')
 @patch.object(own,'PUBLICATION_SHA256',None)
 def test_actual_stage_output_production_shape_retains_raw_classification_and_own_binding(self):
  for code,city,district,sid in IDENTITIES:
   try:g=own.staged_candidate(code,root=ROOT)
   except PermissionError:self.fail("Own P stage integration has no independently bound stage capability yet")
   self.assertEqual((g['province'],g['city'],g['district'],g['source_id']),('fujian',city,district,sid))
   self.assertEqual(g['verification_status'],'partial');self.assertEqual(g['raw_verification_status'],'observed_unverified')
   self.assertFalse(g['published']);self.assertIsNone(g['committee_full_name']);self.assertIsNone(g['official_version'])
   self.assertEqual(g['channel']['online_status'],'auth_required');self.assertIsNone(g['channel']['entry_url'])
   self.assertEqual(len([t for t in g['templates'] if t['download_status']=='downloaded']),2)
   self.assertEqual(len([t for t in g['templates'] if t['download_status']=='metadata_only']),4)
   for kind in own.KINDS:
    schema=own.production_schema_descriptor(code,kind)
    self.assertEqual(schema['source_version'],own.SOURCE_VERSIONS[code]);self.assertEqual(schema['policy']['invalid_xml'],'reject')
    self.assertTrue(all(f['label'] for f in schema['fields']))
   for f in g['fields'].values():self.assertIsNone(f['normalized_value']);self.assertEqual(f['verification_status'],'observed_unverified')
 def test_actual_four_contracts_eight_Word_and_four_originals_strict_headers_whole_ZIP(self):
  with self.isolated() as (root,store,c):
   ids=[]
   for g in self.guides(store):
    for kind in own.KINDS:
     q=self.query(g,kind);f=self.contract(c,g,kind);ids.append(f['contract_id']);self.assertEqual(len(f['context']),15)
     self.assertEqual(f['context']['source_version'],own.SOURCE_VERSIONS[g['region_code']])
     original=own.original_bytes(g['region_code'],kind,root=root)
     fixture=json.loads((root/f"{own.QA_REPORT}/fixtures/{g['region_code']}-{kind}-normal.json").read_bytes())
     for data,expected in [(f['defaults'],original),(fixture['data'],(root/f"{own.QA_REPORT}/word/{g['region_code']}-{kind}-normal.docx").read_bytes())]:
      r=c.post('/regional/generate',json={**q,'mode':'blank','contract_id':f['contract_id'],'data':data})
      self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '');self.assertEqual(r.content,expected)
      self.assertEqual(r.headers['x-guide-source-id'],g['source_id']);self.assertEqual(r.headers['x-guide-version'],str(g['version']));self.assertEqual(r.headers['x-form-contract-id'],f['contract_id'])
      self.assertEqual(r.headers['cache-control'],'no-store');self.assertEqual(r.headers['x-document-origin'],'official-blank-filled')
      with ZipFile(BytesIO(expected)) as a,ZipFile(BytesIO(r.content)) as b:
       self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist());self.assertTrue(all(a.read(n)==b.read(n) for n in a.namelist()))
     r=c.get('/regional/templates/'+q['template_id'],params=q);self.assertEqual(r.status_code,200);self.assertEqual(r.content,original)
     self.assertEqual(r.headers['x-template-sha256'],own.KINDS[kind][2]);self.assertEqual(r.headers['x-guide-source-id'],g['source_id'])
   self.assertEqual(len(set(ids)),4);self.assertEqual(list((root/'private/generated').iterdir()),[])
 def test_source_only_stage_null_and_unknown_region_fail_closed(self):
  with self.isolated('source') as (_,store,c):
   for g in self.guides(store):
    self.assertFalse(g['can_generate']);self.assertFalse(g['published']);self.assertEqual(c.get('/regional/form-contract',params=self.query(g,'application')).status_code,409)
   for city,district in [('福州市','丰泽区'),('福州市','洛江区'),('莆田市','丰泽区'),('泉州市','虚构未知区')]:
    r=c.get('/regional/lookup',params={'province':'fujian','city':city,'district':district});self.assertEqual(r.status_code,200);self.assertIsNone(r.json()['source_id']);self.assertEqual(r.json()['templates'],[])
  for code,*_ in IDENTITIES:
   with patch.object(own,'STAGE_SHA256',None),self.assertRaises(ValueError):own.staged_candidate(code,root=ROOT)
   with patch.object(own,'PUBLICATION_SHA256',None),self.assertRaises((ValueError,PermissionError)):own.published_guide(code,root=ROOT)
 def test_cross_district_same_SHA_foreign_stale_version_and_metadata_refused(self):
  with self.isolated() as (_,store,c):
   a,b=self.guides(store);contracts=[self.contract(c,g,'application') for g in [a,b]]
   self.assertEqual(contracts[0]['context']['template_sha256'],contracts[1]['context']['template_sha256']);self.assertNotEqual(contracts[0]['contract_id'],contracts[1]['contract_id'])
   for i,g in enumerate([a,b]):
    q=self.query(g,'application');base={**q,'mode':'blank','contract_id':contracts[i]['contract_id'],'data':{}}
    for change in [{'source_id':[b,a][i]['source_id']},{'source_id':'c2f441391f073f71f55ce9de'},{'source_id':'28a4418211ce36fedd8069f6'},{'city':'福州市'},{'version':g['version']+9},{'contract_id':contracts[1-i]['contract_id']},{'template_id':own.KINDS['evidence'][1]},{'mode':'reference_adaptation'}]:
     self.assertEqual(c.post('/regional/generate',json={**base,**change}).status_code,409,change)
    for value in [True,False,None,'1',1.0,0,-1]:self.assertEqual(c.post('/regional/generate',json={**base,'version':value}).status_code,422,value)
    for t in g['templates']:
     self.assertIsNone(t['official_material_id'])
     if t['download_status']=='metadata_only':
      self.assertFalse(t['can_generate']);self.assertEqual(c.get('/regional/form-contract',params={**q,'template_id':t['id']}).status_code,409)
      self.assertEqual(c.get('/regional/templates/'+t['id'],params=q).status_code,409)
      self.assertEqual(c.post('/regional/generate',json={**base,'template_id':t['id']}).status_code,409)
 def test_strict_content_unknown_signature_XML_capacity_and_default_one(self):
  with self.isolated() as (_,store,c):
   for g in self.guides(store):
    for kind in own.KINDS:
     q=self.query(g,kind);f=self.contract(c,g,kind);base={**q,'mode':'blank','contract_id':f['contract_id'],'data':{}}
     if kind=='evidence':self.assertEqual(len(f['defaults']['evidenceList']),1);self.assertEqual(f['fields'][0]['maxItems'],9)
     bad=([{'signature':'禁止'},{'committeeName':'不推定'},{'factsReason':'虚构'+chr(0)},{'requests':['虚构']*4}] if kind=='application' else [{'evidenceList':[{}]*10},{'evidenceList':[{'pageCount':True}]},{'evidenceList':[{'pageCount':1}]},{'evidenceList':[{'pageCount':'01'}]},{'evidenceList':[{'name':chr(1)}]},{'evidenceList':[{'signature':'禁止'}]}])
     for data in bad:self.assertEqual(c.post('/regional/generate',json={**base,'data':data}).status_code,422,data)
     self.assertEqual(c.post('/regional/generate',json={**base,'signature':'禁止'}).status_code,422)
 def test_actual_cold_bootstrap_two_stage_rows_evidence_roundtrip_not_publication(self):
  from regional_adapters import checked_reference_adapter
  from regional_public_provenance import public_evidence
  for phase in ['source','stage']:
   with self.isolated(phase,bootstrap=True) as (root,store,c):
    for g in self.guides(store):
     self.assertFalse(g['published']);self.assertEqual(g['evidence'],public_evidence(g,root))
     self.assertEqual(sum(t['can_generate'] for t in g['templates']),2 if phase=='stage' else 0)
     if phase=='stage':
      for kind in own.KINDS:
       self.contract(c,g,kind);t=next(t for t in g['templates'] if t['id']==own.KINDS[kind][1]);self.assertEqual(checked_reference_adapter(g,t,kind,root=root),own.ADAPTER)
     else:self.assertFalse(g['can_generate'])
 def test_missing_proof_or_foreign_derived_evidence_never_uses_checkout_fallback(self):
  with self.isolated() as (root,store,c):
   g=self.guides(store)[0];q=self.query(g,'application');self.contract(c,g,'application')
   from regional_public_provenance import public_evidence
   for bad in [None,True,{}, {'source_projection':'wrong','source_projection_sha256':g['source_version']}]:
    changed=deepcopy(g);changed['evidence']=bad;self.assertIsNone(public_evidence(changed,root))
   (root/own.STAGE_RECEIPT).write_bytes(b'{}');self.assertEqual(c.get('/regional/form-contract',params=q).status_code,409)
   with self.assertRaises(ValueError):own.staged_candidate(g['region_code'],root=root)
 def test_read_only_lookup_contracts_inventory_never_generate_or_mutate(self):
  with self.isolated() as (_,store,c),patch.object(routes,'fill_fujian_p_document',side_effect=AssertionError('Read-only cannot generate')) as filler:
   before=deepcopy(store.inventory())
   for g in self.guides(store):
    self.assertEqual(c.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']}).status_code,200)
    for kind in own.KINDS:self.contract(c,g,kind)
   self.assertEqual(c.get('/regional/inventory').status_code,200);self.assertEqual(filler.call_count,0);self.assertEqual(store.inventory(),before)
if __name__=='__main__':unittest.main()
