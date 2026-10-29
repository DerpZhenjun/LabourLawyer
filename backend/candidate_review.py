"""Prepare isolated public candidate data. This module never starts any service."""
from pathlib import Path
import hashlib
import json
import sqlite3
import os
from uuid import uuid4
from copy import deepcopy
from contextlib import closing
from regional_guides import RegionalStore
from regional_directory import DirectoryStore
from regional_adapters import with_reference_capabilities

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'.runtime/candidate-review-20261029-a'
SOURCE_FILES=[
 'reports/nationwide-verification-20261029/zhejiang/haishu/guide.json',
 'reports/nationwide-verification-20261029/zhejiang/yinzhou/guide.json',
 'reports/nationwide-verification-20261029/anhui/yaohai/guide.json',
 'reports/nationwide-verification-20261029/anhui/feidong/guide.json',
 'reports/nationwide-verification-20261029/jiangsu/320281/guide.json',
 'reports/nationwide-verification-20261029/jiangsu/320282/guide.json',
 'reports/nationwide-verification-20261029/sichuan/qingyang-guide.json',
]
HUNAN_FILES=[f'reports/nationwide-verification-20261029-b/hunan/{name}/guide.json' for name in ['tianxin','xiangjiang']]
C_FILES=[f'reports/nationwide-verification-20261029-c/{place}/guide.json' for place in
         ['hunan/yuhua','hunan/wangcheng','jiangsu/xinbei','jiangsu/wujin']]
D_FILES=[f'reports/nationwide-verification-20261029-d/{place}/guide.json' for place in
         ['jiangsu/gusu','jiangsu/wuzhong','zhejiang/xiaoshan','zhejiang/linan']]


E_FILES=[f'reports/nationwide-verification-20261029-e/{place}/guide.json' for place in
         ['jiangsu/xiangcheng','jiangsu/wujiang','zhejiang/fuyang','zhejiang/jiande']]


def load_e_guides(root=ROOT):
    """Rebuild E4 through own source parsers and explicit-root capability proofs."""
    import regional_jiangsu_oct29e as jiangsu
    import regional_zhejiang_oct29e as zhejiang
    root=Path(root).resolve()
    guides=[jiangsu.parse_capture(code,capture_root=root/jiangsu.REPORT) for code in ['320507','320509']]
    guides += [zhejiang.parse_capture(name,root=root) for name in ['fuyang','jiande']]
    return [with_reference_capabilities(g,root=root) for g in guides]


def load_d_guides(root=ROOT):
    """Use each D provider canonical parser; raw guide flags never authorize."""
    import regional_jiangsu_oct29d as jiangsu
    import regional_zhejiang_oct29d as zhejiang
    root=Path(root).resolve()
    guides=[jiangsu.parse_capture(code,capture_root=root/jiangsu.REPORT) for code in ['320508','320506']]
    guides += [zhejiang.parse_capture(name,root=root) for name in ['xiaoshan','linan']]
    return [with_reference_capabilities(g,root=root) for g in guides]


