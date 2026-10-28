"""Stage and publish only the independently captured functional-area guide."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest,now
from regional_tianjin import parse_ecocity_capture
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city'
OUT=BASE/'guide-publication-0340'


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')


def prepare():
    raw={n:json.loads((BASE/'current-path-dom-0330'/f'{n}.json').read_text('utf8'))
         for n in ['guide','online-channel','official-annexes','current-service-portal','current-list']}
    files=json.loads((BASE/'native-downloads-0306/original-files.json').read_text('utf8'))
    guide=parse_ecocity_capture(raw,files)
    guide['capture_file']=(BASE/'current-path-dom-0330/guide.json').relative_to(ROOT).as_posix()
    guide['capture_sha256']=hashlib.sha256((ROOT/guide['capture_file']).read_bytes()).hexdigest()
    guide['evidence']={name:(BASE/f'current-path-dom-0330/{name}.png').relative_to(ROOT).as_posix() for name in raw}
    return guide


def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
    guide=prepare();database=ROOT/'backend/data/regional-guides.sqlite';store=RegionalStore(database)
    if store.lookup('tianjin','天津市','中新天津生态城').get('source_id'):raise ValueError('Already exists; preserve published version')
    if not args.apply:
        if OUT.exists():raise ValueError('Preserve prior stage evidence')
        OUT.mkdir(parents=True)
        with sqlite3.connect(database) as source,sqlite3.connect(OUT/'staging.sqlite') as stage:source.backup(stage)
        result=RegionalStore(OUT/'staging.sqlite').put_guide(guide)
        save(OUT/'staging.json',{'guide':result,'payload_digest':digest(guide)})
        print(json.dumps({'staged_source':result['source_id'],'version':result['version'],'guide_only':True}));return
    ui_file=OUT/'browser-stage/result.json';ui=json.loads(ui_file.read_text('utf8'))
    approval=json.loads((OUT/'browser-approval.json').read_text('utf8'))
    if (ui['failed'] or len(ui['checks'])<7 or not all(c['passed'] for c in ui['checks'])
            or approval.get('sha256')!=hashlib.sha256(ui_file.read_bytes()).hexdigest()):raise ValueError('Actual browser approval required')
    if json.loads((OUT/'staging.json').read_text('utf8'))['payload_digest']!=digest(guide):raise ValueError('Staged source changed')
    with sqlite3.connect(database) as source,sqlite3.connect(OUT/'before.sqlite') as backup:source.backup(backup)
    result=store.put_guide(guide);events=[]
    for typ,reason,state in [
        ('ONLINE_APPLICATION_UNAVAILABLE','实际点击官网在线办事栏目：此事项未开通在线受理功能。属于办理能力限制，不是技术故障。','verified_window_only'),
        ('OFFICIAL_SOURCE_CONFLICT','指南电话022-66179792与现行人社栏目022-66386789、022-66328970不同，保留双来源。','manual_confirmation_required'),
        ('SOURCE_STALE','现行目录仍链接本指南，但具体内容更新时间未公示，前往窗口前应确认。','current_catalogue_link_verified_content_date_unknown')]:
        events.append(store.record_event({'id':digest([result['source_id'],typ,result['verified_at']])[:32],
            'province':'tianjin','city':'天津市','district':'中新天津生态城','region_code':guide['region_code'],
            'service':guide['service_name'],'type':typ,'url':guide['source_url'],'reason':reason,'final_status':state,
            'screenshot':guide['evidence']['online-channel' if typ=='ONLINE_APPLICATION_UNAVAILABLE' else 'current-service-portal'],
            'remediation':'保留自身来源及不确定性，不扩展至整个天津或滨海新区；请机构确认'}))
    outbox=BASE/'outbox';outbox.mkdir(exist_ok=True);save(outbox/'guide-publication-0340.json',events)
    save(OUT/'publication.json',{'at':now(),'source_id':result['source_id'],'version':result['version'],
        'new_guides':1,'new_generators':0,'materials':5,'own_originals':2,'openclaw':'PENDING_OPENCLAW'})
    print(json.dumps({'published_source':result['source_id'],'version':result['version'],'guide_only':True}))


if __name__=='__main__':main()
