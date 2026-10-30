"""Run exactly two model-free collector crash cases with guarded real children.

The ordinary backend gate remains Node-only. This runner permits only the three
command shapes used by these two frozen test methods. A fail-closed temporary
sitecustomize installs the network/SQLite/process audit guard in each child
before the actual fixture script is imported; child processes cannot spawn.
"""
from contextlib import ExitStack, closing
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / 'backend/tests/test_collector_issue_events.py'
WIRING = ROOT / 'backend/tests/test_collector_issue_wiring.py'
TESTS = (
    'test_collector_issue_events.CollectorIssueEventTests.test_process_crash_before_commit_and_after_commit_replay_without_loss',
    'test_collector_issue_wiring.CollectorIssueWiringTests.test_process_death_after_queue_commit_is_replayed_on_restart',
)


def load_guard():
    spec = importlib.util.spec_from_file_location('ci_backend_guard', ROOT / 'scripts/ci-backend.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_commands(sandbox):
    """Enumerate canonical commands, never parse shell/Windows command strings."""
    sandbox = Path(sandbox).resolve()
    for folder in sandbox.iterdir():
        if not folder.is_dir() or folder.is_symlink() or folder.resolve().parent != sandbox: continue
        if folder.name.startswith('tmp'):
            for phase in ('before', 'after'):
                yield [sys.executable, str(EVENTS), '--collector-crash-fixture', str(folder / (phase + '-issues.sqlite')), phase]
        if folder.name.startswith('collector-wiring-'):
            yield [sys.executable, str(WIRING), '--collector-wiring-crash-fixture', str(folder)]


def make_crash_policy(sandbox, required_environment, *, windows=None):
    sandbox = Path(sandbox).resolve()
    required_environment = dict(required_environment)
    windows = os.name == 'nt' if windows is None else windows
    startup = Path(required_environment['PYTHONPATH']) / 'sitecustomize.py'
    if (not startup.is_absolute() or startup.parent.parent != sandbox
            or startup.is_symlink() or startup.parent.is_symlink()
            or not startup.resolve().is_relative_to(sandbox)):
        raise ValueError('Child guard startup must be a regular file in the new sandbox')
    startup_sha256 = sha256(startup.read_bytes()).hexdigest()

    def startup_unchanged():
        try:
            return (not startup.is_symlink() and not startup.parent.is_symlink()
                    and startup.resolve().is_relative_to(sandbox)
                    and {p.name for p in startup.parent.iterdir()} == {'sitecustomize.py'}
                    and sha256(startup.read_bytes()).hexdigest() == startup_sha256)
        except OSError:
            return False

    def allowed(executable, argv, cwd, env):
        # Original fixtures pass neither cwd nor env. Reject ways to discard
        # the child bootstrap or redirect its temporary/database namespace.
        if cwd is not None or env is not None: return False
        if any(os.environ.get(key) != value for key, value in required_environment.items()): return False
        if not startup_unchanged(): return False
        if executable is not None and os.fsdecode(executable) != sys.executable: return False
        if isinstance(argv, str):
            return windows and argv in {subprocess.list2cmdline(command) for command in expected_commands(sandbox)}
        if executable is None or not isinstance(argv, (list, tuple)): return False
        return list(argv) in list(expected_commands(sandbox))
    return allowed


def prove_process_denials(sandbox):
    """Actual Popen attempts must fail before any fixture/code executes."""
    folder = sandbox / 'tmp-denial-probes'; folder.mkdir(exist_ok=True)
    marker = folder / 'must-not-execute.txt'
    foreign = folder / 'foreign.py'
    code = 'from pathlib import Path; Path(' + repr(str(marker)) + ').write_text("executed")'
    foreign.write_text(code, encoding='utf-8')
    base = [sys.executable, str(EVENTS), '--collector-crash-fixture']
    attempts = [
        [sys.executable, '-c', code],
        [sys.executable, '-e', code],
        [sys.executable, str(foreign)],
        [*base, str(sandbox.parent / 'before-issues.sqlite'), 'before'],
        [sys.executable, str(EVENTS), '--fake-fixture', str(folder / 'before-issues.sqlite'), 'before'],
        [*base, str(folder / 'before-issues.sqlite'), 'after'],
    ]
    for command in attempts:
        try: subprocess.run(command, check=True, capture_output=True, timeout=10)
        except RuntimeError as exc:
            if not str(exc).startswith('CI subprocess is outside'): raise
        else: raise AssertionError('A forbidden Python command reached child execution')
    if marker.exists(): raise AssertionError('Forbidden Python code executed')
    return len(attempts)


def child_entry(sandbox, receipts):
    """Called by the temporary startup module before Python imports a fixture."""
    sandbox, receipts = Path(sandbox).resolve(), Path(receipts).resolve()
    if [sys.executable, *sys.argv] not in list(expected_commands(sandbox)):
        raise RuntimeError('Child startup is outside the exact fixture commands')
    load_guard().install_guard(sandbox, allow_node=False)
    denials = prove_process_denials(sandbox)
    # Also prove the child cannot connect or open any non-sandbox SQLite file.
    for operation in (
        lambda: socket.create_connection(('127.0.0.1', 9), timeout=0.1),
        lambda: sqlite3.connect(str(sandbox.parent / 'ci-child-forbidden.sqlite')),
    ):
        try: operation()
        except RuntimeError: pass
        else: raise AssertionError('Child audit guard did not reject external access')
    with closing(sqlite3.connect(sandbox / 'child-guard.sqlite')) as db: db.execute('SELECT 1')
    receipt = {'fixture': Path(sys.argv[0]).name,
               'phase': sys.argv[-1] if Path(sys.argv[0]) == EVENTS else 'after-queue-commit',
               'process_denials': denials, 'network_denied': True, 'external_sqlite_denied': True,
               'child_processes_allowed': False}
    (receipts / (str(os.getpid()) + '.json')).write_text(json.dumps(receipt) + '\n', encoding='utf-8')


def write_child_bootstrap(sandbox):
    folder = sandbox / 'child-startup'; folder.mkdir()
    receipts = sandbox / 'child-guard-receipts'; receipts.mkdir()
    # sitecustomize errors normally let Python continue. Exit explicitly on
    # every failure so an absent/broken guard cannot silently run a fixture.
    source = (
        'import os, importlib.util\n'
        'try:\n'
        '    spec = importlib.util.spec_from_file_location("collector_crash_guard", ' + repr(str(Path(__file__).resolve())) + ')\n'
        '    module = importlib.util.module_from_spec(spec)\n'
        '    spec.loader.exec_module(module)\n'
        '    module.child_entry(' + repr(str(sandbox)) + ', ' + repr(str(receipts)) + ')\n'
        'except BaseException:\n'
        '    os._exit(78)\n'
    )
    (folder / 'sitecustomize.py').write_text(source, encoding='utf-8')
    return folder, receipts


def main():
    os.umask(0o077)
    sys.dont_write_bytecode = True
    os.chdir(ROOT)
    sys.path[:0] = [str(ROOT), str(ROOT / 'backend'), str(ROOT / 'backend/tests')]
    with tempfile.TemporaryDirectory(prefix='collector-crash-ci-') as temporary, ExitStack() as stack:
        sandbox = Path(temporary).resolve()
        bootstrap, receipts = write_child_bootstrap(sandbox)
        environment = {
            'PYTHONPATH': str(bootstrap), 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
            'TMPDIR': str(sandbox), 'TEMP': str(sandbox), 'TMP': str(sandbox),
            'LABOURLAWYER_DATA_DIR': str(sandbox / 'private-cases'),
            'LABOURLAWYER_AUTH_DB': str(sandbox / 'auth.sqlite'),
            'LABOURLAWYER_REGIONAL_DB': str(sandbox / 'regional.sqlite'),
            'LABOURLAWYER_DIRECTORY_DB': str(sandbox / 'directory.sqlite'),
            'LABOURLAWYER_AI_CONNECTION_FILE': str(sandbox / 'disabled-ai.json'),
            'LABOURLAWYER_AI_TRANSPORT': 'direct', 'OLLAMA_API_BASE': '',
            'LABOURLAWYER_COLLECTOR_CONFIG': '', 'LABOURLAWYER_DIGITAL_URL': '',
            'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        }
        stack.enter_context(patch.dict(os.environ, environment))
        stack.enter_context(patch.object(tempfile, 'tempdir', str(sandbox)))
        guard = load_guard()
        guard.install_guard(sandbox, python_policy=make_crash_policy(sandbox, environment), allow_node=False)
        denials = prove_process_denials(sandbox)
        loaded = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
        if loaded.countTestCases() != 2: raise AssertionError('Named crash suite changed')
        result = unittest.TextTestRunner(verbosity=2).run(loaded)
        proofs = [json.loads(path.read_bytes()) for path in receipts.glob('*.json')]
        expected = sorted([(EVENTS.name, 'before'), (EVENTS.name, 'after'), (WIRING.name, 'after-queue-commit')])
        observed = sorted((proof['fixture'], proof['phase']) for proof in proofs)
        if observed != expected or not all(proof['process_denials'] == 6 and proof['network_denied'] and proof['external_sqlite_denied'] and not proof['child_processes_allowed'] for proof in proofs):
            raise AssertionError('Exactly three guarded crash children must attest successful denial probes')
        print(json.dumps({'guarded_crash_children': len(proofs), 'parent_forbidden_commands_rejected': denials,
                          'network_services_models_started': False}), flush=True)
        return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': raise SystemExit(main())
