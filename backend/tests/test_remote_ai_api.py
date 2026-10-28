import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

class RemoteAIAPITests(unittest.TestCase):
    def client(self):
        from routes.ai import router
        app=FastAPI();app.include_router(router);return TestClient(app)
    def test_unconfigured_ask_is_503_without_disclosing_internal_error(self):
        with patch('routes.ai.resolve_remote',side_effect=ValueError('尚未配置 Ubuntu Ollama')):
            r=self.client().post('/api/ask',json={'question':'虚构联调'})
        self.assertEqual(r.status_code,503);self.assertIn('Ubuntu',r.json()['detail'])
    def test_stream_preserves_history_and_appends_question_once(self):
        seen=[]
        async def generate(history):
            seen.extend(history);yield '远程';yield '回答'
        with patch('routes.ai.resolve_remote'),patch('routes.ai.generate_lawyer_chat',generate):
            r=self.client().post('/api/ask',json={'question':'虚构联调','history':[{'role':'user','content':'虚构联调'}]})
        self.assertEqual(r.status_code,200);self.assertEqual(r.text,'远程回答');self.assertEqual(len(seen),1)
        self.assertTrue(r.headers['content-type'].startswith('text/plain'))
    def test_health_reports_model_metadata_without_loading_it(self):
        from llm_service.remote import RemoteConfig
        observed=[]
        def serve(request):
            observed.append((request.method,request.url.path));return httpx.Response(200,json={'models':[{'name':'qwen3.8:27b','details':{'parameter_size':'27.3B','quantization_level':'Q4_K_M'}}]})
        transport=httpx.MockTransport(serve)
        with patch('routes.ai.resolve_remote',return_value=RemoteConfig('http://192.0.2.8:11434','ollama/qwen3.8:27b','direct')),patch('routes.ai.httpx.AsyncClient',side_effect=lambda **kw:real_client(transport=transport,**kw)):
            r=self.client().get('/api/ai/status')
        self.assertTrue(r.json()['ready']);self.assertEqual(observed,[('GET','/api/tags')])

real_client=httpx.AsyncClient
if __name__=='__main__':unittest.main()
