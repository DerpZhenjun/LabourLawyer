import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from routes import ai
from starlette.requests import ClientDisconnect

class DisconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_before_response_start_cannot_reserve_model_forever(self):
        with patch.object(ai,'resolve_remote'):
            response=await ai.ask(ai.QuestionRequest(question='虚构连接检查'))
        async def send(message):raise OSError('Disconnected before headers')
        async def receive():return {'type':'http.disconnect'}
        try:
            with self.assertRaises(ClientDisconnect):
                await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
            self.assertTrue(ai._slot.acquire(False),'Disconnect leaked the model generation slot')
        finally:
            # Restore test-global state under both the failing and fixed version.
            try:ai._slot.release()
            except (ValueError,RuntimeError):pass

    async def test_disconnect_after_chunk_closes_upstream_and_releases_slot(self):
        closed=[]
        async def generate(history):
            try:yield 'first';yield 'second'
            finally:closed.append(True)
        self.enterContext(patch.object(ai,'resolve_remote'))
        self.enterContext(patch.object(ai,'generate_lawyer_chat',generate))
        response=await ai.ask(ai.QuestionRequest(question='虚构连接检查'))
        async def send(message):
            if message['type']=='http.response.body':raise OSError('Disconnected after chunk')
        async def receive():return {'type':'http.disconnect'}
        try:
            with self.assertRaises(ClientDisconnect):
                await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
            self.assertEqual(closed,[True]);self.assertTrue(ai._slot.acquire(False))
        finally:
            try:await response.body_iterator.aclose()
            except RuntimeError:pass
            try:ai._slot.release()
            except (ValueError,RuntimeError):pass
