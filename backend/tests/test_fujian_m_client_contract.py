"""Actual M ASGI -> one named production TS replay -> ASGI generation."""
from pathlib import Path
from unittest.mock import patch
import json,subprocess,unittest
import test_fujian_oct31m_dispatch as d
ROOT=Path(__file__).resolve().parents[2]
class MClientTests(unittest.TestCase):
 def test_actual_two_source_four_form_TS_display_examples_and_generation(self):
  case=d.MDispatchTests()
  with case.isolated() as (root,store,client):
   cases=[]
   with patch.object(d.routes,'fill_putian_document',side_effect=AssertionError('Read-only phase never generates')) as filler:
    for g in case.guides(store):
     lookup=client.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']});self.assertEqual(lookup.status_code,200)
     forms=[]
     for kind in ['application','evidence']:
      r=client.get('/regional/form-contract',params=case.query(g,kind));self.assertEqual(r.status_code,200,r.text);forms.append(r.json())
     cases.append({'guide':lookup.json(),'forms':forms})
    r=subprocess.run(['node',str(ROOT/'backend/tests/fixtures/test-putian-m-wire.mjs')],input=json.dumps({'cases':cases},ensure_ascii=False).encode(),capture_output=True,check=True,timeout=40)
    replay=json.loads(r.stdout);self.assertEqual(replay['fetch_calls'],0);self.assertEqual(filler.call_count,0)
   self.assertEqual(len(replay['examples']),4);self.assertEqual(len(set(replay['sources'])),2)
   for payload in replay['examples']:
    self.assertIn('虚构',json.dumps(payload['data'],ensure_ascii=False))
    g=next(x['guide'] for x in cases if x['guide']['source_id']==payload['source_id'])
    r=client.post('/regional/generate',json=payload);self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '')
    self.assertEqual(r.content,d.own.candidate_fill(d.own.envelope(g['region_code'],payload['kind'],payload['data'],root=root),root=root))
    self.assertEqual(r.headers['x-guide-source-id'],payload['source_id']);self.assertEqual(r.headers['x-form-contract-id'],payload['contract_id'])
   self.assertEqual(list((root/'private/generated').iterdir()),[])
if __name__=='__main__':unittest.main()
