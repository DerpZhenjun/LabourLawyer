"""Explicit ownership assignment preserves bytes and never steals owned cases."""
import importlib.util
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from auth_store import AuthStore
spec = importlib.util.spec_from_file_location('claim_case', ROOT / 'scripts/claim-legacy-case.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LegacyClaimTests(unittest.TestCase):
    def test_explicit_owner_backup_and_reassignment_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); cases = root / 'cases.sqlite'; auth = root / 'auth.sqlite'
            user = AuthStore(auth).create_user('owner-a', 'fictional-password-a')
            with closing(sqlite3.connect(cases)) as db:
                db.execute('CREATE TABLE cases(id TEXT PRIMARY KEY,owner_user_id TEXT,summary TEXT)')
                db.execute("INSERT INTO cases VALUES('legacy',NULL,'preserved text')"); db.commit()
            backup = module.claim(cases, auth, 'legacy', 'owner-a')
            with closing(sqlite3.connect(backup)) as db:
                self.assertEqual(db.execute('SELECT * FROM cases').fetchone(), ('legacy', None, 'preserved text'))
            with closing(sqlite3.connect(cases)) as db:
                self.assertEqual(db.execute('SELECT * FROM cases').fetchone(), ('legacy', user.id, 'preserved text'))
            with self.assertRaises(ValueError): module.claim(cases, auth, 'legacy', 'owner-a')
            with self.assertRaises(ValueError): module.claim(cases, auth, 'absent', 'owner-a')
            self.assertEqual(len(list(root.glob('cases.sqlite.before-claim-*'))), 1)

    def test_missing_or_disabled_account_does_not_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); cases = root / 'cases.sqlite'; auth = root / 'auth.sqlite'
            store = AuthStore(auth); user = store.create_user('owner-a', 'fictional-password-a')
            with store.connection() as db: db.execute('UPDATE auth_users SET active=0 WHERE id=?', (user.id,))
            with closing(sqlite3.connect(cases)) as db:
                db.execute('CREATE TABLE cases(id TEXT PRIMARY KEY,owner_user_id TEXT)')
                db.execute("INSERT INTO cases VALUES('legacy',NULL)"); db.commit()
            for username in ['owner-a', 'missing']:
                with self.assertRaises(ValueError): module.claim(cases, auth, 'legacy', username)
            self.assertEqual(list(root.glob('cases.sqlite.before-claim-*')), [])
            with closing(sqlite3.connect(cases)) as db:
                self.assertIsNone(db.execute('SELECT owner_user_id FROM cases').fetchone()[0])
