"""Prepare isolated public candidate data. This module never starts any service."""
from pathlib import Path
import hashlib
import json
import sqlite3
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
        if relative not in SOURCE_FILES+HUNAN_FILES or sha(root/relative)!=checksum:raise ValueError('Candidate source evidence changed')
    expected_sources=SOURCE_FILES+HUNAN_FILES if manifest.get('candidate_guides')==9 else SOURCE_FILES
    if set(manifest['source_files'])!=set(expected_sources):raise ValueError('Candidate source set differs')
    for name,checksum in manifest['database_files'].items():
        if name not in {'regional-guides.sqlite','regional-directory.sqlite'} or sha(output/name)!=checksum:
            raise ValueError('Candidate store differs from prepared data; do not replace it automatically')
    with closing(sqlite3.connect((output/'regional-guides.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        count=db.execute('SELECT COUNT(*) FROM regional_current').fetchone()[0]
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
