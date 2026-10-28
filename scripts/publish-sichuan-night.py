"""Stage only explicitly bound, independently captured Sichuan localities.

Default is preflight. --apply backs up the public regional DB before publication;
it never touches the user/case database or enables unbound staged captures.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_adapters import EXTRA_BINDINGS, with_reference_capabilities
from regional_capture import parse_sichuan_capture
from regional_guides import RegionalStore, digest, now
from sichuan_night_evidence import own_region_metadata

OUT=ROOT/'reports/nationwide-localization-20261023-night'


def prepare(code):
    folder=OUT/'sichuan/captures'/code
    guide=json.loads((folder/'guide.json').read_text('utf8'))
    raw_file=folder/'dom.json'
    if hashlib.sha256(raw_file.read_bytes()).hexdigest()!=guide['evidence']['capture_sha256']:
        raise ValueError('真实浏览器证据已变化')
    raw=json.loads(raw_file.read_text('utf8'))
    metadata=own_region_metadata(OUT/'sichuan/directory',code,guide['city'],guide['district'])
    reparsed=parse_sichuan_capture(raw,guide['city'],guide['district'],guide['channel'].get('entry_check'),region_metadata=metadata)
    if reparsed['source_url']!=guide['source_url'] or reparsed['materials']!=guide['materials']:
        raise ValueError('指南与真实捕获不一致')
    if [t['id'] for t in reparsed['templates']]!=[t['id'] for t in guide['templates']]:
        raise ValueError('附件列表与实际官网控件不一致')
    for t in guide['templates']:
        file=(ROOT/t.get('file','')).resolve()
        if t['source_url']!=guide['source_url'] or t['region_code']!=code or not file.is_relative_to((ROOT/'templates/_docx/_regional'/code).resolve()):
            raise ValueError('跨地区附件来源或路径')
        if t.get('download_status')!='downloaded' or hashlib.sha256(file.read_bytes()).hexdigest()!=t.get('sha256'):
            raise ValueError('当地附件未下载或已变化')
    guide=with_reference_capabilities(guide)
    if not any(t.get('can_generate') for t in guide['templates']):
        raise ValueError('地区尚未显式适配，不允许按哈希或省份放行')
    return guide


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--codes',required=True);parser.add_argument('--qa-dir',type=Path,default=OUT/'document-qa');args=parser.parse_args()
    codes=args.codes.split(',')
    if not all(c in EXTRA_BINDINGS for c in codes):raise ValueError('请求地区未列入审核白名单')
    guides=[prepare(code) for code in codes]
    run=OUT/'publication'/uuid.uuid4().hex[:12];run.mkdir(parents=True)
    staging=RegionalStore(run/'staging.sqlite')
    for g in guides:staging.put_guide(g)
    result={'at':now(),'codes':codes,'state':'preflight_passed','apply':args.apply,'model_calls':0}
    if args.apply:
        qa=args.qa_dir.resolve()
        if not qa.is_relative_to(OUT.resolve()):raise ValueError('QA evidence must remain within this night report')
        approval=json.loads((qa/'approval.json').read_text('utf8'))
        manifest_file=qa/'render-manifest.json'
        if approval['status']!='VISUALLY_REVIEWED' or hashlib.sha256(manifest_file.read_bytes()).hexdigest()!=approval['manifest_sha256'] or not set(codes).issubset(approval['codes']):
            raise ValueError('本批文书视觉检查尚未通过或QA产物已变化')
        if approval.get('browser_report'):
            ui_path=(ROOT/approval['browser_report']).resolve()
            if not ui_path.is_relative_to(OUT.resolve()) or hashlib.sha256(ui_path.read_bytes()).hexdigest()!=approval.get('browser_report_sha256'):
                raise ValueError('本批浏览器报告已变化')
            ui=json.loads(ui_path.read_text('utf8'))
            if set(ui.get('codes',[]))!=set(codes) or ui.get('failed')!=0 or len(ui.get('checks',[]))<len(codes)+4:
                raise ValueError('本批浏览器验收未完成')
        manifest=json.loads(manifest_file.read_text('utf8'))
        for code in codes:
            checks=[c for c in manifest['checks'] if c['code']==code]
            if {c['kind'] for c in checks}!={'application','evidence'}:raise ValueError('文书QA覆盖不完整')
            for c in checks:
                if hashlib.sha256((ROOT/c['output']).read_bytes()).hexdigest()!=c['sha256']:raise ValueError('QA文书字节已变化')
        database=ROOT/'backend/data/regional-guides.sqlite'
        with sqlite3.connect(database) as source,sqlite3.connect(run/'before.sqlite') as destination:source.backup(destination)
        store=RegionalStore(database)
        before=store.inventory()
        (run/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),'utf8')
        for g in guides:
            published=store.put_guide(g)
            common={k:published[k] for k in ['province','city','district','region_code']}
            common.update(url=g['source_url'],service=g['service_name'],occurred_at=g['collected_at'],screenshot=g['evidence']['screenshot'])
            status=g['channel']['online_status']
            kind='ONLINE_APPLICATION_UNAVAILABLE' if status=='unavailable' else 'AUTH_REQUIRED' if status=='auth_required' else 'OFFICIAL_SOURCE_CONFLICT' if status=='conflict' else 'ONLINE_CHANNEL_UNVERIFIED'
            data={**common,'type':kind,'reason':'独立核对本地区办理形式及实际入口：'+status,'final_status':'manual_review' if status in {'conflict','unverified'} else 'verified','remediation':'显示本地原文和已核验入口，不代交申请'}
            store.record_event({**data,'id':digest(data)[:32]})
        result.update(state='published',inventory_count=len(store.inventory()),source_ids=[g['source_id'] for g in store.inventory() if g['region_code'] in codes])
        pending=[e for e in store.events() if e['delivery_status']=='PENDING_OPENCLAW']
        (OUT/'outbox').mkdir(exist_ok=True)
        (OUT/'outbox/published-guide-events.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2),'utf8')
    (run/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({'result':str(run/'result.json'),**result},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
