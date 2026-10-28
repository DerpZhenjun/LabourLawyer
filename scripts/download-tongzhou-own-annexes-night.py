"""Low-rate public GETs resolved from this guide's observed attachment metadata.

Native sample controls were clicked but did not start downloads. These alternate
public URLs follow the same guide's rendered /pubtask/download links; HTTP and
bytes are verified independently. No authenticated endpoint or form submission.
"""
import hashlib,json,re,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-tongzhou'
SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110112000000/c692cfd3-1a9d-4734-8f16-86b3a0dbafee.html?locationCode=110112000000&serverType=1002'
def main():
    out=BASE/'downloads-0700'
    if out.exists():raise ValueError('Preserve original download evidence')
    out.mkdir();page=json.loads((BASE/'sections-0650/materials-final.json').read_text('utf8'))
    match=re.search(r'var attachment\s*=\s*(\[.*?\]);',page['html'],re.S)
    entries=json.loads(match[1]);results=[]
    from datetime import datetime,timezone
    for item in entries:
        if item['DOC_TYPE'] not in {'ATT3','DOC_LCT'}:continue
        identity=item['DOC_ID'];ext=item['DOC_EXT'];name=item['DOC_NAME']
        url='https://banshi.beijing.gov.cn/pubtask/download/'+identity+'.'+ext
        record={'id':identity,'original_name':name,'file_type':ext,'source_url':SOURCE,
            'download_url':url,'url_resolution':'own official attachment metadata and own rendered public download path',
            'official_kind':'sample' if item['DOC_TYPE']=='ATT3' else 'instruction',
            'downloaded_at':datetime.now(timezone.utc).isoformat(),'can_generate':False,'document_types':[]}
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as response:
                if urlsplit(response.url).hostname!='banshi.beijing.gov.cn':raise ValueError('Foreign final host')
                data=response.read(12*1024*1024+1)
                if len(data)>12*1024*1024:raise ValueError('Oversize original')
                if not data.startswith(b'PK' if ext=='docx' else b'\xff\xd8'):raise ValueError('Unexpected document bytes')
                target=ROOT/'templates/_docx/_regional/110112'/(identity+'.'+ext)
                if target.exists() and target.read_bytes()!=data:raise ValueError('Existing original differs; not overwritten')
                target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():target.write_bytes(data)
                record.update(file=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(data).hexdigest(),
                    bytes=len(data),http_status=response.status,download_status='downloaded',final_download_url=response.url)
        except Exception as exc:record.update(download_status='failed',download_error=str(exc))
        results.append(record)
        (out/'original-files.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
        time.sleep(1)
    print(json.dumps([{'id':r['id'],'status':r['download_status'],'sha256':r.get('sha256')} for r in results]))
if __name__=='__main__':main()
