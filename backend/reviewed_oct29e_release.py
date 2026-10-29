"""E4 reviewed data delta, fixed main 8000 only. Never manages services/models.

prepare is read-only outside a new isolated runtime folder. apply requires exact
native browser/document receipts and main code marker, preserves 198 existing
facts/history, appends four guides, and leaves the directory DB untouched.
"""
from contextlib import closing
from copy import deepcopy
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
from urllib.request import urlopen
from uuid import uuid4
import xml.etree.ElementTree as ET
import zipfile

from candidate_review import E_FILES,load_e_guides, verify as verify_candidate,_replace_bytes
from regional_adapters import with_reference_capabilities,checked_reference_adapter
from regional_guides import digest,official_content,region_key
from regional_public_provenance import public_evidence
from reviewed_oct29_release import (_json,_bytes,_contained,_ro,_now,_current,
    file_sha,sqlite_count,_backup_db,_atomic_write,PREPARED_FILES)

ROOT=Path(__file__).resolve().parents[1]
RELEASE_ID='oct29e-own-localities-v1'
MAIN_MARKER_URL='http://127.0.0.1:8000/api/regional-guides/release-capabilities'
PROFILES=(('320507','jiangsu','苏州市','相城区'),('320509','jiangsu','苏州市','吴江区'),
          ('330111','zhejiang','杭州市','富阳区'),('330182','zhejiang','杭州市','建德市'))
SOURCE_URLS={'320507': 'https://szxc.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=28&iddept_ql_inf=11320507555810103L4002014302002&ql_kind=20&iddept_yw_inf=11320507555810103L400201430200201', '320509': 'https://szwj.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=29&iddept_ql_inf=1132058401420395XF4002014302002&ql_kind=20&iddept_yw_inf=1132058401420395XF400201430200201', '330111': 'https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=31ce6363-7379-40c0-8454-f0715785e193', '330182': 'https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=ed48d6e4-e7ee-433d-97aa-b1352d1fb341'}
EXPECTED_PAIRS={(code,kind) for code,*_ in PROFILES for kind in ['application','evidence']}
EXPECTED_ADAPTERS={'jiangsu':'jiangsu_own_blank_oct29e_v1','zhejiang':'zhejiang_own_worker_oct29e_v1'}
RECEIPTS=['reports/nationwide-verification-20261029-e/acceptance/'+name for name in ['BROWSER-RESULT.json','DOCUMENT-RESULT.json']]
CANDIDATE='.runtime/candidate-review-20261029-a'
TARGETS=['data/public-regions/'+n for n in ['guides.json','directory.json','manifest.json']]+['config/regional_candidates.json']
INPUT_FILES=tuple(E_FILES+RECEIPTS+TARGETS+[CANDIDATE+'/'+n for n in ['manifest.json','regional-guides.sqlite','regional-directory.sqlite']])
STALE_WARNINGS={'本批只采集来源和原件，未转换、填写适配、文书逐页版式或候选网页验收。', 'DOCX只读结构与文本检查不等于逐页版式验收，render_status仍为NOT_RUN。', '仅本区自身空白文书完成离线填写；申请默认且仅支持劳动者区段，单位申请未适配。版式及候选网页验收另行记录；不代表已发布。', '本批仅采集自身指南与公开来源，未做新适配或候选网页验收，未发布。'}


def scope(g):return tuple(g.get(k,'').strip() for k in ('province','city','district'))

