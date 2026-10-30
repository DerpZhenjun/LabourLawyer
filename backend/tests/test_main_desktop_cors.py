"""Exercise the actual development API used by native desktop connections."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class MainDesktopCorsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='main-desktop-cors-')
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        environment = patch.dict(os.environ, {
            'LABOURLAWYER_AUTH_DB': str(root / 'auth.sqlite3'),
            'LABOURLAWYER_DATA_DIR': str(root / 'cases'),
            'LABOURLAWYER_REGIONAL_DB': str(root / 'regional.sqlite'),
            'LABOURLAWYER_DIRECTORY_DB': str(root / 'directory.sqlite'),
        })
        environment.start()
        self.addCleanup(environment.stop)
        from app import app
        # Deliberately no lifespan: these middleware checks do not bootstrap any
        # catalogue, start a worker, or connect to a model.
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_actual_main_api_accepts_ephemeral_desktop_origins_but_keeps_auth(self):
        for origin in ['http://127.0.0.1:64351', 'http://127.0.0.1:65535']:
            with self.subTest(origin=origin):
                preflight = self.client.options('/health', headers={
                    'Origin': origin, 'Access-Control-Request-Method': 'GET',
                })
                self.assertEqual(preflight.status_code, 200)
                self.assertEqual(preflight.headers.get('access-control-allow-origin'), origin)
                health = self.client.get('/health', headers={'Origin': origin})
                self.assertEqual(health.status_code, 200)
                self.assertEqual(health.headers.get('access-control-allow-origin'), origin)
                protected = self.client.get('/api/platform/cases', headers={'Origin': origin})
                self.assertEqual(protected.status_code, 401)

    def test_actual_main_api_rejects_external_lookalike_and_invalid_origins(self):
        for origin in ['https://attacker.example', 'http://127.0.0.1.attacker.example:64351',
                       'http://127.0.0.1:0', 'http://127.0.0.1:65536',
                       'https://127.0.0.1:64351', 'null']:
            with self.subTest(origin=origin):
                response = self.client.options('/health', headers={
                    'Origin': origin, 'Access-Control-Request-Method': 'GET',
                })
                self.assertEqual(response.status_code, 400)
                self.assertNotIn('access-control-allow-origin', response.headers)


if __name__ == '__main__':
    unittest.main()
