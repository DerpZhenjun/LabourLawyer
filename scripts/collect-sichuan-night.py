"""Province-owned discovery and real-browser capture; never substitutes Chengdu.

Uses the already observed Sichuan directory/search APIs and the same portal's UI
adapter. Each city/district still requires its own formal page and own annexes.
Staging only: this script cannot enable a generator or publish a regional guide.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_directory import DirectoryStore, clock
from chengdu_collection import select_service
from sichuan_search import discover_service, requeue_search_misses
collector=import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/sichuan'
collector.OUT=OUT
collector.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-sichuan-night-20261023'}
save=collector.save
DEADLINE=datetime.fromisoformat('2026-10-24T08:00:00+08:00')


def tree(code):
    path=OUT/'directory'/f'{code}.json'
    if path.is_file():
        return json.loads(path.read_text('utf8'))
    url='https://www.sczwfw.gov.cn/jiq/interface/jitem/find-by-code?'+urlencode({'code':code,'deptType':1,'jsonpCallback':'jsonpcallback'})
    raw=collector.public_get(url)[0].decode('utf8')
    response=json.loads(raw[raw.index('(')+1:raw.rindex(')')])
    if str(response.get('code'))!='200' or response['data']['group']['areaCode']!=code:
        raise ValueError('省官网目录地区编码不匹配')
    result={'source_url':url,'collected_at':clock(),'response':response,'response_sha256':hashlib.sha256(raw.encode()).hexdigest()}
    save(path,result)
    time.sleep(1.5)
    return result


def discover(store):
    root=tree('510000000000')
    for city in root['response']['data']['group']['sonAreas']:
        # The original 23 Chengdu targets and all their evidence are preserved.
        if city['areaCode']=='510100000000':
            continue
        store.enqueue('sichuan_directory',{'code':city['areaCode'],'city':city['shortName'],'official_name':city['name']})


def city_directory(store, data):
    result=tree(data['code'])
    store.put_area({'provider':'sichuan_portal','code':data['code'],'province':'sichuan','city':data['city'],'district':'',
                    'level':3,'parent_code':'510000000000','official_name':data['official_name'],
                    'source_url':result['source_url'],'collected_at':result['collected_at'],'response_sha256':result['response_sha256']})
    count=0
    for area in result['response']['data']['group']['sonAreas']:
        if area.get('areaLevel')!='3':
            continue
        row=store.put_area({'provider':'sichuan_portal','code':area['areaCode'],'province':'sichuan','city':data['city'],
                            'district':area['shortName'],'level':4,'parent_code':data['code'],'official_name':area['name'],
                            'source_url':result['source_url'],'collected_at':result['collected_at'],'response_sha256':result['response_sha256']})
        store.enqueue('sichuan_capture',{'city':row['city'],'district':row['district'],'region_code':row['code'],'region_metadata':area})
        count+=1
    return {'districts':count,'source_url':result['source_url']}


def capture(data):
    code=data['region_code']
    search=discover_service(code,OUT/'discovery',lambda url:collector.public_get(url)[0],time.sleep)
    save(OUT/'search-traces'/f'{code}.json',search)
    service=search['service']
    if search.get('summary_candidate'):
        return 'manual_review',{'type':'GUIDE_PAGE_UNAVAILABLE','reason':'准确事项命中新版概览页，需真实点击进入详细指南；当前旧版采集器不套用旧栏目解析',
                                'source_url':search['summary_candidate']['url'],'search_attempts':search['attempts'],
                                'summary_candidate':search['summary_candidate']}
    if not service:
        return 'manual_review',{'type':'SEARCH_NO_RESULT','reason':'官网四个关键词均未找到该地区正式仲裁申请事项；不代表当地没有仲裁服务',
                                'source_url':search['attempts'][-1]['url'],'search_attempts':search['attempts'],
                                'alias_attempts_completed':True}
    if search['alias_required']:
        event_id=hashlib.sha256((code+'SEARCH_ALIAS_REQUIRED').encode()).hexdigest()[:32]
        save(OUT/'outbox'/f'{event_id}.json',{'id':event_id,'province':'sichuan','city':data['city'],
             'district':data['district'],'region_code':code,'type':'SEARCH_ALIAS_REQUIRED',
             'service':'劳动人事争议仲裁申请','keyword':search['attempts'][-1]['keyword'],'url':service['url'],
             'occurred_at':clock(),'reason':'完整关键词未命中，替换关键词后找到本地区准确事项',
             'search_attempts':search['attempts'],'attempts':len(search['attempts']),
             'delivery_status':'PENDING_OPENCLAW','final_status':'resolved','remediation':'保留每次官方检索记录和准确的地区匹配'})
    target={**data,'service':service}
    guide=collector.capture(target)
    if guide['channel']['form'] in {'online','window_and_online'}:
        try:
            collector.check_online(target)
        except Exception as exc:
            save(OUT/'captures'/code/'online-check-error.json',{'status':'unverified','reason':str(exc),'at':clock()})
    # Full guide and downloaded annexes are staging, NOT enabled generators.
    return 'needs_browser',{'state':'captured_needs_publication_review','source_url':guide['source_url'],
                            'materials':len(guide['materials']),'templates':len(guide['templates']),
                            'downloaded':sum(t['download_status']=='downloaded' for t in guide['templates']),
                            'capture':str((OUT/'captures'/code/'guide.json').relative_to(ROOT))}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=1000)
    parser.add_argument('--retry-no-result',action='store_true',help='One bounded alias pass over prior search misses only')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    import msvcrt
    with (OUT/'worker.lock').open('a+b') as lock:
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:print('Sichuan worker already running.',flush=True);return
        store=DirectoryStore(ROOT/'backend/data/regional-directory.sqlite')
        store.recover_interrupted('sichuan_directory');store.recover_interrupted('sichuan_capture')
        if args.retry_no_result:
            print('Explicit alias retry:',len(requeue_search_misses(store)),flush=True)
        save(OUT/'worker.json',{'pid':os.getpid(),'state':'running','started_at':clock(),'deadline':DEADLINE.isoformat()})
        discover(store)
        count=0
        try:
            while count<args.limit and datetime.now(timezone.utc)<DEADLINE:
                job=store.claim('sichuan_directory') or store.claim('sichuan_capture')
                if not job:break
                try:
                    if job['kind']=='sichuan_directory':state,result='done',city_directory(store,job['payload'])
                    else:state,result=capture(job['payload'])
                    store.finish(job['id'],state,result)
                    if state=='manual_review':
                        save(OUT/'outbox'/f"{job['id']}.json",{'id':job['id'],'province':'sichuan',**job['payload'],
                             **result,'occurred_at':clock(),'delivery_status':'PENDING_OPENCLAW',
                             'attempts':len(result.get('search_attempts',[])) or 1,'final_status':'manual_review'})
                    print(job['payload']['city'],job['payload'].get('district','directory'),state,result,flush=True)
                except Exception as exc:
                    result={'id':job['id'],'type':'GUIDE_PAGE_UNAVAILABLE','province':'sichuan','city':job['payload']['city'],
                            'district':job['payload'].get('district',''),'occurred_at':clock(),'reason':str(exc),
                            'url':getattr(exc,'url',''),'keyword':getattr(exc,'keyword',''),
                            'delivery_status':'PENDING_OPENCLAW','attempts':1,'final_status':'pending_recheck',
                            'remediation':'核对真实页面及控件后重试，不跨地区替代'}
                    save(OUT/'outbox'/f"{job['id']}.json",result);store.finish(job['id'],'failed',result)
                    print('FAILED',job['payload'].get('district',job['payload']['city']),str(exc),flush=True)
                count+=1
                save(OUT/'progress.json',{'updated_at':clock(),**store.summary()})
                time.sleep(2)
        finally:
            try:collector.browser('close')
            except Exception:pass
            save(OUT/'worker.json',{'pid':os.getpid(),'state':'batch_finished','finished_at':clock(),'jobs_this_run':count})


if __name__=='__main__':main()
