"""Conservative public collector issues and a dedicated durable pending outbox.

No browser, network, model, guide-store, worker or ACK operation is performed.
Callers must replay their already durable collector results after interruption.
One result's events and safe observation fingerprints commit in one transaction.
The first event payload is immutable; retries never invalidate external receipts.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import closing
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit,unquote

PENDING='PENDING_OPENCLAW'
ACKNOWLEDGED='ACKNOWLEDGED_OPENCLAW'
APP_ID=0x43495331
TABLES={'collector_issue_schema','collection_outbox','collector_issue_events','collector_issue_observations'}
PROVINCES=dict(zip(('beijing tianjin hebei shanxi neimenggu liaoning jilin heilongjiang shanghai jiangsu zhejiang anhui fujian jiangxi shandong henan hubei hunan guangdong guangxi hainan chongqing sichuan guizhou yunnan xizang shaanxi gansu qinghai ningxia xinjiang').split(),
                  ('11 12 13 14 15 21 22 23 31 32 33 34 35 36 37 41 42 43 44 45 46 50 51 52 53 54 61 62 63 64 65').split()))
MAIN_STATES={'auth_required':'AUTH_REQUIRED','captcha_required':'CAPTCHA_REQUIRED',
    'blocked':'GUIDE_PAGE_UNAVAILABLE','blank':'GUIDE_PAGE_UNAVAILABLE','network_failed':'GUIDE_PAGE_UNAVAILABLE',
    'runtime_failed':'GUIDE_PAGE_UNAVAILABLE','interrupted':'GUIDE_PAGE_UNAVAILABLE','http_failed':'GUIDE_PAGE_UNAVAILABLE',
    'guide_observed':'ONLINE_CHANNEL_UNVERIFIED','unverified':'ONLINE_CHANNEL_UNVERIFIED'}
ATTACHMENT_STATES={'downloaded':None,'unverified':None,'failed':'TEMPLATE_DOWNLOAD_FAILED',
                   'auth_required':'AUTH_REQUIRED','captcha_required':'CAPTCHA_REQUIRED'}
PUBLIC_FIELDS=frozenset('id type province city district region_code service keyword url occurred_at reason attempts final_status remediation'.split())
PERSONAL=re.compile(r'(?<!\d)(?:\d{17}[\dXx]|1[3-9]\d{9})(?!\d)')
SECRET_KEY=re.compile(r'token|nonce|secret|password|session|cookie|ticket|credential|authorization|csrf|signature|api_?key|^auth$|^sig$|^key$|^code$',re.I)
PRIVATE_PATH=re.compile(r'(?:^|/)(?:login|sso|oauth|passport|account|profile|private|session|upload)(?:[/.?_-]|$)',re.I)
FILE=re.compile(r'(?:page\.(?:txt|html|png)|failure\.png|materials\.png|attachment-[1-9][0-9]?\.(?:docx?|pdf|xlsx?))')
HEX=re.compile('[a-f0-9]{64}')


def _require(ok,message):
    if not ok:raise ValueError(message)


def _json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def _digest(value):return sha256(_json(value).encode('utf-8')).hexdigest()
def _groups(value):return '-'.join(value[i:i+8] for i in range(0,64,8))


def _region(value):
    _require(type(value) is dict and set(value)=={'province','city','district','region_code'},'Exact requested region fields required')
    _require(all(type(v) is str and v==v.strip() for v in value.values()),'Invalid requested region labels')
    _require(value['province'] in PROVINCES and re.fullmatch(r'[0-9]{6}(?:[0-9]{6})?',value['region_code'])
        and value['region_code'].startswith(PROVINCES[value['province']]),'Requested region code or province differs')
    for key in ['city','district']:
        _require(re.fullmatch(r'[\u3400-\u9fff·]{2,40}',value[key]) and re.search(r'(?:市|州|地区|盟|县|区|旗|林区|本级|行政区划)$',value[key]),'Administrative region labels required')
    return dict(value)


def _selectors(query,region):
    try:values=parse_qsl(query,keep_blank_values=True,max_num_fields=32)
    except ValueError:raise ValueError('Invalid public source selectors') from None
    output=[]
    for key,value in values:
        _require(not SECRET_KEY.search(key),'Authenticated source cannot become a public issue')
        pattern=None
        if key in {'areaCode','regionCode'}:
            pattern=r'[0-9]{6}(?:[0-9]{6})?'
            _require(value[:6]==region['region_code'][:6],'Public source selector differs from requested region')
        elif key=='localInnerCode':pattern=r'(?:[A-Fa-f0-9]{32}|[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12})'
        elif key in {'itemId','taskCode','qlCode','qlcode','qlbm','serviceCode','itemCode','iddept_ql_inf','iddept_yw_inf','id'}:pattern=r'[A-Za-z0-9_-]{1,128}'
        elif key in {'unid','uuid'}:pattern=r'[A-Fa-f0-9-]{32,36}'
        elif key in {'webId','ql_kind','infoType','type'}:pattern=r'[0-9]{1,6}'
        if pattern is not None:
            _require(re.fullmatch(pattern,value) and not PERSONAL.search(value),'Invalid public source selector')
            output.append((key,value))
        # Unknown values are neither copied nor hashed; they may contain identity.
    _require(len({k for k,v in output})==len(output),'Duplicate public source selectors')
    return sorted(output)


def _source(value,allowed_hosts,region):
    _require(type(allowed_hosts) in {tuple,list} and 1<=len(allowed_hosts)<=100
        and all(type(h) is str and re.fullmatch(r'[a-z0-9.-]+\.gov\.cn',h) for h in allowed_hosts),'Explicit official hosts required')
    _require(type(value) is str and 1<=len(value)<=3000 and value==value.strip()
        and not re.search(r'[\x00-\x20\\]',value) and not re.search(r'%(?![A-Fa-f0-9]{2})',value),'Invalid public source URL')
    try:parts=urlsplit(value);port=parts.port
    except ValueError:raise ValueError('Invalid public source URL') from None
    host=(parts.hostname or '').lower()
    _require(parts.scheme in {'http','https'} and host in allowed_hosts and host.endswith('.gov.cn')
        and not parts.username and not parts.password and port in {None,80 if parts.scheme=='http' else 443},'Configured public government source required')
    decoded=unquote(unquote(parts.path))
    _require(re.fullmatch(r'[/A-Za-z0-9_.~%+-]*',decoded) and '..' not in decoded.split('/')
        and not PRIVATE_PATH.search(decoded) and not PERSONAL.search(decoded) and ';' not in decoded
        and not re.search(r'\.(?:docx?|pdf|xlsx?|png|jpe?g)(?:/|$)',decoded,re.I),'Unsafe public source path')
    from regional_issue_delivery import public_source_url
    # Validate original query ambiguity before unknown fields are discarded.
    _require(public_source_url(value) is not None,'Public delivery source refused')
    query=_selectors(parts.query,region)
    route,separator,parameters=parts.fragment.partition('?');fragment=''
    if separator:
        selections=_selectors(parameters,region)
        if re.fullmatch(r'/[A-Za-z0-9/_-]{0,100}',route) and not PRIVATE_PATH.search(route) and selections:
            fragment=route+'?'+urlencode(selections)
    canonical=urlunsplit((parts.scheme,host,parts.path,urlencode(query),fragment))
    # The one delivery helper defines path-specific public selectors. It keeps
    # the complete own guide URL and removes cross-path/unknown values from both
    # the new DTO and semantic SHA. Sorting above keeps harmless query order stable.
    canonical=public_source_url(canonical)
    _require(canonical is not None,'Public delivery source refused')
    return canonical,_digest(canonical),canonical


def _time(job,result):
    value=next((x for x in [result.get('observed_at'),result.get('completed_at'),job.get('updated_at'),job.get('created_at')] if x is not None),None)
    _require(type(value) is str and len(value)<=40,'Explicit observation timestamp required')
    try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise ValueError('Invalid observation timestamp') from None
    _require(parsed.tzinfo is not None and 2000<=parsed.year<=2100,'Aware observation timestamp required')
    return parsed.astimezone(timezone.utc).isoformat(timespec='seconds')


def _evidence(result,evidence_root):
    values=result.get('evidence',[])
    _require(type(values) is list and len(values)<=32,'Bounded collector evidence required')
    if not values:return _digest([]),0
    _require(evidence_root is not None,'Explicit evidence root required to verify fingerprints')
    raw_root=Path(evidence_root);root=raw_root.resolve(strict=True)
    _require(raw_root.is_absolute() and raw_root==root and root.is_dir(),'Explicit nonsymlink evidence directory required')
    safe=[]
    for item in values:
        _require(type(item) is dict and type(item.get('file')) is str and FILE.fullmatch(item['file'])
            and type(item.get('bytes')) is int and 0<=item['bytes']<=64*1024*1024
            and type(item.get('sha256')) is str and HEX.fullmatch(item['sha256']),'Invalid evidence fingerprint metadata')
        path=(root/item['file']).resolve(strict=True)
        _require(path.parent==root and path.name==item['file'] and path.is_file() and not (root/item['file']).is_symlink(),'Evidence file escaped its explicit directory')
        _require(path.stat().st_size==item['bytes'],'Evidence size differs')
        checksum=sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):checksum.update(chunk)
        _require(checksum.hexdigest()==item['sha256'],'Evidence hash differs')
        safe.append({'kind':item['file'],'bytes':item['bytes'],'sha256':item['sha256']})
    _require(len({x['kind'] for x in safe})==len(safe),'Duplicate collector evidence')
    return _digest(sorted(safe,key=lambda x:x['kind'])),len(safe)


def _drafts(job,result,allowed_hosts,evidence_root):
    _require(type(job) is dict,'Collector job object required')
    if result is None:result=job.get('result')
    if result is None:return []
    _require(type(result) is dict and type(result.get('state')) is str and result['state'] in MAIN_STATES,'Only known observed collector states accepted')
    _require(type(job.get('id')) is str and re.fullmatch('[a-f0-9]{32}',job['id'])
        and type(job.get('attempt')) is int and 1<=job['attempt']<=2,'Collector job identity and bounded attempt required')
    region=_region(job.get('region'));url,source_sha,canonical=_source(job.get('url'),allowed_hosts,region)
    if 'region' in result:_require(_region(result['region'])==region,'Observed region differs from requested region')
    if 'requested_url' in result:_require(_source(result['requested_url'],allowed_hosts,region)[2]==canonical,'Observed source differs from requested source')
    status=result.get('http_status')
    _require(status is None or type(status) is int and 100<=status<=599,'Invalid observed HTTP status')
    _require(result['state']!='http_failed' or status is not None and status>=400,'HTTP failure requires an observed failure status')
    evidence_sha,evidence_count=_evidence(result,evidence_root);observed_at=_time(job,result)
    attachments=result.get('attachments',[])
    _require(type(attachments) is list and len(attachments)<=12,'Bounded attachment observations required')
    subjects=[('page',result['state'],MAIN_STATES[result['state']])]
    for index,item in enumerate(attachments,1):
        _require(type(item) is dict and type(item.get('state')) is str and item['state'] in ATTACHMENT_STATES,'Only known attachment observations accepted')
        kind=ATTACHMENT_STATES[item['state']]
        if kind:subjects.append(('attachment-'+str(index),item['state'],kind))
    output=[]
    for subject,state,kind in subjects:
        semantic={'policy':'collector-public-issues/v1','region':region,'source':canonical,'type':kind,'subject':subject}
        identifier='collector-issue-v1-'+_groups(_digest(semantic))
        boundary=kind in {'AUTH_REQUIRED','CAPTCHA_REQUIRED'}
        reason={'AUTH_REQUIRED':'公开采集停在登录边界；未登录、未提交，登录后办理能力尚未核实。',
            'CAPTCHA_REQUIRED':'公开采集遇到验证码或人机核验；已停止，未处理验证或提交申请。',
            'GUIDE_PAGE_UNAVAILABLE':'本轮公开页面采集未完成；不据此判定事项不存在或官网持续不可用。',
            'ONLINE_CHANNEL_UNVERIFIED':'本轮仅有公开页面观察，网上办理入口和登录后能力尚未核实；不认定不支持网上办理。',
            'TEMPLATE_DOWNLOAD_FAILED':'本轮公开附件下载未完成；附件类别尚待人工核对，不认定模板缺失。'}[kind]
        event={'id':identifier,'type':kind,**region,'service':'劳动人事争议仲裁申请','keyword':'公开采集观察待核对',
            'url':url,'occurred_at':observed_at,'reason':reason+' 公开来源SHA256[8x8]='+_groups(source_sha)+'；证据集合SHA256[8x8]='+_groups(evidence_sha)+'。',
            'attempts':job['attempt'],'final_status':'manual_authorization' if boundary else 'pending_recheck',
            'remediation':'由用户自行在官方渠道处理认证或核验；不绕过边界，不代交申请。' if boundary else '保留公开来源和采集指纹，由人工核对后安排受限重试；不套用其他地区附件。'}
        observation={'job_fingerprint':_digest(job['id']),'attempt':job['attempt'],'state':state,'subject':subject,
            'http_status':status,'observed_at':observed_at,'source_sha256':source_sha,'evidence_sha256':evidence_sha,'evidence_count':evidence_count}
        observation_id=_digest({k:v for k,v in observation.items() if k!='observed_at'}|{'issue_id':identifier})
        output.append((event,semantic,observation_id,observation))
    return output


def build_issue_events(job,result=None,*,allowed_hosts,evidence_root=None):
    """Return only the existing public issue DTO, never raw capture/result text."""
    return [deepcopy(row[0]) for row in _drafts(job,result,allowed_hosts,evidence_root)]


SCHEMA=[
    'CREATE TABLE collector_issue_schema(version INTEGER PRIMARY KEY)',
    'INSERT INTO collector_issue_schema VALUES(1)',
    'CREATE TABLE collection_outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL,delivery_status TEXT NOT NULL,receipt TEXT,created_at TEXT NOT NULL)',
    'CREATE TABLE collector_issue_events(event_id TEXT PRIMARY KEY REFERENCES collection_outbox(id),semantic TEXT NOT NULL,payload_sha256 TEXT NOT NULL)',
    'CREATE TABLE collector_issue_observations(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES collection_outbox(id),observation TEXT NOT NULL)']


def _schema(db,empty=False):
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    app=db.execute('PRAGMA application_id').fetchone()[0];version=db.execute('PRAGMA user_version').fetchone()[0]
    if empty and not names and app==version==0:return False
    _require(names==TABLES and app==APP_ID and version==1,'Only this dedicated collector issue database may be written')
    _require(db.execute('SELECT version FROM collector_issue_schema').fetchall()==[(1,)],'Collector issue schema differs')
    _require(not db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view') LIMIT 1").fetchone(),'Unexpected issue database executable schema')
    return True


def _insert_observation(db,identifier,event_id,observation):
    return db.execute('INSERT INTO collector_issue_observations(id,event_id,observation) VALUES(?,?,?) ON CONFLICT(id) DO NOTHING',
                      (identifier,event_id,_json(observation))).rowcount


def _stored_event(db,identifier,payload):
    meta=db.execute('SELECT semantic,payload_sha256 FROM collector_issue_events WHERE event_id=?',(identifier,)).fetchone()
    _require(meta is not None and type(payload) is str and sha256(payload.encode()).hexdigest()==meta[1],
             'Stored immutable public issue checksum differs')
    _require(identifier=='collector-issue-v1-'+_groups(_digest(json.loads(meta[0]))),'Stored issue identity differs')
    event=json.loads(payload)
    _require(type(event) is dict and set(event)==PUBLIC_FIELDS and event.get('id')==identifier,'Stored public issue shape differs')
    return event


class CollectorIssueOutbox:
    """Explicit dedicated DB only. Existing legacy/guide/queue DBs are refused."""
    def __init__(self,database):
        _require(isinstance(database,(str,os.PathLike)) and str(database).strip(),'Explicit issue outbox path required')
        raw=Path(database)
        _require(raw.is_absolute() and raw.resolve()==raw and raw.parent.is_dir(),'Absolute nonsymlink issue outbox path and existing parent required')
        _require(raw.name.lower() not in {'regional-guides.sqlite','regional-guides.sqlite3','regional-directory.sqlite','queue.sqlite3','partlawyer.db'}
            and not any(a.lower()=='backend' and b.lower()=='data' for a,b in zip(raw.parts,raw.parts[1:])), 'Dedicated issue outbox cannot be a guide/worker/application store')
        self.path=raw

    def _connect(self,mode):
        return sqlite3.connect(self.path.as_uri()+'?mode='+mode,uri=True,timeout=15,isolation_level=None)

    def _initialize(self):
        if self.path.exists():
            with closing(self._connect('ro')) as db:_schema(db,empty=True)
        else:
            try:
                descriptor=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(descriptor)
            except FileExistsError:pass
        db=self._connect('rw')
        try:
            _schema(db,empty=True)  # Recheck before any persistent PRAGMA change.
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            try:
                if not _schema(db,empty=True):
                    for statement in SCHEMA:db.execute(statement)
                    db.execute('PRAGMA application_id='+str(APP_ID));db.execute('PRAGMA user_version=1')
                _schema(db);db.commit()
            except BaseException:db.rollback();raise
        finally:db.close()

    def record_result(self,job,result=None,*,allowed_hosts,evidence_root=None):
        drafts=_drafts(job,result,allowed_hosts,evidence_root)
        if not drafts:return {'inserted':0,'observations_inserted':0,'events':[],'model_calls':0}
        self._initialize();db=self._connect('rw');events=[];inserted=observations=0
        try:
            db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            try:
                _schema(db)
                for event,semantic,observation_id,observation in drafts:
                    identifier=event['id'];row=db.execute('SELECT payload,delivery_status FROM collection_outbox WHERE id=?',(identifier,)).fetchone()
                    if row is None:
                        payload=_json(event)
                        db.execute('INSERT INTO collection_outbox(id,payload,delivery_status,receipt,created_at) VALUES(?,?,?,NULL,?)',(identifier,payload,PENDING,event['occurred_at']))
                        db.execute('INSERT INTO collector_issue_events VALUES(?,?,?)',(identifier,_json(semantic),sha256(payload.encode()).hexdigest()))
                        stored,status=event,PENDING;inserted+=1
                    else:
                        meta=db.execute('SELECT semantic,payload_sha256 FROM collector_issue_events WHERE event_id=?',(identifier,)).fetchone()
                        _require(meta is not None and meta[0]==_json(semantic) and sha256(row[0].encode()).hexdigest()==meta[1]
                            and row[1] in {PENDING,ACKNOWLEDGED},'Existing immutable issue changed; preserved without overwrite')
                        stored=_stored_event(db,identifier,row[0])
                        _require(stored['url']==event['url'],
                            'Existing immutable issue URL projection differs; preserved without overwrite')
                        status=row[1]
                    observations+=_insert_observation(db,observation_id,identifier,observation)
                    events.append({**stored,'delivery_status':status})
                db.commit()
            except BaseException:db.rollback();raise
        finally:db.close()
        return {'inserted':inserted,'observations_inserted':observations,'events':events,'model_calls':0}

    def pending(self,limit=1000):
        _require(type(limit) is int and 1<=limit<=10000,'Bounded pending limit required')
        if not self.path.exists():return []
        db=self._connect('ro')
        try:
            _schema(db)
            return [{**_stored_event(db,identifier,payload),'delivery_status':PENDING} for identifier,payload in db.execute('SELECT id,payload FROM collection_outbox WHERE delivery_status=? ORDER BY created_at,id LIMIT ?',(PENDING,limit))]
        finally:db.close()

    def summary(self):
        if not self.path.exists():return {'events':0,'pending':0,'acknowledged':0,'observations':0,'model_calls':0}
        db=self._connect('ro')
        try:
            _schema(db);counts=dict(db.execute('SELECT delivery_status,COUNT(*) FROM collection_outbox GROUP BY delivery_status'))
            return {'events':sum(counts.values()),'pending':counts.get(PENDING,0),'acknowledged':counts.get(ACKNOWLEDGED,0),
                'observations':db.execute('SELECT COUNT(*) FROM collector_issue_observations').fetchone()[0],'model_calls':0}
        finally:db.close()
