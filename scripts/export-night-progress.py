"""Export public-only resumable evidence and honest stage counts; no model calls."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_directory import DirectoryStore,clock
from regional_guides import RegionalStore
from importlib import import_module
save=import_module('collect-national-directory').save
OUT=ROOT/'reports/nationwide-localization-20261023-night'


def main():
    directory=DirectoryStore(ROOT/'backend/data/regional-directory.sqlite')
    published=RegionalStore(ROOT/'backend/data/regional-guides.sqlite').inventory()
    captures=[]
    for file in sorted((OUT/'sichuan/captures').glob('*/guide.json')):
        g=json.loads(file.read_text('utf8'))
        captures.append({'province':g['province'],'city':g['city'],'district':g['district'],'region_code':g['region_code'],
                         'source_url':g['source_url'],'collected_at':g['collected_at'],'verified_at':g['verified_at'],
                         'capture':str(file.relative_to(ROOT).as_posix()),'materials':len(g['materials']),
                         'templates':len(g['templates']),'downloaded':sum(t['download_status']=='downloaded' for t in g['templates']),
                         'published':any(p['region_code']==g['region_code'] for p in published),
                         'can_generate':any(p['region_code']==g['region_code'] and any(t.get('can_generate') for t in p['templates']) for p in published)})
    with directory.connection() as db:
        failures=[{'id':r['id'],'payload':json.loads(r['payload']),'result':json.loads(r['result'] or '{}')} for r in db.execute("SELECT * FROM discovery_jobs WHERE state='failed'")]
        jobs={r['id']:dict(r) for r in db.execute('SELECT id,state,result,updated_at FROM discovery_jobs')}
    issues={}
    folders=[OUT/'outbox',OUT/'sichuan/outbox',OUT/'sichuan/v4/outbox']
    folders.extend((OUT/'cross-province').glob('*/outbox'))
    for folder in folders:
        if not folder.is_dir():continue
        for file in folder.glob('*.json'):
            value=json.loads(file.read_text('utf8'))
            for e in value if isinstance(value,list) else [value]:
                identity=e.get('id') or file.stem
                item={**e,'id':identity,'evidence_file':str(file.relative_to(ROOT).as_posix())}
                job=jobs.get(identity)
                if job and job['state']=='done' and item.get('final_status') not in {'verified','resolved_directory_classification'}:
                    item['resolution']={'at':job['updated_at'],'result':json.loads(job['result'] or '{}')}
                    item['final_status']='resolved_after_directory_recheck'
                issues[identity]=item
    national_sources=[{'file':str(f.relative_to(ROOT).as_posix()),**json.loads(f.read_text('utf8'))} for f in sorted((OUT/'raw-directory').glob('*.request.json'))]
    summary=directory.summary()
    v4=[json.loads(f.read_text('utf8')) for f in sorted((OUT/'sichuan/v4/captures').glob('*/manifest.json'))]
    cross=[]
    for file in sorted((OUT/'cross-province').glob('*/guide.json')):
        guide=json.loads(file.read_text('utf8'))
        cross.append({k:guide[k] for k in ['province','city','district','region_code','source_url','verified_at']})
        cross[-1].update(capture=str(file.relative_to(ROOT)),materials=len(guide['materials']),
                         own_downloaded_annexes=sum(t.get('download_status')=='downloaded' for t in guide['templates']),
                         published=any(p['province']==guide['province'] and p['city']==guide['city'] and p['district']==guide['district'] for p in published))
    result={'updated_at':clock(),'directory':summary,'directory_place_count':sum(a['count'] for a in summary['areas'] if a['level']==4),
            'provinces_with_district_directory':len({a['province'] for a in summary['areas'] if a['level']==4}),
            'exact_localities_with_published_guides':len(published),'exact_localities_with_generation':sum(any(t.get('can_generate') for t in g['templates']) for g in published),
            'night_new_guides_published':sum(g['city']!='成都市' for g in published),
            'night_staged_guides':len(captures),'night_staged_downloaded_annexes':sum(g['downloaded'] for g in captures),
            'new_portal_raw_browser_captures':len(v4),'cross_province_staged_guides':cross,
            'failed_jobs':failures,'public_events_saved':len(issues),'openclaw_receipt':'NONE_PENDING_ONLY','model_calls':0,
            'local_ollama_started':False,'directory_is_not_guide_coverage':True}
    save(OUT/'NIGHT-PROGRESS.json',result)
    pending_file=OUT/'PENDING-SOURCES.json'
    pending_sources=json.loads(pending_file.read_text('utf8')) if pending_file.exists() else []
    save(OUT/'SOURCE-INVENTORY.json',{'at':clock(),'pending_sources_not_coverage':pending_sources,'national_directory_sources':national_sources,'staged_sichuan_guides':captures,
                                    'sichuan_v4_raw_browser_staging':v4,'cross_province_staged_guides':cross,
                                    'published_localities':[{k:g[k] for k in ['province','city','district','region_code','source_id','source_url','verified_at']} for g in published]})
    save(OUT/'COLLECTION-ISSUES.json',list(issues.values()))
    print(json.dumps({k:v for k,v in result.items() if k not in {'directory','failed_jobs'}},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
