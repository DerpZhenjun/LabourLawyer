import importlib.util
import json
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('openclaw_bridge', ROOT/'backend/template_acquisition/openclaw_bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class OpenClawBridgeTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT/'.runtime/openclaw-tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_relative_root_still_resolves_config_from_cli_working_directory(self):
        relative = Path(os.path.relpath(self.folder, Path.cwd()))
        config, env = bridge.write_isolated_config(relative)
        for key in ('OPENCLAW_STATE_DIR', 'OPENCLAW_CONFIG_PATH', 'OPENCLAW_WORKSPACE_DIR', 'TEMP', 'TMP'):
            path = Path(env[key])
            self.assertTrue(path.is_absolute(), key)
            self.assertTrue(path.exists(), key)
            self.assertTrue(path.is_relative_to(self.folder), key)
        self.assertEqual(Path(env['OPENCLAW_CONFIG_PATH']), config)
        self.assertEqual(json.loads(config.read_text(encoding='utf8'))['agents']['defaults']['imageModel']['primary'], 'ollama/qwen3.8:27b')
        self.assertEqual(json.loads(config.read_text(encoding='utf8'))['models']['providers']['ollama']['baseUrl'], 'http://10.66.66.1:11434')

    def test_configuration_rejects_non_ubuntu_server_and_other_model(self):
        with self.assertRaises(ValueError):bridge.write_isolated_config(self.folder,base_url='http://127.0.0.1:11434')
        with self.assertRaises(ValueError):bridge.write_isolated_config(self.folder,model='qwen3.5:27b')

    def call_fake_cli(self, stdout):
        process = Mock(returncode=0)
        process.communicate.return_value = (stdout, b'')
        result = self.folder/'result.json'
        with patch.object(bridge.subprocess, 'Popen', return_value=process) as launch:
            with patch.object(bridge.shutil, 'which', return_value='openclaw'):
                bridge.describe_image(self.folder/'image.png', result, self.folder/'isolated')
            self.assertTrue(Path(launch.call_args.kwargs['cwd']).is_absolute())
        return json.loads(result.read_text(encoding='utf8'))

    def test_zero_exit_without_model_output_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError, 'no completed model output'):
            self.call_fake_cli(b'{"ok":true,"outputs":[]}')
        record = json.loads((self.folder/'result.json').read_text(encoding='utf8'))
        self.assertFalse(record['completed_output_captured'])

    def test_completed_provider_output_is_preserved(self):
        envelope = {'ok':True,'provider':'ollama','model':'qwen3.8:27b','outputs':[{'text':'{"issues":[]}'}]}
        record = self.call_fake_cli(json.dumps(envelope).encode())
        self.assertTrue(record['completed_output_captured'])
        self.assertEqual(record['result'], envelope)

    def test_different_model_is_not_reported_as_qwen27b_success(self):
        envelope = {'ok':True,'provider':'ollama','model':'qwen3.5:4b','outputs':[{'text':'OK'}]}
        with self.assertRaisesRegex(RuntimeError, 'no completed model output'):
            self.call_fake_cli(json.dumps(envelope).encode())

    def test_timeout_does_not_count_complete_stdout_as_success(self):
        from subprocess import TimeoutExpired
        process=Mock(returncode=0,pid=1234)
        valid=json.dumps({'ok':True,'provider':'ollama','model':'qwen3.8:27b','outputs':[{'text':'{"images":[]}'}]}).encode()
        process.communicate.side_effect=[TimeoutExpired('openclaw',1),(valid,b'')]
        dest=self.folder/'timeout.json'
        with patch.object(bridge.subprocess,'Popen',return_value=process):
            with patch.object(bridge.subprocess,'run'):
                with patch.object(bridge.shutil,'which',return_value='openclaw'):
                    with self.assertRaisesRegex(RuntimeError,'timed out'):
                        bridge.describe_image(self.folder/'image.png',dest,self.folder/'isolated',timeout_seconds=1)
        raw=json.loads(dest.read_text(encoding='utf8'))
        self.assertTrue(raw['timed_out'])
        self.assertTrue(raw['completed_output_captured'])


if __name__ == '__main__':
    unittest.main()
