"""The admin status reflects live durable receipts, not a stale JSON report."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routes import regional_guides as routes


class OpenClawReportCountsTests(unittest.TestCase):
    def test_exports_and_unattested_ack_are_not_service_receipts(self):
        rows = [
            {'type': 'SEARCH_NO_RESULT', 'delivery_status': 'PENDING_OPENCLAW', 'receipt': {'kind': 'workspace_persistence', 'status': 'EXPORTED_PENDING_OPENCLAW'}},
            {'type': 'SEARCH_NO_RESULT', 'delivery_status': 'ACKNOWLEDGED_OPENCLAW', 'receipt': {}},
            {'type': 'AUTH_REQUIRED', 'delivery_status': 'ACKNOWLEDGED_OPENCLAW', 'receipt': {'service_acknowledged': True, 'ai_reviewed': False}},
        ]
        with tempfile.TemporaryDirectory() as folder, patch.object(routes, 'ROOT', Path(folder)), patch.object(routes, 'store') as store, patch.object(routes, 'inventory', return_value={'items': []}):
            store.return_value.events.return_value = rows
            state = routes.report()['openclaw']
            self.assertEqual((state['total_count'], state['pending_count'], state['acknowledged_count'], state['exported_count'], state['ai_reviewed_count']), (3, 1, 1, 1, 0))
            self.assertEqual(state['status'], 'PENDING_OPENCLAW')
            rows[:] = [rows[-1]]
            self.assertEqual(routes.report()['openclaw']['status'], 'ACKNOWLEDGED_OPENCLAW')
