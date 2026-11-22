from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from package_candidate import FRONTEND_BUILD_FLAGS, FRONTEND_OVERLAYS, archive, digest, frontend, json_bytes


class CandidatePackagingTests(unittest.TestCase):
    def test_rejects_frontend_built_outside_pilot_mode(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            lock = b'frozen lock'
            receipt = {
                'source_base_commit': 'base', 'source_revision': 'candidate',
                'source_files': dict.fromkeys(FRONTEND_OVERLAYS, 'sha256'),
                'build_flags': {**FRONTEND_BUILD_FLAGS, 'VITE_LABOURLAWYER_PILOT': '0'},
                'frontend_lock_sha256': digest(lock), 'node_version': 'node', 'npm_version': 'npm',
                'typecheck': 'passed', 'vite_build': 'passed',
            }
            data = json_bytes(receipt)
            manifest = root / 'receipt.json'
            manifest.write_bytes(data)
            with patch('package_candidate.git_bytes', return_value=lock):
                with self.assertRaisesRegex(ValueError, 'build settings differ'):
                    frontend(root, manifest, digest(data), 'base', 'candidate')

    def test_archive_keeps_concurrently_created_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'pilot.tar.gz'

            def another_writer_wins(sibling, destination):
                destination.write_bytes(b'other candidate')
                destination.hardlink_to(sibling)

            with patch('package_candidate.link', side_effect=another_writer_wins):
                with self.assertRaises(FileExistsError):
                    archive(output, {'example.txt': b'ours'})
            self.assertEqual(output.read_bytes(), b'other candidate')
            self.assertEqual(list(root.iterdir()), [output])
