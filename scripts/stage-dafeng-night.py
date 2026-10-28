"""Own-source candidate with document gates; browser approval required to publish."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_jiangsu import parse_dafeng_capture,verify_dafeng_online_capture
from regional_adapters import with_reference_capabilities
from regional_guides import RegionalStore,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'
OUT=BASE/'staging-0358'


def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')


def prepare():
    manifest=json.loads((BASE/'capture-manifest.json').read_text('utf8'));raw=BASE/manifest['capture_file']
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=manifest['capture_sha256'] or len(manifest['sections_clicked'])!=12 or manifest['material_dialogs_opened']!=4:
        raise ValueError('Own raw guide or actual material interaction changed')
    capture=json.loads(raw.read_text('utf8'))
    entry=json.loads((BASE/'online-boundary-0345/online-check.json').read_text('utf8'))
    actual=verify_dafeng_online_capture(json.loads((BASE/'online-boundary-0345/before.json').read_text('utf8')),
        json.loads((BASE/'online-boundary-0345/after.json').read_text('utf8')),
        json.loads((BASE/'callback-source-0352/formal-guide.json').read_text('utf8')))
    if any(entry[k]!=v for k,v in actual.items()):raise ValueError('Own auth callback evidence changed')
    expected=parse_dafeng_capture(capture,entry);guide=json.loads((BASE/'guide.json').read_text('utf8'))
    if any(guide[k]!=expected[k] for k in ['province','city','district','region_code','source_url','fields','materials','channel']):
        raise ValueError('Candidate no longer matches its own capture')
    if len(guide['templates'])!=8 or {t['id'] for t in guide['templates']}!={t['id'] for t in expected['templates']}:raise ValueError('Own annex list changed')
    for t in guide['templates']:
        original=next(x for x in expected['templates'] if x['id']==t['id'])
        if any(t[k]!=original[k] for k in ['official_kind','source_url','region_code','download_url']):raise ValueError('Own annex identity changed')
        path=(ROOT/t['file']).resolve()
        if (not path.is_relative_to((ROOT/'templates/_docx/_regional/320904').resolve())
                or hashlib.sha256(path.read_bytes()).hexdigest()!=t['sha256'] or t.get('can_generate')):
            raise ValueError('Own original path/SHA or raw capability changed')
    result=with_reference_capabilities(guide)
    if sorted(k for t in result['templates'] if t.get('can_generate') for k in t['document_types'])!=['application','evidence']:
        raise ValueError('Both independently bound own forms required')
    qa=BASE/'document-qa';render=qa/'render-manifest.json';approved=json.loads((qa/'document-approval.json').read_text('utf8'))
    if approved['status']!='DOCUMENT_VISUALLY_REVIEWED' or approved['manifest_sha256']!=hashlib.sha256(render.read_bytes()).hexdigest():
        raise ValueError('Exact own output visual approval required')
    reviewed=json.loads(render.read_text('utf8'))
    if reviewed['source_id']!=digest(guide['source_url'])[:24]:raise ValueError('Wrong reviewed source')
    forms={(t['document_types'][0],t['id'],t['sha256']) for t in result['templates'] if t.get('can_generate')}
    if forms!={(c['kind'],c['annex_id'],c['source_sha256']) for c in reviewed['checks']}:raise ValueError('Wrong forms reviewed')
    for item in reviewed['checks']:
        if hashlib.sha256((ROOT/item['output']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Reviewed output changed')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
    guide=prepare();db=ROOT/'backend/data/regional-guides.sqlite';store=RegionalStore(db)
    if store.lookup('jiangsu','盐城市','大丰区')['source_id']:raise ValueError('Preserve already published own guide')
    if not a.apply:
        if OUT.exists():raise ValueError('Preserve prior stage')
        OUT.mkdir()
        with sqlite3.connect(db) as source,sqlite3.connect(OUT/'staging.sqlite') as stage:source.backup(stage)
        staged=RegionalStore(OUT/'staging.sqlite').put_guide(guide)
        save(OUT/'staging.json',{'at':now(),'source_id':staged['source_id'],'version':staged['version'],
            'guide_digest':digest(guide),'materials':4,'own_annexes':8,'own_adapters':2,'production_published':False,
            'browser_acceptance':'NOT_RUN','publication_gate':'Eight actual own candidate MCP checks + original document approval'})
        print(json.dumps({'own_stage_version':staged['version'],'source_id':staged['source_id'],'published':False}));return
    report=OUT/'browser-stage/result.json';approval=json.loads((OUT/'browser-approval.json').read_text('utf8'))
    if approval['sha256']!=hashlib.sha256(report.read_bytes()).hexdigest():raise ValueError('Exact browser approval required')
    ui=json.loads(report.read_text('utf8'))
    if ui['failed'] or len(ui['checks'])<8 or not all(c['passed'] for c in ui['checks']):raise ValueError('Browser acceptance incomplete')
    if json.loads((OUT/'staging.json').read_text('utf8'))['guide_digest']!=digest(guide):raise ValueError('Staged payload changed')
    with sqlite3.connect(db) as source,sqlite3.connect(OUT/'before.sqlite') as backup:source.backup(backup)
    result=store.put_guide(guide)
    save(OUT/'publication.json',{'at':now(),'source_id':result['source_id'],'version':result['version'],'new_guides':1,'new_generators':1})
    print(json.dumps({'own_published_version':result['version'],'source_id':result['source_id']}))


if __name__=='__main__':main()
