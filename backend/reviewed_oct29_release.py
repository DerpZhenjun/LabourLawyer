"""Reviewed nine-locality data delta. Import/prepare never writes a live DB.

CLI apply is deliberately bound to the default main stores and port 8000.
It does not start/restart services, call a model, replace the directory, or
overwrite an existing locality. All changes have consistent SQLite backups.
"""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
from urllib.request import urlopen
from uuid import uuid4

from candidate_review import SOURCE_FILES, HUNAN_FILES, verify as verify_candidate
from regional_adapters import (with_reference_capabilities, checked_reference_adapter,
    NINGBO_ADAPTER, OCT29_JIANGSU_ADAPTER, FEIDONG_ADAPTER, HUNAN_ADAPTER)
from regional_guides import digest, official_content, region_key
from regional_oct29_bindings import jiangsu_binding
from regional_public_provenance import public_evidence, approved_report_attachment

ROOT=Path(__file__).resolve().parents[1]
RELEASE_ID='oct29-own-localities-v1'
MAIN_MARKER_URL='http://127.0.0.1:8000/api/regional-guides/release-capabilities'
RECEIPTS=[
 'reports/nationwide-verification-20261029/candidate-root/BROWSER-RESULT.json',
 'reports/nationwide-verification-20261029/candidate-jiangsu/ACCEPTANCE-SUMMARY.json',
 'reports/nationwide-verification-20261029/native-ningbo-feidong/NATIVE-DOWNLOAD-RESULT.json',
 'reports/nationwide-verification-20261029/native-ningbo-feidong/PAGE-QA.json',
 'reports/nationwide-verification-20261029-b/candidate-hunan/BROWSER-RESULT.json',
 'reports/nationwide-verification-20261029-b/native-hunan/NATIVE-DOWNLOAD-RESULT.json',
 'reports/nationwide-verification-20261029-b/native-hunan/PAGE-QA.json',
]
STALE_WARNINGS={'当前为未发布候选，候选网页验收未运行。','候选网页未验收，不发布、不增加181/166覆盖计数。'}
HN_STALE_PREFIX='当前仅未发布候选，候选网页验收NOT_RUN；'
INPUT_FILES=tuple(SOURCE_FILES+HUNAN_FILES+RECEIPTS+['data/public-regions/'+n for n in ['guides.json','directory.json','manifest.json']]+['config/regional_candidates.json','.runtime/candidate-review-20261029-a/manifest.json','.runtime/candidate-review-20261029-a/regional-guides.sqlite','.runtime/candidate-review-20261029-a/regional-directory.sqlite'])
PREPARED_FILES=frozenset(['additions.json','remaining-candidates.json','snapshot/guides.json','snapshot/directory.json','snapshot/manifest.json']+['base/'+n for n in ['guides.json','directory.json','manifest.json']])


