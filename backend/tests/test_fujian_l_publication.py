"""Actual Pingtan native proof required before publication; no real data."""
from copy import deepcopy
from hashlib import sha256
import json,unittest
import test_fujian_oct31l_dispatch as d
ROOT=d.ROOT;own=d.own
FINAL='8e07c7f4bf1de2060a8af9515c3158ae97bb8fea0d4b69f382cd4b1fd723652a'
class LPublicationTests(unittest.TestCase):
 def test_exact_final_native_scope_four_files_two_contracts_and_partial_channel(self):
  self.assertEqual(own.PUBLICATION_SHA256,FINAL)
  receipt=json.loads((ROOT/own.PUBLICATION_RECEIPT).read_bytes())
  self.assertEqual(sha256((ROOT/own.PUBLICATION_RECEIPT).read_bytes()).hexdigest(),FINAL)
  self.assertEqual(len(receipt['files']),44);self.assertTrue(receipt['native_confirmation_download_own_forms']);self.assertFalse(receipt['database_or_seed_published_by_this_receipt'])
  guide=own._published('350128',ROOT)
  self.assertTrue(guide['published']);self.assertTrue(guide['can_generate']);self.assertEqual(guide['verification_status'],'partial')
  self.assertEqual(guide['city'],guide['district']);self.assertEqual(guide['district'],'平潭综合实验区')
  self.assertIsNone(guide['official_version']);self.assertIsNone(guide['committee_full_name']);self.assertEqual(guide['channel']['online_status'],'unverified');self.assertIsNone(guide['channel']['entry_url'])
  self.assertEqual(sum(t['can_generate'] for t in guide['templates']),2);self.assertEqual(sum(t['download_status']=='metadata_only' for t in guide['templates']),4)
 def test_actual_published_ASGI_two_forms_and_missing_native_proof_refused(self):
  case=d.LDispatchTests()
  with case.isolated('published') as (root,store,client):
   g=case.guide(store);self.assertTrue(g['published'])
   for kind in ['application','evidence']:
    q=case.query(g,kind);r=client.get('/regional/form-contract',params=q);self.assertEqual(r.status_code,200,r.text);c=r.json()
    data=own.example_data('350128',kind,root=root)
    r=client.post('/regional/generate',json={**q,'mode':'blank','contract_id':c['contract_id'],'data':data})
    self.assertEqual(r.status_code,200);self.assertEqual(r.content,own.candidate_fill(own.envelope('350128',kind,data,root=root),root=root))
   for path in [own.PUBLICATION_RECEIPT,own.WORD_MANIFEST,own.STAGE_RECEIPT,own.QA_REPORT+'/contracts/350128-application.json',own.QA_REPORT+'/NATIVE-CANDIDATE-QA.json']:
    p=root/path;raw=p.read_bytes();p.write_bytes(raw+b' ')
    with self.subTest(path=path):
     with self.assertRaises(ValueError):own._published('350128',root)
     self.assertEqual(client.get('/regional/form-contract',params=case.query(g,'application')).status_code,409)
    p.write_bytes(raw)
 def test_equal_bytes_never_authorize_K_or_wrong_material(self):
  from regional_fujian_oct31k import _published as Kguide
  ownGuide=own._published('350128',ROOT);other=Kguide('350111',ROOT)
  template=next(t for t in ownGuide['templates'] if t['can_generate'] and t['document_types']==['application'])
  self.assertEqual(template['sha256'],next(t for t in other['templates'] if t['document_types']==['application'])['sha256'])
  for key,value in [('source_id',other['source_id']),('city','福州市'),('district','晋安区'),('service_code',other['service_code']),('source_version',other['source_version'])]:
   changed=deepcopy(ownGuide);changed[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):own.with_capabilities(changed,root=ROOT)
  changed=deepcopy(template);changed['material_id']='743F21F90A88857531C1B7321E35AD5B'
  with self.assertRaises(ValueError):own.checked_adapter(ownGuide,changed,'application',root=ROOT)
if __name__=='__main__':unittest.main()
