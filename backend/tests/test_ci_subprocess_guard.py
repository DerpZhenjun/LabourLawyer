"""Exact crash-fixture process policy; no actual children/network in this suite."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location('guard_test_' + name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CrashSubprocessPolicyTests(unittest.TestCase):
    def setUp(self):
        self.guard_module = load_script('ci-backend')
        self.runner = load_script('ci-collector-crash')
        temporary = tempfile.TemporaryDirectory(prefix='ci-policy-')
        self.addCleanup(temporary.cleanup)
        self.sandbox = Path(temporary.name).resolve()
        self.events = self.sandbox / 'tmp owned fixture with spaces'; self.events.mkdir()
        self.wiring = self.sandbox / 'collector-wiring-owned with spaces'; self.wiring.mkdir()
        self.environment = {'PYTHONPATH': str(self.sandbox / 'bootstrap'), 'TMPDIR': str(self.sandbox),
                            'TEMP': str(self.sandbox), 'TMP': str(self.sandbox), 'PYTHONNOUSERSITE': '1'}
        self.bootstrap = self.sandbox / 'bootstrap/sitecustomize.py'
        self.bootstrap.parent.mkdir(); self.bootstrap.write_text('# synthetic bootstrap pin')
        self.env_patch = patch.dict(os.environ, self.environment)
        self.env_patch.start(); self.addCleanup(self.env_patch.stop)
        self.policy = self.runner.make_crash_policy(self.sandbox, self.environment, windows=False)
        self.windows_policy = self.runner.make_crash_policy(self.sandbox, self.environment, windows=True)
        self.commands = [
            [sys.executable, str(ROOT / 'backend/tests/test_collector_issue_events.py'), '--collector-crash-fixture', str(self.events / 'before-issues.sqlite'), 'before'],
            [sys.executable, str(ROOT / 'backend/tests/test_collector_issue_events.py'), '--collector-crash-fixture', str(self.events / 'after-issues.sqlite'), 'after'],
            [sys.executable, str(ROOT / 'backend/tests/test_collector_issue_wiring.py'), '--collector-wiring-crash-fixture', str(self.wiring)],
        ]

    def allowed(self, command, executable=None, cwd=None, env=None):
        return self.policy(sys.executable if executable is None else executable, command, cwd, env)

    def test_only_three_exact_calls_accept_fixed_current_python(self):
        for command in self.commands:
            with self.subTest(command=command): self.assertTrue(self.allowed(command))
        for executable in ['python', '/foreign/python', sys.executable + '.foreign']:
            with self.subTest(executable=executable): self.assertFalse(self.allowed(self.commands[0], executable))

    def test_arbitrary_code_module_foreign_file_and_extra_flags_are_denied(self):
        for command in [[sys.executable, '-c', 'raise SystemExit(79)'], [sys.executable, '-e', 'fixture'],
                        [sys.executable, '-m', 'unittest'], [sys.executable, str(self.sandbox / 'foreign.py')],
                        self.commands[0] + ['--extra'], [*self.commands[0][:2], '--fake-flag', *self.commands[0][3:]]]:
            with self.subTest(command=command): self.assertFalse(self.allowed(command))

    def test_wrong_phase_filename_outside_parent_and_missing_directory_are_denied(self):
        for target, phase in [(self.events / 'before-issues.sqlite', 'after'), (self.events / 'foreign.sqlite', 'before'),
                              (self.sandbox.parent / 'before-issues.sqlite', 'before'),
                              (self.sandbox / 'tmpmissing/before-issues.sqlite', 'before'),
                              (self.events / '../before-issues.sqlite', 'before')]:
            command = [*self.commands[0][:3], str(target), phase]
            with self.subTest(target=target, phase=phase): self.assertFalse(self.allowed(command))
        self.assertFalse(self.allowed([*self.commands[2][:3], str(self.events)]))

    def test_windows_uses_exact_canonical_commandline_without_shell_parsing(self):
        for command in self.commands:
            canonical = subprocess.list2cmdline(command)
            self.assertIn('"', canonical, 'Fixture path must exercise actual Windows quoting')
            self.assertTrue(self.windows_policy(None, canonical, None, None))
            self.assertTrue(self.windows_policy(sys.executable, canonical, None, None))
            self.assertFalse(self.windows_policy('cmd.exe', canonical, None, None))
            for suffix in [' --extra', ' & echo forbidden', '; echo forbidden', ' $(whoami)', ' `whoami`', ' "']:
                with self.subTest(suffix=suffix): self.assertFalse(self.windows_policy(None, canonical + suffix, None, None))
            self.assertFalse(self.policy(None, canonical, None, None))

    def test_foreign_cwd_environment_override_and_bootstrap_removal_are_denied(self):
        self.assertFalse(self.allowed(self.commands[0], cwd=str(self.sandbox.parent)))
        self.assertFalse(self.allowed(self.commands[0], env={**os.environ, 'PYTHONPATH': ''}))
        with patch.dict(os.environ, {'PYTHONPATH': ''}): self.assertFalse(self.allowed(self.commands[0]))
        with patch.dict(os.environ, {'TMP': str(self.sandbox.parent)}): self.assertFalse(self.allowed(self.commands[0]))

    def test_deleted_or_modified_startup_guard_is_denied_before_launch(self):
        original = self.bootstrap.read_bytes()
        self.bootstrap.unlink()
        self.assertFalse(self.allowed(self.commands[0]))
        self.bootstrap.write_bytes(original + b'\n# unexpected mutation')
        self.assertFalse(self.allowed(self.commands[0]))
        self.bootstrap.write_bytes(original)
        self.assertTrue(self.allowed(self.commands[0]))

    def test_default_offline_guard_still_denies_all_python(self):
        guard = self.guard_module.make_guard(self.sandbox)
        for command in self.commands + [[sys.executable, '-c', 'raise SystemExit(79)']]:
            with self.subTest(command=command), self.assertRaises(RuntimeError):
                guard('subprocess.Popen', (sys.executable, command, None, None))

    def test_named_runner_guard_allows_fixtures_but_keeps_network_sqlite_and_node_disabled(self):
        guard = self.guard_module.make_guard(self.sandbox, python_policy=self.policy, allow_node=False)
        for command in self.commands: guard('subprocess.Popen', (sys.executable, command, None, None))
        for command in [[sys.executable, '-c', 'pass'], [sys.executable, str(self.sandbox / 'foreign.py')]]:
            with self.subTest(command=command), self.assertRaises(RuntimeError):
                guard('subprocess.Popen', (sys.executable, command, None, None))
        for event, args in [('socket.connect', ()), ('socket.getaddrinfo', ()), ('socket.bind', ()),
                            ('sqlite3.connect', (str(self.sandbox.parent / 'foreign.sqlite'),)),
                            ('os.system', ('python -c forbidden',)), ('os.posix_spawn', ()),
                            ('os.exec', ()), ('os.startfile', ()),
                            ('subprocess.Popen', ('node', ['node', str(ROOT / 'scripts/test-document-clients.cjs')], None, None))]:
            with self.subTest(event=event), self.assertRaises(RuntimeError): guard(event, args)

    def test_child_startup_failure_exits_instead_of_running_unguarded_fixture(self):
        startup, _ = self.runner.write_child_bootstrap(self.sandbox)
        source = (startup / 'sitecustomize.py').read_text(encoding='utf-8')
        with patch.object(importlib.util, 'spec_from_file_location', side_effect=RuntimeError('guard cannot load')):
            with patch.object(os, '_exit', side_effect=SystemExit(78)) as exit_process:
                with self.assertRaises(SystemExit) as stopped:
                    exec(compile(source, str(startup / 'sitecustomize.py'), 'exec'), {})
        self.assertEqual(stopped.exception.code, 78)
        exit_process.assert_called_once_with(78)


if __name__ == '__main__': unittest.main(verbosity=2)
