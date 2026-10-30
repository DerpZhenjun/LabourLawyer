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
    'test_jiangsu_oct30f',
    'test_jiangsu_oct30f_dispatch',
    'test_jiangsu_oct30f_publication',
    'test_jiangsu_f_seed_publication',
    'test_jiangsu_oct31g',
    'test_kunshan_g_seed_publication',
    'test_fujian_oct31h',
    'test_fujian_oct31h_dispatch',
    'test_gulou_h_seed_publication',
    'test_generated_document_storage',
    'test_regional_issue_public_urls',
    'test_service_capabilities',
    'test_linux_guide_collector',
    'test_collector_issue_events',
    'test_collector_issue_wiring',
    'test_ci_subprocess_guard',
    'test_tls_deployment.TLSDeploymentTests',
    'test_tls_deployment.TLSInstallerTests',
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
    (ROOT / 'scripts/test-kunshan-guide-wire.mjs').resolve(),
    (ROOT / 'scripts/test-gulou-guide-wire.mjs').resolve(),
}
OFFLINE_EXCLUSIONS = {
    'test_linux_guide_collector.CollectorTests.test_os_worker_lock_rejects_second_process_and_releases_on_exit':
        'Runs real child processes; execute this named Linux case separately, outside the offline guard.',
    'test_collector_issue_events.CollectorIssueEventTests.test_process_crash_before_commit_and_after_commit_replay_without_loss':
        'Runs only in scripts/ci-collector-crash.py with exact child-command and inherited child audit guards.',
    'test_collector_issue_wiring.CollectorIssueWiringTests.test_process_death_after_queue_commit_is_replayed_on_restart':
        'Runs only in scripts/ci-collector-crash.py with exact child-command and inherited child audit guards.',
}
if os.name == 'nt':
    # This Windows-only fixture invokes cmd/mklink to construct a real junction
    # in its fresh Temp root. Keep the ordinary runner shell-free; execute the
    # named fixture separately on Windows. Linux exercises its native symlink
    # branch here without any child process or exclusion.
    OFFLINE_EXCLUSIONS[
        'test_generated_document_storage.GeneratedDocumentStorageTests.test_symlink_or_junction_generated_is_rejected_without_outside_writes'
    ] = 'Windows junction construction needs its separately run, exact Temp-only fixture; no shell allowance in the offline gate.'


def make_guard(sandbox, *, python_policy=None, allow_node=True):
    """Default is Node-only; the dedicated crash runner supplies a narrow policy."""
    sandbox = Path(sandbox).resolve()
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
            database = os.fsdecode(args[0])
            if database.startswith('file:'):
                uri = urlsplit(database)
                if uri.netloc: raise RuntimeError('CI SQLite URI must be a local sandbox path')
                database = url2pathname(uri.path)
            if database != ':memory:' and not Path(database).resolve().is_relative_to(sandbox):
                raise RuntimeError('CI SQLite database must be inside its temporary sandbox')
        if event == 'subprocess.Popen':
            executable, argv, cwd, env = args
            if os.name == 'nt' and executable is None and isinstance(argv, str):
                allowed = argv in {subprocess.list2cmdline(['node', str(f)]) for f in NODE_FIXTURES}
            else:
                allowed = (executable is not None and Path(executable).stem.lower() == 'node'
                           and isinstance(argv, (list, tuple)) and len(argv) == 2
                           and Path(argv[1]).resolve() in NODE_FIXTURES)
            allowed = (allow_node and allowed) or (python_policy is not None and python_policy(executable, argv, cwd, env))
            if not allowed:
                raise RuntimeError('CI subprocess is outside the exact named offline fixtures')
        if event in {'os.system', 'os.posix_spawn', 'os.spawn', 'os.exec', 'os.fork', 'os.forkpty', 'os.startfile', 'os.startfile/2'}:
            raise RuntimeError('CI forbids shell and alternate process launch paths')
    return audit


def install_guard(sandbox, *, python_policy=None, allow_node=True):
    sys.addaudithook(make_guard(sandbox, python_policy=python_policy, allow_node=allow_node))


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
            'LABOURLAWYER_COLLECTOR_CONFIG': '',
            'LABOURLAWYER_DIGITAL_URL': '',
            'HF_HUB_OFFLINE': '1',
            'TRANSFORMERS_OFFLINE': '1',
        }))
        install_guard(sandbox)
        check_guard(sandbox)
        loaded = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
        def cases(suite):
            for case in suite:
                if isinstance(case, unittest.TestSuite):
                    yield from cases(case)
                else:
                    yield case
        selected = []; excluded = set()
        for case in cases(loaded):
            if case.id() in OFFLINE_EXCLUSIONS:
                excluded.add(case.id())
                print('Separate integration gate:', case.id(), '-', OFFLINE_EXCLUSIONS[case.id()], flush=True)
            else:
                selected.append(case)
        if excluded != set(OFFLINE_EXCLUSIONS):
            raise AssertionError('The explicitly separate integration case changed; review its offline selection')
        suite = unittest.TestSuite(selected)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
