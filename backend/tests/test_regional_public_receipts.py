"""Public collection APIs expose delivery facts without private runtime receipts."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regional_guides import RegionalStore
from routes import regional_guides as routes


class PublicReceiptPrivacyTests(unittest.TestCase):
    def test_events_and_report_hide_private_receipt_but_keep_service_counts_and_raw_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = RegionalStore(root / 'public.sqlite')
            store.record_event({'id': 'public-event', 'type': 'AUTH_REQUIRED'})
            receipt = {'kind': 'openclaw_service_readback', 'status': 'ACKNOWLEDGED_OPENCLAW',
                       'service_acknowledged': True, 'ai_reviewed': False,
                       'content_sha256': 'a' * 64, 'evidence_sha256': 'b' * 64,
                       'workspace': 'C:/private/operator/DO_NOT_LEAK', 'evidence_file': 'C:/private/DO_NOT_LEAK.json',
                       'token': 'DO_NOT_LEAK_CREDENTIAL', 'accepted_event_ids': ['public-event'],
                       'profile': 'DO_NOT_LEAK_OPERATOR_PROFILE', 'nested': {'password': 'DO_NOT_LEAK'}}
            with store.connection() as db:
                db.execute('UPDATE collection_outbox SET delivery_status=?,receipt=?', ('ACKNOWLEDGED_OPENCLAW', json.dumps(receipt)))
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.dict(os.environ, {'LABOURLAWYER_REGIONAL_DB': str(store.path)}), \
                 patch.object(routes, 'ROOT', root), patch.object(routes, 'inventory', return_value={'items': []}), TestClient(app) as client:
                events = client.get('/regional/events').json()
                report = client.get('/regional/report').json()
            combined = json.dumps([events, report])
            self.assertNotIn('DO_NOT_LEAK', combined)
            self.assertNotIn('C:/private', combined)
            public = events['items'][0]['receipt']
            self.assertEqual(public, {key: receipt[key] for key in ['kind', 'status', 'service_acknowledged', 'ai_reviewed', 'content_sha256', 'evidence_sha256']})
            self.assertEqual(events['pending'], 0)
            self.assertEqual((report['openclaw']['acknowledged_count'], report['openclaw']['pending_count'], report['openclaw']['ai_reviewed_count']), (1, 0, 0))
            self.assertEqual(store.events()[0]['receipt'], receipt)

    def test_allowed_receipt_keys_cannot_smuggle_paths_or_credentials_as_values(self):
        rows = [{'type': 'AUTH_REQUIRED', 'delivery_status': 'PENDING_OPENCLAW',
                 'receipt': {'kind': 'C:/private/DO_NOT_LEAK', 'status': 'DO_NOT_LEAK_TOKEN',
                             'content_sha256': 'DO_NOT_LEAK_PASSWORD', 'ai_reviewed': 'DO_NOT_LEAK'}}]
        with patch.object(routes, 'store') as store:
            store.return_value.events.return_value = rows
            public = routes.events()
        self.assertNotIn('DO_NOT_LEAK', json.dumps(public))
        self.assertEqual(public['pending'], 1)
        self.assertEqual(rows[0]['receipt']['status'], 'DO_NOT_LEAK_TOKEN')

    def test_stale_attempt_status_exposes_only_valid_attempt_metadata_and_preserves_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'reports/government-guide-localization/OPENCLAW-STATUS.json'
            path.parent.mkdir(parents=True)
            saved = {'attempted_at': '2026-10-30T01:02:03+00:00', 'engine': 'OpenClaw', 'pending_count': 99,
                     'status': 'PENDING_OPENCLAW', 'reason': 'C:/private/operator/DO_NOT_LEAK',
                     'receipt_file': 'C:/private/DO_NOT_LEAK.json', 'token': 'DO_NOT_LEAK_TOKEN'}
            path.write_text(json.dumps(saved), encoding='utf8')
            original = path.read_bytes()
            rows = [{'type': 'AUTH_REQUIRED', 'delivery_status': 'PENDING_OPENCLAW', 'receipt': None}]
            with patch.object(routes, 'ROOT', root), patch.object(routes, 'store') as store, patch.object(routes, 'inventory', return_value={'items': []}):
                store.return_value.events.return_value = rows
                public = routes.report()
            self.assertNotIn('DO_NOT_LEAK', json.dumps(public))
            self.assertEqual(public['openclaw']['attempted_at'], saved['attempted_at'])
            self.assertEqual(public['openclaw']['engine'], 'OpenClaw')
            self.assertEqual((public['openclaw']['pending_count'], public['openclaw']['last_attempt_pending_count']), (1, 99))
            self.assertEqual(path.read_bytes(), original)
            saved.update(engine='DO_NOT_LEAK', attempted_at='DO_NOT_LEAK', pending_count='DO_NOT_LEAK')
            path.write_text(json.dumps(saved), encoding='utf8')
            with patch.object(routes, 'ROOT', root), patch.object(routes, 'store') as store, patch.object(routes, 'inventory', return_value={'items': []}):
                store.return_value.events.return_value = rows
                self.assertNotIn('DO_NOT_LEAK', json.dumps(routes.report()))


if __name__ == '__main__':
    unittest.main()
