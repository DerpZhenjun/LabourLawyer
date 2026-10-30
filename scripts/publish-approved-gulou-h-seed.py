"""Guarded one-guide H seed append. Default CLI is read-only; no DB access."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
import re
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import regional_fujian_oct31h as own

BASE_GUIDES_SHA256='92f84e5201c49ecf6664391a7423f16bcc84a81f8a84c173a805576e49ac0db1'
DIRECTORY_SHA256='913daa7dd7bcbec570945fd7cc8ed08ae55b15c50665e5f8f4d967b62fc85ba8'
STAGE_SHA256='76b891e7c44261b8a77dc7fbfa190ce06d0b377ad2934b7654181d3de4c9fb34'
FINAL_SHA256='f2dd9dbb759288f4fbbedcb311ea00fc13c69814374982ba43aa3cce03fa22d1'
BACKUP='.runtime/overnight-gap-closure-20261030/gulou-h-seed-publication'
REPORT=Path(own.QA_REPORT)


def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


def generating(rows):return sum(any(t.get('can_generate') is True for t in row['templates']) for row in rows)


def require(condition,message):
    if not condition:raise ValueError(message)


def publish(root,*,execute=False):
    require(root is not None and not (isinstance(root,str) and not root.strip()),'Explicit release root required')
    require(type(execute) is bool,'Execution flag must be a boolean')
    root=Path(root).resolve();public=own.path_at(root,'data/public-regions')
    before={name:own.path_at(root,'data/public-regions/'+name).read_bytes() for name in ['guides.json','manifest.json']}
    directory=own.path_at(root,'data/public-regions/directory.json').read_bytes()
    guides=json.loads(before['guides.json']);manifest=json.loads(before['manifest.json'])
    require(type(guides) is list and type(manifest) is dict,'Unexpected public snapshot shape')
    require(type(manifest.get('schema_version')) is int and manifest['schema_version']==1,'Unexpected seed schema')
    require(type(manifest.get('files')) is dict and set(manifest['files'])=={'guides.json','directory.json'},'Unexpected public files')
    for name,body in [('guides.json',before['guides.json']),('directory.json',directory)]:
        require(sha256(body).hexdigest()==manifest['files'][name],'Existing public snapshot integrity differs')
    require(sha256(directory).hexdigest()==DIRECTORY_SHA256 and type(json.loads(directory)) is list and len(json.loads(directory))==3974,
            'Exact existing directory bytes must stay unchanged')
    require(type(FINAL_SHA256) is str and re.fullmatch('[a-f0-9]{64}',FINAL_SHA256)
            and own.STAGE_SHA256==STAGE_SHA256 and own.PUBLICATION_SHA256==FINAL_SHA256,'Exact independent stage and final receipt pins required')
    approved=own.with_publication_evidence(own.prepare_candidate(root=root),root=root)
    expected={'province':'fujian','city':'福州市','district':'鼓楼区','region_code':'350102','source_id':'3e2246aa2a534d2b37f6c6c5'}
    require(all(key in approved and own.exact(approved[key],value) for key,value in expected.items())
            and approved['published'] is True and approved['can_generate'] is True,'Only the approved own Gulou projection may append')
    require(approved['verification_status']=='partial' and approved['sample_contents_verified'] is False,
            'Publication must preserve H partial-source and unverified-sample status')
    active=[t for t in approved['templates'] if t['can_generate'] is True]
    samples=[t for t in approved['templates'] if t['official_kind']=='sample']
    references=[t for t in approved['templates'] if t['content_role']=='scanning_instructions_only']
    require(len(active)==2 and {t['id'] for t in active}==set(own.ANNEX.values())
            and all(t['official_kind']=='blank' for t in active),'Only H own application/evidence blanks may generate')
    require(len(samples)==3 and all(t['download_status']=='unverified' and t['can_generate'] is False
            and t['document_types']==[] for t in samples),'Unretrieved H sample contents cannot acquire capabilities')
    require(len(references)==1 and references[0]['can_generate'] is False and references[0]['document_types']==[],
            'Scanning reference remains download-only')
    require(own.public_evidence(approved,root) is not None,'Complete own final public-root evidence required')
    require(len(guides) in {206,207},'Only exact baseline206 or completed207 is supported')
    previous=guides[:206]
    require(sha256(encoded(previous)).hexdigest()==BASE_GUIDES_SHA256 and generating(previous)==189,
            'Exact previous206 encoded records must remain unchanged; never rebuild or replace them')
    counts={'guides':len(guides),'generatable_localities':generating(guides),'directory_rows':3974}
    require(all(type(manifest.get(key)) is int and manifest[key]==value for key,value in counts.items()),'Existing public manifest counts differ')
    require(encoded(guides)==before['guides.json'],'Unexpected existing seed serialization or bytes')
    if len(guides)==207:
        require(own.exact(guides[-1],approved) and generating(guides)==190,'Existing H record differs; never overwrite it')
        return {'status':'already_published_exact','guides_after':207,'generatable_localities_after':190}
    require(sha256(before['guides.json']).hexdigest()==BASE_GUIDES_SHA256,'Unexpected baseline bytes')
    after_rows=guides+[approved]
    require(encoded(after_rows[:206])==before['guides.json'],'Previous206 encoded bytes changed')
    after_raw=encoded(after_rows)
    next_manifest={**manifest,'exported_at':datetime.now(timezone.utc).isoformat(),'guides':207,'generatable_localities':190,
                   'files':{**manifest['files'],'guides.json':sha256(after_raw).hexdigest()}}
    after={'guides.json':after_raw,'manifest.json':encoded(next_manifest)}
    result={'status':'dry_run' if not execute else 'published_worktree_seed_only','guides_before':206,'guides_after':207,
        'generatable_localities_before':189,'generatable_localities_after':190,'directory_rows':3974,
        'source_id':approved['source_id'],'stage_evidence_sha256':STAGE_SHA256,'final_evidence_sha256':FINAL_SHA256,
        'previous206_encoded_records_preserved':True,'directory_bytes_preserved':True,
        'guides_before_sha256':BASE_GUIDES_SHA256,'guides_after_sha256':sha256(after_raw).hexdigest(),
        'manifest_after_sha256':sha256(after['manifest.json']).hexdigest(),'directory_sha256':DIRECTORY_SHA256,
        'main_or_worktree_database_written':False,'frozen_source_or_evidence_changed':False,'model_calls':0,
        'published_at':next_manifest['exported_at'] if execute else None}
    if not execute:return result
    pending={name:own.path_at(root,'data/public-regions/'+name+'.gulou-h-next') for name in before}
    reports={own.path_at(root,REPORT/'PUBLISHED-GUIDE.json'):encoded(approved),own.path_at(root,REPORT/'PUBLICATION.json'):encoded(result)}
    require(not any(path.exists() for path in [*pending.values(),*reports]),'Preserve existing pending files or publication reports')
    backup=own.path_at(root,BACKUP);backup.mkdir(parents=True,exist_ok=True)
    for name,body in before.items():
        path=own.path_at(root,BACKUP+'/'+name)
        if path.exists():require(path.read_bytes()==body,'Prior H publication backup differs; preserve it')
        else:
            with path.open('xb') as stream:stream.write(body)
    owned_pending=[];owned_reports=[];commit_started=False
    try:
        for name,path in pending.items():
            with path.open('xb') as stream:owned_pending.append(path);stream.write(after[name])
        require(all((public/name).read_bytes()==body for name,body in before.items())
                and (public/'directory.json').read_bytes()==directory,'Public snapshot changed while preparing append')
        commit_started=True
        pending['guides.json'].replace(public/'guides.json')
        pending['manifest.json'].replace(public/'manifest.json')
        require(all((public/name).read_bytes()==body for name,body in after.items())
                and (public/'directory.json').read_bytes()==directory,'Public snapshot verification failed')
        for path,body in reports.items():
            with path.open('xb') as stream:owned_reports.append(path);stream.write(body)
    except BaseException:
        if commit_started:
            require(all((public/name).read_bytes() in [before[name],after[name]] for name in before),
                    'Concurrent unexpected public content; preserved backups, refusing to overwrite it')
            for name,body in before.items():(public/name).write_bytes(body)
        for path in owned_reports:path.unlink(missing_ok=True)
        raise
    finally:
        for path in owned_pending:path.unlink(missing_ok=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Append only after independent root review')
    args=parser.parse_args()
    if args.execute and not (ROOT/'.git').is_file():raise RuntimeError('Execution is restricted to an isolated Git worktree')
    print(json.dumps(publish(ROOT,execute=args.execute),ensure_ascii=False))
