import os,unittest
from unittest.mock import patch
from llm_service.remote import resolve_remote,_owned_ubuntu_ollama
from pathlib import Path
from types import SimpleNamespace
import json

class UbuntuColocatedAITests(unittest.TestCase):
    def test_explicit_verified_ubuntu_installation_can_serve_its_local_app(self):
        with patch.dict(os.environ,{'OLLAMA_API_BASE':'http://127.0.0.1:11434','LABOURLAWYER_AI_TRANSPORT':'ubuntu-local'}),patch('llm_service.remote._owned_ubuntu_ollama',return_value=True,create=True):
            self.assertEqual(resolve_remote().transport,'ubuntu-local')
    def test_ubuntu_mode_cannot_enable_windows_or_unverified_process(self):
        with patch.dict(os.environ,{'OLLAMA_API_BASE':'http://127.0.0.1:11434','LABOURLAWYER_AI_TRANSPORT':'ubuntu-local'}),patch('llm_service.remote._owned_ubuntu_ollama',return_value=False,create=True):
            with self.assertRaises(ValueError):resolve_remote()
    def test_ubuntu_mode_refuses_any_different_endpoint(self):
        for address in ['http://localhost:11434','http://127.0.0.1:11435','http://192.168.110.81:11434']:
            with self.subTest(address=address),patch.dict(os.environ,{'OLLAMA_API_BASE':address,'LABOURLAWYER_AI_TRANSPORT':'ubuntu-local'}),patch('llm_service.remote._owned_ubuntu_ollama',return_value=True,create=True):
                with self.assertRaises(ValueError):resolve_remote()

    def test_actual_helper_rejects_windows_before_reading_configuration(self):
        with patch('llm_service.remote.sys.platform','win32'),patch.object(Path,'read_text',side_effect=AssertionError('Windows must not inspect local model')):
            self.assertFalse(_owned_ubuntu_ollama())

    def test_actual_helper_fails_closed_on_malformed_installation_receipts(self):
        for receipt in [None,[],{}, {'checks_passed':False}]:
            with self.subTest(receipt=receipt),patch('llm_service.remote.sys.platform','linux'),patch.dict(os.environ,{'LABOURLAWYER_UBUNTU_OLLAMA_ROOT':'/home/test/SJL/Ollama'}),patch.object(Path,'resolve',lambda p:p),patch.object(Path,'is_absolute',return_value=True),patch.object(Path,'stat',return_value=SimpleNamespace(st_uid=1000)),patch('llm_service.remote.os.getuid',return_value=1000,create=True),patch.object(Path,'read_text',lambda p,*a,**k:'ID="ubuntu"\nVERSION_ID="24.04"' if str(p).endswith('os-release') else json.dumps(receipt)):
                self.assertFalse(_owned_ubuntu_ollama())
