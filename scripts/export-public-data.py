"""Publish only the reviewed public catalogue, never databases or browser sessions."""
from contextlib import closing
from copy import deepcopy
import hashlib,json,sqlite3,sys
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,now

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def public_guide(value):
    guide=deepcopy(value)
    # Public field text and source provenance remain; raw browser artifacts,
    # traces, headers, cookies, screenshots and opaque SSO redirects stay local.
    for key in ['evidence','version','region_id','content_hash']:guide.pop(key,None)
    channel=guide.get('channel',{})
    check=channel.get('entry_check',{})
    if check:
        channel['entry_check']={k:check[k] for k in ['status','official_link','checked_at','submitted'] if k in check}
        channel['entry_check']['published_note']='只保留公开核验状态；会话跳转参数不随发行快照分发。'
    entry=channel.get('entry_url')
    if entry and any(word in urlsplit(entry).path.lower() for word in ['login','sso','oauth']):
        channel['entry_url']=guide['source_url']
        channel['entry_note']='打开自己的官方指南后，按官方页面进入登录；不保存临时会话链接。'
    return guide

def main():
    out=ROOT/'data/public-regions';out.mkdir(parents=True,exist_ok=True)
    guides=[public_guide(g) for g in RegionalStore(ROOT/'backend/data/regional-guides.sqlite').inventory()]
    with closing(sqlite3.connect((ROOT/'backend/data/regional-directory.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        directory=[json.loads(row[0]) for row in db.execute('SELECT payload FROM directory_areas ORDER BY level,province,city,district,id')]
    save(out/'guides.json',guides);save(out/'directory.json',directory)
    manifest={'schema_version':1,'exported_at':now(),'scope':'已发布的公开指南与地区目录；目录不等于指南覆盖，不包含个人案件或浏览器会话。',
        'guides':len(guides),'generatable_localities':sum(any(t.get('can_generate') for t in g['templates']) for g in guides),
        'directory_rows':len(directory),'files':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ['guides.json','directory.json']}}
    save(out/'manifest.json',manifest)
    candidates=json.loads((ROOT/'reports/nationwide-localization-20261028/CANDIDATES.json').read_text('utf8'))
    save(ROOT/'config/regional_candidates.json',[{k:c[k] for k in ['province','city','district','region_code','source_id','source_url','published','can_generate'] if k in c} for c in candidates])
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main()
