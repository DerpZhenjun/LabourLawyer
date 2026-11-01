"""Genuine P publication acceptance. Root must seal the literal; never skip/fake it."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import json,os,re,shutil,tempfile,unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import regional_fujian_oct31p as own
from regional_guides import RegionalStore
from routes import regional_guides as routes
from regional_adapters import checked_reference_adapter
from regional_public_provenance import public_evidence
ROOT=Path(__file__).resolve().parents[2]
# Root alone fills this literal after independent acceptance of the actual file.
APPROVED_FINAL_SHA256 = '3e9edd3b57163f8c5997e58ad524db2ea270e176f103b8c6b952fc8f529b246e'
IDENTITIES=[('350503','泉州市','丰泽区','89a6739d1a513a7c5a77717a'),('350504','泉州市','洛江区','4a34ce0e167250f122410ffc')]
CONTEXT_KEYS={'province','city','district','region_code','source_id','version','template_id','kind','mode','adapter','schema_id','schema_version','source_version','template_sha256','template_version'}
NATIVE_NAMES={'BROWSER-RESULT.json','ROOT-NATIVE-REVIEW.json',*[f'{code}-{kind}-CONTRACT.json' for code,_,_,_ in IDENTITIES for kind in ['application','evidence']]}
class PPublicationTests(unittest.TestCase):
 def setUp(self):
  self.assertIs(type(APPROVED_FINAL_SHA256),str,'Root must seal literal APPROVED_FINAL_SHA256 with a genuine accepted receipt hash; this test must fail, never skip, while None')
  self.assertRegex(APPROVED_FINAL_SHA256,r'^[a-f0-9]{64}$');self.assertEqual(own.PUBLICATION_SHA256,APPROVED_FINAL_SHA256)
  self.assertEqual(sha256((ROOT/own.PUBLICATION_RECEIPT).read_bytes()).hexdigest(),APPROVED_FINAL_SHA256)
  self.assertTrue(callable(getattr(own,'publication_files',None)))
 def closure(self):
  sources=own.source_files(ROOT);stage=own.approval_files(ROOT);publication=own.publication_files(ROOT)
  self.assertEqual(len(sources),21);self.assertEqual(len(stage),74);self.assertEqual(len(publication),81)
  names=set(sources)|set(publication);self.assertEqual(len(names),102);self.assertEqual(len(sources)+len(publication),102)
  native={own.QA_REPORT+'/'+n for n in NATIVE_NAMES};self.assertEqual(set(publication)-set(stage)-{own.PUBLICATION_RECEIPT},native)
  self.assertEqual(set(own._native_names()),native)
  return names
 def copy_closure(self,root):
  names=self.closure()
  for name in names:
   target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
  return names
 def query(self,g,kind):return {**{k:g[k] for k in ['province','city','district','source_id','version']},'kind':kind,'template_id':own.KINDS[kind][1]}
 @contextmanager
 def isolated_final(self):
  with tempfile.TemporaryDirectory(prefix='P-genuine-final-cold-') as folder:
   root=Path(folder);self.copy_closure(root);rows=[own.published_guide(code,root=root) for code,_,_,_ in IDENTITIES]
   directory=[row for row in json.loads((ROOT/'data/public-regions/directory.json').read_bytes()) if row['code'] in {'350503','350504'}];self.assertEqual({r['code'] for r in directory},{'350503','350504'})
   public=root/'data/public-regions';public.mkdir(parents=True)
   for filename,value in [('guides.json',rows),('directory.json',directory)]:
    (public/filename).write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
   (public/'manifest.json').write_text(json.dumps({'schema_version':1,'files':{n:sha256((public/n).read_bytes()).hexdigest() for n in ['guides.json','directory.json']}}),encoding='utf8')
   from public_seed import bootstrap_public_data
   state=bootstrap_public_data(root,data_dir=root/'public-db');self.assertEqual((state['guides_imported'],state['directory_imported'],state['missing_attachments']),(2,2,[]))
   store=RegionalStore(root/'public-db/regional-guides.sqlite');app=FastAPI();app.include_router(routes.router,prefix='/regional')
   with patch.dict(os.environ,{'LABOURLAWYER_DATA_DIR':str(root/'private')}),patch.object(routes,'ROOT',root),patch.object(routes,'store',return_value=store),TestClient(app) as client:
    yield root,store,client
 def test_genuine_102_closure_native6_and_raw_source_stage_final_boundaries(self):
  self.closure();receipt=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes());self.assertTrue(receipt['can_publish']);self.assertEqual(receipt['publication_approval'],'APPROVED');self.assertEqual(len(receipt['files']),78)
  for leaf in receipt['files']:
   body=(ROOT/leaf['path']).read_bytes();self.assertEqual((len(body),sha256(body).hexdigest()),(leaf['bytes'],leaf['sha256']))
  review=json.loads((ROOT/own.QA_REPORT/'ROOT-NATIVE-REVIEW.json').read_bytes());self.assertEqual(review['status'],'ROOT_P_OWN_NATIVE_BROWSER_PASS');self.assertTrue(review['actual_browser_review']);self.assertEqual(review['publication_approval'],'APPROVED');self.assertEqual(review['native_downloads'],8);self.assertEqual(review['contracts'],4)
  browser=own._native_proof(ROOT);self.assertEqual(browser['status'],'PASS');self.assertEqual(len(browser['downloads']),8);self.assertEqual(len(browser['contracts']),4)
  for code,city,district,sid in IDENTITIES:
   raw=own.parse_capture(code,root=ROOT);stage=own.staged_candidate(code,root=ROOT);final=own.published_guide(code,root=ROOT)
   self.assertFalse(raw['can_generate']);self.assertFalse(raw['published']);self.assertFalse(own.with_capabilities(raw,root=ROOT)['can_generate']);self.assertTrue(stage['can_generate']);self.assertFalse(stage['published']);self.assertTrue(final['published']);self.assertTrue(final['can_generate'])
   self.assertEqual((final['city'],final['district'],final['source_id']),(city,district,sid));self.assertEqual(final['source_version'],own.SOURCE_VERSIONS[code]);self.assertEqual(final['verification_status'],'partial');self.assertEqual(final['publication_adapter_evidence']['sha256'],APPROVED_FINAL_SHA256)
   with self.assertRaises(ValueError):own.with_publication_evidence(raw,root=ROOT)
   self.assertIsNone(final['committee_name']);self.assertIsNone(final['committee_full_name']);self.assertIsNone(final['official_version']);self.assertIsNone(final['channel']['entry_url']);self.assertEqual(final['channel']['online_status'],'auth_required')
   self.assertEqual(sum(t['can_generate'] for t in final['templates']),2);self.assertEqual(sum(t['download_status']=='metadata_only' for t in final['templates']),4)
   for t in final['templates']:self.assertIsNone(t['official_material_id'])
   for row in final['materials']:self.assertIsNone(row['official_material_id']);self.assertIsNone(row['legal_default_copies'])
 def test_genuine_cold_two_guides_four_full15_contracts_eight_Word(self):
  with self.isolated_final() as (root,store,client):
   contracts=[]
   for code,city,district,sid in IDENTITIES:
    g=store.lookup('fujian',city,district);self.assertTrue(g['published']);self.assertTrue(g['can_generate']);self.assertEqual(g['source_id'],sid);self.assertEqual(g['evidence'],public_evidence(g,root))
    for kind in ['application','evidence']:
     q=self.query(g,kind)
     with patch.object(routes,'fill_fujian_p_document',side_effect=AssertionError('Reading a final contract must not generate')):response=client.get('/regional/form-contract',params=q)
     self.assertEqual(response.status_code,200,response.text);form=response.json();contracts.append(form)
     self.assertEqual(set(form['context']),CONTEXT_KEYS);self.assertEqual(len(form['context']),15);self.assertEqual(form['context']['source_id'],sid);self.assertEqual(form['context']['source_version'],own.SOURCE_VERSIONS[code]);self.assertEqual(form['context']['adapter'],own.ADAPTER)
     native=json.loads((root/f'{own.QA_REPORT}/{code}-{kind}-CONTRACT.json').read_bytes());self.assertEqual(form,native)
     foreign=next(row[3] for row in IDENTITIES if row[3]!=sid);self.assertEqual(client.get('/regional/form-contract',params={**q,'source_id':foreign}).status_code,409)
     template=next(t for t in g['templates'] if t['id']==q['template_id']);self.assertEqual(checked_reference_adapter(g,template,kind,root=root),own.ADAPTER)
     original=own.original_bytes(code,kind,root=root);normal=json.loads((root/f'{own.QA_REPORT}/fixtures/{code}-{kind}-normal.json').read_bytes())['data'];filled=(root/f'{own.QA_REPORT}/word/{code}-{kind}-normal.docx').read_bytes()
     for data,expected in [(form['defaults'],original),(normal,filled)]:
      out=client.post('/regional/generate',json={**q,'mode':'blank','contract_id':form['contract_id'],'data':data});self.assertEqual(out.status_code,200,out.text if out.status_code!=200 else '');self.assertEqual(out.content,expected)
      for key,value in [('x-guide-source-id',sid),('x-guide-version',str(g['version'])),('x-form-contract-id',form['contract_id']),('x-document-origin','official-blank-filled'),('cache-control','no-store')]:self.assertEqual(out.headers[key],value)
      with ZipFile(BytesIO(expected)) as a,ZipFile(BytesIO(out.content)) as b:self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist());self.assertTrue(all(a.read(n)==b.read(n) for n in a.namelist()))
     download=client.get('/regional/templates/'+q['template_id'],params=q);self.assertEqual(download.status_code,200);self.assertEqual(download.content,original);self.assertEqual(download.headers['x-template-sha256'],own.KINDS[kind][2])
    for t in g['templates']:
     if t['download_status']=='metadata_only':
      self.assertFalse(t['can_generate']);self.assertEqual(client.get('/regional/form-contract',params={**self.query(g,'application'),'template_id':t['id']}).status_code,409)
   self.assertEqual(len({f['contract_id'] for f in contracts}),4);self.assertEqual(len(store.inventory()),2);self.assertEqual(sum(any(t['can_generate'] for t in row['templates']) for row in store.inventory()),2)
   self.assertEqual(list((root/'private/generated').iterdir()),[])
 def test_genuine_sealed_source_stage_native_contract_and_receipt_tamper_refused(self):
  relatives=[own.PUBLICATION_RECEIPT,own.STAGE_RECEIPT,own.WORD_MANIFEST,f'{own.QA_REPORT}/BROWSER-RESULT.json',f'{own.QA_REPORT}/ROOT-NATIVE-REVIEW.json',f'{own.QA_REPORT}/350503-application-CONTRACT.json',str(own.SOURCE_BASE/'fengze-350503'/'own-guide.json')]
  with tempfile.TemporaryDirectory(prefix='P-genuine-final-tamper-') as folder:
   root=Path(folder);self.copy_closure(root)
   for name in relatives:
    target=root/name;body=target.read_bytes();target.unlink()
    with self.subTest(missing=name),self.assertRaises((ValueError,OSError,KeyError)):own.published_guide('350503',root=root)
    target.write_bytes(body+b' TEMP_ONLY_TAMPER')
    with self.subTest(tamper=name),self.assertRaises((ValueError,OSError,KeyError)):own.published_guide('350503',root=root)
    target.write_bytes(body)
   empty=root/'empty';empty.mkdir()
   with self.assertRaises((ValueError,OSError,KeyError)):own.published_guide('350504',root=empty)
   self.assertTrue(own.published_guide('350504',root=root)['published'])
 def test_genuine_permission_cannot_survive_disabled_or_invalid_phase_pins(self):
  for value in [None,True,False,'0'*64]:
   with self.subTest(pin=value),patch.object(own,'PUBLICATION_SHA256',value),self.assertRaises(ValueError):own.published_guide('350503',root=ROOT)
  for name in ['WORD_SHA256','STAGE_SHA256']:
   with self.subTest(pin=name),patch.object(own,name,None),self.assertRaises(ValueError):own.published_guide('350504',root=ROOT)
if __name__=='__main__':unittest.main()
