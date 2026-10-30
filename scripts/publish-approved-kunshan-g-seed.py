"""Guarded one-guide G seed append. Default CLI is read-only; no DB access."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import regional_jiangsu_oct31g as own

BASE_GUIDES_SHA256='4f98f18682ad3c8b1ef566df413246d7dbcc0bd2709b0c2be833e17c04b2d9ea'
DIRECTORY_SHA256='913daa7dd7bcbec570945fd7cc8ed08ae55b15c50665e5f8f4d967b62fc85ba8'
STAGE_SHA256='f794e50d5ba7fcc01d520625efeaa60a851fd2c01d5428b1305fd5634e32bc32'
FINAL_SHA256='c55b2c697c5a2668b6752ce6ea6bdfcea4670a4be41be11c55f4d23e131d8894'
BACKUP='.runtime/overnight-gap-closure-20261030/kunshan-g-seed-publication'
REPORT=own.QA_REPORT


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
    require(own.STAGE_SHA256==STAGE_SHA256 and own.PUBLICATION_SHA256==FINAL_SHA256,'Exact independent stage and final receipt pins required')
    approved=own.with_publication_evidence(own.prepare_candidate(root=root),root=root)
    expected={'province':'jiangsu','city':'苏州市','district':'昆山市','region_code':'320583','source_id':'d39444ab7f4bcaea2ea91473'}
    require(all(key in approved and own.exact(approved[key],value) for key,value in expected.items())
            and approved['published'] is True and approved['can_generate'] is True,'Only the approved own Kunshan projection may append')
    require(own.public_evidence(approved,root) is not None,'Complete own final public-root evidence required')
    require(len(guides) in {205,206},'Only exact baseline205 or completed206 is supported')
    previous=guides[:205]
    require(sha256(encoded(previous)).hexdigest()==BASE_GUIDES_SHA256 and generating(previous)==188,
            'Exact previous205 encoded records must remain unchanged; never rebuild or replace them')
    counts={'guides':len(guides),'generatable_localities':generating(guides),'directory_rows':3974}
    require(all(type(manifest.get(key)) is int and manifest[key]==value for key,value in counts.items()),'Existing public manifest counts differ')
    require(encoded(guides)==before['guides.json'],'Unexpected existing seed serialization or bytes')
    if len(guides)==206:
        require(own.exact(guides[-1],approved) and generating(guides)==189,'Existing G record differs; never overwrite it')
        return {'status':'already_published_exact','guides_after':206,'generatable_localities_after':189}
    require(sha256(before['guides.json']).hexdigest()==BASE_GUIDES_SHA256,'Unexpected baseline bytes')
    after_rows=guides+[approved]
    require(encoded(after_rows[:205])==before['guides.json'],'Previous205 encoded bytes changed')
    after_raw=encoded(after_rows)
    next_manifest={**manifest,'exported_at':datetime.now(timezone.utc).isoformat(),'guides':206,'generatable_localities':189,
                   'files':{**manifest['files'],'guides.json':sha256(after_raw).hexdigest()}}
    after={'guides.json':after_raw,'manifest.json':encoded(next_manifest)}
    result={'status':'dry_run' if not execute else 'published_worktree_seed_only','guides_before':205,'guides_after':206,
        'generatable_localities_before':188,'generatable_localities_after':189,'directory_rows':3974,
        'source_id':approved['source_id'],'stage_evidence_sha256':STAGE_SHA256,'final_evidence_sha256':FINAL_SHA256,
        'previous205_encoded_records_preserved':True,'directory_bytes_preserved':True,
        'guides_before_sha256':BASE_GUIDES_SHA256,'guides_after_sha256':sha256(after_raw).hexdigest(),
        'manifest_after_sha256':sha256(after['manifest.json']).hexdigest(),'directory_sha256':DIRECTORY_SHA256,
        'main_or_worktree_database_written':False,'frozen_source_or_evidence_changed':False,'model_calls':0,
        'published_at':next_manifest['exported_at'] if execute else None}
    if not execute:return result
    pending={name:own.path_at(root,'data/public-regions/'+name+'.kunshan-g-next') for name in before}
    reports={own.path_at(root,REPORT/'PUBLISHED-GUIDE.json'):encoded(approved),own.path_at(root,REPORT/'PUBLICATION.json'):encoded(result)}
    require(not any(path.exists() for path in [*pending.values(),*reports]),'Preserve existing pending files or publication reports')
    backup=own.path_at(root,BACKUP);backup.mkdir(parents=True,exist_ok=True)
    for name,body in before.items():
        path=own.path_at(root,BACKUP+'/'+name)
        if path.exists():require(path.read_bytes()==body,'Prior G publication backup differs; preserve it')
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
