"""Relay only the new dedicated collector outbox to an isolated public gateway.

No queue, raw evidence, old relay DB, browser or model is accessed. The SSH
program below has exactly two operations: public pending snapshot and ACK CAS.
The new local mirror is permanently bound to one alias/path/file identity.
"""
import argparse
import base64
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import regional_issue_delivery as bridge
from collector_issue_events import SCHEMA,APP_ID,CollectorIssueOutbox

REMOTE_STATE='/home/ubuntu2204/SJL/LabourLawyer/var/collector'
PROFILE='labourlawyer-public-issues'
PROTOCOL='collector-public-relay/v1'
MAX_BYTES=8*1024*1024

# Static, stdlib-only SSH helper; requests are JSON data passed through stdin.
# root/uid overrides are function-only Temp-test seams, absent from the protocol.
REMOTE_CODE=r'''
from contextlib import closing
import hashlib,json,os,pathlib,re,sqlite3,stat
from urllib.parse import urlsplit,parse_qsl
PROTOCOL='collector-public-relay/v1'
APP_ID=0x43495331
FIELDS=set('id type province city district region_code service keyword url occurred_at reason attempts final_status remediation'.split())
RECEIPT_FIELDS=set('kind ok accepted_event_ids agent profile service_acknowledged ai_reviewed workspace content_file content_sha256 evidence_file evidence_sha256'.split())
DDL=[
'CREATE TABLE collector_issue_schema(version INTEGER PRIMARY KEY)',
'CREATE TABLE collection_outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL,delivery_status TEXT NOT NULL,receipt TEXT,created_at TEXT NOT NULL)',
'CREATE TABLE collector_issue_events(event_id TEXT PRIMARY KEY REFERENCES collection_outbox(id),semantic TEXT NOT NULL,payload_sha256 TEXT NOT NULL)',
'CREATE TABLE collector_issue_observations(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES collection_outbox(id),observation TEXT NOT NULL)']
def need(ok):
 if not ok:raise ValueError('Dedicated public relay validation refused')
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def schema(db):
 rows=db.execute("SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','view','trigger') ORDER BY name").fetchall()
 expected={s.split('(',1)[0].split()[-1]:s for s in DDL}
 need(len(rows)==4 and all(t=='table' and expected.get(n)==s for t,n,s in rows))
 need(db.execute('PRAGMA application_id').fetchone()[0]==APP_ID and db.execute('PRAGMA user_version').fetchone()[0]==1)
 need(db.execute('SELECT version FROM collector_issue_schema').fetchall()==[(1,)])
 need(not db.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchone())
def public_row(row):
 need(type(row) is dict and set(row)=={'id','payload','payload_sha256','semantic','created_at'})
 need(all(type(v) is str and len(v.encode())<=100000 for v in row.values()))
 need(re.fullmatch('[a-f0-9]{64}',row['payload_sha256']) and digest(row['payload'])==row['payload_sha256'])
 event=json.loads(row['payload']);sem=json.loads(row['semantic'])
 need(type(event) is dict and set(event)==FIELDS and event['id']==row['id'])
 need(type(event['attempts']) is int and 1<=event['attempts']<=2)
 need(all(type(v) is str and len(v)<=16000 for k,v in event.items() if k!='attempts'))
 need(event['type'] in {'AUTH_REQUIRED','CAPTCHA_REQUIRED','GUIDE_PAGE_UNAVAILABLE','ONLINE_CHANNEL_UNVERIFIED','TEMPLATE_DOWNLOAD_FAILED'})
 need(event['final_status'] in {'manual_authorization','pending_recheck'})
 for key,value in event.items():
  if key=='attempts':continue
  need(not re.search(r'(?i)bearer\s+\S+|(?:token|password|cookie|authorization|credential|secret|signature)\s*[:=]|(?:/home/|/Users/|[A-Z]:\\)|(?<!\d)(?:\d{17}[\dXx]|1[3-9]\d{9})(?!\d)',value))
 u=urlsplit(event['url']);need(u.scheme in {'https','http'} and u.username is None and u.password is None)
 need(re.fullmatch(r'(?:[a-z0-9-]+\.)+gov\.cn',u.hostname or '') and u.port in {None,443 if u.scheme=='https' else 80})
 need(not re.search(r'[\x00-\x20\\]|%(?![a-fA-F0-9]{2})',event['url']))
 need(not re.search(r'(?i)(?:^|/)(?:login|sso|oauth|passport|account|profile|private|session|upload|auth)(?:[/.?_-]|$)',u.path))
 for query in [u.query,u.fragment.partition('?')[2]]:
  for key,value in parse_qsl(query):need(not re.search(r'(?i)token|secret|password|session|cookie|ticket|credential|authorization|signature|^code$',key))
 need(type(sem) is dict and set(sem)=={'policy','region','source','type','subject'})
 need(sem['policy']=='collector-public-issues/v1' and sem['source']==event['url'] and sem['type']==event['type'])
 need(sem['region']=={k:event[k] for k in ['province','city','district','region_code']})
 need(type(sem['subject']) is str and re.fullmatch(r'page|attachment-(?:[1-9]|1[0-2])',sem['subject']))
 identity=digest(canonical(sem));need(row['id']=='collector-issue-v1-'+'-'.join(identity[i:i+8] for i in range(0,64,8)))
 return event
def file_check(path,root,uid):
 raw=pathlib.Path(path);base=pathlib.Path(root)
 need(raw.is_absolute() and raw.parent==base and re.fullmatch(r'collector-issues[-A-Za-z0-9_.]*\.sqlite3',raw.name))
 need(raw.resolve(strict=True)==raw and base.resolve(strict=True)==base)
 need(not any(p.is_symlink() for p in [raw,*raw.parents]))
 st=raw.stat();need(stat.S_ISREG(st.st_mode) and st.st_uid==uid and st.st_nlink==1 and 0<st.st_size<=64*1024*1024)
 need(base.stat().st_uid==uid)
 if os.name=='posix':need(not (st.st_mode & 0o022) and not (base.stat().st_mode & 0o022))
 return {'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid}
def operate(request,*,root='/home/ubuntu2204/SJL/LabourLawyer/var/collector',uid=1000):
 need(type(request) is dict and request.get('action') in {'snapshot','ack'})
 need(set(request)==({'action','path','limit'} if request['action']=='snapshot' else {'action','path','identity','rows'}))
 if hasattr(os,'getuid'):need(os.getuid()==uid)
 path=request['path'];need(type(path) is str);identity=file_check(path,root,uid)
 mode='ro' if request['action']=='snapshot' else 'rw'
 with closing(sqlite3.connect(pathlib.Path(path).as_uri()+'?mode='+mode,uri=True,timeout=15,isolation_level=None)) as db:
  db.execute('BEGIN' if mode=='ro' else 'BEGIN IMMEDIATE')
  try:
   schema(db);need(file_check(path,root,uid)==identity)
   if mode=='ro':
    limit=request['limit'];need(type(limit) is int and 1<=limit<=100)
    rows=[]
    for item in db.execute('SELECT o.id,o.payload,e.payload_sha256,e.semantic,o.created_at FROM collection_outbox o LEFT JOIN collector_issue_events e ON e.event_id=o.id WHERE o.delivery_status=? ORDER BY o.created_at,o.id LIMIT ?',('PENDING_OPENCLAW',limit)):
     row=dict(zip(['id','payload','payload_sha256','semantic','created_at'],item));public_row(row);rows.append(row)
    counts=dict(db.execute('SELECT delivery_status,count(*) FROM collection_outbox GROUP BY delivery_status'))
    need(set(counts)<={'PENDING_OPENCLAW','ACKNOWLEDGED_OPENCLAW'})
    result={'protocol':PROTOCOL,'identity':identity,'rows':rows,'pending':counts.get('PENDING_OPENCLAW',0),'acknowledged':counts.get('ACKNOWLEDGED_OPENCLAW',0)}
    need(len(canonical(result).encode())<=8*1024*1024)
   else:
    need(request['identity']==identity and type(request['rows']) is list and 1<=len(request['rows'])<=100)
    seen=set()
    for item in request['rows']:
     need(type(item) is dict and set(item)=={'id','payload_sha256','receipt'} and item['id'] not in seen);seen.add(item['id'])
     receipt=item['receipt'];need(type(receipt) is dict and set(receipt)==RECEIPT_FIELDS and len(canonical(receipt).encode())<=100000)
     need(receipt.get('kind')=='openclaw_service_readback' and receipt.get('ok') is True and receipt.get('service_acknowledged') is True and receipt.get('ai_reviewed') is False)
     need(receipt.get('agent')==receipt.get('profile')=='labourlawyer-public-issues' and item['id'] in receipt.get('accepted_event_ids',[]))
     row=db.execute('SELECT o.payload,o.delivery_status,o.receipt,e.payload_sha256,e.semantic,o.created_at FROM collection_outbox o JOIN collector_issue_events e ON e.event_id=o.id WHERE o.id=?',(item['id'],)).fetchone()
     need(row is not None and digest(row[0])==row[3]==item['payload_sha256'])
     public_row(dict(zip(['id','payload','payload_sha256','semantic','created_at'],[item['id'],row[0],row[3],row[4],row[5]])))
     if row[1]=='ACKNOWLEDGED_OPENCLAW':need(row[2] is not None and canonical(json.loads(row[2]))==canonical(receipt))
     else:
      need(row[1]=='PENDING_OPENCLAW')
      changed=db.execute('UPDATE collection_outbox SET delivery_status=?,receipt=? WHERE id=? AND payload=? AND delivery_status=?',('ACKNOWLEDGED_OPENCLAW',canonical(receipt),item['id'],row[0],'PENDING_OPENCLAW')).rowcount;need(changed==1)
    result={'protocol':PROTOCOL,'reconciled':len(seen),'pending':db.execute("SELECT count(*) FROM collection_outbox WHERE delivery_status='PENDING_OPENCLAW'").fetchone()[0]}
   need(file_check(path,root,uid)==identity);db.commit();return result
  except BaseException:db.rollback();raise
'''
_remote={};exec(REMOTE_CODE,_remote)


