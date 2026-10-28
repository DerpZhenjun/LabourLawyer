"""Preflight jiq4 guide-only additions; no private DB, models or adapters."""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_capture import load_sichuan_v4_capture
from regional_guides import RegionalStore,digest,now
from sichuan_night_evidence import own_region_metadata
OUT=ROOT/'reports/nationwide-localization-20261023-night'
RAW=OUT/'sichuan/v4/captures'


def prepare():
    guides=[]
    for path in sorted(RAW.glob('*/manifest.json')):
        manifest=json.loads(path.read_text('utf8'))
        metadata=own_region_metadata(OUT/'sichuan/directory',manifest['region_code'],manifest['city'],manifest['district'])
        guide=load_sichuan_v4_capture(path.parent,metadata)
        guide['evidence']['manifest']=path.relative_to(ROOT).as_posix()
        basic=path.parent/manifest['sections'][0]['file']
        guide['evidence']['screenshot']=basic.with_suffix('.png').relative_to(ROOT).as_posix()
        guides.append(guide)
    if len({g['region_code'] for g in guides})!=len(guides):raise ValueError('Duplicate locality')
    return guides


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    folder=args.output.resolve()
    if not folder.is_relative_to((OUT/'batches').resolve()):raise ValueError('Night batch path required')
    guides=prepare();public=ROOT/'backend/data/regional-guides.sqlite'
    store=RegionalStore(public)
    if args.apply:
        stage=json.loads((folder/'staging.json').read_text('utf8'))
        ui_path=folder/'browser-staging/result.json';ui=json.loads(ui_path.read_text('utf8'))
        if (stage['guide_digest']!=digest(guides) or ui.get('failed')!=0
                or set(ui.get('codes',[]))!={g['region_code'] for g in guides}
                or len(ui.get('checks',[]))<len(guides)+4):raise ValueError('Guide-only staging/browser approval missing or changed')
        if (folder/'publication.json').exists():raise ValueError('Already published; do not overwrite evidence')
        # Add only previously absent exact localities. Never replace functioning generators.
        for g in guides:
            if store.lookup(g['province'],g['city'],g['district']).get('source_id'):raise ValueError('Existing source requires separate version review')
        with sqlite3.connect(public) as source,sqlite3.connect(folder/'before.sqlite') as target:source.backup(target)
        events=[]
        for g in guides:
            store.put_guide(g)
            common={k:g[k] for k in ['province','city','district','region_code']}
            common.update(service=g['service_name'],url=g['source_url'],occurred_at=g['verified_at'],
                          screenshot=g['evidence']['screenshot'],attempts=1,delivery_status='PENDING_OPENCLAW',
                          final_status='pending_local_verification',remediation='只展示自己的原文；附件与网办未核验不开放生成或在线申请')
            descriptions=[('ONLINE_CHANNEL_UNVERIFIED','只核验到办理形式原文；流程通用网上办理标签不等于实际网上入口'),
                          ('OFFICIAL_TEMPLATE_NOT_FOUND','尚未完成本地区可填写官方文书下载及版式核验；不借用其他地区模板')]
            if not g['materials']:descriptions.append(('MATERIAL_INFORMATION_MISSING','官方材料栏目显示暂无申请材料；不能解释成无需材料'))
            for kind,reason in descriptions:
                event={**common,'type':kind,'reason':reason};event['id']=digest(event)[:32]
                store.record_event(event);events.append(event)
        (OUT/'outbox/v4-guide-only-events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2),'utf8')
        result={'at':now(),'state':'published_guide_only','codes':[g['region_code'] for g in guides],
                'guides':len(guides),'new_generators':0,'backup':'before.sqlite',
                'browser_report_sha256':hashlib.sha256(ui_path.read_bytes()).hexdigest()}
        (folder/'publication.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
        print(json.dumps(result,ensure_ascii=False));return
    if folder.exists():raise ValueError('Fresh batch output required')
    folder.mkdir(parents=True)
    stage=RegionalStore(folder/'staging.sqlite')
    # Own-source guide-only evidence + existing generators permit no-regression checks.
    for g in store.inventory():stage.put_guide(g)
    for g in guides:
        if store.lookup(g['province'],g['city'],g['district']).get('source_id'):raise ValueError('Cannot overwrite existing exact source')
        stage.put_guide(g)
        destination=folder/'guides'/g['region_code'];destination.mkdir(parents=True)
        (destination/'guide.json').write_text(json.dumps(g,ensure_ascii=False,indent=2),'utf8')
    result={'at':now(),'database':str(folder/'staging.sqlite'),'codes':[g['region_code'] for g in guides],
            'guides':len(guides),'materials':sum(len(g['materials']) for g in guides),
            'annex_controls':sum(len(g['templates']) for g in guides),'new_generators':0,
            'guide_digest':digest(guides),'state':'staged_guide_only','model_calls':0}
    (folder/'staging.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
