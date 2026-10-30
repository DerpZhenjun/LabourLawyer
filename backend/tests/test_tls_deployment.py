"""Offline TLS deployment checks. Certificate integration cases use private runtime fixtures."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tls_runtime', ROOT / 'deploy/tls/runtime.py')

class TLSDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runtime)

    def test_unsafe_hostname_is_rejected(self):
        for hostname in ['https://example.com', '*.example.com', 'example.com/path', 'user@example.com', 'example.com\nheader', '']:
            with self.subTest(hostname=hostname), self.assertRaises(ValueError):
                self.runtime.hostname_value(hostname)
        self.assertEqual(self.runtime.hostname_value('example.com'), 'example.com')
        self.assertEqual(self.runtime.hostname_value('127.0.0.1'), '127.0.0.1')

    def test_upstream_rejects_credentials_fragments_and_paths(self):
        for url in ['file:///etc/passwd', 'http://user:secret@example.com', 'http://example.com/api', 'http://example.com?token=x', 'http://example.com#fragment', 'http://example.com:bad', 'http://example.com:0', 'http://@example.com']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.runtime.upstream_address(url)
        self.assertEqual(self.runtime.upstream_address('http://127.0.0.1:8088'), ('127.0.0.1:8088', 'http'))

    def test_configuration_disables_global_admin_and_automatic_cert_management(self):
        config = self.runtime.proxy_config('example.com', '127.0.0.1', 8443, Path('/private/server.crt'), Path('/private/server.key'), 'http://127.0.0.1:8088')
        self.assertTrue(config['admin']['disabled'])
        server = config['apps']['http']['servers']['application']
        self.assertEqual(server['listen'], ['127.0.0.1:8443'])
        self.assertTrue(server['automatic_https']['disable'])
        self.assertEqual(server['protocols'], ['h1', 'h2'])
        self.assertEqual(server['routes'][0]['match'], [{'host':['example.com']}])
        self.assertEqual(server['routes'][-1]['handle'][0]['status_code'], 421)
        proxy = server['routes'][0]['handle'][0]
        self.assertNotIn('flush_interval', proxy, 'Negative flush intervals break upstream cancellation')
        self.assertNotIn('response_buffers', proxy)

    def test_key_file_requires_private_permissions_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / 'server.key'
            key.write_text('synthetic invalid key')
            key.chmod(0o600)
            self.runtime.private_file(key, root, secret=True)
            if os.name == 'posix':
                key.chmod(0o644)
                with self.assertRaisesRegex(ValueError, 'permissions'):
                    self.runtime.private_file(key, root, secret=True)
                key.chmod(0o600)
                link = root / 'link.key'
                link.symlink_to(key)
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    self.runtime.private_file(link, root, secret=True)

    def test_key_file_cannot_escape_application_private_root(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            outside = Path(second) / 'key'
            outside.write_text('synthetic')
            with self.assertRaisesRegex(ValueError, 'private root'):
                self.runtime.private_file(outside, Path(first), secret=True)

class TLSInstallerTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'Linux portable installer')
    def test_corrupt_cached_binary_archive_is_never_extracted_or_executed(self):
        import sys
        from unittest.mock import patch
        installer_spec = importlib.util.spec_from_file_location('tls_installer', ROOT/'deploy/tls/install_caddy.py')
        installer = importlib.util.module_from_spec(installer_spec)
        installer_spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/installer.ARCHIVE).write_bytes(b'synthetic corrupted download')
            with patch.object(sys, 'argv', ['install_caddy.py', '--directory', str(root)]), self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                installer.main()
            self.assertFalse((root/('caddy-'+installer.VERSION)).exists())

@unittest.skipUnless(os.environ.get('LABOURLAWYER_TLS_TEST_CERT_DIR'), 'Private generated certificate fixtures are required')
class TLSCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runtime)
        cls.fixtures = Path(os.environ['LABOURLAWYER_TLS_TEST_CERT_DIR'])

    def test_valid_certificate_and_key_match_exact_san(self):
        result = self.runtime.certificate_check(self.fixtures/'server.crt', self.fixtures/'server.key', self.fixtures, '127.0.0.1', minimum_days=0)
        self.assertGreater(result['seconds_remaining'], 0)

    def test_hostname_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SAN'):
            self.runtime.certificate_check(self.fixtures/'server.crt', self.fixtures/'server.key', self.fixtures, 'wrong.invalid', minimum_days=0)

    def test_key_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'certificate.*key'):
            self.runtime.certificate_check(self.fixtures/'server.crt', self.fixtures/'other.key', self.fixtures, '127.0.0.1', minimum_days=0)

    def test_insufficient_lifetime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'renewal'):
            self.runtime.certificate_check(self.fixtures/'server.crt', self.fixtures/'server.key', self.fixtures, '127.0.0.1', minimum_days=30)

    def test_expired_certificate_is_rejected(self):
        from unittest.mock import patch
        with patch.object(self.runtime.time, 'time', return_value=4102444800), self.assertRaisesRegex(ValueError, 'expired'):
            self.runtime.certificate_check(self.fixtures/'server.crt', self.fixtures/'server.key', self.fixtures, '127.0.0.1', minimum_days=0)

if __name__ == '__main__':
    unittest.main()
