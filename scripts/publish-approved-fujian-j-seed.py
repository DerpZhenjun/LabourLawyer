"""Guarded six-own-J seed append. Default read-only; never opens any database."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import regional_fujian_oct31j as own

BASE_GUIDES_SHA256='1db3cc8256d8731ea19b48d3a7734363961be090178a0aa811d82ae17aecb392'
BASE_MANIFEST_SHA256='1e6ceac14c6240b3756b6675692252ec5d532d9c8ef3840e9bfe32656dc95bdd'
DIRECTORY_SHA256='913daa7dd7bcbec570945fd7cc8ed08ae55b15c50665e5f8f4d967b62fc85ba8'
STAGE_SHA256='129474f0bba0f7d79363899ab21244fa595f0a356a0bb000c907fc5d62e2126e'
FINAL_SHA256='9860482c9772783927184e28686fb9779b1cce1a283c0d61902d8cde5dd57c45'
WORD_SHA256='346e74b6afee3a6d8366fcc3910aef11e958d06b898c7045b0988b4525cc501d'
PROVIDER_SHA256='fa8b61de2298a0dd978d889d060d6ffbe01bbf28f5747588f8ac01b5c6fe236e'
BACKUP='.runtime/overnight-gap-closure-20261030/fujian-j-seed-publication'
REPORT=Path('reports/overnight-gap-closure-20261030/localities/fujian-j/integration-qa-v1')
CODES=('350122','350123','350124','350125','350181','350182')
SOURCE_IDS=('bca45154d74905b963af83c9','e6dccff3468cba55aa9b5c09','4d74f378197bace2e63b05e9','3bfbebb0f7115a969c3d77be','9af3a0528483a9bb4fb67de5','e0b2adc9b9b0b10bc0eb9332')
DISTRICTS=('连江县','罗源县','闽清县','永泰县','福清市','长乐区')

def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def generating(rows):return sum(any(t.get('can_generate') is True for t in g['templates']) for g in rows)
def require(ok,message):
    if not ok:raise ValueError(message)

def approved_guides(root):
    require(type(FINAL_SHA256) is str and re.fullmatch('[a-f0-9]{64}',FINAL_SHA256)
        and own.ADAPTER=='fujian_six_own_blank_oct31j_v1' and own.STAGE_SHA256==STAGE_SHA256
        and own.PUBLICATION_SHA256==FINAL_SHA256 and own.WORD_SHA==WORD_SHA256,'Exact independent J source/Word/stage/final phase required')
    require(sha256(Path(own.__file__).read_bytes()).hexdigest()==PROVIDER_SHA256,'Reviewed J provider code changed')
    sources=own.source_files(root)
    require(len(sources)==97 and len(set(sources))==97,'Complete own J97 safe source projection required')
    for relative,pin in ((own.STAGE_RECEIPT,STAGE_SHA256),(own.PUBLICATION_RECEIPT,FINAL_SHA256),(own.WORD_MANIFEST,WORD_SHA256)):
        require(sha256(own.path_at(root,relative).read_bytes()).hexdigest()==pin,'Actual independent Root J receipt differs')
    # This pinned provider's canonical constructor validates the complete own
    # source, Word, stage and final trees. Repeating its validation through
    # display helpers would derive the same canonical guide several times.
    guides=[own._published(code,root) for code in CODES]
    for code,sid,district,g in zip(CODES,SOURCE_IDS,DISTRICTS,guides):
        meta=own.REGIONS[code]
        require(all(own.exact(g.get(k),v) for k,v in {'province':'fujian','city':'福州市','district':district,'region_code':code,'source_id':sid,
            'source_url':meta['source_url'],'source_version':meta['manifest_sha256'],'service_code':meta['service_code'],
            'published':True,'can_generate':True,'verification_status':'partial','guide_status':'partial','sample_contents_verified':False,
            'committee_full_name':None,'committee_autofill_allowed':False}.items()),'Only six canonical own partial J guides may publish')
        active=[t for t in g['templates'] if t.get('can_generate') is True]
        expected=meta['templates']
        require(len(g['templates'])==6 and len(active)==len(expected) and {t['id'] for t in active}=={v['file_id'] for v in expected.values()},'Only own J11 blank forms may generate')
        for kind,spec in expected.items():
            t=next(t for t in active if t['id']==spec['file_id'])
            require(all(own.exact(t.get(k),v) for k,v in {'official_kind':'blank','region_code':code,'material_id':spec['material_id'],
                'file':spec['source_file'],'sha256':spec['sha256'],'document_types':[kind],'adapter':own.ADAPTER}.items()),'Own J source/material/template/kind differs')
        inactive=[t for t in g['templates'] if t.get('can_generate') is not True]
        require(all(t['can_generate'] is False and t['document_types']==[] for t in inactive),'Samples, scanning instructions and filled-format references cannot generate')
        samples=[t for t in g['templates'] if t['official_kind']=='sample']
        require(len(samples)==3 and all(t['download_status']=='downloaded' and t['sample_contents_verified'] is False and t['can_generate'] is False for t in samples),'J samples remain content-unverified')
        require(len([t for t in g['templates'] if t['content_role']=='scanning_instructions_only'])==2,'Own scanning classification differs')
        require(code!='350125' or set(expected)=={'application'},'Yongtai evidence/inherited form refused')
    require(sum(len(t['document_types']) for g in guides for t in g['templates'] if t['can_generate'] is True)==11,'Exactly11 own J forms required')
    return guides

def _publication_expectations(before,after,seed_sha,manifest_sha):
    return {'status':'published_worktree_seed_only','guides_before':209,'guides_after':215,'generatable_localities_before':192,
        'generatable_localities_after':198,'directory_rows':3974,'source_ids':list(SOURCE_IDS),'region_codes':list(CODES),
        'stage_evidence_sha256':STAGE_SHA256,'final_evidence_sha256':FINAL_SHA256,'word_manifest_sha256':WORD_SHA256,
        'previous209_encoded_records_preserved':True,'directory_bytes_preserved':True,'guides_before_sha256':BASE_GUIDES_SHA256,
        'manifest_before_sha256':BASE_MANIFEST_SHA256,'guides_after_sha256':seed_sha,'manifest_after_sha256':manifest_sha,
        'directory_sha256':DIRECTORY_SHA256,'main_or_worktree_database_written':False,'live_database_written':False,
        'frozen_source_or_evidence_changed':False,'model_calls':0}

def publish(root,*,execute=False):
    require(root is not None and str(root).strip(),'Explicit release root required');require(type(execute) is bool,'Execution flag must be boolean')
    root=Path(root).resolve();public=own.path_at(root,'data/public-regions')
    before={n:own.path_at(root,'data/public-regions/'+n).read_bytes() for n in ('guides.json','manifest.json')}
    directory=own.path_at(root,'data/public-regions/directory.json').read_bytes()
    rows=json.loads(before['guides.json']);manifest=json.loads(before['manifest.json'])
    require(type(rows) is list and type(manifest) is dict and type(manifest.get('schema_version')) is int and manifest['schema_version']==1
        and manifest.get('release_id')=='oct30night-own-localities-v1','Unexpected public seed schema/release')
    require(type(manifest.get('files')) is dict and set(manifest['files'])=={'guides.json','directory.json'},'Unexpected public file set')
    require(manifest['files']=={'guides.json':sha256(before['guides.json']).hexdigest(),'directory.json':sha256(directory).hexdigest()},'Seed manifest integrity differs')
    require(sha256(directory).hexdigest()==DIRECTORY_SHA256 and type(json.loads(directory)) is list and len(json.loads(directory))==3974,'Exact directory3974 must remain byte-identical')
    require(len(rows) in {209,215} and encoded(rows)==before['guides.json'],'Only exact209 or complete215 canonical serialization supported')
    require(sha256(encoded(rows[:209])).hexdigest()==BASE_GUIDES_SHA256 and generating(rows[:209])==192,'Exact old209 encoded prefix required')
    require(all(type(manifest.get(k)) is int and manifest[k]==v for k,v in {'guides':len(rows),'generatable_localities':generating(rows),'directory_rows':3974}.items()),'Typed manifest counts differ')
    approved=approved_guides(root)
    reports={name:own.path_at(root,REPORT/name) for name in ('PUBLISHED-GUIDES.json','PUBLICATION.json')}
    if len(rows)==215:
        require(own.exact(rows[-6:],approved) and generating(rows)==198,'Existing J six rows differ; never overwrite or complete partial state')
        require(all(p.is_file() for p in reports.values()),'Existing215 lacks its complete publication metadata; refuse adoption')
        require(own.exact(json.loads(reports['PUBLISHED-GUIDES.json'].read_bytes()),approved),'Canonical published J metadata differs')
        receipt=json.loads(reports['PUBLICATION.json'].read_bytes())
        expected=_publication_expectations(None,None,sha256(before['guides.json']).hexdigest(),sha256(before['manifest.json']).hexdigest())
        require(all(k in receipt and own.exact(receipt[k],v) for k,v in expected.items())
            and type(receipt.get('published_at')) is str and receipt['published_at'] and receipt['published_at']==manifest.get('exported_at'),'Existing J publication receipt differs')
        return {'status':'already_published_exact','guides_after':215,'generatable_localities_after':198,'main_or_worktree_database_written':False,'live_database_written':False}
    require(sha256(before['guides.json']).hexdigest()==BASE_GUIDES_SHA256 and sha256(before['manifest.json']).hexdigest()==BASE_MANIFEST_SHA256,'Exact real209 baseline guide and manifest bytes required')
    require(not any(p.exists() for p in reports.values()),'Preserve existing J publication metadata; never overwrite')
    after_rows=rows+approved;after_raw=encoded(after_rows)
    require(encoded(after_rows[:209])==before['guides.json'] and generating(after_rows)==198,'Old209 prefix or expected198 generating count differs')
    next_manifest={**manifest,'exported_at':datetime.now(timezone.utc).isoformat(),'guides':215,'generatable_localities':198,
        'files':{**manifest['files'],'guides.json':sha256(after_raw).hexdigest()}}
    after={'guides.json':after_raw,'manifest.json':encoded(next_manifest)}
    result=_publication_expectations(before,after,sha256(after_raw).hexdigest(),sha256(after['manifest.json']).hexdigest())
    result.update(status='published_worktree_seed_only' if execute else 'dry_run',published_at=next_manifest['exported_at'] if execute else None)
    if not execute:return result
    pending={name:own.path_at(root,'data/public-regions/'+name+'.fujian-j-next') for name in before}
    require(not any(p.exists() for p in pending.values()),'Existing pending J files must be preserved')
    backup=own.path_at(root,BACKUP);backup.mkdir(parents=True,exist_ok=True)
    for name,body in before.items():
        path=own.path_at(root,BACKUP+'/'+name)
        if path.exists():require(path.read_bytes()==body,'Existing J backup differs; preserve it')
        else:
            with path.open('xb') as stream:stream.write(body)
    owned_pending=[];owned_reports=[];commit_started=False
    try:
        for name,path in pending.items():
            with path.open('xb') as stream:owned_pending.append(path);stream.write(after[name])
        require(all((public/n).read_bytes()==body for n,body in before.items()) and (public/'directory.json').read_bytes()==directory,'Input snapshot changed during preparation')
        commit_started=True
        pending['guides.json'].replace(public/'guides.json');pending['manifest.json'].replace(public/'manifest.json')
        require(all((public/n).read_bytes()==body for n,body in after.items()) and (public/'directory.json').read_bytes()==directory,'Post-write verification failed')
        for name,body in [('PUBLISHED-GUIDES.json',encoded(approved)),('PUBLICATION.json',encoded(result))]:
            with reports[name].open('xb') as stream:owned_reports.append(reports[name]);stream.write(body)
    except BaseException:
        if commit_started:
            require(all((public/n).read_bytes() in (before[n],after[n]) for n in before),'Unknown concurrent content; preserve backups, refuse overwrite')
            for name,body in before.items():(public/name).write_bytes(body)
        for path in owned_reports:path.unlink(missing_ok=True)
        raise
    finally:
        for path in owned_pending:path.unlink(missing_ok=True)
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args(argv)
    if args.execute and not (ROOT/'.git').is_file():raise RuntimeError('Execution restricted to an isolated Git worktree')
    try:result=publish(ROOT,execute=args.execute)
    except BaseException:
        print(json.dumps({'status':'refused_or_unconfirmed' if args.execute else 'refused','seed_files_written':None if args.execute else False,'database_written':False}));return 1
    print(json.dumps(result,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
