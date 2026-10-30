"""Model-free, bounded public-guide collection with persistent Linux state.

This queue records observations, never publishes legal guidance or absence claims.
Only an explicitly configured worker can visit pages; importing has no side effects.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import uuid


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sensitive_query_key(key):
    return bool(re.search(r'token|nonce|secret|password|session|cookie|ticket|credential|authorization|csrf|signature|api_?key|^auth$|^sig$|^key$|^code$',key,re.I))


def public_url(value):
    parsed=urlsplit(value)
    query=[(k,v) for k,v in parse_qsl(parsed.query) if not sensitive_query_key(k)]
    fragment=parsed.fragment
    if '?' in fragment:
        route,params=fragment.split('?',1)
        fragment=route+'?'+urlencode([(k,v) for k,v in parse_qsl(params) if not sensitive_query_key(k)])
    elif any(sensitive_query_key(k) for k,_ in parse_qsl(fragment)):fragment=''
    return urlunsplit((parsed.scheme,parsed.hostname or '',re.split(';jsessionid=',parsed.path,flags=re.I)[0],urlencode(query),fragment))


def save_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
    temporary.replace(path)


@dataclass(frozen=True)
class CollectorConfig:
    data_dir: Path
    release_dir: Path
    browser_executable: Path
    allowed_hosts: tuple[str, ...]
    capacity: int = 128
    batch_limit: int = 32
    max_attempts: int = 2
    min_interval_seconds: float = 5
    job_timeout_seconds: float = 120
    navigation_timeout_seconds: float = 45
    max_attachments: int = 6
    max_attachment_bytes: int = 20 * 1024 * 1024
    issue_outbox: Path | None = None

    def __post_init__(self):
        for name in ('data_dir', 'release_dir', 'browser_executable'):
            if not Path(getattr(self,name)).expanduser().is_absolute():
                raise ValueError('Collector paths must be absolute')
            object.__setattr__(self, name, Path(getattr(self, name)).expanduser().resolve())
        if self.data_dir == self.release_dir or self.data_dir.is_relative_to(self.release_dir):
            raise ValueError('Collector state must be outside the immutable release')
        if self.issue_outbox is not None:
            issue=Path(self.issue_outbox).expanduser()
            if (not issue.is_absolute() or issue.resolve()!=issue or issue.is_relative_to(self.release_dir)
                    or issue==self.data_dir/'queue.sqlite3' or issue.is_relative_to(self.data_dir/'evidence')
                    or issue.name.lower() in {'regional-guides.sqlite','regional-guides.sqlite3','regional-directory.sqlite','queue.sqlite3','partlawyer.db'}
                    or any(a.lower()=='backend' and b.lower()=='data' for a,b in zip(issue.parts,issue.parts[1:]))):
                raise ValueError('Explicit dedicated issue outbox must stay outside the release, queue and evidence')
            if not issue.parent.is_dir() and not issue.parent.is_relative_to(self.data_dir):
                raise ValueError('Issue outbox outside collector state needs an existing parent')
            object.__setattr__(self,'issue_outbox',issue)
        if not self.allowed_hosts or any(not re.fullmatch(r'[a-z0-9.-]+\.gov\.cn', h) for h in self.allowed_hosts):
            raise ValueError('Explicit official allowed_hosts required')
        if not (1 <= self.capacity <= 1000 and 1 <= self.batch_limit <= 32 and
                1 <= self.max_attempts <= 2 and 0 <= self.min_interval_seconds <= 3600 and
                10 <= self.job_timeout_seconds <= 300 and 1 <= self.navigation_timeout_seconds <= 90 and
                0 <= self.max_attachments <= 12 and 1 <= self.max_attachment_bytes <= 50*1024*1024):
            raise ValueError('Collector bounds are invalid')

    @classmethod
    def load(cls, path, release_dir):
        config_path = Path(path).expanduser().resolve()
        release = Path(release_dir).resolve()
        if config_path.is_relative_to(release):
            raise ValueError('Collector configuration must be outside the immutable release')
        values = json.loads(config_path.read_text(encoding='utf8'))
        values['release_dir'] = release
        values['allowed_hosts'] = tuple(values['allowed_hosts'])
        return cls(**values)

    def validate_url(self, url, *, resource=False):
        if not isinstance(url, str) or len(url) > 3000:
            raise ValueError('Invalid official URL')
        try:
            parsed = urlsplit(url)
            valid_port = parsed.port in (None, 80 if parsed.scheme == 'http' else 443)
        except ValueError as exc:
            raise ValueError('Invalid official URL') from exc
        host = (parsed.hostname or '').lower()
        fragment_query=parsed.fragment.split('?',1)[-1]
        if any(sensitive_query_key(key) for key,_ in parse_qsl(parsed.query)+parse_qsl(fragment_query)) or re.search(r';jsessionid=',parsed.path,re.I):
            raise ValueError('Authenticated URLs cannot enter the public collector')
        if (parsed.scheme not in ('https', 'http') or not host.endswith('.gov.cn') or
                parsed.username or parsed.password or not valid_port or
                (not resource and host not in self.allowed_hosts)):
            raise ValueError('Only configured public official URLs are allowed')
        return url


class GuideQueue:
    def __init__(self, config):
        self.config = config
        self.root = config.data_dir
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database = self.root / 'queue.sqlite3'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, url TEXT NOT NULL, region TEXT NOT NULL,
                state TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, result TEXT)''')
            db.execute('''CREATE TABLE IF NOT EXISTS job_observations (
                job_id TEXT NOT NULL, attempt INTEGER NOT NULL, source_url TEXT NOT NULL,
                region TEXT NOT NULL, result TEXT NOT NULL, recorded_at TEXT NOT NULL,
                issue_state TEXT NOT NULL DEFAULT 'pending', issue_error_type TEXT,
                PRIMARY KEY(job_id,attempt))''')
        if os.name == 'posix': self.database.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:yield db
        finally:db.close()

    @staticmethod
    def _job(row):
        job = dict(row)
        job['region'] = json.loads(job['region'])
        job['result'] = json.loads(job['result']) if job.get('result') else None
        return job

    def submit(self, entries):
        if not isinstance(entries, list) or not 1 <= len(entries) <= self.config.batch_limit:
            raise ValueError('Explicit URL batch limit exceeded')
        normalized = []
        for entry in entries:
            url = self.config.validate_url(entry.get('url'))
            region = entry.get('region', {})
            if not isinstance(region,dict) or set(region)-{'province','city','district','region_code'}:
                raise ValueError('Explicit region fields are required')
            if any(not isinstance(v,str) or len(v)>80 or re.search(r'[\x00-\x1f]',v) for v in region.values()):
                raise ValueError('Invalid region label')
            if any(not region.get(k,'').strip() for k in ('province','city','district')) or not re.fullmatch('[0-9]{6,12}',region.get('region_code','')):
                raise ValueError('Explicit province, city, district and numeric region_code are required')
            region=json.dumps({k:region.get(k,'') for k in ('province','city','district','region_code')},ensure_ascii=False,sort_keys=True)
            normalized.append((url, region))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            output = []
            for url, region in normalized:
                previous = db.execute("SELECT * FROM jobs WHERE url=? AND region=? AND state IN ('queued','running')", (url, region)).fetchone()
                if previous:
                    output.append(self._job(previous)); continue
                active = db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]
                if active >= self.config.capacity: raise ValueError('Queue capacity reached')
                identifier = uuid.uuid4().hex
                db.execute('INSERT INTO jobs(id,url,region,state,created_at,updated_at) VALUES (?,?,?,\'queued\',?,?)', (identifier,url,region,now(),now()))
                output.append(self._job(db.execute('SELECT * FROM jobs WHERE id=?',(identifier,)).fetchone()))
            return output

    def get(self, identifier):
        if not re.fullmatch('[a-f0-9]{32}', identifier): raise ValueError('Invalid job identifier')
        with self.connect() as db: row = db.execute('SELECT * FROM jobs WHERE id=?',(identifier,)).fetchone()
        if row is None: raise FileNotFoundError('Collector job not found')
        return self._job(row)

    def summary(self):
        with self.connect() as db:
            counts = {r[0]:r[1] for r in db.execute('SELECT state,count(*) FROM jobs GROUP BY state')}
            rows = db.execute('SELECT * FROM jobs ORDER BY created_at DESC,rowid DESC LIMIT 100').fetchall()
        heartbeat = self.root/'worker.json'
        worker = json.loads(heartbeat.read_text(encoding='utf8')) if heartbeat.is_file() else None
        if worker:
            try:
                proc=Path('/proc')/str(worker['pid'])
                worker['alive']=(proc.stat().st_uid==os.getuid() and
                    proc.joinpath('stat').read_text().split()[21]==worker.get('process_start_ticks'))
            except (OSError,KeyError,AttributeError):worker['alive']=False
            if not worker['alive'] and worker['state']!='stopped':worker['state']='interrupted'
        return {'counts':counts, 'items':[self._job(r) for r in rows], 'worker':worker,
                'concurrency':1, 'capacity':self.config.capacity, 'model_used':False}

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM jobs WHERE state='queued' AND attempt<? ORDER BY rowid LIMIT 1", (self.config.max_attempts,)).fetchone()
            if row is None:return None
            db.execute("UPDATE jobs SET state='running',attempt=attempt+1,updated_at=? WHERE id=?",(now(),row['id']))
            return self._job(db.execute('SELECT * FROM jobs WHERE id=?',(row['id'],)).fetchone())

    def finish(self, identifier, result):
        job=self.get(identifier)
        if job['state']!='running':raise ValueError('Job is not running')
        if not isinstance(result,dict):raise ValueError('Collector result must be an object')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            stamp=now();encoded=json.dumps(result,ensure_ascii=False)
            changed = db.execute("UPDATE jobs SET state='complete',result=?,updated_at=? WHERE id=? AND state='running' AND attempt=?",(encoded,stamp,identifier,job['attempt'])).rowcount
            if not changed:raise ValueError('Job is not running')
            self._journal_observation(db,job,encoded,stamp)
        # Never call an external writer before durable queue/result history.
        with self.connect() as db:
            observation=dict(db.execute('SELECT * FROM job_observations WHERE job_id=? AND attempt=?',(identifier,job['attempt'])).fetchone())
        report=self._persist_issue_observation(observation)
        # The historical private review JSON is secondary to both durable ledgers.
        # Its filesystem failure must never discard a completed observation.
        try:
            outbox=self.root/'outbox';outbox.mkdir(exist_ok=True,mode=0o700)
            save_json(outbox/(identifier+'-'+str(job['attempt'])+'.json'),{
                'schema_version':1,'job_id':identifier,'attempt':job['attempt'],'state':'pending_review',
                'source_url':job['url'],'region':job['region'],'observed_at':result.get('observed_at',now()),
                'observation_state':result.get('state','unverified'),'service_absent':False,
                'review_required':True,'attachment_template_match':'unknown_until_review',
                'evidence':[{'file':x['file'],'sha256':x['sha256'],'bytes':x['bytes']} for x in result.get('evidence',[])],
                'notes':'Public browser observation only; failures do not prove absence. No case or account data.'})
            report['review_proposal_written']=True
        except (OSError,ValueError,KeyError,TypeError):
            report['review_proposal_written']=False
        return report

    @staticmethod
    def _journal_observation(db,job,result,stamp):
        region=job['region'] if isinstance(job['region'],str) else json.dumps(job['region'],ensure_ascii=False)
        return db.execute('''INSERT INTO job_observations(job_id,attempt,source_url,region,result,recorded_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(job_id,attempt) DO NOTHING''',
            (job['id'],job['attempt'],job['url'],region,result,stamp)).rowcount

    @staticmethod
    def _issue_region(region):
        # Exact administrative aliases only. Never rewrite queue/source history
        # or infer a province, city or district from other places' facts.
        from collector_issue_events import PROVINCES
        names=('北京市 天津市 河北省 山西省 内蒙古自治区 辽宁省 吉林省 黑龙江省 上海市 江苏省 浙江省 安徽省 福建省 江西省 山东省 河南省 湖北省 湖南省 广东省 广西壮族自治区 海南省 重庆市 四川省 贵州省 云南省 西藏自治区 陕西省 甘肃省 青海省 宁夏回族自治区 新疆维吾尔自治区').split()
        aliases=dict(zip(names,PROVINCES))
        output=dict(region)
        if type(output.get('province')) is str:output['province']=aliases.get(output['province'],output['province'])
        return output

    def _issue_store(self):
        from collector_issue_events import CollectorIssueOutbox
        path=self.config.issue_outbox
        if path is None:return None
        if path.resolve()!=path:raise ValueError('Issue outbox path changed')
        if not path.parent.is_dir():
            if not path.parent.is_relative_to(self.root):raise ValueError('Issue outbox parent unavailable')
            path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        return CollectorIssueOutbox(path)

    def _mark_issue_observation(self,observation,state,error_type=None):
        with self.connect() as db:
            db.execute('UPDATE job_observations SET issue_state=?,issue_error_type=? WHERE job_id=? AND attempt=?',
                       (state,error_type,observation['job_id'],observation['attempt']))

    def _persist_issue_observation(self,observation):
        report={'enabled':self.config.issue_outbox is not None,'new_events':0,'new_observations':0,
                'failed':0,'rejected':0,'sync_performed':False,'model_calls':0}
        if self.config.issue_outbox is None:
            self._mark_issue_observation(observation,'disabled');return report
        try:
            result=json.loads(observation['result']);region=self._issue_region(json.loads(observation['region']))
            if isinstance(result,dict) and isinstance(result.get('region'),dict):
                result={**result,'region':self._issue_region(result['region'])}
            job={'id':observation['job_id'],'attempt':observation['attempt'],'url':observation['source_url'],
                 'region':region,'updated_at':observation['recorded_at'],'result':result}
            raw=self.root/'evidence'/job['id']/('attempt-'+str(job['attempt']))
            folder=raw.resolve()
            if folder!=raw or not folder.is_relative_to(self.root):raise ValueError('Evidence directory changed')
            persisted=self._issue_store().record_result(job,allowed_hosts=self.config.allowed_hosts,evidence_root=folder)
            self._mark_issue_observation(observation,'outbox_persisted')
            report.update(new_events=persisted['inserted'],new_observations=persisted['observations_inserted'])
        except Exception as exc:
            rejected=isinstance(exc,ValueError);kind=type(exc).__name__
            if not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,79}',kind):kind='Error'
            self._mark_issue_observation(observation,'rejected' if rejected else 'error',kind)
            report.update(failed=1,rejected=int(rejected))
        return report

    def replay_issue_events(self):
        """Backfill durable nonrunning results; replay all snapshots idempotently.

        Replaying even persisted snapshots repairs a lost/replaced dedicated
        outbox, while the immutable issue writer preserves existing service ACKs.
        No workspace export, gateway, model, browser or task import occurs here.
        """
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');backfilled=0
            for row in db.execute("SELECT * FROM jobs WHERE result IS NOT NULL AND attempt>0 AND state!='running' ORDER BY rowid").fetchall():
                backfilled+=self._journal_observation(db,dict(row),row['result'],row['updated_at'])
            upper=db.execute('SELECT COALESCE(MAX(rowid),0) FROM job_observations').fetchone()[0]
        report={'enabled':self.config.issue_outbox is not None,'backfilled':backfilled,'processed':0,
                'new_events':0,'new_observations':0,'failed':0,'rejected':0,'sync_performed':False,'model_calls':0}
        if not report['enabled']:return report
        after=0
        while after<upper:
            with self.connect() as db:
                rows=db.execute('SELECT rowid AS observation_rowid,* FROM job_observations WHERE rowid>? AND rowid<=? ORDER BY rowid LIMIT 100',(after,upper)).fetchall()
            if not rows:break
            for row in rows:
                outcome=self._persist_issue_observation(dict(row));report['processed']+=1
                for key in ['new_events','new_observations','failed','rejected']:report[key]+=outcome[key]
                after=row['observation_rowid']
        return report

    def issue_event_status(self):
        with self.connect() as db:counts={r[0]:r[1] for r in db.execute('SELECT issue_state,COUNT(*) FROM job_observations GROUP BY issue_state')}
        return {'enabled':self.config.issue_outbox is not None,'observations':sum(counts.values()),'states':counts,
                'sync_performed':False,'model_calls':0}

    def retry(self, identifier):
        self.get(identifier)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            active = db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]
            if active >= self.config.capacity:raise ValueError('Queue capacity reached')
            changed = db.execute("UPDATE jobs SET state='queued',updated_at=? WHERE id=? AND state='complete' AND attempt<?", (now(),identifier,self.config.max_attempts)).rowcount
            if not changed:raise ValueError('Job cannot retry: state or attempt limit')
        return self.get(identifier)

    def cancel(self, identifier):
        self.get(identifier)
        with self.connect() as db:
            changed=db.execute("UPDATE jobs SET state='cancelled',updated_at=? WHERE id=? AND state='queued'",(now(),identifier)).rowcount
            if not changed:raise ValueError('Only queued jobs can be cancelled')
        return self.get(identifier)

    def recover_interrupted(self):
        # Called only while holding the exclusive worker lock, never by readers.
        with self.connect() as db:
            rows=db.execute("SELECT * FROM jobs WHERE state='running'").fetchall()
            for row in rows:
                state='queued' if row['attempt']<self.config.max_attempts else 'complete'
                stamp=now();result=json.dumps({'state':'interrupted','service_verified':False,'error':'Worker exited before persisting a result'})
                db.execute('UPDATE jobs SET state=?,result=?,updated_at=? WHERE id=?',(state,result,stamp,row['id']))
                self._journal_observation(db,dict(row),result,stamp)
            return len(rows)


@contextmanager
def worker_lock(root):
    if sys.platform != 'linux': raise RuntimeError('Official collector worker requires Linux; no Windows executor')
    import fcntl
    with (Path(root)/'worker.lock').open('a+') as handle:
        try:fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:raise RuntimeError('Collector worker is already running') from exc
        handle.seek(0);handle.truncate();handle.write(str(os.getpid()));handle.flush()
        try:yield
        finally:fcntl.flock(handle,fcntl.LOCK_UN)


def evidence_manifest(folder):
    return [{'file':str(p.relative_to(folder)).replace('\\','/'), 'bytes':p.stat().st_size,
             'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='result.json']


def classify_observation(text, status, *, main_frame_auth=False):
    if main_frame_auth:return 'auth_required'
    if re.search(r'验证码|人机验证|安全验证',text[:12000]):return 'captcha_required'
    if re.search(r'Access Denied|访问过于频繁', text[:12000], re.I):return 'blocked'
    if status and status >= 400:return 'http_failed'
    if len(text.strip()) < 15:return 'blank'
    if re.search(r'劳动.{0,10}争议.{0,5}仲裁|劳动仲裁',text) and re.search('办理材料|申报材料|申请材料|材料目录',text) and '办理流程' in text:return 'guide_observed'
    return 'unverified'


def record_auth_boundary(result,url,*,main_frame):
    parsed=urlsplit(url)
    boundary=urlunsplit((parsed.scheme,parsed.hostname or '',parsed.path,'',''))
    if main_frame:result['auth_boundary_url']=boundary
    else:result.setdefault('blocked_auth_frames',[]).append({'url':boundary,'state':'blocked_anonymous_auth_check'})


async def public_destination(config,url,*,navigation,cache,document_active=False):
    try:
        observed_document=document_active and re.search(r'\.(docx?|pdf|xlsx?)(?:[?#]|$)',url,re.I)
        config.validate_url(url,resource=not navigation or bool(observed_document))
        host=urlsplit(url).hostname
        if host not in cache:
            records=await asyncio.to_thread(socket.getaddrinfo,host,None,type=socket.SOCK_STREAM)
            cache[host]=bool(records) and all(ipaddress.ip_address(r[4][0]).is_global for r in records)
        return cache[host]
    except (ValueError,OSError):return False


def store_attachment(config,folder,index,body,record):
    from portal_attachment_downloads import file_type
    if len(body)>config.max_attachment_bytes:raise ValueError('Attachment exceeds configured bound')
    extension=file_type(body)
    if not extension:raise ValueError('Response is not a recognized document')
    final=folder/('attachment-'+str(index)+extension)
    final.write_bytes(body)
    record.update(state='downloaded',file=final.name,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),observed_at=now(),template_kind='unknown_until_review')


async def capture_response_document(config,responses,folder,index,record):
    for response in reversed(responses):
        if not await public_destination(config,response.url,navigation=False,cache={}):continue
        try:
            length=int(response.headers.get('content-length','0'))
            if length>config.max_attachment_bytes:continue
            data=await asyncio.wait_for(response.body(),8)
            store_attachment(config,folder,index,data,record)
            record.update(source_url=public_url(response.url),capture_method='browser_response')
            return True
        except Exception:continue
    return False


class ClickDocumentRequests:
    """Freeze the clicked control's request window before considering fallbacks."""
    def __init__(self):self._urls=[];self._frozen=False
    def add(self,url):
        if not self._frozen and re.search(r'\.(docx?|pdf|xlsx?)(?:[?#]|$)',url,re.I) and url not in self._urls:
            self._urls.append(url)
    def freeze(self):self._frozen=True
    @property
    def urls(self):return tuple(self._urls)


