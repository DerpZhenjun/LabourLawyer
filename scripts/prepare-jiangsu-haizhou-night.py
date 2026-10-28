"""Download only the eight links in the actual independently captured county guide."""
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote
from urllib.request import Request,build_opener

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_jiangsu import parse_haizhou_capture,official_filename
from regional_directory import DirectoryStore
from regional_guides import digest,now
c=importlib.import_module('collect-chengdu-districts')
transport=importlib.import_module('prepare-jiangsu-xishan-night')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'


def main():
    if (OUT/'guide.json').exists():raise ValueError('Own preparation already exists; preserve it')
    source=OUT/'formal-0525';manifest=json.loads((source/'manifest.json').read_text('utf8'))
    path=source/'formal-guide-final.json'
    if (hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['capture_sha256']
            or len(manifest['sections_clicked'])!=12 or manifest['material_dialogs']!=4):
        raise ValueError('Own actual interactions or capture digest missing')
    guide=parse_haizhou_capture(json.loads(path.read_text('utf8')))
    own=[p for p in DirectoryStore(ROOT/'backend/data/regional-directory.sqlite').areas('jiangsu','连云港市')
         if p['district']=='海州区' and p['code']=='320706' and p['parent_code']=='320700' and p['level']==4]
    if len(own)!=1:raise ValueError('Own public directory identity not matched')
    guide['evidence']={'capture_file':path.relative_to(ROOT).as_posix(),'capture_sha256':manifest['capture_sha256'],
        'screenshot':(source/'formal-guide.png').relative_to(ROOT).as_posix(),'official_directory':own[0]}
    c.save(OUT/'identity.json',own[0])
    opener=build_opener(transport.OfficialRedirect())
    for t in guide['templates']:
        try:
            if not transport.official(t['download_url']):raise ValueError('Not own observed official URL')
            with opener.open(Request(t['download_url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                body=response.read(20*1024*1024+1)
                if len(body)>20*1024*1024 or not body.startswith((b'PK',b'\xd0\xcf',b'%PDF',b'\xff\xd8',b'\x89PNG')):
                    raise ValueError('Not accepted office/image bytes')
                original=unquote(response.headers.get_filename() or '');name=official_filename(original)
                if not name:raise ValueError('Official filename missing')
                safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name)[:140]
                relative=Path('templates/_docx/_regional/320706')/(t['id']+'-'+safe);file=ROOT/relative
                if file.exists():raise ValueError('Original already present; no overwrite')
                file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(body)
                t.update(original_name=name,original_http_filename=original,file=relative.as_posix(),
                    sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),file_type=file.suffix[1:].lower(),
                    downloaded_at=now(),verified_at=now(),download_status='downloaded',http_status=response.status,
                    final_download_url=response.url,response_headers=dict(response.headers.items()))
        except Exception as exc:
            t.update(download_status='failed',download_error=str(exc))
            event={k:guide[k] for k in ['province','city','district','region_code']}
            event.update(id=digest([guide['source_url'],t['id'],'TEMPLATE_DOWNLOAD_FAILED'])[:32],
                type='TEMPLATE_DOWNLOAD_FAILED',service=guide['service_name'],url=t['download_url'],occurred_at=now(),
                keyword='劳动人事争议仲裁申请',screenshot=guide['evidence']['screenshot'],reason=str(exc),attempts=1,
                final_status='pending_own_attachment_recheck',remediation='保留自己的失败记录，不借用市级或邻县附件',delivery_status='PENDING_OPENCLAW')
            c.save(OUT/'outbox'/(event['id']+'.json'),event)
        c.save(OUT/'guide.json',guide)
        print(t['id'],t['download_status'],t.get('sha256',''),flush=True);time.sleep(1)
    c.save(OUT/'preparation.json',{'at':now(),'own_materials':len(guide['materials']),
        'own_downloaded_annexes':sum(t['download_status']=='downloaded' for t in guide['templates']),
        'published':False,'can_generate':False,'model_calls':0})


if __name__=='__main__':main()
