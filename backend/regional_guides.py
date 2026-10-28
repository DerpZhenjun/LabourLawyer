"""Exact-locality public guide store. Separate from users and case data."""
from __future__ import annotations
import copy
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

EVENT_TYPES=set('SEARCH_NO_RESULT SEARCH_ALIAS_REQUIRED WRONG_SERVICE_MATCH GUIDE_PAGE_UNAVAILABLE REGION_SELECTION_FAILURE ONLINE_APPLICATION_UNAVAILABLE ONLINE_CHANNEL_UNVERIFIED OFFICIAL_TEMPLATE_NOT_FOUND TEMPLATE_DOWNLOAD_FAILED MATERIAL_INFORMATION_MISSING AUTH_REQUIRED CAPTCHA_REQUIRED OFFICIAL_SOURCE_CONFLICT SOURCE_STALE'.split())

def now():return datetime.now(timezone.utc).isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def region_key(province,city,district):return digest([province.strip(),city.strip(),district.strip()])[:24]

def official_content(value):
    """Version substantive content, not recheck clocks or expiring download tokens."""
    volatile={'collected_at','verified_at','version','content_hash','source_id','region_id','evidence',
              'screenshot','capture_file','capture_sha256','download_url','final_download_url'}
    if isinstance(value,dict):return {k:official_content(v) for k,v in value.items() if k not in volatile}
    if isinstance(value,list):return [official_content(v) for v in value]
    return value

def resolve_channel(fields, flow, entry_check=None):
    raw=fields.get('办理形式','').strip()
    form=('window_and_online' if '窗口' in raw and '网上' in raw else 'window' if '窗口' in raw else
          'online_precheck' if '预审' in raw else 'online_appointment' if '预约' in raw else
          'offline_verification' if '核验' in raw else 'online' if '网上' in raw else 'unverified')
    urls=re.findall(r'https?://[^\s<>，。；）]+',flow)
    urls=[u.split('进行')[0] for u in urls]
    conflict=form=='window' and ('线上申请' in flow or '网上申请' in flow)
    status='conflict' if conflict else 'unavailable' if form=='window' and fields.get('是否网办')=='否' else 'unverified'
    entry=None
    if not conflict and form in {'online','window_and_online','online_precheck','online_appointment'} and entry_check:
        if entry_check.get('official_link') and entry_check.get('status') in {'verified','auth_required'} and re.match(r'^https?://',entry_check.get('url','')):
            status=entry_check['status'];entry=entry_check['url']
    return {'raw_value':raw,'form':form,'online_status':status,'entry_url':entry,
            'mentioned_urls':urls,'entry_check':entry_check or {}}

def select_template(guide, template_id, kind, mode):
    if guide.get('verification_status') not in {'verified','partial','conflict'}:raise ValueError('该地区尚未核验，不能匹配官方文书')
    template=next((t for t in guide.get('templates',[]) if t['id']==template_id),None)
    if not template or template.get('region_code')!=guide.get('region_code'):raise ValueError('模板与办理地区不匹配')
    if kind not in template.get('document_types',[]) or not template.get('can_generate'):raise ValueError('该附件尚未完成填写适配')
    if template.get('official_kind')!='blank' and mode!='reference_adaptation':raise ValueError('官方标注为样表，不能当作空白模板生成')
    return template

class RegionalStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS regional_schema(version INTEGER PRIMARY KEY);
            INSERT OR IGNORE INTO regional_schema VALUES(1);
            CREATE TABLE IF NOT EXISTS regional_guides(
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,region_id TEXT NOT NULL,source_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,province TEXT NOT NULL,city TEXT NOT NULL,district TEXT NOT NULL,
              payload TEXT NOT NULL,UNIQUE(region_id,content_hash));
            CREATE INDEX IF NOT EXISTS regional_lookup ON regional_guides(province,city,district,sequence DESC);
            CREATE TABLE IF NOT EXISTS regional_current(region_id TEXT PRIMARY KEY,sequence INTEGER NOT NULL);
            INSERT OR IGNORE INTO regional_current SELECT region_id,MAX(sequence) FROM regional_guides GROUP BY region_id;
            CREATE TABLE IF NOT EXISTS collection_outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL,
              delivery_status TEXT NOT NULL,receipt TEXT,created_at TEXT NOT NULL);
            ''')
    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        try:yield db;db.commit()
        finally:db.close()
    def put_guide(self, payload):
        d=copy.deepcopy(payload)
        if d.get('service_name') not in {'劳动人事争议仲裁申请','劳动争议仲裁申请'}:raise ValueError('不是已核验的仲裁申请事项')
        u=urlsplit(d['source_url']);host=u.hostname or ''
        if u.scheme not in {'http','https'} or not (host.endswith('.gov.cn') or host.endswith('.cngy.gov.cn')):raise ValueError('非官方来源')
        actual=parse_qs(u.query).get('areaCode',[None])[0]
        if actual and actual!=d.get('region_code'):raise ValueError('来源地区编码不匹配')
        if not all(d.get(k) for k in ('province','city','district','region_code','collected_at','verified_at')):raise ValueError('缺少地区或核验信息')
        rid=region_key(d['province'],d['city'],d['district']);sid=digest(d['source_url'])[:24]
        content=official_content(d)
        checksum=digest(content)
        d.update(region_id=rid,source_id=sid,content_hash=checksum)
        with self.connection() as db:
            existing=db.execute('SELECT sequence FROM regional_guides WHERE region_id=? AND content_hash=?',(rid,checksum)).fetchone()
            if existing:
                db.execute('UPDATE regional_guides SET payload=? WHERE sequence=?',(json.dumps(d,ensure_ascii=False),existing['sequence']))
            else:
                db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',
                           (rid,sid,checksum,d['province'],d['city'],d['district'],json.dumps(d,ensure_ascii=False)))
            seq=db.execute('SELECT sequence FROM regional_guides WHERE region_id=? AND content_hash=?',(rid,checksum)).fetchone()['sequence']
            db.execute('INSERT OR REPLACE INTO regional_current VALUES(?,?)',(rid,seq))
        return self.lookup(d['province'],d['city'],d['district'])
    def lookup(self,province,city,district):
        with self.connection() as db:
            row=db.execute('SELECT * FROM regional_guides WHERE province=? AND city=? AND district=? AND sequence IN (SELECT sequence FROM regional_current) LIMIT 1',
                           (province.strip(),city.strip(),district.strip())).fetchone()
        if row:
            d=json.loads(row['payload']);d['version']=row['sequence'];return d
        return {'province':province,'city':city,'district':district,'region_id':region_key(province,city,district),
                'source_id':None,'verification_status':'unverified','fields':{},'materials':[],'templates':[],
                'sections':{},'channel':resolve_channel({},''),'message':'该地区办事指南尚未核验'}
    def versions(self,province,city,district):
        with self.connection() as db:
            rows=db.execute('SELECT payload FROM regional_guides WHERE province=? AND city=? AND district=? ORDER BY sequence DESC',(province,city,district)).fetchall()
        return [json.loads(r['payload']) for r in rows]
    def inventory(self):
        with self.connection() as db:
            rows=db.execute('SELECT payload FROM regional_guides WHERE sequence IN (SELECT sequence FROM regional_current) ORDER BY province,city,district').fetchall()
        return [json.loads(r['payload']) for r in rows]
    def record_event(self,event):
        if event.get('type') not in EVENT_TYPES:raise ValueError('未知问题类型')
        allowed={'province','city','district','region_code','service','keyword','url','occurred_at','type','screenshot','reason','attempts','final_status','remediation'}
        d={k:v for k,v in event.items() if k in allowed}
        d.update(id=event.get('id') or uuid.uuid4().hex,occurred_at=event.get('occurred_at') or now(),attempts=event.get('attempts',1),final_status=event.get('final_status','pending'),delivery_status='PENDING_OPENCLAW')
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO collection_outbox VALUES(?,?,?,?,?)',(d['id'],json.dumps(d,ensure_ascii=False),d['delivery_status'],None,now()))
        return d
    def events(self):
        with self.connection() as db:rows=db.execute('SELECT * FROM collection_outbox ORDER BY created_at').fetchall()
        return [{**json.loads(r['payload']),'delivery_status':r['delivery_status'],'receipt':json.loads(r['receipt']) if r['receipt'] else None} for r in rows]
    def acknowledge(self,ids,receipt):
        if receipt.get('ok') is not True or set(receipt.get('accepted_event_ids',[]))!=set(ids):raise ValueError('OpenClaw 未确认完整事件编号')
        with self.connection() as db:
            for identifier in ids:db.execute('UPDATE collection_outbox SET delivery_status=?,receipt=? WHERE id=?',('ACKNOWLEDGED_OPENCLAW',json.dumps(receipt,ensure_ascii=False),identifier))