def material_anchor(anchor):
    return bool(re.search(r'\.(docx?|pdf|xlsx?)(?:[?#]|$)',anchor.get('url',''),re.I) and
                re.search('申请书|证据清单|证据目录|表格|材料',anchor.get('label','')) and
                not re.search('指南下载|下载指南|仲裁法|劳动合同法|劳动法',anchor.get('label','')))


async def click_document_control(config,page,target,record,folder,index):
    responses=[]
    requests=ClickDocumentRequests()
    existing_pages=set(page.context.pages)
    def response_seen(response):
        if response.url in requests.urls:responses.append(response)
    def request_seen(request):
        try:
            if request.frame.page==page or request.frame.page not in existing_pages:requests.add(request.url)
        except Exception:pass
    page.context.on('response',response_seen)
    page.context.on('request',request_seen)
    scratch=folder/('pending-'+str(index))
    try:
        try:
            async with page.expect_download(timeout=18000) as event:
                await target.click(timeout=5000)
                await page.wait_for_timeout(500)
                requests.freeze()
            download=await event.value
        except Exception:
            requests.freeze()
            record['initial_control_result']='no_browser_download_event'
            if await capture_response_document(config,responses,folder,index,record):return
            # Some public controls load a Word document as a subresource and
            # Chromium correctly blocks it with ORB. Open only the exact public
            # document URL observed from that click as a normal navigation.
            for url in requests.urls[:1]:
                if not await public_destination(config,url,navigation=False,cache={}):continue
                tab=await page.context.new_page()
                try:
                    async with tab.expect_download(timeout=12000) as event:
                        try:await tab.goto(url,timeout=12000)
                        except Exception as exc:
                            if 'Download is starting' not in str(exc):raise
                    download=await event.value
                    await asyncio.wait_for(download.save_as(str(scratch)),15)
                    if scratch.stat().st_size>config.max_attachment_bytes:raise ValueError('Attachment exceeds configured bound')
                    store_attachment(config,folder,index,scratch.read_bytes(),record)
                    record.update(source_url=public_url(url),capture_method='observed_document_navigation')
                    return
                except Exception:pass
                finally:await tab.close()
            raise
        await asyncio.wait_for(download.save_as(str(scratch)),20)
        if scratch.stat().st_size>config.max_attachment_bytes:raise ValueError('Attachment exceeds configured bound')
        body=scratch.read_bytes()
        store_attachment(config,folder,index,body,record)
        record['capture_method']='browser_download'
        if await public_destination(config,download.url,navigation=False,cache={}):record['source_url']=public_url(download.url)
        # Blob downloads are tied to the actual public response bytes, rather
        # than inventing a backing URL from the control's JavaScript handler.
        for response in reversed(responses):
            if not await public_destination(config,response.url,navigation=False,cache={}):continue
            length=int(response.headers.get('content-length','0'))
            if length>config.max_attachment_bytes:continue
            try:data=await asyncio.wait_for(response.body(),5)
            except Exception:continue
            if hashlib.sha256(data).hexdigest()==record['sha256']:
                record['source_url']=public_url(response.url);break
        record['control_evidence_url']=public_url(page.url)
    finally:
        record['document_responses']=[{'url':public_url(response.url),'status':response.status,'content_type':response.headers.get('content-type','')} for response in responses]
        record['document_requests']=[public_url(url) for url in requests.urls]
        page.context.remove_listener('response',response_seen)
        page.context.remove_listener('request',request_seen)
        scratch.unlink(missing_ok=True)


