"""Download Dafeng's eight own observed annexes; never enables generation."""
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote
from urllib.request import Request,build_opener
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_jiangsu import parse_dafeng_capture,official_filename
from regional_directory import DirectoryStore
from regional_guides import digest,now
c=importlib.import_module('collect-chengdu-districts')
transport=importlib.import_module('prepare-jiangsu-xishan-night')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'


def main():
    if (OUT/'guide.json').exists():raise ValueError('Preserve prepared own guide, no repeated acquisition')
    manifest=json.loads((OUT/'capture-manifest.json').read_text('utf8'));path=OUT/manifest['capture_file']
    if (hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['capture_sha256']
            or len(manifest['sections_clicked'])!=12 or manifest['material_dialogs_opened']!=4):
        raise ValueError('Own actual interactions missing or capture changed')
    guide=parse_dafeng_capture(json.loads(path.read_text('utf8')))
    own=[p for p in DirectoryStore(ROOT/'backend/data/regional-directory.sqlite').areas('jiangsu','盐城市')
         if p['district']=='大丰区' and p['code']=='320904' and p['city']=='盐城市'
         and p['parent_code']=='320900' and p['level']==4]
    if len(own)!=1:raise ValueError('Own city/district directory identity not independently matched')
    guide['evidence']={'capture_file':path.relative_to(ROOT).as_posix(),'capture_sha256':manifest['capture_sha256'],
        'screenshot':(OUT/'formal-guide.png').relative_to(ROOT).as_posix(),'official_directory':own[0]}
    opener=build_opener(transport.OfficialRedirect())
    for t in guide['templates']:
        try:
            if not transport.official(t['download_url']):raise ValueError('Not own observed official attachment')
            with opener.open(Request(t['download_url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                body=response.read(20*1024*1024+1)
                if len(body)>20*1024*1024 or not body.startswith((b'PK',b'\xd0\xcf',b'%PDF',b'\xff\xd8',b'\x89PNG')):
                    raise ValueError('Not accepted office/image file')
                original=unquote(response.headers.get_filename() or '');name=official_filename(original)
                if not name:raise ValueError('Official filename not provided; no invented template identity')
                safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name)[:140]
                relative=Path('templates/_docx/_regional/320904')/(t['id']+'-'+safe);file=ROOT/relative
                if file.exists():raise ValueError('Own original already present; do not overwrite')
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
                reason=str(exc),attempts=1,final_status='pending_own_attachment_recheck',
                remediation='保留本地区错误，继续其他材料，不借用建湖或锡山附件',delivery_status='PENDING_OPENCLAW')
            c.save(OUT/'outbox'/(event['id']+'.json'),event)
        c.save(OUT/'guide.json',guide)
        print(t['id'],t['download_status'],t.get('sha256',''),flush=True);time.sleep(1)
    c.save(OUT/'preparation.json',{'at':now(),'own_materials':len(guide['materials']),
        'own_downloaded_annexes':sum(t['download_status']=='downloaded' for t in guide['templates']),
        'published':False,'can_generate':False,'model_calls':0})


if __name__=='__main__':main()
