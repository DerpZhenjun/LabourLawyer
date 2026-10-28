"""Download only the two ZIP links actually observed in Baiyun's own page."""
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/nationwide-localization-20261023-night/cross-province/guangdong-baiyun'
OUT = BASE / 'downloads-0410'
SOURCE = 'https://www.by.gov.cn/gzjg/qrlzyhshbzj/zcgg/cjgg/content/post_10451075.html'
NOW = lambda: datetime.now(timezone.utc).isoformat()


class OwnRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https' or urlsplit(newurl).hostname != 'www.by.gov.cn':
            raise ValueError('Refuse non-own HTTPS redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    if OUT.exists(): raise ValueError('Preserve previous download evidence')
    OUT.mkdir()
    links = json.loads((BASE / 'source-0405/links.json').read_text('utf8'))
    annexes = [a for a in links if a['text'].startswith(('附件1：','附件2：'))]
    if len(annexes) != 2: raise ValueError('Actual own annex structure changed')
    files = []
    for n, a in enumerate(annexes, 1):
        record = {'source_url': SOURCE, 'official_display_name': a['text'], 'download_url': a['url'],
                  'package_kind': 'official_material_package' if n == 1 else 'official_filled_examples',
                  'collected_at': NOW(), 'region_code': '440111', 'published': False}
        try:
            if urlsplit(a['url']).hostname != 'www.by.gov.cn': raise ValueError('Foreign annex')
            with build_opener(OwnRedirect()).open(Request(a['url'], headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r:
                body = r.read(20*1024*1024+1)
                record.update(http_status=r.status, final_url=r.url, headers=dict(r.headers), downloaded_at=NOW())
            if len(body) > 20*1024*1024 or not zipfile.is_zipfile(io.BytesIO(body)): raise ValueError('Not a bounded ZIP package')
            relative = Path('templates/_docx/_regional/440111') / ('official-materials.zip' if n == 1 else 'official-examples.zip')
            dest = ROOT / relative
            if dest.exists() and dest.read_bytes() != body: raise ValueError('Original changed; retain both versions before overwrite')
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists(): dest.write_bytes(body)
            record.update(file=relative.as_posix(),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),download_status='downloaded',members=[])
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                infos=z.infolist()
                if len(infos)>100 or sum(i.file_size for i in infos)>40*1024*1024: raise ValueError('Unbounded archive')
                for i in infos:
                    name=i.filename
                    if not i.flag_bits & 0x800:
                        try:name=name.encode('cp437').decode('gbk')
                        except (UnicodeError,LookupError):pass
                    if i.is_dir(): continue
                    data=z.read(i)
                    # No archive-controlled output paths. Own immutable numbered originals.
                    ext=Path(name).suffix.lower()
                    if ext not in {'.doc','.docx','.pdf','.jpg','.png','.jpeg'}: raise ValueError('Unexpected archive member type')
                    member_relative=relative.parent / f'package-{n}' / f'{len(record["members"])+1:02}{ext}'
                    target=ROOT/member_relative;target.parent.mkdir(parents=True,exist_ok=True)
                    if target.exists() and target.read_bytes()!=data: raise ValueError('Member changed')
                    if not target.exists():target.write_bytes(data)
                    record['members'].append({'archive_member_name':name,'file':member_relative.as_posix(),
                        'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'file_type':ext[1:],
                        'classification':'unreviewed' if n==1 else 'sample'})
        except Exception as exc:
            record.update(download_status='failed',reason=str(exc))
        files.append(record)
        (OUT/'original-files.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(record,ensure_ascii=True),flush=True)
        time.sleep(2)


if __name__=='__main__':main()
