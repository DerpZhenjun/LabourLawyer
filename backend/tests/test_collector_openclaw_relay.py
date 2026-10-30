"""Temporary synthetic dedicated stores; mocked SSH and gateway, no live writes."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from collector_issue_events import CollectorIssueOutbox
import regional_issue_delivery as bridge


class CollectorRelayTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('collector_relay',ROOT/'scripts/relay-collector-openclaw.py')
        self.r=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.r)
        self.temp=tempfile.TemporaryDirectory(prefix='collector-relay-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.state=self.root/'remote-state';self.state.mkdir()
        self.remote=self.state/'collector-issues-v1.sqlite3';self.mirror=self.root/'collector-issues-mirror.sqlite3'
        self.workspace=self.root/'public-workspace';self.workspace.mkdir()
        self.uid=self.state.stat().st_uid
        self.ns={};exec(self.r.REMOTE_CODE,self.ns)
        self.calls=[];self.gateway_calls=0
        self.addCleanup(patch.stopall)
        patch.object(self.r,'REMOTE_STATE',self.state.as_posix()).start()
        patch.object(bridge,'_configured_profile_workspace',return_value=self.workspace).start()
        patch.object(bridge,'_gateway_memory_read',side_effect=self.gateway).start()
        self.store=CollectorIssueOutbox(self.remote)
        for index in range(2):
            job={'id':format(index+1,'032x'),'attempt':1,'url':'https://www.zjzwfw.gov.cn/zjservice-fe/?areaCode=330127#/workguide?localInnerCode='+('a'*31+str(index)),
                'region':{'province':'zhejiang','city':'杭州市','district':'淳安县','region_code':'330127'},
                'updated_at':'2026-10-31T02:00:00Z','result':{'state':'guide_observed','observed_at':'2026-10-31T02:00:00Z','evidence':[],'attachments':[]}}
            self.store.record_result(job,allowed_hosts=['www.zjzwfw.gov.cn'])

    def gateway(self,agent,workspace,relative,timeout,*,profile=None):
        self.gateway_calls+=1
        return {'ok':True,'toolName':'memory_get','output':{'details':{'status':'ok','path':relative,'from':1,'text':(workspace/relative).read_text(encoding='utf8').removesuffix('\n')}}}

    def transport(self,alias,request):
        self.calls.append(deepcopy(request))
        return self.ns['operate'](request,root=str(self.state),uid=self.uid)

    def run_relay(self):
        return self.r.relay('ubuntu2204',self.remote.as_posix(),self.mirror,self.workspace,transport=self.transport)

    def rows(self,path,table='collection_outbox'):
        with closing(sqlite3.connect(path)) as db:return db.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()

    def test_actual_public_snapshot_gateway_and_remote_cas_ack_keep_other_tables_exact(self):
        protected={table:self.rows(self.remote,table) for table in ['collector_issue_schema','collector_issue_events','collector_issue_observations']}
        result=self.run_relay();self.assertEqual(result['status'],'ACKNOWLEDGED_OPENCLAW');self.assertEqual(result['remote_reconciled'],2)
        self.assertGreater(self.gateway_calls,0);self.assertEqual(self.store.summary()['acknowledged'],2)
        for table,rows in protected.items():self.assertEqual(self.rows(self.remote,table),rows)
        self.assertEqual(self.run_relay()['remote_pending_before'],0)

    def test_remote_snapshot_contains_only_public_pending_rows_not_observations_or_raw(self):
        snap=self.transport('ubuntu2204',{'action':'snapshot','path':str(self.remote),'limit':100})
        self.assertEqual(set(snap),{'protocol','identity','rows','pending','acknowledged'})
        self.assertEqual(len(snap['rows']),2)
        for row in snap['rows']:self.assertEqual(set(row),{'id','payload','payload_sha256','semantic','created_at'})
        self.assertNotIn('observation',json.dumps(snap));self.assertNotIn('receipt',json.dumps(snap))

    def test_failed_or_truncated_gateway_never_remote_acks_and_later_round_recovers(self):
        with patch.object(bridge,'_gateway_memory_read',return_value={'ok':True,'toolName':'memory_get','output':{'details':{'status':'ok','truncated':True}}}):
            result=self.run_relay()
        self.assertEqual(result['status'],'PENDING_OPENCLAW');self.assertEqual(self.store.summary()['pending'],2)
        self.assertFalse(any(c['action']=='ack' for c in self.calls))
        self.assertEqual(self.run_relay()['remote_reconciled'],2)

    def test_ssh_loss_after_local_ack_preserves_mirror_proof_and_retries_idempotently(self):
        actual=self.transport
        def lost(alias,request):
            if request['action']=='ack':raise OSError('password=PRIVATE_SENTINEL')
            return actual(alias,request)
        with patch.object(self,'transport',side_effect=lost):result=self.run_relay()
        self.assertEqual(result['status'],'PENDING_OPENCLAW');self.assertNotIn('PRIVATE_SENTINEL',json.dumps(result))
        self.assertEqual(self.store.summary()['pending'],2)
        before=self.gateway_calls;self.assertEqual(self.run_relay()['remote_reconciled'],2)
        self.assertEqual(self.gateway_calls,before)

    def test_lost_ack_reply_repeated_same_receipt_is_accepted_without_replacing_it(self):
        result=self.run_relay();ack=next(c for c in self.calls if c['action']=='ack');before=self.rows(self.remote)
        again=self.transport('ubuntu2204',ack);self.assertEqual(again['reconciled'],2);self.assertEqual(self.rows(self.remote),before)
        changed=deepcopy(ack);changed['rows'][0]['receipt']['content_sha256']='0'*64
        with self.assertRaises(ValueError):self.transport('ubuntu2204',changed)
        self.assertEqual(self.rows(self.remote),before)

    def test_remote_cas_conflict_rolls_back_entire_batch_and_keeps_payloads(self):
        self.run_relay();ack=next(c for c in self.calls if c['action']=='ack')
        with closing(sqlite3.connect(self.remote)) as db,db:db.execute("UPDATE collection_outbox SET delivery_status='PENDING_OPENCLAW',receipt=NULL")
        before=self.rows(self.remote);bad=deepcopy(ack);bad['rows'][1]['payload_sha256']='0'*64
        with self.assertRaises(ValueError):self.transport('ubuntu2204',bad)
        self.assertEqual(self.rows(self.remote),before)

    def test_old_relay_or_unbound_mirror_is_refused_without_modification(self):
        with closing(sqlite3.connect(self.mirror)) as db,db:db.execute('CREATE TABLE old_ack(secret TEXT)')
        before=self.mirror.read_bytes();result=self.run_relay()
        self.assertEqual(result['status'],'PENDING_OPENCLAW');self.assertEqual(self.mirror.read_bytes(),before)
        self.assertEqual(self.store.summary()['pending'],2)

    def test_tampered_cached_proof_cannot_ack_remote_pending(self):
        actual=self.transport
        def unavailable(alias,request):
            if request['action']=='ack':raise OSError('unavailable')
            return actual(alias,request)
        with patch.object(self,'transport',side_effect=unavailable):self.run_relay()
        proof=next((self.workspace/'partlawyer-public-issues/service-readbacks').rglob('*.json'));proof.write_bytes(b'{}')
        result=self.run_relay();self.assertEqual(result['status'],'PENDING_OPENCLAW');self.assertEqual(self.store.summary()['pending'],2)

    def test_cached_receipt_unknown_secret_field_is_never_transferred(self):
        actual=self.transport
        def unavailable(alias,request):
            if request['action']=='ack':raise OSError('unavailable')
            return actual(alias,request)
        with patch.object(self,'transport',side_effect=unavailable):self.run_relay()
        with closing(sqlite3.connect(self.mirror)) as db,db:
            for identifier,raw in db.execute('SELECT id,receipt FROM collection_outbox').fetchall():
                receipt=json.loads(raw);receipt['token']='PRIVATE_SENTINEL'
                db.execute('UPDATE collection_outbox SET receipt=? WHERE id=?',(json.dumps(receipt),identifier))
        self.calls.clear();result=self.run_relay()
        self.assertEqual(result['status'],'PENDING_OPENCLAW');self.assertFalse(any(c['action']=='ack' for c in self.calls))
        self.assertEqual(self.store.summary()['pending'],2)

    def test_remote_path_uid_schema_size_and_file_replacement_fail_closed(self):
        request={'action':'snapshot','path':str(self.remote),'limit':100}
        for path in [str(self.state/'queue.sqlite3'),str(self.state/'../outside.sqlite3')]:
            bad={**request,'path':path}
            with self.assertRaises(ValueError):self.transport('ubuntu2204',bad)
        with self.assertRaises(ValueError):self.ns['operate'](request,root=str(self.state),uid=self.uid+1)
        with closing(sqlite3.connect(self.remote)) as db,db:db.execute('CREATE TABLE unknown_private(data TEXT)')
        with self.assertRaises(ValueError):self.transport('ubuntu2204',request)

    def test_remote_file_size_symlink_and_inode_change_refuse_without_ack(self):
        request={'action':'snapshot','path':str(self.remote),'limit':100}
        original=self.ns['file_check'];before=self.rows(self.remote)
        # Actual oversized sparse file is rejected before opening SQLite.
        large=self.state/'collector-issues-large.sqlite3'
        with large.open('wb') as stream:stream.truncate(64*1024*1024+1)
        large.chmod(0o600)
        with self.assertRaises(ValueError):self.transport('ubuntu2204',{**request,'path':str(large)})
        # The inode captured from snapshot must still match at the ACK operation.
        self.run_relay();ack=next(c for c in self.calls if c['action']=='ack')
        bad=deepcopy(ack);bad['identity']['inode']+=1
        with self.assertRaises(ValueError):self.transport('ubuntu2204',bad)
        preserved=self.rows(self.remote)
        with patch.object(self.ns['pathlib'].Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):self.transport('ubuntu2204',request)
        self.assertEqual(self.rows(self.remote),preserved)

    def test_remote_unknown_trigger_or_nonprivate_permissions_are_refused(self):
        request={'action':'snapshot','path':str(self.remote),'limit':100}
        with closing(sqlite3.connect(self.remote)) as db,db:
            db.execute('CREATE TRIGGER unexpected AFTER UPDATE ON collection_outbox BEGIN SELECT 1; END')
        before=self.rows(self.remote)
        with self.assertRaises(ValueError):self.transport('ubuntu2204',request)
        self.assertEqual(self.rows(self.remote),before)
        if os.name=='posix':
            with closing(sqlite3.connect(self.remote)) as db,db:db.execute('DROP TRIGGER unexpected')
            self.remote.chmod(0o666)
            with self.assertRaises(ValueError):self.transport('ubuntu2204',request)

    def test_mirror_binding_refuses_another_alias_or_replaced_remote_file(self):
        self.run_relay();before=self.mirror.read_bytes()
        result=self.r.relay('other-alias',self.remote.as_posix(),self.mirror,self.workspace,transport=self.transport)
        self.assertEqual(result['status'],'PENDING_OPENCLAW');self.assertEqual(self.mirror.read_bytes(),before)

    def test_snapshot_pending_reads_consistent_wal_content(self):
        with closing(sqlite3.connect(self.remote)) as db:
            db.execute('PRAGMA journal_mode=WAL');db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE collection_outbox SET delivery_status='ACKNOWLEDGED_OPENCLAW' WHERE id=(SELECT id FROM collection_outbox ORDER BY id LIMIT 1)")
            snap=self.transport('ubuntu2204',{'action':'snapshot','path':str(self.remote),'limit':100})
            self.assertEqual(snap['pending'],2);self.assertEqual(len(snap['rows']),2);db.rollback()

    def test_ssh_uses_fixed_batchmode_stdin_program_and_redacts_remote_errors(self):
        successful={'protocol':self.r.PROTOCOL,'rows':[],'identity':{},'pending':0,'acknowledged':0}
        completed=type('Result',(),{'returncode':0,'stdout':json.dumps(successful),'stderr':''})()
        with patch.object(self.r.subprocess,'run',return_value=completed) as run:
            self.r.exchange('ubuntu2204',{'action':'snapshot','path':'/safe/public','limit':1})
        args=run.call_args
        compile(args.kwargs['input'],'<fixed-ssh-stdin-program>','exec')
        self.assertEqual(args.args[0],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','--','ubuntu2204','python3','-B','-'])
        self.assertNotIn('/safe/public',repr(args.args[0]));self.assertIn('operate',args.kwargs['input'])
        completed.returncode=1;completed.stderr='password=PRIVATE_SENTINEL'
        with patch.object(self.r.subprocess,'run',return_value=completed):
            with self.assertRaises(ValueError) as exc:self.r.exchange('ubuntu2204',{})
        self.assertNotIn('PRIVATE_SENTINEL',str(exc.exception))

    def test_continuous_mode_survives_failed_round_and_reaches_next_round(self):
        args=['--ssh-alias','ubuntu2204','--remote-database',self.remote.as_posix(),'--mirror',str(self.mirror),'--workspace',str(self.workspace),'--interval','5']
        output=StringIO()
        with patch.object(self.r,'relay',side_effect=[{'status':'PENDING_OPENCLAW','failed':1},{'status':'ACKNOWLEDGED_OPENCLAW','failed':0}]) as run,patch.object(self.r.time,'sleep',side_effect=[None,KeyboardInterrupt]),redirect_stdout(output):
            self.assertEqual(self.r.main(args),0)
        self.assertEqual(run.call_count,2)
        self.assertEqual([json.loads(line)['failed'] for line in output.getvalue().splitlines()],[1,0])

    def test_malformed_nested_private_or_checksum_changed_snapshot_is_not_mirrored(self):
        original=self.transport('ubuntu2204',{'action':'snapshot','path':str(self.remote),'limit':100})
        for mutate in ['nested','unknown','sha']:
            snap=deepcopy(original)
            if mutate=='sha':snap['rows'][0]['payload_sha256']='0'*64
            else:
                event=json.loads(snap['rows'][0]['payload']);event['reason']={'private':'x'} if mutate=='nested' else 'token=PRIVATE_SENTINEL'
                snap['rows'][0]['payload']=json.dumps(event);snap['rows'][0]['payload_sha256']=sha256(snap['rows'][0]['payload'].encode()).hexdigest()
            result=self.r.relay('ubuntu2204',self.remote.as_posix(),self.root/('collector-issues-'+mutate+'.sqlite3'),self.workspace,transport=lambda a,r:snap)
            self.assertEqual(result['status'],'PENDING_OPENCLAW');self.assertEqual(self.store.summary()['pending'],2)

    def test_explicit_alias_mirror_remote_path_and_workspace_are_required(self):
        for alias in ['-oProxyCommand=x','ubuntu2204;echo x','user@host','']:
            with self.assertRaises(ValueError):self.r.validate_arguments(alias,self.remote.as_posix(),self.mirror,self.workspace)
        for mirror in [Path('relative.sqlite3'),self.root/'regional-guides.sqlite',self.remote]:
            with self.assertRaises(ValueError):self.r.validate_arguments('ubuntu2204',self.remote.as_posix(),mirror,self.workspace)


if __name__=='__main__':unittest.main(verbosity=2)