def need(value):
    if not value:raise ValueError('Dedicated collector relay validation refused')


def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def validate_arguments(alias,remote_database,mirror,workspace):
    need(type(alias) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',alias))
    from pathlib import PurePosixPath
    remote=PurePosixPath(remote_database)
    need(str(remote)==remote_database and remote.parent==PurePosixPath(REMOTE_STATE)
         and re.fullmatch(r'collector-issues[-A-Za-z0-9_.]*\.sqlite3',remote.name))
    path=Path(mirror);work=Path(workspace)
    need(path.is_absolute() and path.resolve()==path and path.parent.is_dir() and not path.is_symlink()
         and re.fullmatch(r'collector-issues[-A-Za-z0-9_.]*\.sqlite3',path.name) and path.as_posix()!=remote_database)
    need(work.is_absolute() and work.resolve(strict=True)==work and work.is_dir())
    return path,work


def exchange(alias,request):
    code=REMOTE_CODE+'\nimport base64,sys\ntry:\n r=operate(json.loads(base64.b64decode('+repr(base64.b64encode(encode(request).encode()).decode())+')))\n print(json.dumps(r,ensure_ascii=False))\nexcept Exception as e:\n print(json.dumps({"protocol":PROTOCOL,"error_type":type(e).__name__}));sys.exit(1)\n'
    process=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','--',alias,'python3','-B','-'],
        input=code,capture_output=True,text=True,encoding='utf8',timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    need(process.returncode==0 and len(process.stdout.encode())<=MAX_BYTES)
    result=json.loads(process.stdout);need(type(result) is dict and result.get('protocol')==PROTOCOL and 'error_type' not in result)
    return result


def prepare_mirror(path,binding,rows):
    sidecar=path.with_suffix(path.suffix+'.relay-binding.json')
    need(not sidecar.is_symlink())
    if path.exists():
        need(sidecar.is_file() and json.loads(sidecar.read_bytes())==binding)
    else:
        need(not sidecar.exists())
        for target,body in [(sidecar,(encode(binding)+'\n').encode()),(path,b'')]:
            descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
        with closing(sqlite3.connect(path)) as db,db:
            for statement in SCHEMA:db.execute(statement)
            db.execute('PRAGMA application_id='+str(APP_ID));db.execute('PRAGMA user_version=1')
    need(path.stat().st_size<=64*1024*1024)
    with closing(sqlite3.connect(path)) as db,db:
        _remote['schema'](db)
        for row in rows:
            event=_remote['public_row'](row)
            need(bridge._public_event(row['payload'],row['id'])==event)
            found=db.execute('SELECT payload,delivery_status FROM collection_outbox WHERE id=?',(row['id'],)).fetchone()
            if found:
                need(found[0]==row['payload'] and found[1] in {'PENDING_OPENCLAW','ACKNOWLEDGED_OPENCLAW'})
                need(db.execute('SELECT semantic,payload_sha256 FROM collector_issue_events WHERE event_id=?',(row['id'],)).fetchone()==(row['semantic'],row['payload_sha256']))
            else:
                db.execute('INSERT INTO collection_outbox VALUES(?,?,?,NULL,?)',(row['id'],row['payload'],'PENDING_OPENCLAW',row['created_at']))
                db.execute('INSERT INTO collector_issue_events VALUES(?,?,?)',(row['id'],row['semantic'],row['payload_sha256']))
    CollectorIssueOutbox(path).pending()


def proof_receipt(path,workspace,identifier):
    """Validate persisted exact service proof before retrying a lost SSH ACK."""
    with closing(sqlite3.connect(path)) as db:
        row=db.execute('SELECT delivery_status,receipt FROM collection_outbox WHERE id=?',(identifier,)).fetchone()
        need(row is not None and row[0]=='ACKNOWLEDGED_OPENCLAW' and row[1] is not None)
        receipt=json.loads(row[1]);need(type(receipt) is dict and set(receipt)==_remote['RECEIPT_FIELDS']);checksum=receipt.get('content_sha256')
        need(type(checksum) is str and re.fullmatch('[a-f0-9]{64}',checksum))
        need(receipt.get('kind')=='openclaw_service_readback' and receipt.get('ok') is True and receipt.get('service_acknowledged') is True and receipt.get('ai_reviewed') is False)
        need(receipt.get('agent')==receipt.get('profile')==PROFILE and receipt.get('workspace')==str(workspace))
        relative='memory/partlawyer-public-issues/'+checksum+'.md'
        proof_relative='partlawyer-public-issues/service-readbacks/v2/'+PROFILE+'/'+checksum+'.json'
        need(receipt.get('content_file')==relative and receipt.get('evidence_file')==proof_relative)
        def read(relative):
            target=workspace/relative;need(target.resolve(strict=True).is_relative_to(workspace) and not target.is_symlink() and target.stat().st_size<=MAX_BYTES)
            return target.read_bytes()
        content=read(relative);evidence=read(proof_relative)
        need(sha256(content).hexdigest()==checksum and sha256(evidence).hexdigest()==receipt.get('evidence_sha256'))
        proof=json.loads(evidence);bundle=json.loads(content)
        need(proof.get('schema')=='partlawyer-openclaw-service-proof/v2' and proof.get('method')=='tools.invoke' and proof.get('tool')=='memory_get'
             and proof.get('agent')==proof.get('profile')==PROFILE and proof.get('path')==relative and proof.get('content_sha256')==checksum)
        response=proof['response'];details=response['output']['details']
        need(response.get('ok') is True and response.get('toolName')=='memory_get' and details.get('status')=='ok'
             and not any(details.get(k) for k in ['disabled','error','truncated']) and details.get('path')==relative and details.get('from')==1
             and details.get('text')==content.decode('utf8').removesuffix('\n'))
        need(set(bundle)=={'schema','scope','events','content_sha256s'} and bundle['schema']=='partlawyer-service-receipt/v1' and bundle['scope']=='public_government_collection_only')
        ids=[];hashes={}
        for event in bundle['events']:
            event_id=event['id'];need(event_id not in ids);ids.append(event_id)
            stored=db.execute('SELECT payload FROM collection_outbox WHERE id=?',(event_id,)).fetchone();need(stored is not None)
            need(bridge._public_event(stored[0],event_id)==event)
            hashes[event_id]=sha256(bridge._json({'schema':'partlawyer-public-issues/v1','scope':'public_government_collection_only','events':[event]})).hexdigest()
        need(ids==receipt.get('accepted_event_ids') and identifier in ids and hashes==bundle['content_sha256s'])
        return receipt


def relay(alias,remote_database,mirror,workspace,*,transport=exchange):
    mirror,workspace=validate_arguments(alias,remote_database,mirror,workspace)
    result={'status':'PENDING_OPENCLAW','model_calls':0,'remote_reconciled':0,'failed':0}
    try:
        need(bridge._configured_profile_workspace(PROFILE)==workspace)
        snapshot=transport(alias,{'action':'snapshot','path':remote_database,'limit':100})
        need(set(snapshot)=={'protocol','identity','rows','pending','acknowledged'} and snapshot['protocol']==PROTOCOL)
        need(type(snapshot['identity']) is dict and set(snapshot['identity'])=={'device','inode','uid'}
             and all(type(x) is int and x>=0 for x in snapshot['identity'].values()))
        need(type(snapshot['rows']) is list and len(snapshot['rows'])<=100 and type(snapshot['pending']) is int and snapshot['pending']>=len(snapshot['rows']))
        need(len({row['id'] for row in snapshot['rows']})==len(snapshot['rows']))
        result['remote_pending_before']=snapshot['pending']
        binding={'protocol':PROTOCOL,'alias':alias,'remote_path':remote_database,'identity':snapshot['identity']}
        prepare_mirror(mirror,binding,snapshot['rows'])
        if not snapshot['rows']:
            result.update(status='ACKNOWLEDGED_OPENCLAW' if snapshot['pending']==0 else 'PENDING_OPENCLAW',remote_pending_after=snapshot['pending']);return result
        # Only the existing full service read-back helper may create local ACKs.
        verification=bridge.verify_pending_with_openclaw(mirror,workspace,PROFILE,profile=PROFILE,record_receipts=True,limit=100,timeout=15)
        result['local_service_verified_this_round']=verification.get('service_verified',0)
        accepted=[]
        for row in snapshot['rows']:
            try:receipt=proof_receipt(mirror,workspace,row['id'])
            except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError):continue
            accepted.append({'id':row['id'],'payload_sha256':row['payload_sha256'],'receipt':receipt})
        if accepted:
            applied=transport(alias,{'action':'ack','path':remote_database,'identity':snapshot['identity'],'rows':accepted})
            need(set(applied)=={'protocol','reconciled','pending'} and applied['protocol']==PROTOCOL and applied['reconciled']==len(accepted))
            result.update(remote_reconciled=applied['reconciled'],remote_pending_after=applied['pending'])
        if len(accepted)!=len(snapshot['rows']) or verification.get('failed',0):result['failed']=1
        if not result['failed'] and result.get('remote_pending_after')==0:result['status']='ACKNOWLEDGED_OPENCLAW'
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error,subprocess.SubprocessError) as exc:
        result.update(failed=1,error_type=type(exc).__name__)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ['ssh-alias','remote-database','mirror','workspace']:parser.add_argument('--'+option,required=True)
    parser.add_argument('--interval',type=int,default=0,help='0 runs once; 5..3600 seconds retries future rounds without exiting on a failed round')
    args=parser.parse_args(argv)
    if args.interval!=0 and not 5<=args.interval<=3600:parser.error('interval must be 0 or 5..3600')
    try:
        validate_arguments(args.ssh_alias,args.remote_database,Path(args.mirror),Path(args.workspace))
        while True:
            report=relay(args.ssh_alias,args.remote_database,Path(args.mirror),Path(args.workspace));print(json.dumps(report),flush=True)
            if not args.interval:return 1 if report['failed'] else 0
            time.sleep(args.interval)
    except KeyboardInterrupt:return 0
    except (ValueError,OSError) as exc:
        print(json.dumps({'status':'PENDING_OPENCLAW','failed':1,'error_type':type(exc).__name__,'model_calls':0}));return 1


if __name__=='__main__':raise SystemExit(main())
