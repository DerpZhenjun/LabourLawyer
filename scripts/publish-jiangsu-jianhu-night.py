"""Stage or publish own-source guide + two forms, behind explicit visual QA."""
import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path
from importlib import import_module

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_guides import RegionalStore, digest, now
from regional_jiangsu import parse_jianhu_capture
from regional_adapters import with_reference_capabilities
c=import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    raw=OUT/'attempts/20261024-0227/formal-guide-final.json'
    manifest=json.loads((raw.parent/'capture-manifest.json').read_text('utf8'))
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=manifest['capture_sha256'] or len(manifest['sections_clicked'])!=12 or manifest['material_dialogs_opened']!=4:
        raise ValueError('Own actual browser capture changed or incomplete')
    capture=json.loads(raw.read_text('utf8'))
    entry=None
    expected=parse_jianhu_capture(capture,entry)
    guide=json.loads((OUT/'guide.json').read_text('utf8'))
    for key in ['province','city','district','region_code','source_url','fields','materials','channel']:
        if guide[key]!=expected[key]:raise ValueError('Staged source no longer matches actual browser capture: '+key)
    if {t['id'] for t in expected['templates']}!={t['id'] for t in guide['templates']}:raise ValueError('Own attachment IDs do not match')
    for t in guide['templates']:
        target=next(e for e in expected['templates'] if e['id']==t['id'])
        if any(t[k]!=target[k] for k in ['official_kind','region_code','source_url','download_url']):raise ValueError('Attachment source mismatch')
        path=(ROOT/t['file']).resolve()
        if not path.is_relative_to((ROOT/'templates/_docx/_regional/320925').resolve()):raise ValueError('File belongs to another locality')
        if t['download_status']!='downloaded' or hashlib.sha256(path.read_bytes()).hexdigest()!=t['sha256']:raise ValueError('Attachment file changed')
        if t['can_generate'] or t['document_types']:raise ValueError('Raw capture must not contain a crawler-granted generator')
    guide=with_reference_capabilities(guide)
    if sorted(k for t in guide['templates'] if t.get('can_generate') for k in t['document_types'])!=['application','evidence']:
        raise ValueError('Both own blank forms must be adapted before replacing the existing form')
    if args.apply:
        qa=OUT/'document-qa';approval=json.loads((qa/'approval.json').read_text('utf8'))
        manifest=qa/'render-manifest.json'
        if approval.get('status')!='VISUALLY_REVIEWED' or approval.get('manifest_sha256')!=hashlib.sha256(manifest.read_bytes()).hexdigest():
            raise ValueError('Fresh visual approval of this exact output manifest is required')
        reviewed=json.loads(manifest.read_text('utf8'))
        expected_forms={(t['document_types'][0],t['id'],t['sha256']) for t in guide['templates'] if t.get('can_generate')}
        if reviewed.get('source_id')!=digest(guide['source_url'])[:24] or {(c['kind'],c['annex_id'],c['source_sha256']) for c in reviewed['checks']}!=expected_forms:
            raise ValueError('Reviewed forms do not belong to this exact source and adapter')
        ui_path=(ROOT/approval['browser_report']).resolve()
        if not ui_path.is_relative_to(OUT.resolve()) or hashlib.sha256(ui_path.read_bytes()).hexdigest()!=approval.get('browser_report_sha256'):
            raise ValueError('Fresh browser report is required')
        ui=json.loads(ui_path.read_text('utf8'))
        if ui.get('failed')!=0 or len(ui.get('checks',[]))<8 or not all(c.get('passed') for c in ui['checks']):
            raise ValueError('Browser acceptance is not complete')
        for check in reviewed['checks']:
            if hashlib.sha256((ROOT/check['output']).read_bytes()).hexdigest()!=check['sha256']:raise ValueError('Reviewed output changed')
    folder=OUT/'publication'/uuid.uuid4().hex[:12];folder.mkdir(parents=True)
    with sqlite3.connect(ROOT/'backend/data/regional-guides.sqlite') as source,sqlite3.connect(folder/'staging.sqlite') as staging_db:source.backup(staging_db)
    staging=RegionalStore(folder/'staging.sqlite');staged=staging.put_guide(guide)
    result={'at':now(),'applied':args.apply,'source_id':staged['source_id'],'region':'江苏省/盐城市/建湖县',
            'materials':len(guide['materials']),'own_attachments':len(guide['templates']),
            'generation':'two_own_blank_forms','entry_status':guide['channel']['online_status']}
    c.save(OUT/'staging.json',{'database':str((folder/'staging.sqlite').resolve()),'source_id':staged['source_id'],'version':staged['version'],
                             'production_published':False,'result':str((folder/'result.json').relative_to(ROOT))})
    if args.apply:
        dbfile=ROOT/'backend/data/regional-guides.sqlite'
        with sqlite3.connect(dbfile) as source,sqlite3.connect(folder/'before.sqlite') as backup:source.backup(backup)
        store=RegionalStore(dbfile);c.save(folder/'before.json',store.lookup('jiangsu','盐城市','建湖县'))
        published=store.put_guide(guide);result['version']=published['version']
        events=[]
        for typ,reason in [('ONLINE_CHANNEL_UNVERIFIED','本地区官网显示网上办理，但本轮未独立核验其跳转；不发布未经核实的在线申请入口'),
                           ('MATERIAL_INFORMATION_MISSING','材料用途、适用情形及部分填报须知未由官网单列填写；原文留空，不补造规则')]:
            events.append(store.record_event({'id':digest([published['source_id'],typ])[:32],
                'province':'jiangsu','city':'盐城市','district':'建湖县','region_code':'320925',
                'service':guide['service_name'],'type':typ,'url':guide['source_url'],'occurred_at':guide['verified_at'],
                'screenshot':guide['evidence']['screenshot'],'reason':reason,'attempts':1,'final_status':'manual_review',
                'remediation':'公开来源和原附件可下载；模板填写须单独版式验收，不移植四川样表'}))
        c.save(OUT/'outbox/published-events.json',events)
    c.save(folder/'result.json',result)
    print(json.dumps({**result,'evidence':str((folder/'result.json').relative_to(ROOT))},ensure_ascii=False))


if __name__=='__main__':main()
