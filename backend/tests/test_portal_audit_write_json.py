"""Atomic portal status writes tolerate bounded Windows sharing races only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portal_audit import write_json


def windows_permission(code):
    error = PermissionError('deterministic sharing fixture')
    if code is not None:error.winerror = code
    return error


class PortalAtomicWriteTests(unittest.TestCase):
    def test_two_windows_sharing_failures_then_success_publish_complete_json(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'status.json'
            target.write_bytes(b'{"old":true}\n')
            real_replace = Path.replace
            attempts = []
            def replace(source, destination):
                attempts.append((source, destination))
                if len(attempts) <= 2:raise windows_permission([5, 32][len(attempts) - 1])
                return real_replace(source, destination)
            with patch.object(Path, 'replace', autospec=True, side_effect=replace), patch('time.sleep') as sleep:
                write_json(target, {'fresh': True})
            self.assertEqual(json.loads(target.read_bytes()), {'fresh': True})
            self.assertEqual(len(attempts), 3)
            self.assertEqual(sleep.call_args_list, [call(0.025), call(0.05)])
            self.assertFalse(target.with_suffix('.tmp').exists())

    def test_exhausted_windows_sharing_error_preserves_old_target_and_new_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'status.json'
            target.write_bytes(b'{"old":true}\n')
            with patch.object(Path, 'replace', side_effect=windows_permission(33)) as replace, patch('time.sleep') as sleep:
                with self.assertRaises(PermissionError):write_json(target, {'fresh': True})
            self.assertEqual(replace.call_count, 5)
            self.assertEqual(sleep.call_args_list, [call(0.025), call(0.05), call(0.1), call(0.2)])
            self.assertEqual(target.read_bytes(), b'{"old":true}\n')
            self.assertEqual(json.loads(target.with_suffix('.tmp').read_bytes()), {'fresh': True})

    def test_other_permission_or_io_errors_propagate_without_retry_or_sleep(self):
        for error in [windows_permission(None), windows_permission(13), OSError('disk failure')]:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / 'status.json'
                target.write_bytes(b'{"old":true}\n')
                with patch.object(Path, 'replace', side_effect=error) as replace, patch('time.sleep') as sleep:
                    with self.assertRaises(type(error)):write_json(target, {'fresh': True})
                self.assertEqual(replace.call_count, 1)
                sleep.assert_not_called()
                self.assertEqual(target.read_bytes(), b'{"old":true}\n')


if __name__ == '__main__':unittest.main()
