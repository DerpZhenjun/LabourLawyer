"""Preserve the single original actually linked by Rongjiang's own 2026 notice."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,HTTPRedirectHandler,build_opener
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang'
OUT=BASE/'downloads-0425'
SOURCE='https://rjxq.ganzhou.gov.cn/rjxq/tzgg/202606/f931ffb78c85406cbf9636a3489296b5.shtml'


class OwnRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urlsplit(newurl).scheme!='https' or urlsplit(newurl).hostname!='rjxq.ganzhou.gov.cn':raise ValueError('Refuse foreign redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def main():
    if OUT.exists():raise ValueError('Preserve completed original evidence')
    raw=json.loads((BASE/'source-0425/dom.json').read_text('utf8'))
    if raw['url']!=SOURCE or '赣州蓉江新区劳动人事争议仲裁申请书、证据目录及模板' not in raw['title']:raise ValueError('Own notice identity missing')
    links=json.loads((BASE/'source-0425/links.json').read_text('utf8'))
    items=[a for a in links if a['text']=='劳动仲裁申请书及证据目录']
    if len(items)!=1:raise ValueError('Own annex link changed')
    a=items[0];url=a['url']
    if not url.startswith(SOURCE.removesuffix('.shtml')+'/files/'):raise ValueError('Not own public annex path')
    OUT.mkdir()
    record={'source_url':SOURCE,'official_display_name':a['text'],'original_name':Path(urlsplit(url).path).name,
        'download_url':url,'province':'jiangxi','city':'赣州市','district':'赣州蓉江新区',
        'official_region_code':None,'region_identity_status':'pending_own_directory_verification',
        'published':False,'can_generate':False,'official_kind':'mixed_pending_original_review',
        'note':'网页同时展示空白申请书、空白证据目录及已填示例；整个文件不能直接认定为纯空白模板。'}
    try:
        with build_opener(OwnRedirect()).open(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r:
            body=r.read(20*1024*1024+1)
            record.update(http_status=r.status,final_download_url=r.url,headers=dict(r.headers))
        if len(body)>20*1024*1024 or not body.startswith((b'\xd0\xcf',b'PK')):raise ValueError('Not a bounded Word original')
        relative=Path('templates/_docx/_regional/function-jiangxi-ganzhou-rongjiang')/record['original_name']
        target=ROOT/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=body:raise ValueError('Original changed; do not overwrite')
        if not target.exists():target.write_bytes(body)
        record.update(file=relative.as_posix(),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),
            downloaded_at=datetime.now(timezone.utc).isoformat(),download_status='downloaded')
    except Exception as exc:record.update(download_status='failed',reason=str(exc))
    (OUT/'original-file.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(record,ensure_ascii=True))


if __name__=='__main__':main()
