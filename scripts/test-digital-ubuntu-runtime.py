import importlib.util
import socket
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('digital_runtime', ROOT / 'ChatVRM/deploy/run.py')

class DigitalRuntimeTests(unittest.TestCase):
    def test_occupied_port_is_rejected_without_terminating_listener(self):
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            with self.assertRaisesRegex(RuntimeError, 'already occupied'):
                module.check_port('127.0.0.1', listener.getsockname()[1])
            self.assertEqual(listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN), 1)

    @unittest.skipIf(sys.platform == 'win32', 'Linux TCP TIME_WAIT regression')
    def test_free_port_can_restart_after_server_time_wait(self):
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with socket.socket() as listener, socket.socket() as client:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            listener.listen()
            client.connect(('127.0.0.1', port))
            accepted, _ = listener.accept()
            accepted.close()
        module.check_port('127.0.0.1', port)

    def test_api_endpoint_requires_explicit_trusted_http_origin(self):
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.api_origin('http://192.0.2.10:8088'), 'http://192.0.2.10:8088')
        for value in ['https://user:password@example.com', 'file:///etc/passwd', 'http://example.com/api', 'http://example.com?key=secret', 'http://@example.com', 'http://example.com:0', 'http://example.com:99999', 'http://example.com:bad', ' http://example.com', 'http://example.com\r\n', 'http://example.com?', 'http://example.com#']:
            with self.subTest(origin=value), self.assertRaises(ValueError):
                module.api_origin(value)

    def test_source_pack_includes_external_contract_and_excludes_dependencies(self):
        import subprocess, tarfile, json
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'digital.tar.gz'
            subprocess.run([sys.executable, str(ROOT / 'ChatVRM/deploy/prepare.py'), '--output', str(target)], check=True)
            second = Path(tmp) / 'second.tar.gz'
            subprocess.run([sys.executable, str(ROOT / 'ChatVRM/deploy/prepare.py'), '--output', str(second)], check=True)
            self.assertEqual(target.read_bytes(), second.read_bytes(), 'Identical source must produce identical package bytes')
            with tarfile.open(target) as archive:
                names = archive.getnames()
                self.assertIn('ChatVRM/src/pages/api/chat.ts', names)
                self.assertIn('packages/client-contracts/generated/index.cjs', names)
                self.assertFalse(any('/node_modules/' in name or '/.next/' in name or name.startswith('.runtime/') for name in names))
                manifest = json.load(archive.extractfile('DIGITAL-SOURCE-MANIFEST.json'))
                self.assertEqual(set(manifest['files']), set(names) - {'DIGITAL-SOURCE-MANIFEST.json'})

if __name__ == '__main__':
    unittest.main()

