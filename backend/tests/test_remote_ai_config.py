import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from llm_service.remote import resolve_remote

class RemoteConfigurationTests(unittest.TestCase):
    def test_all_local_ollama_aliases_are_rejected_without_owned_tunnel(self):
        for address in ['http://127.0.0.2:11434','http://[::ffff:127.0.0.1]:11434','http://localhost:11434','http://localhost.:11434']:
            with self.subTest(address=address),patch.dict(os.environ,{'OLLAMA_API_BASE':address,'LABOURLAWYER_AI_TRANSPORT':'direct'}):
                with self.assertRaisesRegex(ValueError,'Ubuntu Ollama'):resolve_remote()
    def test_owned_attested_ssh_forward_is_a_remote_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'connection.json';p.write_text(json.dumps({'endpoint':'http://127.0.0.1:11435','transport':'ssh',
                'model':'ollama/qwen3.8:27b','local_port':11435,'ssh_pid':123,'verified_remote':True}),encoding='utf8')
            with patch.dict(os.environ,{'OLLAMA_API_BASE':'http://127.0.0.1:11435','LABOURLAWYER_AI_TRANSPORT':'ssh','LABOURLAWYER_AI_CONNECTION_FILE':str(p)}),patch('llm_service.remote._owned_ssh_tunnel',return_value=True):
                c=resolve_remote();self.assertEqual(c.transport,'ssh');self.assertEqual(c.model,'ollama/qwen3.8:27b')
            with patch.dict(os.environ,{'OLLAMA_API_BASE':'http://127.0.0.1:11435','LABOURLAWYER_AI_TRANSPORT':'ssh','LABOURLAWYER_AI_CONNECTION_FILE':str(p)}),patch('llm_service.remote._owned_ssh_tunnel',return_value=False):
                with self.assertRaises(ValueError):resolve_remote()

    def test_reconnected_ssh_receipt_supersedes_stale_process_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'connection.json';p.write_text(json.dumps({'endpoint':'http://127.0.0.1:11436','transport':'ssh',
                'model':'ollama/qwen3.8:27b','local_port':11436,'ssh_pid':124,'verified_remote':True}),encoding='utf8')
            with patch.dict(os.environ,{'OLLAMA_API_BASE':'http://127.0.0.1:11435','LABOURLAWYER_AI_TRANSPORT':'ssh','LABOURLAWYER_AI_CONNECTION_FILE':str(p)}),patch('llm_service.remote._owned_ssh_tunnel',return_value=True):
                self.assertEqual(resolve_remote().endpoint,'http://127.0.0.1:11436')

if __name__=='__main__':unittest.main()