async def capture_official_guide(config, job, folder):
    from playwright.async_api import async_playwright
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    result={'requested_url':job['url'], 'region':job['region'], 'started_at':now(),
            'state':'unverified','service_verified':False,'model_used':False,'attachments':[], 'failures':[]}
    addresses={}
    document_phase={'active':False}

    async def allowed_request(route):
        url=route.request.url
        if url.startswith(('data:','blob:')):return await route.continue_()
        if re.search(r'/login(?:[./?]|$)|/sso/|/oauth|passport',url,re.I):
            record_auth_boundary(result,url,main_frame=route.request.is_navigation_request() and route.request.frame==page.main_frame)
            return await route.abort('blockedbyclient')
        if not await public_destination(config,url,navigation=route.request.is_navigation_request(),cache=addresses,document_active=document_phase['active']):
            return await route.abort('blockedbyclient')
        return await route.continue_()

    async with async_playwright() as pw:
        # Never disable Chromium's process sandbox or certificate validation.
        browser=await pw.chromium.launch(executable_path=str(config.browser_executable),headless=True,chromium_sandbox=True)
        context=await browser.new_context(locale='zh-CN',viewport={'width':1440,'height':1000},accept_downloads=True,service_workers='block')
        await context.route('**/*',allowed_request)
        page=await context.new_page()
        page.on('requestfailed',lambda request:result['failures'].append({'url':request.url,'error':request.failure}) if len(result['failures'])<40 else None)
        try:
            response=await page.goto(config.validate_url(job['url']),wait_until='domcontentloaded',timeout=int(config.navigation_timeout_seconds*1000))
            result['http_status']=response.status if response else None
            try:await page.wait_for_load_state('networkidle',timeout=6000)
            except Exception:pass
            await page.wait_for_timeout(1500)
            result.update(final_url=page.url,title=await page.title(),observed_at=now())
            config.validate_url(page.url)
            texts=[]
            for frame in page.frames:
                if not frame.url.startswith(('https:','http:')):continue
                try:texts.append(await frame.locator('body').inner_text(timeout=3000))
                except Exception:
                    if frame==page.main_frame:raise
            text='\n'.join(texts)
            (folder/'page.txt').write_text(text,encoding='utf8')
            (folder/'page.html').write_text(await page.content(),encoding='utf8')
            await page.screenshot(path=str(folder/'page.png'),full_page=False)
            result['state']=classify_observation(text,result.get('http_status'),main_frame_auth=bool(result.get('auth_boundary_url')))
            result['guide_detected']=result['state']=='guide_observed'
            result['review_state']='pending_human_review'
            result['attachment_template_match']='unknown_until_review'
            if result['state']=='guide_observed':
                # Only explicit public document anchors. No apply/login controls,
                # guessed backend endpoints, CAPTCHA actions, or model decisions.
                anchors=await page.locator('a[href]').evaluate_all("ns=>ns.map(n=>({url:n.href,label:(n.innerText||'').trim()}))")
                for anchor in anchors:
                    if len(result['attachments'])>=config.max_attachments:break
                    if not material_anchor(anchor):continue
                    record={'source_url':anchor['url'],'label':anchor['label'][:180],'state':'unverified'}
                    result['attachments'].append(record)
                    try:
                        config.validate_url(anchor['url'],resource=True)
                        await asyncio.sleep(config.min_interval_seconds)
                        # Browser navigation uses the same network restrictions
                        # and certificate policy as the guide itself.
                        target=await context.new_page()
                        try:
                            document_phase['active']=True
                            async with target.expect_download(timeout=15000) as event:
                                try:await target.goto(anchor['url'],timeout=15000)
                                except Exception as exc:
                                    if 'Download is starting' not in str(exc):raise
                            download=await event.value
                            path=folder/('attachment-'+str(len(result['attachments'])))
                            await download.save_as(str(path))
                            if path.stat().st_size>config.max_attachment_bytes:
                                path.unlink();raise ValueError('Attachment exceeds configured bound')
                            body=path.read_bytes()
                            from portal_attachment_downloads import file_type
                            extension=file_type(body)
                            if not extension:path.unlink();raise ValueError('Response is not a recognized document')
                            final=path.with_suffix(extension);path.rename(final)
                            record.update(state='downloaded',file=final.name,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),observed_at=now(),template_kind='unknown_until_review',capture_method='browser_download',control_evidence_url=public_url(page.url))
                        finally:
                            document_phase['active']=False
                            await target.close()
                    except Exception as exc:record.update(state='failed',error=str(exc)[:500])
                if len(result['attachments'])<config.max_attachments:
                    from portal_interactions import material_controls
                    controls=await material_controls(page.main_frame)
                    for control in controls:
                        if len(result['attachments'])>=config.max_attachments:break
                        if control.get('url') in {x.get('source_url') for x in result['attachments']}:continue
                        if control.get('control_text') not in ('下载','空白表格','示例样表','样例下载','模板下载'):continue
                        record={'source_url':public_url(page.url),'label':control['text'][:180],
                                'state':'unverified','template_kind':'unknown_until_review'}
                        result['attachments'].append(record)
                        try:
                            await asyncio.sleep(config.min_interval_seconds)
                            target=page.locator(control['selector'])
                            await target.scroll_into_view_if_needed(timeout=4000)
                            await page.screenshot(path=str(folder/'materials.png'),full_page=False)
                            document_phase['active']=True
                            await click_document_control(config,page,target,record,folder,len(result['attachments']))
                        except Exception as exc:record.update(state='auth_required' if result.get('auth_boundary_url') else 'failed',error=str(exc)[:500])
                        finally:document_phase['active']=False
                        if result.get('auth_boundary_url'):break
        except Exception as exc:
            result.update(state='auth_required' if result.get('auth_boundary_url') else 'network_failed',error=str(exc)[:1500],final_url=page.url,observed_at=now())
            try:await page.screenshot(path=str(folder/'failure.png'))
            except Exception:pass
        finally:
            await context.close();await browser.close()
    result['completed_at']=now()
    result['evidence']=evidence_manifest(folder)
    save_json(folder/'result.json',result)
    return result


