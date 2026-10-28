"""Initialize empty public catalogues from a versioned, integrity-checked snapshot.

Existing catalogues are never merged, reset or overwritten. Case/user databases,
network requests and model services are outside this module.
"""
from contextlib import closing
from copy import deepcopy
import hashlib,json,sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from regional_guides import RegionalStore,digest
from regional_directory import DirectoryStore
from regional_adapters import checked_reference_adapter

ROOT=Path(__file__).resolve().parents[1]

def _count(path,table):
    if not path.exists():return 0
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        if not db.execute('SELECT 1 FROM sqlite_master WHERE type="table" AND name=?',(table,)).fetchone():
            raise ValueError('Existing public catalogue has an unexpected schema; leave it untouched')
        return db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]

def bootstrap_public_data(root=ROOT):
    root=Path(root).resolve();folder=root/'data/public-regions'
    result={'guides_imported':0,'directory_imported':0,'missing_attachments':[]}
    if not (folder/'manifest.json').is_file():return {**result,'state':'no_public_snapshot'}
    manifest=json.loads((folder/'manifest.json').read_text('utf8'))
    if manifest.get('schema_version')!=1:raise ValueError('Unsupported public snapshot version')
    payload={}
    # Verify the complete release before creating or changing either database.
    for filename in ['guides.json','directory.json']:
        body=(folder/filename).read_bytes()
        if hashlib.sha256(body).hexdigest()!=manifest.get('files',{}).get(filename):raise ValueError('Public snapshot checksum differs: '+filename)
        payload[filename]=json.loads(body)
        if not isinstance(payload[filename],list):raise ValueError('Public snapshot must be a record list')
    guides=deepcopy(payload['guides.json'])
    for g in guides:
        source=urlsplit(g.get('source_url',''));host=source.hostname or ''
        if (source.scheme not in {'http','https'} or not host.endswith('.gov.cn')
            or not all(g.get(k) for k in ['province','city','district','region_code','collected_at','verified_at'])
            or g.get('source_id')!=digest(g['source_url'])[:24]):raise ValueError('Public guide source identity is invalid')
        for t in g.get('templates',[]):
            if t.get('region_code')!=g['region_code']:raise ValueError('Attachment belongs to another locality')
            filename=t.get('file')
            path=(root/filename).resolve() if isinstance(filename,str) and filename else root
            valid=path.is_relative_to((root/'templates/_docx/_regional').resolve()) and path.is_file()
            valid=valid and hashlib.sha256(path.read_bytes()).hexdigest()==t.get('sha256')
            if t.get('download_status')=='downloaded' and not valid:
                t.update(can_generate=False,document_types=[],download_status='local_copy_unavailable')
                result['missing_attachments'].append(t.get('file'))
            if t.get('can_generate'):
                try:
                    if not valid or not t.get('document_types'):raise ValueError('No approved local attachment')
                    for kind in t['document_types']:checked_reference_adapter(g,t,kind)
                except ValueError:t.update(can_generate=False,document_types=[])
    for a in payload['directory.json']:
        if not all(a.get(k) for k in ['provider','code','province','source_url','collected_at']) or a.get('level') not in {2,3,4}:
            raise ValueError('Public directory source identity is invalid')
        if a['level']==4 and not all(a.get(k) for k in ['city','district']):raise ValueError('Missing precise locality')
    guide_path=root/'backend/data/regional-guides.sqlite';directory_path=root/'backend/data/regional-directory.sqlite'
    guide_count=_count(guide_path,'regional_guides');area_count=_count(directory_path,'directory_areas')
    if not guide_count:
        store=RegionalStore(guide_path)
        for g in guides:store.put_guide(g);result['guides_imported']+=1
    if not area_count:
        store=DirectoryStore(directory_path)
        for a in payload['directory.json']:store.put_area(a);result['directory_imported']+=1
    return {**result,'state':'existing_preserved' if guide_count and area_count else 'public_snapshot_initialized'}
