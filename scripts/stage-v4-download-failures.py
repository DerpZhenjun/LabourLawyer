"""Version exact guides with observed download failure; never fills substitutes."""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest,now
from sichuan_v4_capture import annotate_download_failure
BASE=ROOT/'reports/nationwide-localization-20261023-night'
BATCH=BASE/'batches/v4-forms-0215'
EVIDENCE=BATCH/'official-downloads-verified'
CODES={'510704000000':('绵阳市','游仙区'),'510723000000':('绵阳市','盐亭县')}


def prepare(store):
    updates=[]
    for code,(city,district) in CODES.items():
        guide=store.lookup('sichuan',city,district)
        if guide.get('region_code')!=code or any(t.get('can_generate') for t in guide['templates']):raise ValueError('Own guide-only source required')
        folder=EVIDENCE/code
        failure=json.loads((folder/'failure.json').read_text('utf8'))
        path=folder/'actual-network.json';network=json.loads(path.read_text('utf8'))
        updated=annotate_download_failure(guide,network,failure['at'],path.relative_to(ROOT).as_posix())
        if len(updated['warnings'])!=len(guide['warnings'])+1:raise ValueError('Warning not explicitly appended')
        updates.append((guide,updated))
    return updates


def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
    public=ROOT/'backend/data/regional-guides.sqlite';store=RegionalStore(public)
    updates=prepare(store);manifest=BATCH/'staging-failures.json'
    if a.apply:
        prior=json.loads(manifest.read_text('utf8'))
        if prior['guide_digest']!=digest(updates):raise ValueError('Source changed since stage')
        ui_path=BATCH/'browser-staging/result.json';ui=json.loads(ui_path.read_text('utf8'))
        if ui.get('failed')!=0 or set(ui.get('codes',[]))!=set(CODES) or len(ui.get('checks',[]))<5:raise ValueError('Actual UI failure-state acceptance required')
        if (BATCH/'publication-failures.json').exists():raise ValueError('Preserve prior publication')
        with sqlite3.connect(public) as s,sqlite3.connect(BATCH/'before-failures.sqlite') as d:s.backup(d)
        events=[]
        for old,g in updates:
            latest=store.put_guide(g)
            assert latest['source_id']==old['source_id']
            assert len(store.versions(g['province'],g['city'],g['district']))==2
            template=next(t for t in g['templates'] if t.get('download_http_status')==504)
            event={k:g[k] for k in ['province','city','district','region_code']}
            event.update(id=digest([g['source_id'],template['id'],'HTTP504',template['download_checked_at']])[:32],
                         service=g['service_name'],keyword='劳动人事争议仲裁申请',url=g['source_url'],
                         occurred_at=template['download_checked_at'],type='TEMPLATE_DOWNLOAD_FAILED',
                         reason='官网实际附件接口HTTP200后文件网关HTTP504；原文件未取得，不能适配或用其他地区文书代替。',
                         screenshot=str((EVIDENCE/g['region_code']/'failure.png').relative_to(ROOT).as_posix()),
                         attempts=1,final_status='pending_official_file_gateway',delivery_status='PENDING_OPENCLAW',
                         remediation='保留原指南和失败证据，生成关闭，后续低频核验；继续其他地区。',
                         network_evidence=template['download_network_evidence'],annex_id=template['id'])
            store.record_event(event);events.append(event)
        (BASE/'outbox/v4-own-attachment-http504.json').write_text(json.dumps(events,ensure_ascii=False,indent=2),'utf8')
        result={'at':now(),'codes':list(CODES),'state':'published_own_failure_versions','new_generators':0,
                'browser_report_sha256':hashlib.sha256(ui_path.read_bytes()).hexdigest(),'user_data_touched':False}
        (BATCH/'publication-failures.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
        print(json.dumps(result,ensure_ascii=False));return
    if manifest.exists():raise ValueError('Staging already exists, do not overwrite')
    stage=RegionalStore(BATCH/'staging-failures.sqlite')
    for g in store.inventory():stage.put_guide(g)
    for _,g in updates:stage.put_guide(g)
    result={'at':now(),'codes':list(CODES),'database':str(stage.path),'guide_digest':digest(updates),'new_generators':0}
    manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    for _,g in updates:
        (BATCH/(g['region_code']+'-failure-guide.json')).write_text(json.dumps(g,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
