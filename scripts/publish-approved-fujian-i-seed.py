"""Guarded two-own-I seed append; CLI defaults read-only and never opens a DB."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import regional_fujian_oct31i as own

BASE_GUIDES_SHA256='50a15968ae23ad4bee8f16f5ec6870ec7c722cd0eaa40ad36edff5c84de7cda9'
DIRECTORY_SHA256='913daa7dd7bcbec570945fd7cc8ed08ae55b15c50665e5f8f4d967b62fc85ba8'
STAGE_SHA256='d51d75f69935039d605a5627794b2ae280df1c8bc61bf54b449874d56dc16c6e'
FINAL_SHA256='60d0a9ec2b141a7704c5b72c9127fbbbdb2ca5f4c0f667dca50f4cee96690319'
BACKUP='.runtime/overnight-gap-closure-20261030/fujian-i-seed-publication'
REPORT=Path('reports/overnight-gap-closure-20261030/localities/fujian-i/integration-qa-v1')
CODES=('350103','350104')
SOURCE_IDS=('dcf9b71dee1c1cb61a3af637','9ab36db8d0ff985d9617a944')


def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def generating(rows):return sum(any(t.get('can_generate') is True for t in row['templates']) for row in rows)
def require(condition,message):
    if not condition:raise ValueError(message)


def approved_guides(root):
    require(type(FINAL_SHA256) is str and re.fullmatch('[a-f0-9]{64}',FINAL_SHA256)
        and own.STAGE_SHA256==STAGE_SHA256 and own.PUBLICATION_SHA256==FINAL_SHA256,'Exact independent I stage and final pins required')
    require(sha256(own.path_at(root,own.STAGE_RECEIPT).read_bytes()).hexdigest()==STAGE_SHA256
        and sha256(own.path_at(root,own.PUBLICATION_RECEIPT).read_bytes()).hexdigest()==FINAL_SHA256,'Actual Root I stage/final receipts differ')
    guides=[own.with_publication_evidence(own.staged_candidate(code,root=root),root=root) for code in CODES]
    for code,sid,district,g in zip(CODES,SOURCE_IDS,('台江区','仓山区'),guides):
        require(all(own.exact(g.get(k),v) for k,v in {'province':'fujian','city':'福州市','district':district,'region_code':code,'source_id':sid,
            'published':True,'can_generate':True,'verification_status':'partial','sample_contents_verified':False,'committee_full_name':None,'committee_autofill_allowed':False}.items()),'Only canonical own partial I projections may publish')
        active=[t for t in g['templates'] if t['can_generate'] is True]
        samples=[t for t in g['templates'] if t['official_kind']=='sample']
        references=[t for t in g['templates'] if t['content_role']=='scanning_instructions_only']
        require(len(active)==2 and {t['id'] for t in active}=={s['id'] for s in own.SPECS.values()}
            and all(t['official_kind']=='blank' and t['region_code']==code for t in active),'Only own I two verified blanks may generate')
        require(len(samples)==3 and all(t['download_status']=='downloaded' and t['sample_contents_verified'] is False
            and t['can_generate'] is False and t['document_types']==[] for t in samples),'I retrieved samples must remain content-unverified and unavailable for generation')
        require(len(references)==2 and all(t['can_generate'] is False and t['document_types']==[] for t in references),'I scanning references cannot generate')
        require(own.public_evidence(g,root) is not None,'Complete own explicit-root I evidence required')
    return guides


def publish(root,*,execute=False):
    require(root is not None and not (isinstance(root,str) and not root.strip()),'Explicit release root required')
    require(type(execute) is bool,'Execution flag must be boolean')
    root=Path(root).resolve();public=own.path_at(root,'data/public-regions')
    before={n:own.path_at(root,'data/public-regions/'+n).read_bytes() for n in ['guides.json','manifest.json']}
    directory=own.path_at(root,'data/public-regions/directory.json').read_bytes()
    rows=json.loads(before['guides.json']);manifest=json.loads(before['manifest.json'])
    require(type(rows) is list and type(manifest) is dict,'Unexpected seed shape')
    require(type(manifest.get('schema_version')) is int and manifest['schema_version']==1
        and manifest.get('release_id')=='oct30night-own-localities-v1','Unexpected seed schema/release')
    require(type(manifest.get('files')) is dict and set(manifest['files'])=={'guides.json','directory.json'},'Unexpected public files')
    for name,body in [('guides.json',before['guides.json']),('directory.json',directory)]:
        require(sha256(body).hexdigest()==manifest['files'][name],'Existing seed integrity differs')
    require(sha256(directory).hexdigest()==DIRECTORY_SHA256 and type(json.loads(directory)) is list and len(json.loads(directory))==3974,'Exact directory3974 bytes must remain unchanged')
    approved=approved_guides(root)
    require(len(rows) in {207,209},'Only exact baseline207 or complete209 supported; partial append refused')
    require(sha256(encoded(rows[:207])).hexdigest()==BASE_GUIDES_SHA256 and generating(rows[:207])==190,'Exact previous207 encoded rows must remain unchanged')
    require(encoded(rows)==before['guides.json'],'Existing seed serialization differs')
    counts={'guides':len(rows),'generatable_localities':generating(rows),'directory_rows':3974}
    require(all(type(manifest.get(k)) is int and manifest[k]==v for k,v in counts.items()),'Existing manifest counts differ')
    if len(rows)==209:
        require(own.exact(rows[-2:],approved) and generating(rows)==192,'Existing I pair differs; never overwrite')
        return {'status':'already_published_exact','guides_after':209,'generatable_localities_after':192}
    require(sha256(before['guides.json']).hexdigest()==BASE_GUIDES_SHA256,'Unexpected baseline bytes')
    after_rows=rows+approved;after_raw=encoded(after_rows)
    require(encoded(after_rows[:207])==before['guides.json'],'Previous207 encoded bytes changed')
    next_manifest={**manifest,'exported_at':datetime.now(timezone.utc).isoformat(),'guides':209,'generatable_localities':192,
        'files':{**manifest['files'],'guides.json':sha256(after_raw).hexdigest()}}
    after={'guides.json':after_raw,'manifest.json':encoded(next_manifest)}
    result={'status':'published_worktree_seed_only' if execute else 'dry_run','guides_before':207,'guides_after':209,
        'generatable_localities_before':190,'generatable_localities_after':192,'directory_rows':3974,
        'source_ids':list(SOURCE_IDS),'region_codes':list(CODES),'stage_evidence_sha256':STAGE_SHA256,'final_evidence_sha256':FINAL_SHA256,
        'previous207_encoded_records_preserved':True,'directory_bytes_preserved':True,'guides_before_sha256':BASE_GUIDES_SHA256,
        'guides_after_sha256':sha256(after_raw).hexdigest(),'manifest_after_sha256':sha256(after['manifest.json']).hexdigest(),
        'directory_sha256':DIRECTORY_SHA256,'main_or_worktree_database_written':False,'frozen_source_or_evidence_changed':False,
        'model_calls':0,'published_at':next_manifest['exported_at'] if execute else None}
    if not execute:return result
    pending={name:own.path_at(root,'data/public-regions/'+name+'.fujian-i-next') for name in before}
    reports={own.path_at(root,REPORT/'PUBLISHED-GUIDES.json'):encoded(approved),own.path_at(root,REPORT/'PUBLICATION.json'):encoded(result)}
    require(not any(p.exists() for p in [*pending.values(),*reports]),'Preserve existing pending files or publication reports')
    backup=own.path_at(root,BACKUP);backup.mkdir(parents=True,exist_ok=True)
    for name,body in before.items():
        path=own.path_at(root,BACKUP+'/'+name)
        if path.exists():require(path.read_bytes()==body,'Prior I backup differs; preserve it')
        else:
            with path.open('xb') as stream:stream.write(body)
    owned_pending=[];owned_reports=[];commit_started=False
    try:
        for name,path in pending.items():
            with path.open('xb') as stream:owned_pending.append(path);stream.write(after[name])
        require(all((public/n).read_bytes()==body for n,body in before.items()) and (public/'directory.json').read_bytes()==directory,'Snapshot changed while preparing append')
        commit_started=True
        pending['guides.json'].replace(public/'guides.json');pending['manifest.json'].replace(public/'manifest.json')
        require(all((public/n).read_bytes()==body for n,body in after.items()) and (public/'directory.json').read_bytes()==directory,'Snapshot post-write verification failed')
        for path,body in reports.items():
            with path.open('xb') as stream:owned_reports.append(path);stream.write(body)
    except BaseException:
        if commit_started:
            require(all((public/n).read_bytes() in [before[n],after[n]] for n in before),'Unexpected concurrent content; preserve backups and refuse overwrite')
            for name,body in before.items():(public/name).write_bytes(body)
        for path in owned_reports:path.unlink(missing_ok=True)
        raise
    finally:
        for path in owned_pending:path.unlink(missing_ok=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.execute and not (ROOT/'.git').is_file():raise RuntimeError('Execution restricted to isolated Git worktree')
    print(json.dumps(publish(ROOT,execute=args.execute),ensure_ascii=False))
