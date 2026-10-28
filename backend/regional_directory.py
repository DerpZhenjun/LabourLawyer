"""Official place directory and durable discovery queue; not a guide authority.

This database is separate from both private case data and published local guides.
Provider-qualified IDs prevent functional areas from replacing administrative units.
"""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def clock():
    return datetime.now(timezone.utc).isoformat()


def national_children(response, parent):
    if response.get('success') is not True or str(response.get('code')) != '200' or not isinstance(response.get('data'), list):
        raise ValueError('官方目录未返回成功列表，不代表当地没有办理服务')
    result = []
    for row in response['data']:
        if row.get('del_flag') == 1 or row.get('regionStatus', 'US01') != 'US01':
            continue
        if not re.fullmatch(r'\d{6}', str(row.get('regionCode', ''))) or not str(row.get('regionName', '')).strip():
            raise ValueError('官方目录地区标识缺失或格式改变')
        if parent and str(row.get('parentId')) != str(parent):
            raise ValueError('官方返回目录的父地区不匹配')
        if str(row.get('regionLvl')) not in {'2', '3', '4'}:
            raise ValueError('目录层级不在省市区县范围，需单独核验')
        result.append(row)
    return result


def national_area(row, province, city, evidence):
    level=int(row['regionLvl'])
    # The platform's actual work.js stops descent when the last two digits are
    # not 00. Direct provincial county/city/functional stations use level=3 in
    # that source; preserve that raw level but expose the terminal as selectable.
    terminal=(level==3 and not row['regionCode'].endswith('00')) or (level==4 and not city)
    municipalities={'beijing':'北京市','tianjin':'天津市','shanghai':'上海市','chongqing':'重庆市'}
    return {'provider':'national','code':row['regionCode'],'level':4 if terminal else level,
            'parent_code':str(row.get('parentId','')),'province':province,
            'city':municipalities.get(province,row['regionName']) if terminal else city,
            'district':row['regionName'] if level==4 or terminal else '',
            'official_name':row['regionName'],'directory_terminal':terminal,
            'normalization_note':'官网目录不再向下展开的省直管服务站；保留原始层级，不推断仲裁管辖' if terminal else '',
            'source_url':evidence['url'],'source_request':evidence.get('form',{}),
            'collected_at':evidence['collected_at'],'response_sha256':evidence['sha256'],'raw_record':row}


def sichuan_city_areas(capture):
    """Read a captured own-city directory, not a statement of arbitration support."""
    url = capture.get('source_url', '')
    address = urlsplit(url)
    query = parse_qs(address.query)
    response = capture.get('response', {})
    group = (response.get('data') or {}).get('group') or {}
    code = str(group.get('areaCode', ''))
    city = str(group.get('shortName') or group.get('name') or '').strip()
    if (address.scheme != 'https' or address.hostname != 'www.sczwfw.gov.cn'
            or address.path != '/jiq/interface/jitem/find-by-code'
            or query.get('code') != [code] or query.get('deptType') != ['1']
            or not re.fullmatch(r'51\d{10}', code) or not code.endswith('000000')
            or str(response.get('code')) != '200' or str(group.get('areaLevel')) != '2'
            or not city or not group.get('iid') or not capture.get('collected_at')
            or not isinstance(group.get('sonAreas'), list)):
        raise ValueError('四川自己的城市目录来源或地区身份不匹配')
    shared = {'provider': 'sichuan_portal', 'province': 'sichuan', 'city': city,
              'source_url': url, 'collected_at': capture['collected_at'],
              'verification_status': 'unverified', 'source_id': None, 'can_generate': False}
    rows = [{**shared, 'code': code, 'district': '', 'level': 3,
             'parent_code': code[:2] + '0000000000', 'official_name': group['name'],
             'raw_record': {k: v for k, v in group.items() if k != 'sonAreas'}}]
    seen = set()
    for child in group['sonAreas']:
        if child.get('status') != 'US01':
            continue
        child_code = str(child.get('areaCode', ''))
        name = str(child.get('shortName') or child.get('name') or '').strip()
        if (str(child.get('areaLevel')) != '3' or child.get('pid') != group['iid']
                or not re.fullmatch(r'51\d{10}', child_code) or not child.get('name')
                or not name or child_code in seen):
            raise ValueError('目录子地区的原始父地区、编码或名称不匹配')
        seen.add(child_code)
        rows.append({**shared, 'code': child_code, 'district': name, 'level': 4,
                     'parent_code': code, 'official_name': child['name'], 'raw_record': child})
    return rows


class DirectoryStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS directory_areas(
                  id TEXT PRIMARY KEY, province TEXT NOT NULL, city TEXT NOT NULL,
                  district TEXT NOT NULL, level INTEGER NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS directory_place ON directory_areas(province,city,level);
                CREATE TABLE IF NOT EXISTS discovery_jobs(
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
                  state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                  updated_at TEXT NOT NULL, result TEXT);
                CREATE INDEX IF NOT EXISTS discovery_state ON discovery_jobs(state,kind);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def put_area(self, area):
        if not all(area.get(k) for k in ('provider','code','province','source_url','collected_at')):
            raise ValueError('地区目录缺少来源和身份')
        if area['level'] not in {2,3,4} or (area['level'] == 4 and not all(area.get(k) for k in ('city','district'))):
            raise ValueError('缺少地区层级或完整父地区')
        identity = area['provider'] + ':' + area['code']
        # Directory records must NEVER carry guide/generation capability from crawlers.
        item = {**area, 'id':identity, 'source_id':None, 'can_generate':False, 'verification_status':'unverified'}
        item.setdefault('city','')
        item.setdefault('district','')
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO directory_areas VALUES(?,?,?,?,?,?)',
                       (identity,item['province'],item['city'],item['district'],item['level'],json.dumps(item,ensure_ascii=False)))
        return item

    def areas(self, province, city=''):
        with self.connection() as db:
            if city:
                rows = db.execute('SELECT payload FROM directory_areas WHERE province=? AND city=? AND level=4 ORDER BY id',(province,city))
            else:
                rows = db.execute('SELECT payload FROM directory_areas WHERE province=? AND level IN (3,4) ORDER BY level,id',(province,))
            result=[json.loads(row['payload']) for row in rows]
            if not city:
                # Include terminal stations and district-only supplementary sources.
                result=list({item['city']:item for item in reversed(result) if item['city']}.values())
            return result

    def enqueue(self, kind, payload):
        identity = hashlib.sha256(json.dumps([kind,payload],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:32]
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO discovery_jobs(id,kind,payload,state,updated_at) VALUES(?,?,?,?,?)',
                       (identity,kind,json.dumps(payload,ensure_ascii=False),'pending',clock()))
        return identity

    def claim(self, kind=None):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM discovery_jobs WHERE state='pending'" + (' AND kind=?' if kind else '') + ' ORDER BY rowid LIMIT 1', (kind,) if kind else ()).fetchone()
            if not row:
                return None
            db.execute("UPDATE discovery_jobs SET state='running',attempts=attempts+1,updated_at=? WHERE id=?",(clock(),row['id']))
            result = dict(row)
            result['payload'] = json.loads(result['payload'])
            return result

    def finish(self, identity, state, result):
        if state not in {'done','failed','pending','needs_browser','manual_review'}:
            raise ValueError('未知任务状态')
        with self.connection() as db:
            db.execute('UPDATE discovery_jobs SET state=?,result=?,updated_at=? WHERE id=?',
                       (state,json.dumps(result,ensure_ascii=False),clock(),identity))

    def recover_interrupted(self, kind=None):
        # Only call after acquiring the worker's exclusive OS lock.
        with self.connection() as db:
            db.execute("UPDATE discovery_jobs SET state='pending' WHERE state='running'" + (' AND kind=?' if kind else ''), (kind,) if kind else ())

    def summary(self):
        with self.connection() as db:
            areas = [dict(r) for r in db.execute("SELECT province,level,COUNT(DISTINCT city || char(0) || district) AS count FROM directory_areas GROUP BY province,level")]
            jobs = [dict(r) for r in db.execute('SELECT kind,state,COUNT(*) AS count FROM discovery_jobs GROUP BY kind,state')]
        return {'areas':areas,'jobs':jobs,'directory_is_not_guide_coverage':True}
