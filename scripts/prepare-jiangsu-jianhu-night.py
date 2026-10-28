"""Jianhu's own captured material links, own files; no inherited template."""
import hashlib
import importlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request,build_opener
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_jiangsu import parse_jianhu_capture,official_filename
from regional_directory import DirectoryStore
from regional_guides import now,digest
c=importlib.import_module('collect-chengdu-districts')
download=importlib.import_module('prepare-jiangsu-xishan-night')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu'
CAPTURE=OUT/'attempts/20261024-0227'


def main():
    if (OUT/'guide.json').exists():raise ValueError('Preserve own previously prepared evidence')
    manifest=json.loads((CAPTURE/'capture-manifest.json').read_text('utf8'))
    raw=CAPTURE/manifest['capture_file']
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=manifest['capture_sha256']:raise ValueError('Raw capture changed')
    if len(manifest['sections_clicked'])!=12 or manifest['material_dialogs_opened']!=4:raise ValueError('Actual guide interactions incomplete')
    guide=parse_jianhu_capture(json.loads(raw.read_text('utf8')))
    places=DirectoryStore(ROOT/'backend/data/regional-directory.sqlite').areas('jiangsu','盐城市')
    match=[p for p in places if p['district']=='建湖县' and p['code']=='320925'
           and p['parent_code']=='320900' and p['city']=='盐城市' and p['level']==4]
    if len(match)!=1:raise ValueError('Own official county/city directory identity not established')
    guide['evidence']={'capture_file':raw.relative_to(ROOT).as_posix(),'capture_sha256':manifest['capture_sha256'],
                       'screenshot':(CAPTURE/'formal-guide.png').relative_to(ROOT).as_posix(),'official_directory':match[0]}
    opener=build_opener(download.OfficialRedirect())
    for t in guide['templates']:
        try:
            if not download.official(t['download_url']):raise ValueError('Not the captured official host')
            with opener.open(Request(t['download_url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                body=response.read(20*1024*1024+1)
                if len(body)>20*1024*1024 or not body.startswith((b'PK',b'\xd0\xcf',b'%PDF',b'\xff\xd8',b'\x89PNG')):raise ValueError('Not an accepted office/image file')
                original=unquote(response.headers.get_filename() or '')
                name=official_filename(original)
                if not name:raise ValueError('Official filename missing; keep pending rather than guess')
                safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name)[:140]
                relative=Path('templates/_docx/_regional/320925')/(t['id']+'-'+safe)
                file=ROOT/relative;file.parent.mkdir(parents=True,exist_ok=True)
                if file.exists():raise ValueError('Own original already exists; preserve and recheck separately')
                file.write_bytes(body)
                t.update(original_name=name,original_http_filename=original,file=relative.as_posix(),
                         sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),file_type=file.suffix.lstrip('.').lower(),
                         download_status='downloaded',final_download_url=response.url,downloaded_at=now(),verified_at=now())
        except Exception as exc:
            t.update(download_status='failed',download_error=str(exc))
            e={k:guide[k] for k in ['province','city','district','region_code']}
            e.update(id=digest([guide['source_url'],t['id'],'TEMPLATE_DOWNLOAD_FAILED'])[:32],
                     type='TEMPLATE_DOWNLOAD_FAILED',service=guide['service_name'],url=t['download_url'],
                     occurred_at=now(),reason=str(exc),attempts=1,final_status='pending_own_attachment_recheck',
                     remediation='继续其他材料，不借用锡山或省级模板',delivery_status='PENDING_OPENCLAW')
            c.save(OUT/'outbox'/(e['id']+'.json'),e)
        c.save(OUT/'guide.json',guide)
        print(t['id'],t['download_status'],t.get('original_name'),t.get('sha256',''),flush=True)
        time.sleep(1)
    c.save(OUT/'preparation.json',{'at':now(),'own_materials':len(guide['materials']),
                                 'own_downloaded_annexes':sum(t['download_status']=='downloaded' for t in guide['templates']),
                                 'generation_enabled':False,'published':False,'model_calls':0})


if __name__=='__main__':main()
