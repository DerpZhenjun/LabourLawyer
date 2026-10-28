"""Low-rate copies of public originals actually requested by own native controls."""
import hashlib,json,re,sqlite3,sys,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs,urlsplit,unquote
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong'
OUT=BASE/'downloads-round26'
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    if OUT.exists():raise ValueError('Preserve own downloaded evidence')
    OUT.mkdir()
    formal=json.loads((BASE/'formal-round26/dom.json').read_text('utf8'));source=formal['url']
    first=json.loads((BASE/'control-template-round26/public-file-requests.json').read_text('utf8'))['requests']
    all_requests=json.loads((BASE/'control-sample-round26/public-file-requests.json').read_text('utf8'))['requests']
    template_urls={r['url'] for r in first if r.get('resourceType')=='Fetch'}
    assert len(template_urls)==2 and len(all_requests)==5
    results=[]
    for r in all_requests:
        url=r['url'];parsed=urlsplit(url);query=parse_qs(parsed.query)
        assert parsed.scheme=='https' and parsed.hostname=='zwfw-new.hunan.gov.cn' and parsed.path=='/picPathMapping'
        assert r['status']==200 and query['bucketName'][0] in {'zwfw202106','zwfw202411'}
        name=query['picPath'][0].rsplit('$$',1)[1];identity=re.search(r'/(\d+)\$\$',query['picPath'][0])[1]
        image=r['resourceType']=='Image';kind='official_flow_image' if image else 'blank_control_unclassified' if url in template_urls else 'sample_control_unclassified'
        with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':source}),timeout=25) as response:
            assert response.url==url and response.status==200
            data=response.read(8*1024*1024+1);assert len(data)<8*1024*1024
            ext='png' if image else 'doc';signature=b'\x89PNG\r\n\x1a\n' if image else bytes.fromhex('D0CF11E0A1B11AE1')
            assert data.startswith(signature),'Unexpected public original signature'
            target=ROOT/'templates/_docx/_regional/430102'/(identity+'.'+ext);target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert target.read_bytes()==data,'Changed original; preserve previous bytes'
            else:target.write_bytes(data)
            row={'id':identity,'source_url':source,'download_url':url,'final_download_url':response.url,'http_status':response.status,
                'original_name':name,'official_download_name':unquote(response.headers.get('Content-Disposition','').split('filename=')[-1]),
                'file_type':ext,'file':target.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
                'download_status':'downloaded','official_kind':kind,'can_generate':False,'applicable_district':'芙蓉区','region_code':'430102',
                'collected_at':datetime.now(timezone.utc).isoformat(),'discovery':'actual_native_template_or_sample_control_network_GET200'}
        results.append(row);save(OUT/'original-files.json',results);print(identity,kind,len(data),flush=True);time.sleep(.5)
    with sqlite3.connect((ROOT/'backend/data/regional-directory.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute('SELECT payload FROM directory_areas WHERE id=?',('national:430102',)).fetchall()
    assert len(rows)==1;identity=json.loads(rows[0][0]);assert identity['province']=='hunan' and identity['city']=='长沙市' and identity['code']=='430102' and identity['parent_code']=='430100'
    save(BASE/'directory-identity.json',identity)
    save(OUT/'manifest.json',{'source_url':source,'own_original_docs':4,'own_flow_image':1,'generation_enabled':False,'native_zip_download_wait':'timed_out_after_control_GET200; copied actual observed public originals separately','models':0})
if __name__=='__main__':main()
