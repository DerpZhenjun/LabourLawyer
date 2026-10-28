import os
import unittest
from unittest.mock import patch

from llm_service.QA import generate_lawyer_chat

class RemoteOllamaRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_local_ollama_environment(self):
        with patch.dict(os.environ,{'LABOURLAWYER_LLM_MODEL':'ollama/qwen3.8:27b','OLLAMA_API_BASE':'http://127.0.0.1:11434'}):
            stream=generate_lawyer_chat([{'role':'user','content':'test'}])
            with self.assertRaisesRegex(ValueError,'Ubuntu Ollama'):
                await stream.__anext__()

    async def test_rejects_different_model(self):
        with patch.dict(os.environ,{'LABOURLAWYER_LLM_MODEL':'ollama/qwen3.5:4b','OLLAMA_API_BASE':'http://10.66.66.1:11434'}):
            stream=generate_lawyer_chat([{'role':'user','content':'test'}])
            with self.assertRaisesRegex(ValueError,'Ubuntu Ollama'):
                await stream.__anext__()

if __name__=='__main__':unittest.main()
