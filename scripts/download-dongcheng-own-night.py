"""Copy only this own guide's observed public sample/flow attachments."""
import hashlib,json,re,sqlite3,time
from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-dongcheng'
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'downloads-round28'
    if out.exists():raise ValueError('Preserve own originals')
    out.mkdir();page=json.loads((BASE/'capture-remaining-round28/materials-final.json').read_text('utf8'));source=page['url']
    assert '/110101000000/' in source and '63fb2f78-f61a-434e-a834-ac398cd29417' in source
    entries=json.loads(re.search(r'var attachment\s*=\s*(\[.*?\]);',page['html'],re.S)[1]);rows=[]
    for item in entries:
        if item['DOC_TYPE'] not in {'ATT3','DOC_LCT'}:continue
        identity=item['DOC_ID'];ext=item['DOC_EXT'];url='https://banshi.beijing.gov.cn/pubtask/download/'+identity+'.'+ext
        with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':source}),timeout=25) as response:
            assert response.status==200 and response.url==url
            data=response.read(12*1024*1024+1);assert len(data)<=12*1024*1024
            actual='docx' if data.startswith(b'PK') else 'png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'jpg' if data.startswith(b'\xff\xd8') else None
            assert actual and (ext!='docx' or actual=='docx')
            target=ROOT/'templates/_docx/_regional/110101'/(identity+'.'+actual);target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data)
            rows.append({'id':identity,'original_name':item['DOC_NAME'],'file_type':ext,'actual_file_type':actual,
                'file':target.relative_to(ROOT).as_posix(),'source_url':source,'download_url':url,'final_download_url':response.url,
                'region_code':'110101','http_status':response.status,'download_status':'downloaded','bytes':len(data),
                'sha256':hashlib.sha256(data).hexdigest(),'official_kind':'sample' if item['DOC_TYPE']=='ATT3' else 'instruction',
                'downloaded_at':datetime.now(timezone.utc).isoformat(),'can_generate':False,'document_types':[]})
        save(out/'original-files.json',rows);time.sleep(.5)
    with sqlite3.connect((ROOT/'backend/data/regional-directory.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        ids=db.execute('SELECT payload FROM directory_areas WHERE id=?',('national:110101',)).fetchall()
    assert len(ids)==1;area=json.loads(ids[0][0]);assert area['district']=='东城区' and area['city']=='北京市'
    save(BASE/'directory-identity.json',area)
    print(json.dumps([{'id':r['id'],'type':r['actual_file_type'],'sha256':r['sha256']} for r in rows]))
if __name__=='__main__':main()