def _public(g,root):
    """Use only the selected root's exporter; never fall back to this checkout."""
    script=_contained(Path(root),'scripts/export-public-data.py')
    spec=importlib.util.spec_from_file_location('oct29e_public_export',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.public_guide(g,root=Path(root))


def validate_sources(guides):
    if len(guides)!=4 or [(g.get('region_code'),*scope(g)) for g in guides]!=list(PROFILES):raise ValueError('E4 exact locality identity differs')
    for g in guides:
        if g.get('source_url')!=SOURCE_URLS[g['region_code']] or g.get('source_id',digest(g['source_url'])[:24])!=digest(g['source_url'])[:24]:raise ValueError('E4 own source identity differs')
        if any(t.get('region_code')!=g['region_code'] for t in g['templates']):raise ValueError('E4 attachment locality differs')


def _capabilities(guides,root=None):
    observed=set();documents=0
    for g in guides:
        for t in g['templates']:
            if t.get('can_generate'):
                for kind in t.get('document_types',[]):

                    if checked_reference_adapter(g,t,kind,root=root)!=EXPECTED_ADAPTERS[g['province']]:raise ValueError('E4 adapter identity differs')
                    observed.add((g['region_code'],kind));documents+=1
    if observed!=EXPECTED_PAIRS or documents!=8:raise ValueError('Expected four own-source E localities / eight documents')
    return {'localities':4,'documents':8}


def _receipt_file(root,row,suffix):
    path=_contained(root,row['file']);receipt_root=(Path(root)/Path(RECEIPTS[0]).parent).resolve()
    if not path.is_relative_to(receipt_root) or path.suffix.lower()!=suffix or file_sha(path)!=row.get('sha256'):raise ValueError('E4 receipt artifact bytes/path differ')
    return path


def _verify_png(path):
    """Validate actual PNG structure/chunk CRCs, not merely a .png suffix."""
    import struct,zlib
    body=Path(path).read_bytes()
    if not body.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('E4 page is not PNG')
    offset=8;seen=[]
    while offset+12<=len(body):
        length=struct.unpack('>I',body[offset:offset+4])[0]
        end=offset+12+length
        if end>len(body):raise ValueError('E4 PNG truncated')
        kind=body[offset+4:offset+8];data=body[offset+8:end-4]
        if zlib.crc32(kind+data)&0xffffffff!=struct.unpack('>I',body[end-4:end])[0]:raise ValueError('E4 PNG CRC differs')
        if not seen:
            if kind!=b'IHDR' or length!=13 or 0 in struct.unpack('>II',data[:8]):raise ValueError('E4 PNG dimensions/header differ')
        seen.append(kind);offset=end
        if kind==b'IEND':
            if length or offset!=len(body) or b'IDAT' not in seen:raise ValueError('E4 PNG structure differs')
            from PIL import Image
            try:
                with Image.open(path) as image:
                    if image.format!='PNG':raise ValueError('E4 page is not PNG')
                    image.load()
            except (OSError,SyntaxError) as exc:raise ValueError('E4 PNG pixels cannot be decoded') from exc
            return
    raise ValueError('E4 PNG incomplete')


def verify_receipts(root,guides):
    browser,document=[_json(_contained(root,p)) for p in RECEIPTS];by_code={g['region_code']:g for g in guides}
    expected={code:{'source_id':g['source_id'],'version':g['version']} for code,g in by_code.items()}
    if set(expected)!={p[0] for p in PROFILES}:raise ValueError('E4 receipt guide scope differs')
    if browser.get('status')!='PASS' or browser.get('candidate_acceptance') is not True or len(browser.get('checks',[]))<4 or not all(c.get('passed') is True for c in browser['checks']) or browser.get('regions')!=expected:raise ValueError('E4 browser receipt is not PASS / own source versions differ')
    if document.get('status')!='PASS' or document.get('completed')!=8 or len(document.get('records',[]))!=8:raise ValueError('E4 native document receipt is not PASS')
    hashes={p:file_sha(_contained(root,p)) for p in RECEIPTS};observed=set();artifact_paths=set()
    for row in document['records']:
        code=row.get('region_code');pair=(code,row.get('kind'));g=by_code.get(code)
        if pair not in EXPECTED_PAIRS or pair in observed or g is None:raise ValueError('E4 receipt exact document set differs')
        template=next((t for t in g['templates'] if t['id']==row.get('template_id') and t.get('can_generate') and row['kind'] in t.get('document_types',[])),None)
        if template is None or row.get('candidate_source_context')!=expected[code]:raise ValueError('E4 receipt template/source/version differs')
        if checked_reference_adapter(g,template,row['kind'],root=root)!=EXPECTED_ADAPTERS[g['province']]:raise ValueError('E4 receipt adapter identity differs')
        if row.get('x_guide_source_id')!=expected[code]['source_id'] or row.get('x_document_origin')!='official-blank-filled':raise ValueError('E4 native response source/origin differs')
        if row.get('native_ui_generation') is not True or row.get('api_replay_used') is not False or row.get('http_status')!=200 or row.get('zip_integrity')!='PASS' or row.get('document_xml_parse')!='PASS':raise ValueError('E4 native download receipt is not PASS')
        docx=_receipt_file(root,row,'.docx')
        if row['file'] in artifact_paths:raise ValueError('E4 repeated document artifact')
        artifact_paths.add(row['file'])
        with zipfile.ZipFile(docx) as archive:
            if archive.testzip() is not None:raise ValueError('E4 downloaded document ZIP differs')
            xml=ET.fromstring(archive.read('word/document.xml'))
            if xml.tag!='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document' or xml.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body') is None:raise ValueError('E4 downloaded document XML is not Word document/body')
        hashes[row['file']]=file_sha(docx)
        qa=row.get('visual_qa',{})
        if qa.get('status')!='PASS' or not qa.get('pages'):raise ValueError('E4 page QA is not PASS')
        for page in qa['pages']:
            if page.get('visual_status')!='PASS':raise ValueError('E4 page QA is not PASS')
            path=_receipt_file(root,page,'.png')
            if page['file'] in artifact_paths:raise ValueError('E4 repeated PNG page artifact')
            artifact_paths.add(page['file']);_verify_png(path);hashes[page['file']]=file_sha(path)
        observed.add(pair)
    if observed!=EXPECTED_PAIRS:raise ValueError('E4 receipt exact document set differs')
    return hashes


def _project(g,root):
    result=deepcopy(g)
    if public_evidence(result,root) is None:raise ValueError('Missing E4 own public canonical source proof')
    result.update(published=True,publication_status='published',candidate_web_qa='PASS')
    result['warnings']=[w for w in result.get('warnings',[]) if w not in STALE_WARNINGS]
    if any('NOT_RUN' in w or '未做新适配' in w or '不提供生成' in w for w in result['warnings']):raise ValueError('Unknown E4 stale candidate warning')
    result=with_reference_capabilities(result,root=root);result['can_generate']=any(t.get('can_generate') for t in result['templates'])
    exported=_public(result,root)
    if public_evidence(exported,root) is None:raise ValueError('E4 public export lost own canonical proof')
    return exported


def _inputs(root):
    root=Path(root).resolve();manifest=verify_candidate(root,root/CANDIDATE)
    if (manifest.get('candidate_guides'),manifest.get('guides'),manifest.get('generatable_localities'))!=(21,202,185):raise ValueError('E4 candidate must be 202/185')
    base=root/'data/public-regions';public_manifest=_json(base/'manifest.json')
    if (public_manifest.get('guides'),public_manifest.get('generatable_localities'))!=(198,181):raise ValueError('Public E4 baseline must be 198/181')
    if set(public_manifest.get('files',{}))!={'guides.json','directory.json'}:raise ValueError('Public E4 baseline file allowlist differs')
    for n,checksum in public_manifest['files'].items():
        if file_sha(base/n)!=checksum:raise ValueError('Public baseline checksum differs')
    published=_json(base/'guides.json')
    if len(published)!=198 or sum(any(t.get('can_generate') for t in g['templates']) for g in published)!=181:raise ValueError('Actual public baseline counts differ')
    all_rows=_current(root/CANDIDATE/'regional-guides.sqlite');expected=[]
    for transformed in load_e_guides(root):
        matches=[g for g in all_rows if scope(g)==scope(transformed)]
        if len(matches)!=1 or official_content(matches[0])!=official_content(transformed):raise ValueError('E4 candidate payload differs from exact own source projection')
        if type(matches[0].get('version')) is not int or matches[0]['version']!=199+len(expected):raise ValueError('E4 candidate version sequence differs')
        expected.append(matches[0])
    validate_sources(expected);receipts=verify_receipts(root,expected)
    additions=[_project(g,root) for g in expected];caps=_capabilities(additions,root=root)
    places=[scope(g) for g in published+additions]
    if len(places)!=len(set(places)):raise ValueError('E4 overlaps old exact scope')
    cfg=_json(root/'config/regional_candidates.json');wanted={scope(g):g for g in additions};matched=[c for c in cfg if scope(c) in wanted]
    if len(cfg)!=28 or len(matched)!=4 or len({scope(c) for c in matched})!=4:raise ValueError('E4 queue must be exact 28 minus four')
    for c in matched:
        if c.get('source_id') not in {None,wanted[scope(c)]['source_id']} or c.get('source_url') not in {None,wanted[scope(c)]['source_url']}:raise ValueError('E4 canonical candidate identity conflict')
    return additions,published,[c for c in cfg if scope(c) not in wanted],{p:file_sha(_contained(root,p)) for p in INPUT_FILES},caps,receipts


def prepare(root=ROOT,output=None):
    root=Path(root).resolve();output=Path(output or root/'.runtime/reviewed-oct29e-release').resolve()
    if not output.is_relative_to(root/'.runtime') or output.exists():raise ValueError('Use a new E4 prepared directory under workspace .runtime')
    additions,published,remaining,inputs,caps,receipts=_inputs(root)
    output.mkdir(parents=True);(output/'base').mkdir();(output/'snapshot').mkdir()
    for n in ['guides.json','directory.json','manifest.json']:shutil.copy2(root/'data/public-regions'/n,output/'base'/n)
    bodies={'additions.json':_bytes(additions),'remaining-candidates.json':_bytes(remaining),'snapshot/guides.json':_bytes(published+additions),'snapshot/directory.json':(root/'data/public-regions/directory.json').read_bytes()}
    for n,body in bodies.items():(output/n).write_bytes(body)
    snapshot={**_json(output/'base/manifest.json'),'exported_at':_now(),'guides':202,'generatable_localities':185,'files':{n:file_sha(output/'snapshot'/n) for n in ['guides.json','directory.json']}}
    (output/'snapshot/manifest.json').write_bytes(_bytes(snapshot))
    plan={'release_id':RELEASE_ID,'prepared_at':_now(),'guides':202,'generatable_localities':185,'new_capabilities':caps,'source_files':E_FILES,'source_ids':[g['source_id'] for g in additions],'input_sha256':inputs,'receipt_sha256':receipts,'prepared_sha256':{n:file_sha(output/n) for n in sorted(PREPARED_FILES)},'main_modified':False,'snapshot_modified':False,'candidate_queue_after':24}
    (output/'prepare-receipt.json').write_bytes(_bytes(plan));return plan


def verify_prepared(root,output):
    root=Path(root).resolve();output=Path(output).resolve()
    if not output.is_relative_to(root/'.runtime'):raise ValueError('E4 prepared path escapes runtime')
    plan=_json(output/'prepare-receipt.json')
    if plan.get('release_id')!=RELEASE_ID or plan.get('source_files')!=E_FILES or set(plan.get('prepared_sha256',{}))!=PREPARED_FILES or set(plan.get('input_sha256',{}))!=set(INPUT_FILES):raise ValueError('E4 prepared identity/allowlist differs')
    fixed={'guides':202,'generatable_localities':185,'new_capabilities':{'localities':4,'documents':8},
           'main_modified':False,'snapshot_modified':False,'candidate_queue_after':24,
           'source_ids':[digest(SOURCE_URLS[p[0]])[:24] for p in PROFILES]}
    if any(type(plan.get(k)) is not type(v) or plan.get(k)!=v for k,v in fixed.items()):raise ValueError('E4 prepared identity/counts differ')
    for n,checksum in plan['prepared_sha256'].items():
        if file_sha(_contained(output,n))!=checksum:raise ValueError('E4 prepared file changed')
    for n,checksum in plan['input_sha256'].items():
        if file_sha(_contained(root,n))!=checksum:raise ValueError('E4 input changed since prepare')
    additions,published,remaining,inputs,caps,receipts=_inputs(root)
    if additions!=_json(output/'additions.json') or inputs!=plan['input_sha256'] or caps!=plan['new_capabilities'] or receipts!=plan['receipt_sha256']:raise ValueError('E4 prepared projection differs')
    if _json(output/'snapshot/guides.json')!=published+additions or _json(output/'remaining-candidates.json')!=remaining:raise ValueError('E4 snapshot/queue projection differs')
    for n in ['guides.json','directory.json','manifest.json']:
        if (output/'base'/n).read_bytes()!=(root/'data/public-regions'/n).read_bytes():raise ValueError('E4 saved baseline differs')
    if (output/'snapshot/directory.json').read_bytes()!=(root/'data/public-regions/directory.json').read_bytes():raise ValueError('E4 directory bytes differ')
    manifest=_json(output/'snapshot/manifest.json');expected={**_json(output/'base/manifest.json'),'exported_at':manifest['exported_at'],'guides':202,'generatable_localities':185,'files':{n:file_sha(output/'snapshot'/n) for n in ['guides.json','directory.json']}}
    if manifest!=expected:raise ValueError('E4 snapshot manifest differs')
    return plan


def expected_marker():
    return {'release_id':RELEASE_ID,'adapters':list(EXPECTED_ADAPTERS.values()),'source_bound':True,'models_required':False,'regional_store':'main_default'}


def _read_marker():
    with urlopen(MAIN_MARKER_URL,timeout=5) as response:
        if response.geturl()!=MAIN_MARKER_URL:raise ValueError('E4 marker redirected away from fixed main API')
        return json.loads(response.read(16384))

def check_main_marker():
    try:marker=_read_marker()
    except (OSError,ValueError) as exc:raise ValueError('Main E4 marker unavailable; main data mutation is not authorized') from exc
    expected=expected_marker()
    if not isinstance(marker,dict) or marker.get('release_id')!=RELEASE_ID or marker.get('regional_store')!='main_default' or marker.get('source_bound') is not True or marker.get('models_required') is not False or not isinstance(marker.get('adapters'),list) or not all(isinstance(a,str) for a in marker['adapters']) or len(marker['adapters'])!=2 or set(marker['adapters'])!=set(expected['adapters']):raise ValueError('Main E4 marker mismatch')
    return marker


def apply(root=ROOT,output=None):
    root=Path(root).resolve();output=Path(output or root/'.runtime/reviewed-oct29e-release').resolve()
    plan=verify_prepared(root,output);marker=check_main_marker()
    main=root/'backend/data/regional-guides.sqlite';directory=root/'backend/data/regional-directory.sqlite'
    if not main.is_file() or not directory.is_file() or main.resolve()!=main or directory.resolve()!=directory:raise ValueError('Default E4 main stores must exist without symlinks')
    additions=_json(output/'additions.json');baseline=_json(output/'base/guides.json');live=_current(main)
    if len(live)!=198 or {scope(g):g['source_id'] for g in live}!={scope(g):digest(g['source_url'])[:24] for g in baseline}:raise ValueError('Main E4 baseline differs or already contains incoming scope')
    if sqlite_count(main,'regional_guides')!=206 or sqlite_count(directory,'discovery_jobs')!=4294:raise ValueError('Main E4 history/jobs baseline differs')
    if len({scope(g) for g in additions})!=4 or {scope(g) for g in additions}&{scope(g) for g in live}:raise ValueError('Existing scope cannot be overwritten')
    rollback=output/('rollback-'+uuid4().hex);rollback.mkdir();saved={n:(root/n).read_bytes() for n in TARGETS}
    for n,body in saved.items():p=rollback/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
    directory_sha=file_sha(directory);db=sqlite3.connect(main,timeout=15);inserted=[];committed=False;original_db_bytes=None
    try:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('PRAGMA journal_mode').fetchone()[0].lower()!='delete':raise ValueError('E4 main requires a standalone DELETE-journal store')
        original_db_bytes=main.read_bytes()
        if db.execute('SELECT count(*) FROM regional_current').fetchone()[0]!=198 or db.execute('SELECT count(*) FROM regional_guides').fetchone()[0]!=206:raise ValueError('Main E4 baseline changed before lock')
        if db.execute("SELECT seq FROM sqlite_sequence WHERE name='regional_guides'").fetchone()!=(206,):raise ValueError('E4 main version sequence differs')
        locked=[_public(json.loads(row[0]),root) for row in db.execute('SELECT payload FROM regional_guides WHERE sequence IN (SELECT sequence FROM regional_current)')]
        if {scope(g):digest(official_content(g)) for g in locked}!={scope(g):digest(official_content(g)) for g in baseline}:raise ValueError('Main E4 baseline facts changed')
        for g in additions:
            if db.execute('SELECT 1 FROM regional_guides WHERE (province=? AND city=? AND district=?) OR source_id=?',(*scope(g),g['source_id'])).fetchone():raise ValueError('Existing scope/source history must never be overwritten')
        _backup_db(main,rollback/'regional-guides.sqlite');_backup_db(directory,rollback/'regional-directory.sqlite')
        (rollback/'regional-guides.exact-before.sqlite').write_bytes(original_db_bytes)
        (rollback/'rollback-manifest.json').write_bytes(_bytes({'release_id':RELEASE_ID,'created_at':_now(),'files':{p.relative_to(rollback).as_posix():file_sha(p) for p in rollback.rglob('*') if p.is_file()},'restore_note':'Coordinate writers before manual restoration; directory DB was never written.'}))
        for g in additions:
            d=deepcopy(g);d.pop('version',None);rid=region_key(*scope(d));sid=digest(d['source_url'])[:24];checksum=digest(official_content(d));d.update(region_id=rid,source_id=sid,content_hash=checksum)
            if sid!=g['source_id']:raise ValueError('E4 prepared source ID differs')
            cursor=db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',(rid,sid,checksum,*scope(d),json.dumps(d,ensure_ascii=False)))

            if cursor.lastrowid!=207+len(inserted):raise ValueError('E4 main version sequence differs')
            db.execute('INSERT INTO regional_current VALUES(?,?)',(rid,cursor.lastrowid));inserted.append({'scope':list(scope(d)),'source_id':sid,'version':cursor.lastrowid,'content_hash':checksum})
        for source,target in [('snapshot/guides.json',TARGETS[0]),('snapshot/manifest.json',TARGETS[2]),('remaining-candidates.json',TARGETS[3])]:_atomic_write(root/target,(output/source).read_bytes())
        if db.execute('SELECT count(*) FROM regional_current').fetchone()[0]!=202 or db.execute('SELECT count(*) FROM regional_guides').fetchone()[0]!=210:raise ValueError('Unexpected E4 final counts')
        db.commit();committed=True;db.close();db=None
        _backup_db(main,output/'after-guides.sqlite')
        result={'release_id':RELEASE_ID,'applied_at':_now(),'marker_url':MAIN_MARKER_URL,'marker':marker,'inserted':4,'versions':inserted,'guides_before':198,'guides_after':sqlite_count(main,'regional_current'),'generatable_localities_after':185,'history_rows_after':sqlite_count(main,'regional_guides'),'discovery_jobs_before':4294,'discovery_jobs_after':sqlite_count(directory,'discovery_jobs'),'directory_db_unchanged':file_sha(directory)==directory_sha,'candidate_queue_after':len(_json(root/'config/regional_candidates.json')),'rollback_directory':str(rollback),'after_consistent_sqlite_sha256':file_sha(output/'after-guides.sqlite'),'public_files_sha256':{n:file_sha(root/n) for n in TARGETS},'prepared_receipt_sha256':file_sha(output/'prepare-receipt.json')}
        (output/'apply-receipt.json').write_bytes(_bytes(result));return result
    except BaseException:
        if db is not None:db.rollback();db.close();db=None
        if committed and original_db_bytes is not None:_replace_bytes(main,original_db_bytes)
        for n,body in saved.items():
            if (root/n).read_bytes()!=body:_atomic_write(root/n,body)
        raise
    finally:
        if db is not None:db.close()



def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['prepare','apply']);parser.add_argument('--output',type=Path)
    args=parser.parse_args();print(json.dumps((prepare if args.operation=='prepare' else apply)(ROOT,args.output),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
