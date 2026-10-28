"""Audit existing own captures for the next QA batch; grants no capabilities."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_guides import RegionalStore,digest,now
from regional_capture import parse_sichuan_capture
from regional_adapters import REFERENCE_SHA256
from sichuan_night_evidence import own_region_metadata
from importlib import import_module
save=import_module('collect-national-directory').save
OUT=ROOT/'reports/nationwide-localization-20261023-night'


def main():
    published={g['region_code'] for g in RegionalStore(ROOT/'backend/data/regional-guides.sqlite').inventory()}
    ready=[];held=[]
    for file in sorted((OUT/'sichuan/captures').glob('*/guide.json')):
        guide=json.loads(file.read_text('utf8'));code=guide['region_code']
        if code in published:continue
        try:
            raw=file.parent/'dom.json'
            assert hashlib.sha256(raw.read_bytes()).hexdigest()==guide['evidence']['capture_sha256'],'Capture SHA changed'
            captured=json.loads(raw.read_text('utf8'))
            metadata=own_region_metadata(OUT/'sichuan/directory',code,guide['city'],guide['district'])
            reparsed=parse_sichuan_capture(captured,guide['city'],guide['district'],guide['channel'].get('entry_check'),region_metadata=metadata)
            for key in ['source_url','region_code','authority','fields','materials','sections','channel']:
                assert guide[key]==reparsed[key],f'Own raw guide mismatch: {key}'
            assert guide['materials'] and guide['authority'] and len(guide['sections'])==8,'Incomplete guide'
            assert {t['id'] for t in guide['templates']}=={t['id'] for t in reparsed['templates']},'Attachment IDs changed'
            for t in guide['templates']:
                own=next(r for r in reparsed['templates'] if r['id']==t['id'])
                assert all(t[k]==own[k] for k in ['official_kind','region_code','source_url','annex_id']),'Own attachment mismatch'
                local=(ROOT/t['file']).resolve()
                assert local.is_relative_to((ROOT/'templates/_docx/_regional'/code).resolve()),'Cross-locality file'
                assert t['download_status']=='downloaded' and hashlib.sha256(local.read_bytes()).hexdigest()==t['sha256'],'Download SHA changed'
            samples=[t for t in guide['templates'] if t['official_kind']=='sample' and t['sha256']==REFERENCE_SHA256 and t['original_name']=='仲裁申请书(模板).docx']
            assert len(samples)==1,'No uniquely audited combined sample layout'
            sample=samples[0]
            ready.append({k:guide[k] for k in ['province','city','district','region_code','source_url','collected_at','verified_at','verification_status']})
            ready[-1].update(source_id=digest(guide['source_url'])[:24],annex_id=sample['annex_id'],sample_file=sample['file'],sample_sha256=sample['sha256'],
                materials=len(guide['materials']),own_annexes=len(guide['templates']),channel=guide['channel']['online_status'],
                guide_file=str(file.relative_to(ROOT).as_posix()),capture_sha256=guide['evidence']['capture_sha256'],
                status='OWN_SOURCE_PREFLIGHT_ONLY_NOT_GENERATABLE')
        except (AssertionError,ValueError,KeyError,OSError) as error:
            held.append({'region_code':code,'city':guide['city'],'district':guide['district'],'reason':str(error)})
    save(OUT/'NEXT-SICHUAN-BATCH.json',{'at':now(),'ready_for_explicit_binding_and_document_QA':ready,'held':held,
        'published_by_this_script':0,'note':'Only own capture/file preflight. Explicit bindings, document generation/layout QA and actual UI tests are still required. Do not recollect successful captures.'})
    print(json.dumps({'own_sources_preflighted':len(ready),'held':len(held),'published':0},ensure_ascii=False))


if __name__=='__main__':main()
