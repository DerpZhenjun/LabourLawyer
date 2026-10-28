"""Source-preserving channel-only version; keep every approved annex unchanged."""
import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_guides import RegionalStore,digest,now,resolve_channel
from regional_jiangsu import verify_jianhu_online_capture
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu'
RAW=BASE/'online-recheck-tabs-0306'
OUT=BASE/'channel-publication-0300'


def prepare():
    before=json.loads((RAW/'before.json').read_text('utf8'));after=json.loads((RAW/'after.json').read_text('utf8'))
    entry=verify_jianhu_online_capture(before,after)
    entry['screenshot']=(RAW/'authentication-boundary.png').relative_to(ROOT).as_posix()
    entry['before_sha256']=hashlib.sha256((RAW/'before.json').read_bytes()).hexdigest()
    entry['after_sha256']=hashlib.sha256((RAW/'after.json').read_bytes()).hexdigest()
    db=ROOT/'backend/data/regional-guides.sqlite';store=RegionalStore(db)
    original=store.lookup('jiangsu','盐城市','建湖县')
    if original['source_id']!='ef1eb897ebf880c6f2a316f5' or original['source_url']!=entry['source_url']:raise ValueError('Own source identity changed')
    if original['channel']['online_status']!='unverified':raise ValueError('Channel was already updated; preserve it')
    for t in original['templates']:
        if hashlib.sha256((ROOT/t['file']).read_bytes()).hexdigest()!=t['sha256']:raise ValueError('Approved own annex changed')
    guide=copy.deepcopy(original)
    guide['channel']=resolve_channel({k:v['raw_value'] for k,v in guide['fields'].items()},guide['sections']['办理流程'],entry)
    assert guide['materials']==original['materials'] and guide['templates']==original['templates']
    return db,original,guide,entry


def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
    db,original,guide,entry=prepare()
    if not args.apply:
        if OUT.exists():raise ValueError('Never overwrite staged evidence')
        OUT.mkdir(parents=True)
        with sqlite3.connect(db) as source,sqlite3.connect(OUT/'staging.sqlite') as stage:source.backup(stage)
        result=RegionalStore(OUT/'staging.sqlite').put_guide(guide)
        c.save(OUT/'staging.json',{'database':str((OUT/'staging.sqlite').resolve()),'old_version':original['version'],
                    'new_version':result['version'],'source_id':result['source_id'],'new_generators':0,
                    'materials_and_templates_unchanged':True,'entry':entry})
        print(json.dumps({'staged_version':result['version'],'status':guide['channel']['online_status']}));return
    approval=json.loads((OUT/'browser-approval.json').read_text('utf8'))
    report=OUT/'browser-stage/result.json'
    if approval.get('sha256')!=hashlib.sha256(report.read_bytes()).hexdigest():raise ValueError('Exact stage browser approval required')
    ui=json.loads(report.read_text('utf8'))
    if ui.get('failed')!=0 or len(ui['checks'])<8 or not all(x['passed'] for x in ui['checks']):raise ValueError('Stage browser regression incomplete')
    staged=json.loads((OUT/'staging.json').read_text('utf8'))
    if staged['old_version']!=original['version'] or staged['entry']!=entry:raise ValueError('Source or channel evidence changed after staging')
    if (OUT/'publication.json').exists():raise ValueError('Already published; preserve history')
    with sqlite3.connect(db) as source,sqlite3.connect(OUT/'before.sqlite') as backup:source.backup(backup)
    store=RegionalStore(db);result=store.put_guide(guide)
    assert result['source_id']==original['source_id'] and result['version']!=original['version']
    assert result['materials']==original['materials'] and result['templates']==original['templates']
    events=[]
    for typ,reason,state in [('AUTH_REQUIRED','实际点击自身官网在线办理，读取统一身份认证表单，停于登录，未填写或提交申请','manual_authorization'),
                             ('ONLINE_CHANNEL_UNVERIFIED','先前入口待核实记录已通过自身实际跳转解决；仅核验登录边界，不保证登录后的业务可用','resolved_by_own_browser_navigation')]:
        events.append(store.record_event({'id':digest([result['source_id'],typ,entry['checked_at']])[:32],
            'province':'jiangsu','city':'盐城市','district':'建湖县','region_code':'320925','service':guide['service_name'],
            'type':typ,'url':entry['url'],'occurred_at':entry['checked_at'],'screenshot':entry['screenshot'],
            'reason':reason,'attempts':3,'final_status':state,'remediation':'用户自行前往官方渠道认证；本平台不代登录、不代提交'}))
    c.save(BASE/'outbox/online-boundary-0300.json',events)
    c.save(OUT/'publication.json',{'at':now(),'old_version':original['version'],'new_version':result['version'],
          'source_id':result['source_id'],'materials_and_templates_unchanged':True,'status':'auth_required','new_generators':0})
    print(json.dumps({'published_version':result['version'],'old_version':original['version'],'status':'auth_required'}))


if __name__=='__main__':main()
