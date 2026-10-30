"""Deployment must preserve API routing and exclude every private source tree."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class DeploymentRoutingTests(unittest.TestCase):
    def test_desktop_ephemeral_loopback_cors_keeps_api_authentication_and_rejects_external_origins(self):
        from deployment_app import configure_desktop_cors
        from auth_dependencies import current_user
        from fastapi import Depends
        from fastapi.middleware.cors import CORSMiddleware
        app = FastAPI()
        app.add_middleware(CORSMiddleware, allow_origins=['http://192.168.110.81:8088', 'capacitor://localhost', 'http://localhost'], allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['*'])
        @app.get('/api/platform/cases')
        def cases(user=Depends(current_user)): return {'items': []}
        configure_desktop_cors(app)
        client = TestClient(app)
        for origin in ['http://127.0.0.1:45678', 'http://127.0.0.1:65535', 'capacitor://localhost', 'http://localhost']:
            response = client.options('/api/platform/cases', headers={'Origin': origin, 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization,content-type'})
            self.assertEqual(response.status_code, 200, origin)
            self.assertEqual(response.headers.get('access-control-allow-origin'), origin)
            self.assertEqual(client.get('/api/platform/cases', headers={'Origin': origin}).status_code, 401)
        for origin in ['https://attacker.example', 'http://127.0.0.1.attacker.example:45678', 'http://127.0.0.1:99999', 'http://127.0.0.1:0', 'https://127.0.0.1:45678']:
            response = client.options('/api/platform/cases', headers={'Origin': origin, 'Access-Control-Request-Method': 'GET'})
            self.assertEqual(response.status_code, 400, origin)
            self.assertNotIn('access-control-allow-origin', response.headers)

    def test_unconfigured_collection_cannot_write_release_or_start_a_process(self):
        from deployment_app import defer_collection_routes
        from auth_dependencies import require_admin
        app = FastAPI(); called = []
        @app.post('/api/portal-reports/openclaw-tasks')
        def start(): called.append(True); return {'started': True}
        defer_collection_routes(app)
        client = TestClient(app)
        self.assertEqual(client.post('/api/portal-reports/openclaw-tasks', json={}).status_code, 401)
        app.dependency_overrides[require_admin] = lambda: object()
        self.assertEqual(client.post('/api/portal-reports/openclaw-tasks', json={}).status_code, 503)
        self.assertEqual(called, [])

    def test_spa_navigation_assets_and_api_boundaries(self):
        from deployment_app import attach_frontend
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'assets').mkdir()
            (root / 'index.html').write_text('<main>public deployment</main>', encoding='utf8')
            (root / 'assets/app.js').write_text('window.ready=true', encoding='utf8')
            (root / '.env').write_text('PRIVATE_SECRET', encoding='utf8')
            app = FastAPI()
            @app.get('/')
            def old_root(): return {'old': True}
            @app.get('/health')
            def health(): return {'status': 'ok'}
            @app.get('/api/example')
            def example(): return {'kept': True}
            attach_frontend(app, root)
            with TestClient(app) as client:
                self.assertIn('public deployment', client.get('/').text)
                self.assertEqual(client.get('/province/zhejiang', headers={'Accept': 'text/html'}).status_code, 200)
                self.assertEqual(client.get('/assets/app.js').text, 'window.ready=true')
                self.assertEqual(client.get('/health').json(), {'status': 'ok'})
                self.assertEqual(client.get('/api/example').json(), {'kept': True})
                self.assertEqual(client.post('/api/missing', json={}).status_code, 404)
                self.assertEqual(client.post('/api/example', json={}).status_code, 405)
                for path in ['/api/missing', '/api', '/assets/missing.js', '/.env', '/%2e%2e/private.txt']:
                    response = client.get(path, headers={'Accept': 'text/html'})
                    self.assertEqual(response.status_code, 404, path)
                    self.assertNotIn('public deployment', response.text)

    def test_symlinked_static_files_cannot_escape_web_root(self):
        from deployment_app import attach_frontend
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); web = root / 'web'; web.mkdir()
            (web / 'index.html').write_text('public', encoding='utf8')
            (root / 'secret.txt').write_text('PRIVATE_SECRET', encoding='utf8')
            try: (web / 'secret.txt').symlink_to(root / 'secret.txt')
            except OSError: self.skipTest('filesystem does not permit symlinks')
            app = FastAPI(); attach_frontend(app, web)
            self.assertEqual(TestClient(app).get('/secret.txt').status_code, 404)

    def test_public_seed_override_stays_outside_readonly_release_and_preserves_existing_data(self):
        from public_seed import bootstrap_public_data
        from test_public_seed import PublicSeedTests
        with tempfile.TemporaryDirectory() as folder:
            release = Path(folder) / 'release'; release.mkdir()
            data = Path(folder) / 'persistent'; PublicSeedTests().bundle(release)
            result = bootstrap_public_data(release, data_dir=data)
            self.assertEqual(result['guides_imported'], 1)
            before = {p.name: p.read_bytes() for p in data.glob('*.sqlite')}
            self.assertEqual(bootstrap_public_data(release, data_dir=data)['guides_imported'], 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in data.glob('*.sqlite')})
            self.assertFalse((release / 'backend/data').exists())


class DeploymentBundleTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location('deployment_bundle', ROOT / 'scripts/build-deployment-bundle.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def fixture(self, folder):
        root = Path(folder); allowed = 'templates/_docx/official.docx'
        files = {
            'backend/app.py': '# source', 'llm_service/QA.py': '# source',
            'deploy/run.sh': '# launch', allowed: 'OFFICIAL_TEMPLATE',
            'frontend/dist/index.html': '<main>public</main>',
            'backend/data/private.db': 'PRIVATE_CASE', 'backend/uploads/private.docx': 'PRIVATE_UPLOAD',
            'backend/data/secret.py': 'PRIVATE_CODE', 'backend/.env': 'PRIVATE_CREDENTIAL',
            'backend/personal_secrets.py': 'PRIVATE_UNTRACKED_CODE',
            '.runtime/session.json': 'PRIVATE_SESSION', 'llm_service/model.gguf': 'PRIVATE_MODEL',
            'reports/private-case.json': 'PRIVATE_REPORT', 'templates/_docx/unapproved.docx': 'PRIVATE_TEMPLATE',
            'frontend/dist/.env': 'PRIVATE_FRONTEND_ENV',
        }
        for name, body in files.items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body, encoding='utf8')
        body = (root / allowed).read_bytes()
        policy = root / 'deploy/public-files.json'
        policy.write_text(json.dumps({'schema_version': 1, 'files': [{'path': allowed, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}]}), encoding='utf8')
        (root / 'deploy/source-files.json').write_text(json.dumps({'schema_version': 1, 'files': ['backend/app.py', 'llm_service/QA.py', 'deploy/run.sh', 'deploy/public-files.json', 'deploy/source-files.json']}), encoding='utf8')
        receipt = {'status': 'passed', 'sourceSha256': 'a' * 64, 'artifacts': [{'path': 'frontend/dist/index.html', 'bytes': len(files['frontend/dist/index.html'].encode()), 'sha256': hashlib.sha256(files['frontend/dist/index.html'].encode()).hexdigest()}]}
        return root, policy, receipt

    def test_actual_archive_has_exact_manifest_and_omits_private_trees(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as folder:
            root, policy, receipt = self.fixture(folder)
            with patch.object(module, 'verify_build', return_value=receipt):
                output = module.build_bundle(root, root / 'output.tar.gz', policy, root / 'receipt.json')
            with tarfile.open(output) as archive:
                names = set(archive.getnames())
                self.assertEqual(names, {'backend/app.py', 'llm_service/QA.py', 'deploy/run.sh', 'deploy/public-files.json', 'deploy/source-files.json', 'templates/_docx/official.docx', 'frontend/dist/index.html', 'DEPLOYMENT-MANIFEST.json'})
                manifest = json.load(archive.extractfile('DEPLOYMENT-MANIFEST.json'))
                for row in manifest['files']:
                    body = archive.extractfile(row['path']).read()
                    self.assertEqual((len(body), hashlib.sha256(body).hexdigest()), (row['bytes'], row['sha256']))
                    self.assertNotIn(b'PRIVATE_', body)

    def test_tampered_public_sources_and_forbidden_policy_paths_are_refused_before_output(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as folder:
            root, policy, receipt = self.fixture(folder)
            (root / 'templates/_docx/official.docx').write_text('tampered', encoding='utf8')
            with patch.object(module, 'verify_build', return_value=receipt), self.assertRaises(ValueError):
                module.build_bundle(root, root / 'output.tar.gz', policy, root / 'receipt.json')
            self.assertFalse((root / 'output.tar.gz').exists())
            data = json.loads(policy.read_text()); data['files'][0]['path'] = 'backend/data/private.db'
            policy.write_text(json.dumps(data))
            with patch.object(module, 'verify_build', return_value=receipt), self.assertRaises(ValueError):
                module.build_bundle(root, root / 'output.tar.gz', policy, root / 'receipt.json')

    def test_receipt_cannot_bless_hidden_frontend_files_or_stale_bytes(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as folder:
            root, policy, receipt = self.fixture(folder)
            for record in [{'path': 'frontend/dist/.env'}, {**receipt['artifacts'][0], 'sha256': '0' * 64}]:
                with patch.object(module, 'verify_build', return_value={**receipt, 'artifacts': [record]}), self.assertRaises(ValueError):
                    module.build_bundle(root, root / 'output.tar.gz', policy, root / 'receipt.json')

    def test_public_json_policy_is_portable_between_windows_and_linux_line_endings(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as folder:
            root, policy, receipt = self.fixture(folder)
            name = 'config/public.json'; target = root / name; target.parent.mkdir()
            target.write_bytes(b'{"public":true}\r\n')
            canonical = b'{"public":true}\n'
            data = json.loads(policy.read_text()); data['files'].append({'path': name, 'bytes': len(canonical), 'sha256': hashlib.sha256(canonical).hexdigest(), 'newline': 'lf'})
            policy.write_text(json.dumps(data))
            with patch.object(module, 'verify_build', return_value=receipt):
                output = module.build_bundle(root, root / 'output.tar.gz', policy, root / 'receipt.json')
            with tarfile.open(output) as archive:
                self.assertEqual(archive.extractfile(name).read(), canonical)
            self.assertEqual(target.read_bytes(), b'{"public":true}\r\n')


if __name__ == '__main__': unittest.main()