def load_c_guides(root=ROOT):
    """Rebuild C4 from each provider's pinned captures, never mutable raw flags.

    The sealed guide files remain source evidence. Canonical parsers verify
    their complete source bundles and derive the normalized identity/channel
    fields required by their own adapters without rewriting those originals.
    """
    import regional_hunan_oct29c as hunan
    import regional_jiangsu_oct29c as jiangsu
    root=Path(root).resolve()
    guides=[hunan.parse_capture(name,capture_root=root/hunan.REPORT) for name in ['yuhua','wangcheng']]
    guides += [jiangsu.parse_capture(name,capture_root=root/jiangsu.REPORT) for name in ['xinbei','wujin']]
    return [with_reference_capabilities(g) for g in guides]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(root=ROOT,output=OUTPUT):
    root=Path(root).resolve();output=Path(output).resolve()
    if not output.is_relative_to(root/'.runtime'):raise ValueError('Only an isolated workspace runtime directory is permitted')
    if output.exists():raise ValueError('Existing candidate data is preserved; verify it instead of rebuilding')
    history=root/'data/public-regions/history/20261028-181'
    snapshot=history if history.is_dir() else root/'data/public-regions'
    manifest=json.loads((snapshot/'manifest.json').read_text('utf-8'))
    if (manifest.get('guides'),manifest.get('generatable_localities'))!=(181,166):
        raise ValueError('This dated candidate review requires its preserved 181/166 public baseline')
    for name,checksum in manifest['files'].items():
        if sha(snapshot/name)!=checksum:raise ValueError('Public source snapshot changed')
    published=json.loads((snapshot/'guides.json').read_text('utf-8'))
    directory=json.loads((snapshot/'directory.json').read_text('utf-8'))
    candidates=[]
    for relative in SOURCE_FILES:
        g=json.loads((root/relative).read_text('utf-8'))
        candidates.append(with_reference_capabilities(g))
    places=[(g['province'],g['city'],g['district']) for g in published+candidates]
    if len(places)!=len(set(places)):raise ValueError('A candidate overlaps an existing exact published locality')
    if sum(any(t.get('can_generate') for t in g['templates']) for g in candidates)!=5:
        raise ValueError('Expected five own-source document adapters; inspect missing originals or failed source bindings')
    output.mkdir(parents=True)
    guides=RegionalStore(output/'regional-guides.sqlite')
    for g in published+candidates:guides.put_guide(deepcopy(g))
    areas=DirectoryStore(output/'regional-directory.sqlite')
    for row in directory:areas.put_area(row)
    result={'scope':'isolated-public-candidate-review-only','main_database_modified':False,'models_disabled':True,
            'published':False,'guides':len(published+candidates),'candidate_guides':7,'generatable_localities':171,
            'source_files':{p:sha(root/p) for p in SOURCE_FILES},
            'candidate_source_ids':[guides.lookup(g['province'],g['city'],g['district'])['source_id'] for g in candidates],
            'database_files':{name:sha(output/name) for name in ['regional-guides.sqlite','regional-directory.sqlite']}}
    (output/'manifest.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return result


def verify(root=ROOT,output=OUTPUT):
    root=Path(root).resolve();output=Path(output).resolve()
    if not output.is_relative_to(root/'.runtime'):raise ValueError('Candidate path outside the isolated workspace')
    manifest=json.loads((output/'manifest.json').read_text('utf-8'))
    if manifest.get('scope')!='isolated-public-candidate-review-only' or manifest.get('published') is not False:
        raise ValueError('Candidate manifest identity differs')
    for relative,checksum in manifest['source_files'].items():
        if relative not in SOURCE_FILES+HUNAN_FILES+C_FILES+D_FILES+E_FILES or sha(root/relative)!=checksum:raise ValueError('Candidate source evidence changed')
    expected_sources={7:SOURCE_FILES,9:SOURCE_FILES+HUNAN_FILES,13:SOURCE_FILES+HUNAN_FILES+C_FILES,17:SOURCE_FILES+HUNAN_FILES+C_FILES+D_FILES,21:SOURCE_FILES+HUNAN_FILES+C_FILES+D_FILES+E_FILES}.get(manifest.get('candidate_guides'))
    if expected_sources is None:raise ValueError('Unknown candidate source generation')
    if set(manifest['source_files'])!=set(expected_sources):raise ValueError('Candidate source set differs')
    if manifest.get('candidate_guides')==17:
        if (manifest.get('guides'),manifest.get('generatable_localities'))!=(198,181) or set(manifest.get('database_files',{}))!={'regional-guides.sqlite','regional-directory.sqlite'}:
            raise ValueError('D4 candidate exact counts/database hash set differs')
        ids=manifest.get('candidate_source_ids',[])
        if len(ids)!=17 or len(set(ids))!=17:raise ValueError('D4 candidate source identities differ')
    if manifest.get('candidate_guides')==21:
        if (manifest.get('guides'),manifest.get('generatable_localities'))!=(202,185) or set(manifest.get('database_files',{}))!={'regional-guides.sqlite','regional-directory.sqlite'}:
            raise ValueError('E4 candidate exact counts/database hash set differs')
        ids=manifest.get('candidate_source_ids',[])
        if len(ids)!=21 or len(set(ids))!=21:raise ValueError('E4 candidate source identities differ')
    for name,checksum in manifest['database_files'].items():
        if name not in {'regional-guides.sqlite','regional-directory.sqlite'} or sha(output/name)!=checksum:
            raise ValueError('Candidate store differs from prepared data; do not replace it automatically')
    with closing(sqlite3.connect((output/'regional-guides.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        count=db.execute('SELECT COUNT(*) FROM regional_current').fetchone()[0]
        if manifest.get('candidate_guides')==17:
            if db.execute('SELECT count(*),max(sequence) FROM regional_guides').fetchone()!=(198,198) or db.execute("SELECT seq FROM sqlite_sequence WHERE name='regional_guides'").fetchone()!=(198,):raise ValueError('D4 candidate history/version sequence differs')
            tail=[row[0] for row in db.execute('SELECT source_id FROM regional_guides WHERE sequence BETWEEN 195 AND 198 ORDER BY sequence')]
            if tail!=manifest['candidate_source_ids'][-4:]:raise ValueError('D4 candidate source/version binding differs')
            rows=[json.loads(row[0]) for row in db.execute('SELECT payload FROM regional_guides WHERE sequence IN (SELECT sequence FROM regional_current)')]
            if sum(any(t.get('can_generate') is True for t in g.get('templates',[])) for g in rows)!=181:raise ValueError('D4 candidate stored capability count differs')
        if manifest.get('candidate_guides')==21:
            if db.execute('SELECT count(*),max(sequence) FROM regional_guides').fetchone()!=(202,202) or db.execute("SELECT seq FROM sqlite_sequence WHERE name='regional_guides'").fetchone()!=(202,):raise ValueError('E4 candidate history/version sequence differs')
            tail=[row[0] for row in db.execute('SELECT source_id FROM regional_guides WHERE sequence BETWEEN 199 AND 202 ORDER BY sequence')]
            if tail!=manifest['candidate_source_ids'][-4:]:raise ValueError('E4 candidate source/version binding differs')
            rows=[json.loads(row[0]) for row in db.execute('SELECT payload FROM regional_guides WHERE sequence IN (SELECT sequence FROM regional_current)')]
            if sum(any(t.get('can_generate') is True for t in g.get('templates',[])) for g in rows)!=185:raise ValueError('E4 candidate stored capability count differs')
    expected_count=181+len(expected_sources)
    if count!=expected_count or manifest['guides']!=expected_count:raise ValueError('Prepared candidate count differs')
    return manifest


def extend_hunan(root=ROOT,output=OUTPUT):
    """Append two reviewed public candidates; keep the original test snapshot."""
    root=Path(root).resolve();output=Path(output).resolve()
    previous=verify(root,output)
    if previous['candidate_guides']!=7:raise ValueError('Hunan candidates were already added; do not repeat')
    additions=[with_reference_capabilities(json.loads((root/p).read_text('utf8'))) for p in HUNAN_FILES]
    if not all(sum(t.get('can_generate') is True for t in g['templates'])==1 for g in additions):
        raise ValueError('Each own Hunan worker application must pass its source binding')
    store=RegionalStore(output/'regional-guides.sqlite')
    if any(store.lookup(g['province'],g['city'],g['district']).get('source_id') for g in additions):
        raise ValueError('Existing locality must never be replaced by this append operation')
    backup=output/'before-hunan-extension'
    if backup.exists():raise ValueError('Previous extension evidence exists; inspect it instead of overwriting')
    backup.mkdir()
    (backup/'manifest.json').write_bytes((output/'manifest.json').read_bytes())
    with closing(sqlite3.connect(output/'regional-guides.sqlite')) as original, closing(sqlite3.connect(backup/'regional-guides.sqlite')) as saved:
        original.backup(saved)
    for g in additions:store.put_guide(g)
    result=deepcopy(previous)
    result.update(guides=190,candidate_guides=9,generatable_localities=173)
    result['source_files'].update({p:sha(root/p) for p in HUNAN_FILES})
    result['candidate_source_ids'] += [g['source_id'] for g in additions]
    result['database_files']['regional-guides.sqlite']=sha(output/'regional-guides.sqlite')
    result['extension_note']='Two own Hunan guides appended; prior A7 manifest and SQLite backup retained; main untouched.'
    (output/'manifest.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    return verify(root,output)


def _replace_bytes(path,body):
    temporary=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def _atomic_write(path,body):
    _replace_bytes(path,body)


def append_c(root=ROOT,output=OUTPUT):
    """Append C4 data only; preserve the tested A9 manifest and consistent DBs.

    No service, model, public snapshot or main database is touched. Failed
    appends keep the original manifest and roll back every SQLite insertion.
    """
    from regional_guides import digest,official_content,region_key
    root=Path(root).resolve();output=Path(output).resolve();previous=verify(root,output)
    if (previous.get('candidate_guides'),previous.get('guides'),previous.get('generatable_localities'))!=(9,190,173):
        raise ValueError('C4 append requires the preserved 190/173 A9 candidate')
    additions=load_c_guides(root)
    from reviewed_oct29c_release import validate_sources,_capabilities
    validate_sources(additions);_capabilities(additions)
    backup=output/'before-c-extension'
    if backup.exists():raise ValueError('Previous C extension evidence exists; never overwrite it')
    original_manifest=(output/'manifest.json').read_bytes();backup.mkdir()
    (backup/'manifest.json').write_bytes(original_manifest)
    db=sqlite3.connect(output/'regional-guides.sqlite',timeout=15)
    try:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT count(*) FROM regional_current').fetchone()[0]!=190:raise ValueError('Candidate changed before append lock')
        for g in additions:
            if db.execute('SELECT 1 FROM regional_guides WHERE (province=? AND city=? AND district=?) OR source_id=?',
                          (g['province'],g['city'],g['district'],digest(g['source_url'])[:24])).fetchone():
                raise ValueError('Existing exact candidate scope/source history must never be replaced')
        for name in ['regional-guides.sqlite','regional-directory.sqlite']:
            with closing(sqlite3.connect((output/name).as_uri()+'?mode=ro',uri=True)) as current,closing(sqlite3.connect(backup/name)) as saved:current.backup(saved)
        ids=[]
        for g in additions:
            d=deepcopy(g);d.pop('version',None);sid=digest(d['source_url'])[:24];rid=region_key(d['province'],d['city'],d['district']);checksum=digest(official_content(d))
            d.update(region_id=rid,source_id=sid,content_hash=checksum)
            row=db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',
                           (rid,sid,checksum,d['province'],d['city'],d['district'],json.dumps(d,ensure_ascii=False)))
            db.execute('INSERT INTO regional_current VALUES(?,?)',(rid,row.lastrowid));ids.append(sid)
        # Commit all four together, then install the hashed manifest atomically.
        # Failure after commit restores the consistent pre-append SQLite backup.
        db.commit()
        result=deepcopy(previous);result.update(guides=194,candidate_guides=13,generatable_localities=177)
        result['source_files'].update({p:sha(root/p) for p in C_FILES});result['candidate_source_ids']+=ids
        result['database_files']['regional-guides.sqlite']=sha(output/'regional-guides.sqlite')
        result['extension_note']='C4 appended; before-c-extension retains the tested A9 manifest and consistent SQLite snapshots.'
        _atomic_write(output/'manifest.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
        return verify(root,output)
    except BaseException:
        db.rollback();db.close();db=None
        if (backup/'regional-guides.sqlite').exists():
            with closing(sqlite3.connect(backup/'regional-guides.sqlite')) as saved,closing(sqlite3.connect(output/'regional-guides.sqlite')) as target:saved.backup(target)
        if (output/'manifest.json').read_bytes()!=original_manifest:_atomic_write(output/'manifest.json',original_manifest)
        raise
    finally:
        if db is not None:db.close()


def append_d(root=ROOT,output=OUTPUT):
    """Append D4 data only; preserve the tested C13 manifest and consistent DBs.

    No service, model, public snapshot or main database is touched. Failed
    appends keep the original manifest and roll back every SQLite insertion.
    """
    from regional_guides import digest,official_content,region_key
    root=Path(root).resolve();output=Path(output).resolve();previous=verify(root,output)
    if (previous.get('candidate_guides'),previous.get('guides'),previous.get('generatable_localities'))!=(13,194,177):
        raise ValueError('D4 append requires the preserved 194/177 C13 candidate')
    additions=load_d_guides(root)
    from reviewed_oct29d_release import validate_sources,_capabilities
    validate_sources(additions);_capabilities(additions,root=root)
    backup=output/'before-d-extension'
    if backup.exists():raise ValueError('Previous D extension evidence exists; never overwrite it')
    original_manifest=(output/'manifest.json').read_bytes();backup.mkdir()
    (backup/'manifest.json').write_bytes(original_manifest)
    db=sqlite3.connect(output/'regional-guides.sqlite',timeout=15);original_db_bytes=None
    try:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('PRAGMA journal_mode').fetchone()[0].lower()!='delete':raise ValueError('D4 candidate requires a standalone DELETE-journal snapshot')
        original_db_bytes=(output/'regional-guides.sqlite').read_bytes()
        if hashlib.sha256(original_db_bytes).hexdigest()!=previous['database_files']['regional-guides.sqlite']:raise ValueError('Candidate changed before append lock')
        (backup/'regional-guides.exact-before.sqlite').write_bytes(original_db_bytes)
        if db.execute('SELECT count(*) FROM regional_current').fetchone()[0]!=194 or db.execute('SELECT count(*) FROM regional_guides').fetchone()[0]!=194:raise ValueError('D4 candidate history changed before append lock')
        if db.execute("SELECT seq FROM sqlite_sequence WHERE name='regional_guides'").fetchone()!=(194,):raise ValueError('D4 candidate version sequence differs')
        for g in additions:
            if db.execute('SELECT 1 FROM regional_guides WHERE (province=? AND city=? AND district=?) OR source_id=?',
                          (g['province'],g['city'],g['district'],digest(g['source_url'])[:24])).fetchone():
                raise ValueError('Existing exact candidate scope/source history must never be replaced')
        for name in ['regional-guides.sqlite','regional-directory.sqlite']:
            with closing(sqlite3.connect((output/name).as_uri()+'?mode=ro',uri=True)) as current,closing(sqlite3.connect(backup/name)) as saved:current.backup(saved)
        (backup/'backup-checksums.json').write_text(json.dumps({
            'scope':'D4 pre-append consistent SQLite backups plus exact standalone guide bytes',
            'files':{p.name:sha(p) for p in backup.iterdir() if p.is_file()},
            'exact_manifest_restore_guide':'regional-guides.exact-before.sqlite',
            'directory_database_never_written':True},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        ids=[]
        for g in additions:
            d=deepcopy(g);d.pop('version',None);sid=digest(d['source_url'])[:24];rid=region_key(d['province'],d['city'],d['district']);checksum=digest(official_content(d))
            d.update(region_id=rid,source_id=sid,content_hash=checksum)
            row=db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',
                           (rid,sid,checksum,d['province'],d['city'],d['district'],json.dumps(d,ensure_ascii=False)))

            if row.lastrowid!=195+len(ids):raise ValueError('D4 candidate version sequence differs')
            db.execute('INSERT INTO regional_current VALUES(?,?)',(rid,row.lastrowid));ids.append(sid)
        # Commit all four together, then install the hashed manifest atomically.
        # Failure after commit restores the consistent pre-append SQLite backup.
        db.commit()
        result=deepcopy(previous);result.update(guides=198,candidate_guides=17,generatable_localities=181)
        result['source_files'].update({p:sha(root/p) for p in D_FILES});result['candidate_source_ids']+=ids
        result['database_files']['regional-guides.sqlite']=sha(output/'regional-guides.sqlite')
        result['extension_note']='D4 appended; before-d-extension retains the tested C13 manifest and consistent SQLite snapshots.'
        _atomic_write(output/'manifest.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
        return verify(root,output)
    except BaseException:
        db.rollback();db.close();db=None
        # SQLite backup restore changes its file header. Restore the exact locked
        # standalone bytes so the preserved manifest remains verifiable as well.
        if original_db_bytes is not None and (output/'regional-guides.sqlite').read_bytes()!=original_db_bytes:_replace_bytes(output/'regional-guides.sqlite',original_db_bytes)
        if (output/'manifest.json').read_bytes()!=original_manifest:_replace_bytes(output/'manifest.json',original_manifest)
        raise
    finally:
        if db is not None:db.close()


def append_e(root=ROOT,output=OUTPUT):
    """Append E4 data only; preserve the tested D17 manifest and consistent DBs.

    No service, model, public snapshot or main database is touched. Failed
    appends keep the original manifest and roll back every SQLite insertion.
    """
    from regional_guides import digest,official_content,region_key
    root=Path(root).resolve();output=Path(output).resolve();previous=verify(root,output)
    if (previous.get('candidate_guides'),previous.get('guides'),previous.get('generatable_localities'))!=(17,198,181):
        raise ValueError('E4 append requires the preserved 198/181 D17 candidate')
    original_manifest=(output/'manifest.json').read_bytes()
    if json.loads(original_manifest)!=previous:raise ValueError('E4 candidate manifest changed before append lock')
    additions=load_e_guides(root)
    from reviewed_oct29e_release import validate_sources,_capabilities
    validate_sources(additions);_capabilities(additions,root=root)
    backup=output/'before-e-extension'
    if backup.exists():raise ValueError('Previous E extension evidence exists; never overwrite it')
    backup.mkdir()
    (backup/'manifest.json').write_bytes(original_manifest)
    db=sqlite3.connect(output/'regional-guides.sqlite',timeout=15);original_db_bytes=None;manifest_install_started=False
    try:
        db.execute('BEGIN IMMEDIATE')
        if (output/'manifest.json').read_bytes()!=original_manifest:raise ValueError('E4 candidate manifest changed before append lock')
        if db.execute('PRAGMA journal_mode').fetchone()[0].lower()!='delete':raise ValueError('E4 candidate requires a standalone DELETE-journal snapshot')
        original_db_bytes=(output/'regional-guides.sqlite').read_bytes()
        if hashlib.sha256(original_db_bytes).hexdigest()!=previous['database_files']['regional-guides.sqlite']:raise ValueError('Candidate changed before append lock')
        (backup/'regional-guides.exact-before.sqlite').write_bytes(original_db_bytes)
        if db.execute('SELECT count(*) FROM regional_current').fetchone()[0]!=198 or db.execute('SELECT count(*) FROM regional_guides').fetchone()[0]!=198:raise ValueError('E4 candidate history changed before append lock')
        if db.execute("SELECT seq FROM sqlite_sequence WHERE name='regional_guides'").fetchone()!=(198,):raise ValueError('E4 candidate version sequence differs')
        for g in additions:
            if db.execute('SELECT 1 FROM regional_guides WHERE (province=? AND city=? AND district=?) OR source_id=?',
                          (g['province'],g['city'],g['district'],digest(g['source_url'])[:24])).fetchone():
                raise ValueError('Existing exact candidate scope/source history must never be replaced')
        for name in ['regional-guides.sqlite','regional-directory.sqlite']:
            with closing(sqlite3.connect((output/name).as_uri()+'?mode=ro',uri=True)) as current,closing(sqlite3.connect(backup/name)) as saved:current.backup(saved)
        (backup/'backup-checksums.json').write_text(json.dumps({
            'scope':'E4 pre-append consistent SQLite backups plus exact standalone guide bytes',
            'files':{p.name:sha(p) for p in backup.iterdir() if p.is_file()},
            'exact_manifest_restore_guide':'regional-guides.exact-before.sqlite',
            'directory_database_never_written':True},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        ids=[]
        for g in additions:
            d=deepcopy(g);d.pop('version',None);sid=digest(d['source_url'])[:24];rid=region_key(d['province'],d['city'],d['district']);checksum=digest(official_content(d))
            d.update(region_id=rid,source_id=sid,content_hash=checksum)
            row=db.execute('INSERT INTO regional_guides(region_id,source_id,content_hash,province,city,district,payload) VALUES(?,?,?,?,?,?,?)',
                           (rid,sid,checksum,d['province'],d['city'],d['district'],json.dumps(d,ensure_ascii=False)))

            if row.lastrowid!=199+len(ids):raise ValueError('E4 candidate version sequence differs')
            db.execute('INSERT INTO regional_current VALUES(?,?)',(rid,row.lastrowid));ids.append(sid)
        # Commit all four together, then install the hashed manifest atomically.
        # Failure after commit restores the consistent pre-append SQLite backup.
        db.commit()
        result=deepcopy(previous);result.update(guides=202,candidate_guides=21,generatable_localities=185)
        result['source_files'].update({p:sha(root/p) for p in E_FILES});result['candidate_source_ids']+=ids
        result['database_files']['regional-guides.sqlite']=sha(output/'regional-guides.sqlite')
        result['extension_note']='E4 appended; before-e-extension retains the tested D17 manifest and consistent SQLite snapshots.'
        if (output/'manifest.json').read_bytes()!=original_manifest:raise ValueError('E4 candidate manifest changed during append lock')
        manifest_install_started=True
        _atomic_write(output/'manifest.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
        return verify(root,output)
    except BaseException:
        db.rollback();db.close();db=None
        # SQLite backup restore changes its file header. Restore the exact locked
        # standalone bytes so the preserved manifest remains verifiable as well.
        if original_db_bytes is not None and (output/'regional-guides.sqlite').read_bytes()!=original_db_bytes:_replace_bytes(output/'regional-guides.sqlite',original_db_bytes)
        if manifest_install_started and (output/'manifest.json').read_bytes()!=original_manifest:_replace_bytes(output/'manifest.json',original_manifest)
        raise
    finally:
        if db is not None:db.close()
