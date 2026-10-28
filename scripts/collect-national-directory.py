"""Resumable low-rate public national locality directory; no models/private DB.

Every queue item preserves the official raw response, request parameters and SHA.
Only directory metadata is written. Real guides still need their own browser QA.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from regional_directory import DirectoryStore, national_children, national_area, clock

OUT = ROOT/'reports/nationwide-localization-20261023-night'
ENDPOINT = 'https://gjzwfw.www.gov.cn/fwmh/ucGovRegion/findUcGovRegion.do'
DEADLINE = datetime.fromisoformat('2026-10-24T08:00:00+08:00')


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    temporary.replace(path)


def request(parent):
    payload = {'parentId':parent} if parent else {}
    key = parent or 'root'
    path = OUT/'raw-directory'/f'{key}.json'
    metadata = OUT/'raw-directory'/f'{key}.request.json'
    if path.is_file() and metadata.is_file():
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() == json.loads(metadata.read_text('utf8')).get('sha256'):
            response = json.loads(body)
            national_children(response,parent)
            return response, json.loads(metadata.read_text('utf8'))
    for attempt in range(3):
        try:
            with urlopen(Request(ENDPOINT,data=urlencode(payload).encode(),headers={'User-Agent':'Mozilla/5.0','Referer':'https://gjzwfw.www.gov.cn/'}),timeout=25) as result:
                if not result.url.startswith('https://gjzwfw.www.gov.cn/'):
                    raise ValueError('公开目录跳转到未授权来源')
                body = result.read(5*1024*1024+1)
                if len(body)>5*1024*1024:
                    raise ValueError('目录响应超过限制')
                response = json.loads(body)
                national_children(response,parent)
                evidence = {'url':ENDPOINT,'method':'POST','form':payload,'http_status':result.status,
                            'collected_at':clock(),'sha256':hashlib.sha256(body).hexdigest(),
                            'source_js':'templates/_reports/openclaw-tasks/20261007-130607-2c6533a3/national-navigation/services/work.js'}
                # Preserve raw response bytes, not reserialized JSON.
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(body)
                save(metadata,evidence)
                return response,evidence
        except Exception:
            if attempt==2:
                raise
            time.sleep(2*(attempt+1))


def handle(store, job):
    data = job['payload']
    response, evidence = request(data.get('parent',''))
    rows = national_children(response,data.get('parent',''))
    catalog = json.loads((ROOT/'frontend/src/data/provinceCatalog.json').read_text('utf8'))
    slugs = {p['name']:p['slug'] for p in catalog}
    accepted = 0
    for row in rows:
        level = int(row['regionLvl'])
        slug = data.get('province') or slugs.get(row['regionName'])
        if not slug:
            # Territories outside the current 31-province product remain explicit gaps.
            continue
        city = data.get('city','')
        if level==3:
            city = next((p['name'] for p in catalog if p['slug']==slug),row['regionName']) if slug in {'beijing','tianjin','shanghai','chongqing'} else row['regionName']
        area = store.put_area(national_area(row,slug,city,evidence))
        accepted += 1
        if area['level']<4:
            store.enqueue('directory',{'provider':'national','parent':row['regionCode'],'province':slug,'city':city})
        else:
            store.enqueue('service_discovery',{'provider':'national','code':row['regionCode'],'province':slug,'city':area['city'],'district':area['district']})
    return {'children':len(rows),'accepted':accepted,'source':evidence,'state':'directory_only_not_verified_guides'}


def repair_terminals(store):
    """Incremental correction using preserved successful raw records, no recrawl."""
    with store.connection() as db:
        old=[json.loads(r['payload']) for r in db.execute('SELECT payload FROM directory_areas WHERE level IN (3,4)')]
        jobs=[dict(r) for r in db.execute("SELECT id,payload FROM discovery_jobs WHERE kind='directory' AND state!='done'")]
    terminals=set()
    for item in old:
        row=item.get('raw_record',{})
        if item['provider']!='national' or not row or str(row.get('regionLvl'))!='3' or row['regionCode'].endswith('00'):
            continue
        area=store.put_area(national_area(row,item['province'],item['city'],{
            'url':item['source_url'],'collected_at':item['collected_at'],'form':item.get('source_request',{}),'sha256':item['response_sha256']}))
        terminals.add(area['code'])
        if item['city']!=area['city']:
            with store.connection() as db:
                previous_jobs=[dict(r) for r in db.execute("SELECT id,payload FROM discovery_jobs WHERE kind='service_discovery' AND state='pending'")]
            for previous_job in previous_jobs:
                previous_data=json.loads(previous_job['payload'])
                if previous_data.get('code')==area['code'] and previous_data.get('city')!=area['city']:
                    store.finish(previous_job['id'],'done',{'state':'superseded_by_normalized_municipality_path','not_a_verified_guide':True})
        store.enqueue('service_discovery',{'provider':'national','code':area['code'],'province':area['province'],'city':area['city'],'district':area['district']})
    for job in jobs:
        data=json.loads(job['payload'])
        if data.get('parent') in terminals:
            result={'state':'official_directory_terminal','reason':'公开导航JS对非00结尾编码不继续展开；不推断没有仲裁服务','resolved_at':clock()}
            store.finish(job['id'],'done',result)
            previous=OUT/'outbox'/f"{job['id']}.json"
            if previous.is_file():
                issue=json.loads(previous.read_text('utf8'));issue['resolution']=result;issue['final_status']='resolved_directory_classification'
                save(previous,issue)
    if terminals:print('Normalized official terminal stations:',len(terminals),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=10000)
    parser.add_argument('--delay',type=float,default=1.5)
    parser.add_argument('--retry-failed',action='store_true',help='One explicit bounded pass over failed jobs; preserves previous issue evidence')
    args = parser.parse_args()
    if args.delay<1:
        parser.error('公开目录最小请求间隔1秒')
    OUT.mkdir(parents=True,exist_ok=True)
    import msvcrt
    with (OUT/'directory-worker.lock').open('a+b') as lock:
        if lock.tell()==0:
            lock.write(b'0');lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            print('Existing directory worker owns lock; no duplicate started.',flush=True)
            return
        store = DirectoryStore(ROOT/'backend/data/regional-directory.sqlite')
        repair_terminals(store)
        if args.retry_failed:
            with store.connection() as db:
                db.execute("UPDATE discovery_jobs SET state='pending' WHERE kind='directory' AND state='failed'")
        store.recover_interrupted('directory')
        store.enqueue('directory',{'provider':'national','parent':''})
        save(OUT/'directory-worker.json',{'pid':os.getpid(),'started_at':clock(),'deadline':DEADLINE.isoformat(),'state':'running'})
        completed = 0
        while completed<args.limit and datetime.now(timezone.utc)<DEADLINE:
            job = store.claim('directory')
            if not job:
                break
            try:
                result = handle(store,job)
                store.finish(job['id'],'done',result)
                print(job['payload'],result['accepted'],flush=True)
            except Exception as exc:
                issue = {'type':'GUIDE_PAGE_UNAVAILABLE','scope':'region_directory_not_service','job':job['payload'],
                         'url':ENDPOINT,'occurred_at':clock(),'reason':str(exc),'attempts':3,
                         'delivery_status':'PENDING_OPENCLAW','final_status':'pending_recheck'}
                save(OUT/'outbox'/f"{job['id']}.json",issue)
                store.finish(job['id'],'failed',issue)
                print('FAILED',job['payload'],str(exc),flush=True)
            completed+=1
            save(OUT/'DIRECTORY-PROGRESS.json',{'updated_at':clock(),**store.summary()})
            time.sleep(args.delay)
        save(OUT/'directory-worker.json',{'pid':os.getpid(),'finished_at':clock(),'state':'directory_batch_finished',
                                         'completed_jobs_this_run':completed,'summary':store.summary()})
        print('Directory batch finished. Service discovery still requires browser verification.',flush=True)


if __name__=='__main__':
    main()
