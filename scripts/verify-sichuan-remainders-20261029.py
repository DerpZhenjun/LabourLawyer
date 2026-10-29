"""Recheck three previously failed own guides, without changing their old evidence or DB."""
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'backend'))
from regional_capture import load_sichuan_v4_capture
from regional_guides import RegionalStore


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    capture=importlib.import_module('collect-sichuan-v4-night');browser=capture.c
    raw=ROOT/'.runtime/nationwide-verification-20261029/sichuan'
    public=ROOT/'reports/nationwide-verification-20261029/sichuan'
    raw.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
    capture.OUT=raw;browser.OUT=raw
    browser.ENV={**os.environ,'AGENT_BROWSER_SESSION':'sc-oct29-verify'}
    original=browser.browser
    def compatible(*args):
        if args[0]=='screenshot' and len(args)==2:
            return original('screenshot','body',str(Path(args[1]).resolve()).replace('\\','/'))
        return original(*args)
    browser.browser=compatible
    codes={'510603000000','510623000000','510727000000'}
    # Read public queue payloads without constructors/migrations/claiming jobs.
    with sqlite3.connect((ROOT/'backend/data/regional-directory.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        targets=[json.loads(r[0]) for r in db.execute("SELECT payload FROM discovery_jobs WHERE kind='sichuan_v4_capture' AND state='failed'")
                 if json.loads(r[0]).get('region_code') in codes]
    published=json.loads((ROOT/'data/public-regions/guides.json').read_text('utf-8'))
    existing={g['region_code'] for g in published}
    results=[]
    try:
        for target in targets:
            code=target['region_code']
            if code in existing:continue
            destination=public/(code+'-guide.json')
            if destination.exists():
                results.append({'code':code,'state':'retained_existing_capture'});continue
            try:
                capture.capture(target)
                guide=load_sichuan_v4_capture(raw/'captures'/code,target['region_metadata'])
                isolated=RegionalStore(raw/'parsed-guides.sqlite');isolated.put_guide(guide)
                guide=isolated.lookup(guide['province'],guide['city'],guide['district'])
                guide.pop('evidence',None)
                destination.write_bytes((json.dumps(guide,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
                result={'code':code,'city':guide['city'],'district':guide['district'],'state':'candidate_not_published',
                        'materials':len(guide['materials']),'annex_controls':len(guide['templates']),
                        'source_url':guide['source_url'],'generation_enabled':False}
            except Exception as exc:
                result={'code':code,'city':target['city'],'district':target['district'],'state':'pending_recheck',
                        'reason':str(exc),'source_url':target['summary']['url'],'absence_verified':False}
            results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
            (raw/'recheck-result.json').write_bytes((json.dumps(results,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    finally:
        original('close')


if __name__=='__main__':main()