async def run_worker(config, *, once=False, stop=None):
    queue=GuideQueue(config)
    with worker_lock(queue.root):
        queue.recover_interrupted()
        # Existing complete results and recovered attempts precede any new visit.
        # This does not run OpenClaw synchronization or acknowledge events.
        queue.replay_issue_events()
        token=uuid.uuid4().hex
        start_ticks=Path('/proc/self/stat').read_text().split()[21]
        def heartbeat(state,job=None):save_json(queue.root/'worker.json',{'pid':os.getpid(),'process_start_ticks':start_ticks,'token':token,'updated_at':now(),'state':state,'job':job,'concurrency':1,'model_used':False})
        heartbeat('idle')
        try:
            while stop is None or not stop.is_set():
                job=queue.claim()
                if not job:
                    heartbeat('idle')
                    if once:break
                    await asyncio.sleep(2);continue
                heartbeat('running',job['id'])
                folder=queue.root/'evidence'/job['id']/('attempt-'+str(job['attempt']))
                try:
                    result=await asyncio.wait_for(capture_official_guide(config,job,folder),config.job_timeout_seconds)
                except Exception as exc:
                    folder.mkdir(parents=True,exist_ok=True)
                    result={'state':'runtime_failed','service_verified':False,'model_used':False,'error':str(exc)[:2000],'observed_at':now(),'evidence':evidence_manifest(folder)}
                    save_json(folder/'result.json',result)
                result['evidence_directory']=str(folder.relative_to(queue.root)).replace('\\','/')
                queue.finish(job['id'],result)
                heartbeat('idle')
                if once:break
                await asyncio.sleep(config.min_interval_seconds)
        finally:heartbeat('stopped')
