"""Own Pingtan ASGI -> shared TS -> ASGI, independent temporary data."""
from pathlib import Path
from unittest.mock import patch
import json,subprocess,unittest
import test_fujian_oct31l_dispatch as d
ROOT=Path(__file__).resolve().parents[2]
class LClientTests(unittest.TestCase):
 def test_actual_Typescript_defaults_context_cancel_and_two_generation_requests(self):
  case=d.LDispatchTests()
  with case.isolated() as (root,store,client):
   g=case.guide(store);forms=[]
   with patch.object(d.routes,'fill_pingtan_document',side_effect=AssertionError('Reads do not generate')) as filler:
    lookup=client.get('/regional/lookup',params={k:g[k] for k in ['province','city','district']})
    self.assertEqual(lookup.status_code,200)
    for kind in ['application','evidence']:
     response=client.get('/regional/form-contract',params=case.query(g,kind));self.assertEqual(response.status_code,200);forms.append(response.json())
    wire={'guide':lookup.json(),'forms':forms}
    result=subprocess.run(['node',str(ROOT/'backend/tests/fixtures/test-pingtan-l-wire.mjs')],input=json.dumps(wire,ensure_ascii=False).encode(),capture_output=True,check=True,timeout=40)
    replay=json.loads(result.stdout);self.assertEqual(replay['network'],0);self.assertEqual(replay['cancel_posts'],0);self.assertEqual(filler.call_count,0)
   self.assertEqual(len(replay['examples']),2)
   for payload in replay['examples']:
    self.assertIn('虚构',json.dumps(payload['data'],ensure_ascii=False))
    response=client.post('/regional/generate',json=payload);self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
    self.assertEqual(response.content,d.own.candidate_fill(d.own.envelope('350128',payload['kind'],payload['data'],root=root),root=root))
    self.assertEqual(response.headers['x-form-contract-id'],payload['contract_id'])
   self.assertEqual(list((root/'private/generated').iterdir()),[])
if __name__=='__main__':unittest.main()
