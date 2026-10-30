import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class ServiceCapabilitiesTests(unittest.TestCase):
 def test_explicit_service_is_normalized_without_network_or_model(self):
  from service_capabilities import router
  app=FastAPI();app.include_router(router)
  with patch.dict(os.environ,{'LABOURLAWYER_DIGITAL_URL':' http://192.168.110.81:8089/ '}),patch('socket.create_connection',side_effect=AssertionError('No network during config read')):
   response=TestClient(app).get('/api/services')
  self.assertEqual(response.status_code,200);self.assertEqual(response.json()['digital'],{'status':'configured','url':'http://192.168.110.81:8089'})
  self.assertEqual(response.headers['cache-control'],'no-store')
 def test_absent_or_unsafe_configuration_never_leaks_value_or_guesses_localhost(self):
  from service_capabilities import capabilities
  for value in ['', 'http://public.example','https://user:private@example.com','https://example.com/path?secret=private','file:///private','http://127.1','https://bad\\host']:
   with patch.dict(os.environ,{'LABOURLAWYER_DIGITAL_URL':value}):
    data=capabilities().model_dump();self.assertIsNone(data['digital']['url']);self.assertNotEqual(data['digital']['status'],'configured');self.assertNotIn('private',str(data))
if __name__=='__main__':unittest.main()
