"""Fetch only own public component attachment URLs; never persist response cookies."""
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit, urlunsplit
import urllib.request

from collect import OUT, NOW, save

ROOT = OUT.parents[2]

def safe_url(value):
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))

def main():
    raw_file = OUT/'.private-sealed/luyang/public-guide-viewmodel.json'
    raw = json.loads(raw_file.read_text(encoding='utf-8'))
    source_url = raw['data']['source_url']
    data = raw['data']['data']
    assert data['ssqdCode']=='da27275dce0645ffb87c9d9423e84452'
    assert data['ssqdZoneCode']=='340103000000'
    targets=[]
    for material in data['clJson']:
        for kind, field in [('blank','materialEmpty'),('sample','materialSample')]:
            for item in material['json'][field]:
                targets.append({**item,'classification':kind,'material_id':material['id'],'material_name':material['materialName']})
    for item in data.get('processImgJson',[]):
        targets.append({**item,'classification':'instruction','material_name':'办理流程图'})
    manifest=[]
    private=[]
    for item in targets:
        url=item['filePath']
        assert urlsplit(url).hostname=='hf.ahzwfw.gov.cn'
        filename=item['id']+'-'+item['fileName']
        assert not re.search(r'[<>:"/\\|?*\x00-\x1f]',filename)
        captured_at=NOW()
        request=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':source_url})
        # Default opener has no CookieJar. No request auth/cookies and no login operation.
        with urllib.request.urlopen(request,timeout=25) as response:
            final_url=response.url
            assert urlsplit(final_url).hostname=='hf.ahzwfw.gov.cn'
            body=response.read(20_000_001)
            assert len(body)<=20_000_000
            assert body.startswith((b'PK',b'\xd0\xcf',b'%PDF',b'\x89PNG',b'\xff\xd8'))
            metadata={'http_status':response.status,'content_type':response.headers.get('Content-Type'),'content_length':response.headers.get('Content-Length'),'content_disposition':response.headers.get('Content-Disposition'),'last_modified':response.headers.get('Last-Modified')}
            omitted=bool(response.headers.get('Set-Cookie'))
        digest=hashlib.sha256(body).hexdigest()
        copies=[]
        for path in [OUT/'luyang/downloads'/filename, ROOT/'templates/_docx/_regional/340103000000'/filename]:
            if path.exists():raise ValueError('Refusing to overwrite original')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
            copies.append(path.relative_to(ROOT).as_posix())
        clean={k:v for k,v in item.items() if k!='filePath'}
        clean.update(source_url=source_url,download_url=safe_url(url),requested_url_sha256=hashlib.sha256(url.encode()).hexdigest(),final_url=safe_url(final_url),final_url_sha256=hashlib.sha256(final_url.encode()).hexdigest(),downloaded_at=captured_at,sha256=digest,bytes=len(body),path=copies[0],file=copies[1],status='downloaded',request_credentials='none',response_session_headers='present_value_not_saved' if omitted else 'absent',visual_qa='NOT_RUN',**metadata)
        manifest.append(clean)
        private.append({'id':item['id'],'requested_url':url,'final_url':final_url,'requested_at':captured_at,'sha256':digest})
        print(item['classification'],filename,len(body),digest,flush=True)
        time.sleep(2)
    save(OUT/'luyang/downloads/manifest.json',manifest)
    save(OUT/'.private-sealed/luyang/exact-download-urls.json',private)
    # Definitions retain literal official fields and attachment IDs but omit opaque URL queries.
    def clean(v):
        if isinstance(v,dict):return {k:clean(w) for k,w in v.items()}
        if isinstance(v,list):return [clean(w) for w in v]
        if isinstance(v,str) and v.startswith(('http://','https://')) and urlsplit(v).query:
            return safe_url(v)
        return v
    save(OUT/'luyang/public-component-without-url-queries.json',{'captured_at':raw['captured_at'],'source_url':source_url,'raw_component_sha256':hashlib.sha256(raw_file.read_bytes()).hexdigest(),'transformation':'URL query removed from all component URL values; raw component retained privately','data':clean(data)})

if __name__=='__main__':main()
