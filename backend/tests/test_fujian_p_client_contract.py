"""Actual O ASGI -> one fixed production TS replay -> actual ASGI Word."""
from pathlib import Path
from unittest.mock import patch
import json,subprocess,unittest
import test_fujian_oct31p_dispatch as d
ROOT=Path(__file__).resolve().parents[2]
class PClientTests(unittest.TestCase):
 def test_actual_two_district_four_form_strict_TS_display_example_roundtrip(self):
  case=d.PDispatchTests()
  with case.isolated() as (root,store,client):
   cases=[]
   with patch.object(d.routes,'fill_fujian_p_document',side_effect=AssertionError('Reading cannot fill')) as filler:
    for g in case.guides(store):
     r=client.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']});self.assertEqual(r.status_code,200)
     cases.append({'guide':r.json(),'forms':[case.contract(client,g,kind) for kind in d.own.KINDS]})
    process=subprocess.run(['node',str(ROOT/'backend/tests/fixtures/test-fujian-p-wire.mjs')],input=json.dumps({'cases':cases},ensure_ascii=False).encode(),capture_output=True,timeout=40)
    self.assertEqual(process.returncode,0,process.stderr.decode('utf8',errors='replace'));replay=json.loads(process.stdout)
    self.assertEqual(replay['fetch_calls'],0);self.assertEqual(filler.call_count,0)
   self.assertEqual(len(replay['examples']),4);self.assertEqual(len(set(replay['sources'])),2)
   for payload in replay['examples']:
    g=next(row['guide'] for row in cases if row['guide']['source_id']==payload['source_id'])
    r=client.post('/regional/generate',json=payload);self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '')
    self.assertEqual(r.content,d.own.candidate_fill(d.own.envelope(g['region_code'],payload['kind'],payload['data'],root=root),root=root,private_review=True))
    self.assertEqual(r.headers['x-guide-source-id'],payload['source_id']);self.assertEqual(r.headers['x-form-contract-id'],payload['contract_id'])
   self.assertEqual(list((root/'private/generated').iterdir()),[])
if __name__=='__main__':unittest.main()
