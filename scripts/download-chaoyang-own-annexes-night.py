"""Independently download only this exact guide's observed public attachments."""
import hashlib,json,re,sqlite3,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-chaoyang'
SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110105000000/75d01c1c-dc66-49fe-93a1-7003eaaedd8a.html'
def main():
    out=BASE/'downloads-round23'
    if out.exists():raise ValueError('Preserve own original download iteration')
    out.mkdir();raw=json.loads((BASE/'sections-round23-resumed/materials-final.json').read_text('utf8'))
    entries=json.loads(re.search(r'var attachment\s*=\s*(\[.*?\]);',raw['html'],re.S)[1]);result=[]
    for item in entries:
        if item['DOC_TYPE'] not in {'ATT3','DOC_LCT'}:continue
        identity=item['DOC_ID'];ext=item['DOC_EXT'];url='https://banshi.beijing.gov.cn/pubtask/download/'+identity+'.'+ext
        row={'id':identity,'original_name':item['DOC_NAME'],'source_url':SOURCE,'download_url':url,
            'file_type':ext,'official_kind':'sample' if item['DOC_TYPE']=='ATT3' else 'instruction',
            'downloaded_at':datetime.now(timezone.utc).isoformat(),'can_generate':False,'document_types':[],
            'url_resolution':'own observed public attachment metadata; own guide rendered public-download path; no authenticated endpoint'}
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:
                if urlsplit(r.url).hostname!='banshi.beijing.gov.cn':raise ValueError('Unexpected final host')
                data=r.read(12*1024*1024+1)
                if len(data)>12*1024*1024:raise ValueError('Oversize original')
                actual='docx' if data.startswith(b'PK') else 'png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'jpg' if data.startswith(b'\xff\xd8') else None
                if not actual or (ext=='docx' and actual!='docx'):raise ValueError('Unknown source bytes')
                target=ROOT/'templates/_docx/_regional/110105'/(identity+'.'+actual)
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():assert target.read_bytes()==data,'Original changed; not overwritten'
                else:target.write_bytes(data)
                row.update(file=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(data).hexdigest(),
                    bytes=len(data),http_status=r.status,download_status='downloaded',final_download_url=r.url,
                    actual_file_type=actual,content_type=r.headers.get('Content-Type'))
        except Exception as exc:row.update(download_status='failed',download_error=str(exc))
        result.append(row);(out/'original-files.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');time.sleep(1)
    directory=ROOT/'backend/data/regional-directory.sqlite'
    with sqlite3.connect(directory.as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute("SELECT payload FROM directory_areas WHERE province='beijing' AND district='朝阳区'").fetchall()
    assert len(rows)==1;identity=json.loads(rows[0][0]);assert (identity['code'],identity['parent_code'],identity['city'])==('110105','110100','北京市')
    (BASE/'directory-identity.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps([{'id':r['id'],'kind':r['official_kind'],'status':r['download_status'],'sha256':r.get('sha256')} for r in result]))
if __name__=='__main__':main()
