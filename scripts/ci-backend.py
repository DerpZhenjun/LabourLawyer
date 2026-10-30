"""Run an explicit offline backend gate; never discover machine/browser tests.

Use Python 3.11 with .github/workflows/requirements-ci.txt and installed client
dependencies. The audit hook applies before test imports: accidental Python
network connections, non-temporary SQLite files and unlisted subprocesses fail.
"""
from contextlib import ExitStack
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from urllib.request import url2pathname

ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    'test_stable_api_contracts',
    'test_remote_ai_config',
    'test_ubuntu_colocated_ai',
    'test_remote_ai_api',
    'test_remote_ai_stream',
    'test_remote_ai_disconnect',
    'test_template_only_generation',
    'test_document_client_contract',
    'test_document_field_regressions',
    'test_unified_regional_validation',
    'test_zhejiang_chunan_oct30',
    'test_chunan_oct30_dispatch',
    'test_chunan_publication_evidence',
    'test_chunan_seed_publication',
    'test_platform_auth',
    'test_legacy_case_claim',
    'test_openclaw_report_counts',
    'test_regional_public_receipts',
    'test_portal_audit_write_json',
    'test_deployment',
)
NODE_FIXTURES = {
    (ROOT / 'scripts/test-document-clients.cjs').resolve(),
    (ROOT / 'scripts/export_document_examples.mjs').resolve(),
}


def install_guard(sandbox):
    # Windows implements the stdlib's socketpair using loopback sockets. Only
    # that exact stdlib frame may connect/bind, so asyncio can create its wakeup
    # pair without allowing application connections (including localhost).
    socketpair_code = getattr(getattr(socket, '_fallback_socketpair', None), '__code__', None)

    def inside_socketpair():
        frame = sys._getframe(1)
        while frame is not None:
            if frame.f_code is socketpair_code:
                return True
            frame = frame.f_back
        return False

    def audit(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.bind'}:
            if not inside_socketpair():
                raise RuntimeError('CI forbids real network connections and services')
        if event == 'sqlite3.connect':
            database = os.fspath(args[0])
            if database.startswith('file:'):
                uri = urlsplit(database)
                if uri.netloc: raise RuntimeError('CI SQLite URI must be a local sandbox path')
                database = url2pathname(uri.path)
            if database != ':memory:' and not Path(database).resolve().is_relative_to(sandbox):
                raise RuntimeError('CI SQLite database must be inside its temporary sandbox')
        if event == 'subprocess.Popen':
            executable, argv, *_ = args
            if os.name == 'nt' and executable is None and isinstance(argv, str):
                allowed = argv in {subprocess.list2cmdline(['node', str(f)]) for f in NODE_FIXTURES}
            else:
                allowed = (executable is not None and Path(executable).stem.lower() == 'node'
                           and isinstance(argv, (list, tuple)) and len(argv) == 2
                           and Path(argv[1]).resolve() in NODE_FIXTURES)
            if not allowed:
                raise RuntimeError('CI subprocess is outside the two offline Node fixtures')
    sys.addaudithook(audit)


def check_guard(sandbox):
    """Prove rejected operations fail before opening a socket or database."""
    for operation in (
        lambda: socket.create_connection(('127.0.0.1', 9)),
        lambda: sqlite3.connect(str(ROOT / 'backend/data/ci-forbidden.sqlite')),
        lambda: sqlite3.connect((ROOT / 'backend/data/ci-forbidden.sqlite').as_uri() + '?mode=ro', uri=True),
        lambda: subprocess.run([sys.executable, '-c', 'raise SystemExit(99)'], check=True),
    ):
        try:
            operation()
        except RuntimeError:
            pass
        else:
            raise AssertionError('CI isolation guard did not reject a forbidden operation')
    with sqlite3.connect(str(sandbox / 'guard.sqlite')) as connection:
        connection.execute('SELECT 1')


def main():
    os.chdir(ROOT)
    sys.path[:0] = [str(ROOT), str(ROOT / 'backend'), str(ROOT / 'backend/tests')]
    with tempfile.TemporaryDirectory(prefix='labourlawyer-ci-') as folder, ExitStack() as stack:
        sandbox = Path(folder).resolve()
        stack.enter_context(patch.object(tempfile, 'tempdir', str(sandbox)))
        stack.enter_context(patch.dict(os.environ, {
            'LABOURLAWYER_DATA_DIR': str(sandbox / 'private-cases'),
            'LABOURLAWYER_AUTH_DB': str(sandbox / 'auth.sqlite'),
            'LABOURLAWYER_REGIONAL_DB': str(sandbox / 'regional.sqlite'),
            'LABOURLAWYER_DIRECTORY_DB': str(sandbox / 'directory.sqlite'),
            'LABOURLAWYER_AI_CONNECTION_FILE': str(sandbox / 'no-remote-connection.json'),
            'OLLAMA_API_BASE': '',
            'LABOURLAWYER_AI_TRANSPORT': 'direct',
            'HF_HUB_OFFLINE': '1',
            'TRANSFORMERS_OFFLINE': '1',
        }))
        install_guard(sandbox)
        check_guard(sandbox)
        suite = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
