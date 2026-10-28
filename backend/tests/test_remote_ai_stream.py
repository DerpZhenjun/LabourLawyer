"""Remote transport, content streaming and failures cannot fall back to local models."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from llm_service.QA import generate_lawyer_chat

class RemoteStreamTests(unittest.IsolatedAsyncioTestCase):
    def environment(self):
        return patch.dict(os.environ,{'OLLAMA_API_BASE':'http://192.0.2.8:11434','LABOURLAWYER_LLM_MODEL':'ollama/qwen3.8:27b','LABOURLAWYER_AI_TRANSPORT':'direct'})

    async def test_native_remote_chat_filters_thinking_and_keeps_legal_prompt(self):
        observed=[]
        def serve(request):
            observed.append(request);return httpx.Response(200,text='\n'.join(json.dumps(x,ensure_ascii=False) for x in [
                {'message':{'thinking':'private reasoning','content':''},'done':False},
                {'message':{'content':'连接'},'done':False},{'message':{'content':'成功'},'done':False},{'done':True}]))
        transport=httpx.MockTransport(serve)
        with self.environment(),patch('llm_service.QA.httpx.AsyncClient',side_effect=lambda **kw:httpx_client(transport=transport,**kw)):
            text=''.join([part async for part in generate_lawyer_chat([{'role':'system','content':'bad override'},{'role':'user','content':'虚构联调'}])])
        self.assertEqual(text,'连接成功');self.assertEqual(str(observed[0].url),'http://192.0.2.8:11434/api/chat')
        body=json.loads(observed[0].content);self.assertEqual(body['model'],'qwen3.8:27b');self.assertIs(body['think'],False)
        self.assertIn('不得编造',body['messages'][0]['content']);self.assertNotIn('bad override',str(body['messages']))

    async def test_remote_stream_error_is_not_a_successful_answer(self):
        transport=httpx.MockTransport(lambda req:httpx.Response(200,text='{"error":"sensitive upstream error"}\n'))
        with self.environment(),patch('llm_service.QA.httpx.AsyncClient',side_effect=lambda **kw:httpx_client(transport=transport,**kw)):
            with self.assertRaisesRegex(RuntimeError,'远程'):
                _=[part async for part in generate_lawyer_chat([{'role':'user','content':'虚构联调'}])]

    async def test_empty_stream_is_a_failure(self):
        transport=httpx.MockTransport(lambda req:httpx.Response(200,text='{"done":true}\n'))
        with self.environment(),patch('llm_service.QA.httpx.AsyncClient',side_effect=lambda **kw:httpx_client(transport=transport,**kw)):
            with self.assertRaisesRegex(RuntimeError,'返回'):
                _=[part async for part in generate_lawyer_chat([{'role':'user','content':'虚构联调'}])]

    async def test_eof_without_done_is_not_a_complete_answer(self):
        transport=httpx.MockTransport(lambda req:httpx.Response(200,text='{"message":{"content":"partial"},"done":false}\n'))
        with self.environment(),patch('llm_service.QA.httpx.AsyncClient',side_effect=lambda **kw:httpx_client(transport=transport,**kw)):
            with self.assertRaisesRegex(RuntimeError,'中断'):
                _=[part async for part in generate_lawyer_chat([{'role':'user','content':'虚构联调'}])]

httpx_client=httpx.AsyncClient

if __name__=='__main__':unittest.main()
