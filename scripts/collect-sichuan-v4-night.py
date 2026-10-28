"""Actual summary -> detailed-guide clicks for Sichuan's newer portal.

Raw browser staging only. A different portal layout is not silently interpreted
using the old parser, and successful capture does not enable any generator.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_directory import DirectoryStore, clock
from sichuan_search import discover_service
c=import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/sichuan'
OUT=BASE/'v4';c.OUT=OUT
c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-sichuan-v4-night-20261023'}
DEADLINE=datetime.fromisoformat('2026-10-24T08:00:00+08:00')
SECTIONS=['基本信息','申请材料','受理条件','办理流程','收费标准','设定依据','中介服务','常见问题']


def enqueue_candidates(store):
    with store.connection() as db:
        targets=[json.loads(r['payload']) for r in db.execute("SELECT payload FROM discovery_jobs WHERE kind='sichuan_capture'")]
    count=0
    for target in targets:
        existing=BASE/'captures'/target['region_code']/'guide.json'
        if existing.is_file():
            own=json.loads(existing.read_text('utf8'))
            if (own.get('province'),own.get('city'),own.get('district'),own.get('region_code'))==(
                    'sichuan',target['city'],target['district'],target['region_code']):
                # Retain the existing evidence, not a second browser pass.
                with store.connection() as db:
                    stale=[r['id'] for r in db.execute("SELECT id,payload FROM discovery_jobs WHERE kind='sichuan_v4_capture' AND state IN ('pending','failed')")
                           if json.loads(r['payload']).get('region_code')==target['region_code']]
                for identity in stale:store.finish(identity,'done',{'state':'superseded_existing_own_capture','capture':str(existing.relative_to(ROOT))})
                continue
        path=BASE/'discovery'/(target['region_code']+'.json')
        if not path.exists():continue
        response=json.loads(path.read_text('utf8'))
        # No network calls here; only already captured own exact-name results.
        candidates=[]
        for row in response.get('response',{}).get('data',[]):
            item=row.get('data',{});p=urlsplit(item.get('url',''))
            if (item.get('title')=='劳动人事争议仲裁申请' and item.get('areacode')==target['region_code']
                    and p.hostname=='www.sczwfw.gov.cn' and p.path=='/jiq4/front/transition/ywTransToDetail_summary'
                    and parse_qs(p.query).get('areaCode')==[target['region_code']]):candidates.append(item)
        unique={item['url']:item for item in candidates}
        if len(unique)==1:
            store.enqueue('sichuan_v4_capture',{**target,'summary':next(iter(unique.values())),
                'search_file':str(path.relative_to(ROOT))});count+=1
    return count


def capture(target):
    code=target['region_code'];basefolder=OUT/'captures'/code
    basefolder.mkdir(parents=True,exist_ok=True)
    if (basefolder/'manifest.json').is_file():return json.loads((basefolder/'manifest.json').read_text('utf8'))
    folder=basefolder/'attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    c.browser('open',target['summary']['url'])
    # The official back-to-top control overlaps the last horizontal tab at the
    # native 1258px default viewport. Use a real desktop viewport, not JS clicks.
    c.browser('set','viewport','1440','1000')
    c.browser('wait','--text','劳动人事争议仲裁申请')
    c.save(folder/'summary.json',c.evaluate(c.CAPTURE_JS))
    snapshot=c.browser('snapshot','-i')['snapshot']
    match=re.search(r'link "进入详细指南" \[ref=(\w+)\]',snapshot)
    if not match:raise ValueError('未找到当前概览页实际的“进入详细指南”控件')
    c.browser('click','@'+match.group(1))
    c.browser('wait','--text','进入简版指南')
    allowed_headers={target['district'],target['region_metadata']['name'],'四川'+target['district']}
    # The common navigation is rendered before the asynchronously loaded region.
    c.browser('wait','--fn',json.dumps(sorted(allowed_headers),ensure_ascii=False)+'.includes(document.querySelector("#cityName")?.textContent.trim())')
    selected=c.evaluate('''({url:location.href,header:document.querySelector('#cityName')?.textContent.trim(),
        code:document.querySelector('#areaCode')?.value,item:document.querySelector('#itemCode')?.value})''')
    c.save(folder/'transition-check.json',selected)
    p=urlsplit(selected['url']);q=parse_qs(p.query)
    if (p.hostname!='www.sczwfw.gov.cn' or p.path!='/jiq4/front/transition/ywTransToDetail'
            or q.get('areaCode')!=[code] or selected['code']!=code
            or selected['header'] not in allowed_headers
            or q.get('itemCode')!=parse_qs(urlsplit(target['summary']['url']).query).get('itemCode')):
        raise ValueError('点击后的正式指南与目标地区、事项或页头不一致')
    files=[]
    for index,name in enumerate(SECTIONS,1):
        snapshot=c.browser('snapshot','-i')['snapshot']
        control=re.search(r'listitem "'+name+r'"[^\n]*ref=(\w+)',snapshot)
        if not control:raise ValueError('未找到实际栏目：'+name)
        c.browser('click','@'+control.group(1))
        c.browser('wait','--fn','typeof jQuery === "undefined" || (jQuery.active === 0 && jQuery(":animated").length === 0)')
        raw=c.evaluate(c.CAPTURE_JS)
        filename=f'{index:02d}.json';c.save(folder/filename,raw)
        if name in {'基本信息','申请材料','办理流程'}:
            c.browser('screenshot',str((folder/f'{index:02d}.png').relative_to(ROOT)))
        files.append({'section':name,'file':str((folder/filename).relative_to(basefolder)),
                      'sha256':hashlib.sha256((folder/filename).read_bytes()).hexdigest(),
                      'captured_at':raw['captured_at']})
    result={'province':'sichuan','city':target['city'],'district':target['district'],'region_code':code,
            'source_url':selected['url'],'summary_url':target['summary']['url'],'search_file':target['search_file'],
            'selected':selected,'sections':files,'captured_at':clock(),'state':'raw_browser_capture_requires_v4_parser',
            'generation_enabled':False,'published':False,'no_login_or_submission':True}
    c.save(basefolder/'manifest.json',result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=1000)
    parser.add_argument('--retry-failed',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    import msvcrt
    with (BASE/'worker.lock').open('a+b') as lock:
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:print('Another Sichuan worker holds the lock.',flush=True);return
        store=DirectoryStore(ROOT/'backend/data/regional-directory.sqlite')
        store.recover_interrupted('sichuan_v4_capture')
        print('Observed v4 summary candidates:',enqueue_candidates(store),flush=True)
        if args.retry_failed:
            with store.connection() as db:
                db.execute("UPDATE discovery_jobs SET state='pending',updated_at=? WHERE kind='sichuan_v4_capture' AND state='failed'",(clock(),))
        c.save(OUT/'worker.json',{'pid':os.getpid(),'state':'running','started_at':clock(),'deadline':DEADLINE.isoformat()})
        count=0
        try:
            while count<args.limit and datetime.now(timezone.utc)<DEADLINE:
                job=store.claim('sichuan_v4_capture')
                if not job:break
                try:
                    result=capture(job['payload']);store.finish(job['id'],'needs_browser',result)
                    print(job['payload']['city'],job['payload']['district'],'raw_v4_captured',result['source_url'],flush=True)
                except Exception as exc:
                    evidence=OUT/'failed-attempts'/job['id']/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                    evidence.mkdir(parents=True,exist_ok=True)
                    screenshot=''
                    try:
                        c.save(evidence/'actual-page.json',c.evaluate(c.CAPTURE_JS))
                        c.browser('screenshot',str((evidence/'actual-page.png').relative_to(ROOT)))
                        screenshot=str((evidence/'actual-page.png').relative_to(ROOT))
                    except Exception:pass
                    event={'id':job['id'],'province':'sichuan','city':job['payload']['city'],'district':job['payload']['district'],
                           'region_code':job['payload']['region_code'],'service':'劳动人事争议仲裁申请','type':'GUIDE_PAGE_UNAVAILABLE',
                           'url':job['payload']['summary']['url'],'occurred_at':clock(),'reason':str(exc),'attempts':job['attempts']+1,
                           'screenshot':screenshot,'actual_page_evidence':str((evidence/'actual-page.json').relative_to(ROOT)),
                           'delivery_status':'PENDING_OPENCLAW','final_status':'pending_recheck','remediation':'核对新版实际页面，不套用旧版解析器'}
                    c.save(OUT/'outbox'/(job['id']+'.json'),event);store.finish(job['id'],'failed',event)
                    print('FAILED',job['payload']['district'],str(exc),flush=True)
                count+=1;time.sleep(2)
        finally:
            try:c.browser('close')
            except Exception:pass
            c.save(OUT/'worker.json',{'pid':os.getpid(),'state':'batch_finished','finished_at':clock(),'jobs_this_run':count})


if __name__=='__main__':main()
