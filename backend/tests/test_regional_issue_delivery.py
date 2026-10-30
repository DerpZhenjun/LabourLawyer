"""Exercise durable delivery against real SQLite and filesystem boundaries."""
import importlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regional_guides import RegionalStore


class IssueDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.delivery = importlib.import_module('regional_issue_delivery')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'actual-openclaw-workspace'
        self.workspace.mkdir()
        profile_patch = patch.object(self.delivery, '_configured_profile_workspace', return_value=self.workspace.resolve())
        self.profile_lookup = profile_patch.start()
        self.addCleanup(profile_patch.stop)
        self.store = RegionalStore(self.root / 'regional.sqlite')
        self.store.record_event({'id': 'public-event-1', 'type': 'AUTH_REQUIRED',
                                 'province': 'sichuan', 'city': '成都市', 'district': '青羊区',
                                 'url': 'https://user.example.gov.cn/login?token=do-not-copy&areaCode=510105#secret',
                                 'reason': '官方入口要求用户自行登录', 'occurred_at': '2026-10-30T01:00:00Z'})

    def sync(self, **kwargs):
        return self.delivery.deliver_pending(self.store.path, self.workspace, record_receipts=True, **kwargs)

    def test_persistence_receipt_proves_exact_event_and_never_claims_ai_review(self):
        result = self.sync()
        self.assertEqual((result['workspace_exported'], result['pending'], result['failed']), (1, 1, 0))
        event = self.store.events()[0]
        self.assertEqual(event['delivery_status'], 'PENDING_OPENCLAW')
        receipt = event['receipt']
        self.assertEqual(receipt['persisted_event_ids'], ['public-event-1'])
        self.assertIs(receipt['ai_reviewed'], False)
        content = (self.workspace / receipt['content_file']).read_bytes()
        import hashlib
        self.assertEqual(hashlib.sha256(content).hexdigest(), receipt['content_sha256'])
        persisted = json.loads((self.workspace / receipt['receipt_file']).read_bytes())
        self.assertEqual(persisted['persisted_event_ids'], ['public-event-1'])
        self.assertEqual(json.loads(content)['events'][0]['type'], 'AUTH_REQUIRED')

    def test_only_public_scalar_fields_reach_workspace_and_urls_lose_credentials(self):
        with self.store.connection() as db:
            data = json.loads(db.execute('SELECT payload FROM collection_outbox').fetchone()[0])
            data.update(user_document='PRIVATE_DOC', account={'token': 'PRIVATE_TOKEN'},
                        screenshot='C:/private/identity.png', reason='password=PRIVATE_PASSWORD',
                        url='https://name:PRIVATE_PASSWORD@example.gov.cn/guide?token=PRIVATE_TOKEN&areaCode=510105#PRIVATE_DOC')
            db.execute('UPDATE collection_outbox SET payload=?', (json.dumps(data),))
        self.sync()
        data = (self.workspace / self.store.events()[0]['receipt']['content_file']).read_text(encoding='utf8')
        for private in ('PRIVATE_DOC', 'PRIVATE_TOKEN', 'PRIVATE_PASSWORD', 'identity.png', 'user_document'):
            self.assertNotIn(private, data)
        self.assertEqual(json.loads(data)['events'][0]['url'], 'https://example.gov.cn/guide?areaCode=510105')

    def test_missing_workspace_leaves_pending_without_creating_fake_workspace(self):
        missing = self.root / 'offline-volume' / 'workspace'
        result = self.delivery.deliver_pending(self.store.path, missing)
        self.assertEqual(result['pending'], 1)
        self.assertEqual(result['workspace_exported'], 0)
        self.assertFalse(missing.exists())
        self.assertEqual(self.store.events()[0]['delivery_status'], 'PENDING_OPENCLAW')

    def test_crash_after_persist_before_database_ack_reuses_exact_receipt(self):
        with patch.object(self.delivery, '_record_export', side_effect=RuntimeError('simulated crash after persistence')):
            result = self.sync()
        self.assertEqual((result['workspace_exported'], result['pending']), (0, 1))
        files_before = {p.relative_to(self.workspace): p.read_bytes() for p in self.workspace.rglob('*.json')}
        self.assertEqual(len(files_before), 2)
        self.sync()
        files_after = {p.relative_to(self.workspace): p.read_bytes() for p in self.workspace.rglob('*.json')}
        self.assertEqual(files_before, files_after)
        self.assertEqual(self.store.events()[0]['delivery_status'], 'PENDING_OPENCLAW')
        self.assertEqual(self.sync()['workspace_exported'], 1)

    def test_corrupt_existing_receipt_cannot_ack_pending_event_or_overwrite_evidence(self):
        with patch.object(self.delivery, '_record_export', side_effect=RuntimeError('crash')):
            self.sync()
        receipt = next(self.workspace.rglob('receipt.json'))
        receipt.write_text('{"ok":true,"accepted_event_ids":["some-other-event"]}', encoding='utf8')
        before = receipt.read_bytes()
        result = self.sync()
        self.assertEqual((result['workspace_exported'], result['pending'], result['failed']), (0, 1, 1))
        self.assertEqual(receipt.read_bytes(), before)
        self.assertIsNone(self.store.events()[0]['receipt'])

    def test_one_bad_event_does_not_block_other_events_or_lose_pending_work(self):
        self.store.record_event({'id': 'public-event-2', 'type': 'SOURCE_STALE'})
        with self.store.connection() as db:
            db.execute('UPDATE collection_outbox SET payload=? WHERE id=?',
                       ('{"id":"public-event-1","type":"PRIVATE_DOCUMENT_UPLOAD"}', 'public-event-1'))
        result = self.sync()
        self.assertEqual((result['workspace_exported'], result['pending'], result['failed']), (1, 2, 1))
        states = {event['id']: event['delivery_status'] for event in self.store.events()}
        self.assertEqual(states['public-event-1'], 'PENDING_OPENCLAW')
        self.assertEqual(states['public-event-2'], 'PENDING_OPENCLAW')

    def test_changed_payload_during_delivery_is_not_acknowledged_as_old_content(self):
        original = self.delivery._record_export
        def change_then_ack(database, identifier, expected_payload, receipt):
            with closing(sqlite3.connect(database)) as db, db:
                data = json.loads(expected_payload)
                data['reason'] = '新的公开核验结果'
                db.execute('UPDATE collection_outbox SET payload=? WHERE id=?', (json.dumps(data), identifier))
            return original(database, identifier, expected_payload, receipt)
        with patch.object(self.delivery, '_record_export', side_effect=change_then_ack):
            result = self.sync()
        self.assertEqual((result['workspace_exported'], result['pending']), (0, 1))
        self.assertIsNone(self.store.events()[0]['receipt'])
        self.assertEqual(self.sync()['workspace_exported'], 1)

    def test_nested_public_fields_are_rejected_and_nonpublic_url_is_omitted(self):
        with self.store.connection() as db:
            data = json.loads(db.execute('SELECT payload FROM collection_outbox').fetchone()[0])
            data.update(reason={'document': 'do-not-copy'}, url='file:///private/case.docx')
            db.execute('UPDATE collection_outbox SET payload=?', (json.dumps(data),))
        self.assertEqual(self.sync()['failed'], 1)
        self.assertFalse(list(self.workspace.rglob('*.json')))

    def test_default_export_keeps_database_bytes_and_all_rows_pending(self):
        before = self.store.path.read_bytes()
        result = self.delivery.deliver_pending(self.store.path, self.workspace)
        self.assertEqual(result['workspace_exported'], 1)
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertIsNone(self.store.events()[0]['receipt'])
        self.assertEqual(self.delivery.delivery_summary(self.store.path),
                         {'total': 1, 'pending': 1, 'workspace_exported': 0, 'acknowledged': 0, 'ai_reviewed': 0})

    def test_export_summary_does_not_promote_persistence_to_service_ack(self):
        self.sync()
        self.assertEqual(self.delivery.delivery_summary(self.store.path),
                         {'total': 1, 'pending': 1, 'workspace_exported': 1, 'acknowledged': 0, 'ai_reviewed': 0})

    def test_content_corruption_preserves_evidence_and_refuses_export_receipt(self):
        with patch.object(self.delivery, '_record_export', side_effect=RuntimeError('crash')):
            self.sync()
        content = next(self.workspace.rglob('events.json'))
        content.write_text('{"events":[]}', encoding='utf8')
        before = content.read_bytes()
        result = self.sync()
        self.assertEqual(result['failed'], 1)
        self.assertEqual(content.read_bytes(), before)
        self.assertIsNone(self.store.events()[0]['receipt'])

    def test_nonofficial_and_local_urls_are_removed_from_export(self):
        with self.store.connection() as db:
            data = json.loads(db.execute('SELECT payload FROM collection_outbox').fetchone()[0])
            data['url'] = 'file:///private/case.docx'
            db.execute('UPDATE collection_outbox SET payload=?', (json.dumps(data),))
        self.sync()
        receipt = self.store.events()[0]['receipt']
        content = json.loads((self.workspace / receipt['content_file']).read_bytes())
        self.assertNotIn('url', content['events'][0])

    def test_partial_write_then_failure_retries_without_duplicating_completed_artifacts(self):
        original = self.delivery._immutable_write
        def fail_receipt(path, content, workspace):
            if path.name == 'receipt.json':
                raise OSError('simulated receipt volume write failure')
            return original(path, content, workspace)
        with patch.object(self.delivery, '_immutable_write', side_effect=fail_receipt):
            result = self.sync()
        self.assertEqual(result['failed'], 1)
        self.assertEqual(len(list(self.workspace.rglob('events.json'))), 1)
        self.assertFalse(list(self.workspace.rglob('receipt.json')))
        self.assertEqual(self.sync()['workspace_exported'], 1)
        self.assertEqual(len(list(self.workspace.rglob('events.json'))), 1)

    def test_cli_missing_database_returns_nonzero_without_creating_database(self):
        import subprocess
        missing = self.root / 'does-not-exist.sqlite'
        completed = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[2] / 'scripts/sync-regional-openclaw.py'),
                                    '--database', str(missing), '--workspace', str(self.workspace), '--report', str(self.root / 'logs')],
                                   capture_output=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(missing.exists())

    def test_engine_readback_exact_content_is_required_before_recording_service_ack(self):
        self.assertTrue(hasattr(self.delivery, 'verify_pending_with_openclaw'), 'service readback verifier is missing')
        def reader(agent, workspace, relative_path, timeout, *, profile):
            text = (workspace / relative_path).read_text(encoding='utf8').removesuffix('\n')
            details = {'status': 'ok', 'path': relative_path, 'text': text, 'from': 1, 'lines': len(text.splitlines())}
            return {'ok': True, 'toolName': 'memory_get', 'output': {'content': [{'type': 'text', 'text': json.dumps(details)}], 'details': details}, 'source': 'plugin'}
        with patch.object(self.delivery, '_gateway_memory_read', side_effect=reader):
            result = self.delivery.verify_pending_with_openclaw(self.store.path, self.workspace, 'labourlawyer-public-issues', profile='labourlawyer-public-issues', record_receipts=True)
        self.assertEqual((result['acknowledged'], result['pending'], result['ai_reviewed']), (1, 0, 0))
        event = self.store.events()[0]
        self.assertEqual(event['delivery_status'], 'ACKNOWLEDGED_OPENCLAW')
        self.assertEqual(event['receipt']['accepted_event_ids'], ['public-event-1'])
        self.assertEqual(event['receipt']['kind'], 'openclaw_service_readback')
        self.assertIs(event['receipt']['ai_reviewed'], False)

    def test_engine_ok_outer_response_with_disabled_tool_is_never_service_ack(self):
        self.assertTrue(hasattr(self.delivery, 'verify_pending_with_openclaw'), 'service readback verifier is missing')
        # Shape observed from the actual installed gateway's memory_get failure.
        response = {'ok': True, 'toolName': 'memory_get', 'output': {'content': [{'type': 'text', 'text': '{"disabled":true,"error":"path required","text":""}'}],
                    'details': {'disabled': True, 'error': 'path required', 'text': ''}}, 'source': 'plugin'}
        with patch.object(self.delivery, '_gateway_memory_read', return_value=response):
            result = self.delivery.verify_pending_with_openclaw(self.store.path, self.workspace, 'labourlawyer-public-issues', profile='labourlawyer-public-issues', record_receipts=True)
        self.assertEqual((result['acknowledged'], result['pending']), (0, 1))
        self.assertIsNone(self.store.events()[0]['receipt'])
        self.assertTrue(list(self.workspace.rglob('*.md')))

    def test_truncated_or_changed_engine_readback_leaves_all_rows_pending(self):
        self.assertTrue(hasattr(self.delivery, 'verify_pending_with_openclaw'), 'service readback verifier is missing')
        for details in [{'status': 'ok', 'text': '{}', 'path': 'wrong.md'}, {'status': 'ok', 'text': '{}', 'truncated': True}]:
            with self.subTest(details=details), patch.object(self.delivery, '_gateway_memory_read', return_value={
                'ok': True, 'toolName': 'memory_get', 'source': 'plugin', 'output': {'details': details, 'content': []}}):
                result = self.delivery.verify_pending_with_openclaw(self.store.path, self.workspace, 'labourlawyer-public-issues', profile='labourlawyer-public-issues', record_receipts=True)
            self.assertEqual(result['acknowledged'], 0)
            self.assertIsNone(self.store.events()[0]['receipt'])

    def test_malformed_engine_response_is_reported_without_ack_or_crash(self):
        for response in [[], {'ok': True, 'output': None}, {'ok': True, 'output': {'details': []}}]:
            with self.subTest(response=response), patch.object(self.delivery, '_gateway_memory_read', return_value=response):
                result = self.delivery.verify_pending_with_openclaw(self.store.path, self.workspace, 'labourlawyer-public-issues', profile='labourlawyer-public-issues', record_receipts=True)
                self.assertEqual((result['acknowledged'], result['pending']), (0, 1))
                self.assertGreater(result['failed'], 0)
                self.assertIsNone(self.store.events()[0]['receipt'])

    def test_official_workguide_hash_and_public_item_selectors_remain_traceable(self):
        for url in ['https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=91413c73-75e5-4df0-9b5c-9d6ef192361f',
                    'https://www.jszwfw.gov.cn/guide?itemId=6de260dc797c433b82e0eb2a4dd9a419&taskCode=11320900717413933Q3322014317000&areaCode=320900']:
            with self.subTest(url=url):
                event = self.delivery._public_event(json.dumps({'id': 'traceable', 'type': 'SOURCE_STALE', 'url': url}), 'traceable')
                self.assertEqual(event['url'], url)
        event = self.delivery._public_event(json.dumps({'id': 'oauth', 'type': 'AUTH_REQUIRED',
            'url': 'https://user.zjzwfw.gov.cn/login?code=SECRET&state=SECRET#access_token=SECRET&refresh_token=SECRET'}), 'oauth')
        self.assertEqual(event['url'], 'https://user.zjzwfw.gov.cn/login')

    def test_service_verification_rejects_global_profile_and_mismatched_workspace(self):
        for profile in [None, 'default', 'main']:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.delivery.verify_pending_with_openclaw(self.store.path, self.workspace, 'labourlawyer-public-issues', profile=profile)
        self.profile_lookup.return_value = self.root / 'different-profile-workspace'
        with self.assertRaises(ValueError):
            self.delivery.verify_pending_with_openclaw(self.store.path, self.workspace, 'labourlawyer-public-issues', profile='labourlawyer-public-issues')
        self.assertFalse(list(self.workspace.rglob('*.md')))

    def test_gateway_command_explicitly_names_isolated_profile_and_drops_global_overrides(self):
        import subprocess
        response = {'ok': False, 'toolName': 'memory_get', 'error': {'code': 'not_found', 'message': 'fixture unavailable'}}
        with patch.dict('os.environ', {'OPENCLAW_CONFIG_PATH': 'C:/global/openclaw.json', 'OPENCLAW_GATEWAY_TOKEN': 'do-not-forward'}), \
             patch.object(self.delivery.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(response), '')) as run:
            self.delivery._gateway_memory_read('labourlawyer-public-issues', self.workspace, 'memory/own.md', 15, profile='labourlawyer-public-issues')
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--profile') + 1], 'labourlawyer-public-issues')
        self.assertNotIn('OPENCLAW_CONFIG_PATH', run.call_args.kwargs['env'])
        self.assertNotIn('OPENCLAW_GATEWAY_TOKEN', run.call_args.kwargs['env'])

    def test_profile_bound_proof_keeps_earlier_unbound_proof_as_immutable_history(self):
        historical = []
        def reader(agent, workspace, relative_path, timeout, *, profile):
            legacy = workspace / 'partlawyer-public-issues/service-readbacks' / (Path(relative_path).stem + '.json')
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text('{"historical_unbound_proof":true}', encoding='utf8')
            historical.append(legacy)
            text = (workspace / relative_path).read_text(encoding='utf8').removesuffix('\n')
            details = {'status': 'ok', 'path': relative_path, 'text': text, 'from': 1, 'lines': len(text.splitlines())}
            return {'ok': True, 'toolName': 'memory_get', 'output': {'content': [{'type': 'text', 'text': json.dumps(details)}], 'details': details}, 'source': 'plugin'}
        with patch.object(self.delivery, '_gateway_memory_read', side_effect=reader):
            result = self.delivery.verify_pending_with_openclaw(self.store.path, self.workspace, 'labourlawyer-public-issues', profile='labourlawyer-public-issues', record_receipts=True)
        self.assertEqual(result['acknowledged'], 1)
        self.assertEqual(historical[0].read_text(encoding='utf8'), '{"historical_unbound_proof":true}')
        receipt = self.store.events()[0]['receipt']
        self.assertEqual(receipt['profile'], 'labourlawyer-public-issues')
        self.assertNotEqual(self.workspace / receipt['evidence_file'], historical[0])

    def test_startup_rejects_broadened_tools_and_embedding_provider(self):
        path = Path(__file__).resolve().parents[2] / 'scripts/start-openclaw-issue-gateway.py'
        self.assertTrue(path.is_file(), 'repeatable isolated gateway startup is missing')
        spec = importlib.util.spec_from_file_location('receipt_gateway_startup', path)
        startup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(startup)
        entry = {'workspace': str(self.workspace), 'contextInjection': 'never', 'heartbeat': {'every': '0m'},
                 'tools': {'allow': ['memory_get'], 'fs': {'workspaceOnly': True}},
                 'memory': {'search': {'provider': 'none', 'rememberAcrossConversations': False,
                    'sources': ['memory'], 'extraPaths': [], 'experimental': {'sessionMemory': False},
                    'store': {'vector': {'enabled': False}}}}}
        self.assertEqual(startup.validate_public_entry(entry, self.workspace), self.workspace.resolve())
        entry['tools']['allow'].append('exec')
        with self.assertRaises(ValueError):startup.validate_public_entry(entry, self.workspace)
        entry['tools']['allow'] = ['memory_get']
        entry['memory']['search']['provider'] = 'openai'
        with self.assertRaises(ValueError):startup.validate_public_entry(entry, self.workspace)


if __name__ == '__main__':
    unittest.main()