def _now():return datetime.now(timezone.utc).isoformat()
def _json(path):return json.loads(Path(path).read_text('utf8'))
def _bytes(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _contained(root,name):
    relative=Path(name)
    if relative.is_absolute() or relative.drive or '..' in relative.parts:raise ValueError('Release path must be a fixed contained relative path')
    path=(Path(root)/relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise ValueError('Release path escapes its fixed root')
    return path
def scope(g):return tuple(g.get(k,'').strip() for k in ('province','city','district'))
def _ro(path):return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
def sqlite_count(path,table):
    if table not in {'regional_current','regional_guides','directory_areas','discovery_jobs'}:raise ValueError('Unknown release table')
    with closing(_ro(path)) as db:return db.execute('SELECT count(*) FROM '+table).fetchone()[0]


def _current(path):
    with closing(_ro(path)) as db:
        return [{**json.loads(payload),'version':sequence} for payload,sequence in db.execute(
            'SELECT g.payload,g.sequence FROM regional_guides g JOIN regional_current c ON c.sequence=g.sequence ORDER BY g.sequence')]


def _public(g,root):
    spec=importlib.util.spec_from_file_location('oct29_public_export',ROOT/'scripts/export-public-data.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.public_guide(g,root=root)


def verify_receipts(root,guides):
    values=[_json(Path(root)/p) for p in RECEIPTS]
    a,js,nb,nbqa,hn,hnnative,hnqa=values
    if len(a.get('checks',[]))<15 or a.get('candidate_acceptance') is not True or not all(x.get('passed') is True for x in a['checks']):raise ValueError('A7 browser receipt is not PASS')
    if js.get('acceptance_passed') is not True or js.get('actual_native_downloads')!=6 or js.get('rendered_and_viewed_pages')!=6 or js.get('actual_docx_values_verified') is not True:raise ValueError('Jiangsu native receipt is not PASS')
    if len(hn.get('results',[]))!=11 or not all(x.get('passed') is True for x in hn['results']):raise ValueError('Hunan browser receipt is not PASS')
    by_code={g['region_code']:g for g in guides}
    for receipt,qa,expected in [(nb,nbqa,5),(hnnative,hnqa,2)]:
        if receipt.get('status')!='PASS' or receipt.get('completed')!=expected or len(receipt.get('records',[]))!=expected or qa.get('status')!='PASS' or qa.get('documents')!=expected:raise ValueError('Native download/page receipt is not PASS')
        observed=set()
        for row in receipt['records']:
            key=(row['region_code'],row['kind']);context=row['candidate_source_context'];g=by_code.get(row['region_code'])
            if key in observed or g is None or row.get('native_ui_generation') is not True or row.get('api_replay_used') is not False or row.get('zip_integrity')!='PASS' or row.get('document_xml_parse')!='PASS' or row.get('visual_qa',{}).get('status')!='PASS':raise ValueError('Native receipt record differs')
            if context.get('source_id')!=g['source_id'] or context.get('version')!=g['version']:raise ValueError('Native receipt source/version differs')
            observed.add(key)
        expected_pairs={('330203','application'),('330203','evidence'),('330212','application'),('330212','evidence'),('340122','application')} if expected==5 else {('430103','application'),('430104','application')}
        if observed!=expected_pairs:raise ValueError('Native receipt exact locality/kind set differs')
        if len(qa.get('files',[]))!=qa.get('pages') or qa.get('pages')!=(10 if expected==5 else 4):raise ValueError('Reviewed page receipt is incomplete')
        page_root=Path(root)/Path(RECEIPTS[3 if expected==5 else 6]).parent/'pages'
        for row in qa.get('files',[]):
            page=_contained(root,row['file'])
            if not page.is_relative_to(page_root.resolve()) or page.suffix!='.png' or row.get('visual_status')!='PASS' or file_sha(page)!=row['sha256']:raise ValueError('Reviewed page bytes changed')
    if guides:
        for code,observed in js.get('regions',{}).items():
            g=by_code.get(code)
            if g is None or observed.get('source_id')!=g['source_id'] or observed.get('live_version')!=g['version']:raise ValueError('Jiangsu receipt source/version differs')
        if set(js.get('regions',{}))!={'320281','320282'}:raise ValueError('Jiangsu receipt scope differs')
    return {p:file_sha(Path(root)/p) for p in RECEIPTS}


def _project(g,root):
    result=deepcopy(g);proof=public_evidence(result,root)
    for t in result['templates']:
        if 'region_code' not in t:
            if proof is None or not approved_report_attachment(result,t,root):raise ValueError('Missing attachment region_code without own public proof')
            t['region_code']=result['region_code']
    result.update(published=True,publication_status='published',candidate_web_qa='PASS')
    for key in ('web_qa_status',):
        if key in result:result[key]='PASS'
    if 'status' in result:result['status']='published'
    result['warnings']=[w.removeprefix(HN_STALE_PREFIX) for w in result.get('warnings',[]) if w not in STALE_WARNINGS]
    if any('验收NOT_RUN' in w or '候选网页未验收' in w or '候选网页验收未运行' in w for w in result['warnings']):raise ValueError('Unknown stale candidate warning; review exact wording')
    if result['province']=='jiangsu':
        for t in result['templates']:
            if jiangsu_binding(result,t) not in {'application','evidence'}:
                t.update(download_status='local_copy_unavailable',can_generate=False,document_types=[])
    result=with_reference_capabilities(result)
    result['can_generate']=any(t.get('can_generate') for t in result['templates'])
    if 'generation_enabled' in result:result['generation_enabled']=result['can_generate']
    exported=_public(result,root)
    if proof is not None and public_evidence(exported,root) is None:raise ValueError('Public export lost own canonical proof')
    return exported


def _capabilities(guides):
    documents=0;localities=0
    for g in guides:
        supported=False
        for t in g['templates']:
            if t.get('can_generate'):
                for kind in t['document_types']:checked_reference_adapter(g,t,kind);documents+=1;supported=True
        localities+=supported
    if (localities,documents)!=(7,11):raise ValueError('Expected seven own-source localities / eleven documents')
    return {'localities':localities,'documents':documents}


def _inputs(root):
    root=Path(root).resolve();candidate=root/'.runtime/candidate-review-20261029-a'
    manifest=verify_candidate(root,candidate)
    if manifest.get('candidate_guides')!=9 or manifest.get('guides')!=190:raise ValueError('Candidate must be reviewed 190-guide store')
    base=root/'data/public-regions';public_manifest=_json(base/'manifest.json')
    if (public_manifest['guides'],public_manifest['generatable_localities'])!=(181,166):raise ValueError('Public baseline is not 181/166')
    for name,checksum in public_manifest['files'].items():
        if file_sha(base/name)!=checksum:raise ValueError('Public baseline checksum differs')
    all_rows=_current(candidate/'regional-guides.sqlite');expected=[]
    for relative in SOURCE_FILES+HUNAN_FILES:
        source=_json(root/relative);matches=[g for g in all_rows if scope(g)==scope(source)]
        if len(matches)!=1 or matches[0]['source_id']!=digest(source['source_url'])[:24]:raise ValueError('Candidate source/scope differs')
        expected.append(matches[0])
    if len({g['source_id'] for g in expected})!=9:raise ValueError('Sources are not independent')
    receipts=verify_receipts(root,expected)
    additions=[_project(g,root) for g in expected];capabilities=_capabilities(additions)
    published=_json(base/'guides.json');places=[scope(g) for g in published+additions]
    if len(published)!=181 or sum(any(t.get('can_generate') for t in g['templates']) for g in published)!=166:raise ValueError('Actual baseline guide/generation counts differ')
    if len(places)!=len(set(places)):raise ValueError('Published baseline overlaps reviewed additions')
    cfg=_json(root/'config/regional_candidates.json');wanted={scope(g):g for g in additions};matched=[c for c in cfg if scope(c) in wanted]
    if len(cfg)!=33 or len(matched)!=9 or len({scope(g) for g in matched})!=9:raise ValueError('Canonical candidate queue is not exact 33 minus nine')
    for c in matched:
        if c.get('source_id') not in {None,wanted[scope(c)]['source_id']} or c.get('source_url') not in {None,wanted[scope(c)]['source_url']}:raise ValueError('Canonical candidate identity conflict')
    return additions,published,[c for c in cfg if scope(c) not in wanted],{p:file_sha(_contained(root,p)) for p in INPUT_FILES},capabilities,receipts


def prepare(root=ROOT,output=None):
    root=Path(root).resolve();output=Path(output or root/'.runtime/reviewed-oct29-release').resolve()
    if not output.is_relative_to(root/'.runtime') or output.exists():raise ValueError('Use a new prepared directory under workspace .runtime')
    additions,published,remaining,inputs,caps,receipts=_inputs(root)
    output.mkdir(parents=True);(output/'base').mkdir();(output/'snapshot').mkdir()
    for name in ['guides.json','directory.json','manifest.json']:shutil.copy2(root/'data/public-regions'/name,output/'base'/name)
    bodies={'additions.json':_bytes(additions),'remaining-candidates.json':_bytes(remaining),'snapshot/guides.json':_bytes(published+additions),'snapshot/directory.json':(root/'data/public-regions/directory.json').read_bytes()}
    for relative,body in bodies.items():(output/relative).write_bytes(body)
    snapshot_manifest={**_json(output/'base/manifest.json'),'exported_at':_now(),'guides':190,'generatable_localities':173,'files':{n:file_sha(output/'snapshot'/n) for n in ['guides.json','directory.json']}}
    (output/'snapshot/manifest.json').write_bytes(_bytes(snapshot_manifest))
    plan={'release_id':RELEASE_ID,'prepared_at':_now(),'guides':190,'generatable_localities':173,'new_capabilities':caps,'source_files':SOURCE_FILES+HUNAN_FILES,'source_ids':[g['source_id'] for g in additions],'input_sha256':inputs,'receipt_sha256':receipts,'prepared_sha256':{n:file_sha(output/n) for n in sorted(PREPARED_FILES)},'main_modified':False,'snapshot_modified':False,'candidate_queue_after':24}
    (output/'prepare-receipt.json').write_bytes(_bytes(plan));return plan


def verify_prepared(root,output):
    root=Path(root).resolve();output=Path(output).resolve();plan=_json(output/'prepare-receipt.json')
    if not output.is_relative_to(root/'.runtime') or plan.get('release_id')!=RELEASE_ID or plan.get('source_files')!=SOURCE_FILES+HUNAN_FILES:raise ValueError('Wrong prepared release identity')
    if set(plan.get('prepared_sha256',{}))!=PREPARED_FILES or set(plan.get('input_sha256',{}))!=set(INPUT_FILES):raise ValueError('Prepared input/file key set differs from fixed release allowlist')
    for name,checksum in plan['prepared_sha256'].items():
        if file_sha(_contained(output,name))!=checksum:raise ValueError('Changed prepared file')
    for name,checksum in plan['input_sha256'].items():
        if file_sha(_contained(root,name))!=checksum:raise ValueError('Release input changed since prepare: '+name)
    additions,published,remaining,inputs,caps,_=_inputs(root)
    if additions!=_json(output/'additions.json') or inputs!=plan['input_sha256'] or caps!=plan['new_capabilities']:raise ValueError('Revalidated prepared projection differs')
    if _json(output/'snapshot/guides.json')!=published+additions or _json(output/'remaining-candidates.json')!=remaining:raise ValueError('Prepared snapshot/queue projection differs')
    if (output/'snapshot/directory.json').read_bytes()!=(root/'data/public-regions/directory.json').read_bytes():raise ValueError('Prepared directory bytes differ')
    snapshot_manifest=_json(output/'snapshot/manifest.json')
    expected_manifest={**_json(root/'data/public-regions/manifest.json'),'exported_at':snapshot_manifest['exported_at'],'guides':190,'generatable_localities':173,'files':{n:file_sha(output/'snapshot'/n) for n in ['guides.json','directory.json']}}
    if snapshot_manifest!=expected_manifest:raise ValueError('Prepared snapshot manifest differs')
    return plan


def expected_marker():return {'release_id':RELEASE_ID,'adapters':[NINGBO_ADAPTER,OCT29_JIANGSU_ADAPTER,FEIDONG_ADAPTER,HUNAN_ADAPTER],'source_bound':True,'models_required':False,'regional_store':'main_default'}
def _read_marker():
    with urlopen(MAIN_MARKER_URL,timeout=5) as response:
        if response.geturl()!=MAIN_MARKER_URL:raise ValueError('Release marker redirected away from fixed main API')
        return json.loads(response.read(16384))
def check_main_marker():
    try:marker=_read_marker()
    except (OSError,ValueError) as exc:raise ValueError('Main API release marker unavailable; user must restart main; never use candidate marker') from exc
    expected=expected_marker()
    if not isinstance(marker,dict) or not isinstance(marker.get('adapters'),list) or not all(isinstance(a,str) for a in marker['adapters']):raise ValueError('Main API release marker schema mismatch')
    if marker.get('release_id')!=RELEASE_ID or marker.get('regional_store')!='main_default' or marker.get('source_bound') is not True or marker.get('models_required') is not False or set(marker.get('adapters',[]))!=set(expected['adapters']):raise ValueError('Main API release marker mismatch')
    return marker


def _backup_db(source,target):
    with closing(_ro(source)) as current,closing(sqlite3.connect(target)) as saved:current.backup(saved)
def _atomic_write(path,body):
    path=Path(path);temporary=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def apply(root=ROOT,output=None):
    root=Path(root).resolve();output=Path(output or root/'.runtime/reviewed-oct29-release').resolve()
    plan=verify_prepared(root,output);marker=check_main_marker()
    # No DB/path/API flags: candidate port or a different store cannot authorize main.
    main=root/'backend/data/regional-guides.sqlite';directory=root/'backend/data/regional-directory.sqlite'
    if not main.is_file() or not directory.is_file():raise ValueError('Default main stores must already exist')
    if main.resolve()!=main or directory.resolve()!=directory:raise ValueError('Default main DB cannot point into another store through a symlink')
    additions=_json(output/'additions.json');baseline=_json(output/'base/guides.json');live=_current(main)
    if len(live)!=181 or {scope(g):g['source_id'] for g in live}!={scope(g):g['source_id'] for g in baseline}:raise ValueError('Main baseline differs or already contains a reviewed scope')
    incoming={scope(g) for g in additions}
    if len(incoming)!=9 or incoming & {scope(g) for g in live}:raise ValueError('Existing exact scope must never be overwritten')
    rollback=output/('rollback-'+uuid4().hex);rollback.mkdir()
    targets=['data/public-regions/guides.json','data/public-regions/directory.json','data/public-regions/manifest.json','config/regional_candidates.json']
    saved={name:(root/name).read_bytes() for name in targets}
    for name,body in saved.items():p=rollback/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
    jobs=sqlite_count(directory,'discovery_jobs');directory_sha=file_sha(directory)
    db=sqlite3.connect(main,timeout=15);inserted=[]
    try:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT count(*) FROM regional_current').fetchone()[0]!=181:raise ValueError('Main baseline changed while acquiring write lock')
        locked=[_public(json.loads(row[0]),root) for row in db.execute('SELECT payload FROM regional_guides WHERE sequence IN (SELECT sequence FROM regional_current)')]
        if {scope(g):digest(official_content(g)) for g in locked}!={scope(g):digest(official_content(g)) for g in baseline}:raise ValueError('Main baseline facts changed; do not replace its public projection')
        for g in additions:
            if db.execute('SELECT 1 FROM regional_guides WHERE province=? AND city=? AND district=? OR source_id=?',(*scope(g),g['source_id'])).fetchone():raise ValueError('Existing scope/source history must never be overwritten')
        _backup_db(main,rollback/'regional-guides.sqlite');_backup_db(directory,rollback/'regional-directory.sqlite')
        backup_manifest={'release_id':RELEASE_ID,'created_at':_now(),'files':{p.relative_to(rollback).as_posix():file_sha(p) for p in rollback.rglob('*') if p.is_file()},'restore_note':'Stop/coordinate writers before manual restore; use SQLite backup API for DBs, restore exact four saved files. Directory DB was never replaced or written by apply.'}
        (rollback/'rollback-manifest.json').write_bytes(_bytes(backup_manifest))
        for g in additions:
            d=deepcopy(g);d.pop('version',None);rid=region_key(*scope(d));checksum=digest(official_content(d));d.update(region_id=rid,source_id=digest(d['source_url'])[:24],content_hash=checksum)
            if d['source_id']!=g['source_id']:raise ValueError('Prepared source ID differs')
            cursor=db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',(rid,d['source_id'],checksum,*scope(d),json.dumps(d,ensure_ascii=False)))
            db.execute('INSERT INTO regional_current(region_id,sequence) VALUES(?,?)',(rid,cursor.lastrowid));inserted.append({'scope':list(scope(d)),'source_id':d['source_id'],'version':cursor.lastrowid,'content_hash':checksum})
        for source,target in [('snapshot/guides.json','data/public-regions/guides.json'),('snapshot/manifest.json','data/public-regions/manifest.json'),('remaining-candidates.json','config/regional_candidates.json')]:_atomic_write(root/target,(output/source).read_bytes())
        if db.execute('SELECT count(*) FROM regional_current').fetchone()[0]!=190:raise ValueError('Unexpected final guide count')
        db.commit()
    except BaseException:
        db.rollback()
        for name,body in saved.items():
            if (root/name).read_bytes()!=body:(root/name).write_bytes(body)
        raise
    finally:db.close()
    _backup_db(main,output/'after-guides.sqlite')
    result={'release_id':RELEASE_ID,'applied_at':_now(),'marker_url':MAIN_MARKER_URL,'marker':marker,'inserted':len(inserted),'versions':inserted,'guides_before':181,'guides_after':sqlite_count(main,'regional_current'),'generatable_localities_after':173,'history_rows_after':sqlite_count(main,'regional_guides'),'discovery_jobs_before':jobs,'discovery_jobs_after':sqlite_count(directory,'discovery_jobs'),'directory_db_unchanged':file_sha(directory)==directory_sha,'candidate_queue_after':len(_json(root/'config/regional_candidates.json')),'rollback_directory':str(rollback),'after_consistent_sqlite_sha256':file_sha(output/'after-guides.sqlite'),'public_files_sha256':{name:file_sha(root/name) for name in targets},'prepared_receipt_sha256':file_sha(output/'prepare-receipt.json')}
    (output/'apply-receipt.json').write_bytes(_bytes(result));return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['prepare','apply']);parser.add_argument('--output',type=Path)
    args=parser.parse_args();print(json.dumps((prepare if args.operation=='prepare' else apply)(ROOT,args.output),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
