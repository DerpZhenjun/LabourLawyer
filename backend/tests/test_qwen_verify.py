import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('remote_qwen',ROOT/'tools/qwen_verify.py')
qwen=importlib.util.module_from_spec(spec);spec.loader.exec_module(qwen)

class RemoteQwenTests(unittest.TestCase):
    def test_network_request_is_bounded_and_uses_ubuntu(self):
        response=Mock(returncode=0,stdout=b'{"data":[]}',stderr=b'')
        with patch.object(qwen.subprocess,'run',return_value=response) as run:
            qwen.request('/v1/models',timeout=30)
        command=run.call_args.args[0]
        self.assertIn('http://10.66.66.1:11434/v1/models',command)
        self.assertEqual(command[command.index('--max-time')+1],'30')
        self.assertEqual(run.call_args.kwargs['timeout'],35)
        for invalid in (0,601):
            with self.assertRaises(ValueError):qwen.request('/v1/models',timeout=invalid)

    def test_no_local_fallback_and_no_wrong_model_acceptance(self):
        with patch.object(qwen,'request',return_value={'data':[{'id':'qwen3.5:27b'}]}) as request:
            with self.assertRaisesRegex(RuntimeError,'does not list'):qwen.verify('real context')
        self.assertEqual(request.call_count,1)
        with patch.object(qwen,'request',side_effect=[{'data':[{'id':qwen.MODEL}]},{'model':'qwen3.5:27b'}]):
            with self.assertRaisesRegex(RuntimeError,'Unexpected response model'):qwen.verify('real context')

    def test_openai_request_preserves_context_and_disables_reasoning(self):
        answer={'model':qwen.MODEL,'choices':[{'message':{'content':'Reviewed'}}]}
        with patch.object(qwen,'request',side_effect=[{'data':[{'id':qwen.MODEL}]},answer]) as request:
            result=qwen.verify('actual diff and test results',timeout=600)
        payload=request.call_args.args[1]
        self.assertEqual(payload['messages'][1]['content'][0]['text'],'actual diff and test results')
        self.assertEqual(payload['reasoning_effort'],'none')
        self.assertEqual(request.call_args.kwargs['timeout'],600)
        self.assertEqual(result['base_url'],qwen.BASE_URL)

if __name__=='__main__':unittest.main()
