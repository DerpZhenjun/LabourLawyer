"""Own-session official public capture only; no model, DB or services."""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
import email.message
import io
import zipfile
from pathlib import Path
from urllib.parse import parse_qs,urlsplit,unquote
from datetime import datetime,timezone

sys.stdout.reconfigure(encoding='utf8')
OUT = Path(__file__).resolve().parent
CLI = r'D:\Apps\agent-browser\node_modules\agent-browser\bin\agent-browser-win32-x64.exe'
ENV = {**os.environ, 'AGENT_BROWSER_SESSION': 'js-oct29c'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def ab(*args):
    runtime = OUT / '.browser-runtime'; runtime.mkdir(exist_ok=True)
    # A first Windows daemon can retain inherited pipe handles. Regular output
    # files prevent communicate() waiting for EOF from a descendant daemon.
    with tempfile.TemporaryFile(dir=runtime) as output, tempfile.TemporaryFile(dir=runtime) as errors:
        subprocess.run([CLI, *args, '--json'], env=ENV, stdout=output, stderr=errors, timeout=55)
        output.seek(0); result = json.loads(output.read().decode('utf8', 'replace'))
    if not result.get('success'): raise RuntimeError(result.get('error', 'Browser command failed'))
    return result['data']


def ev(code):
    return ab('eval', '-b', base64.b64encode(code.encode()).decode())['result']


def capture(folder):
    # Never dump SSO URLs, browser state, cookies, headers or authentication DOM.
    location = ev('({origin:location.origin,host:location.hostname,path:location.pathname,auth:/sso|login|oauth|auth\\./i.test(location.origin+location.pathname)})')
    if location['auth'] or not location['host'].endswith('.gov.cn'):
        raise ValueError('Only an official public page may be captured; auth boundary needs a sanitized summary')
    value = ev('({url:location.href,title:document.title,captured_at:new Date().toISOString(),text:document.body.innerText,tables:Array.from(document.querySelectorAll("table")).map(t=>Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.innerText))),links:Array.from(document.querySelectorAll("a[href]")).filter(a=>/^https?:/.test(a.href)&&!/(sso|login|ticket|token|oauth)/i.test(a.href)).map(a=>({text:a.innerText,href:a.href})),download_controls:Array.from(document.querySelectorAll("a.kbbg,a.slyb")).map(a=>({label:a.innerText,material:a.closest("tr")?.cells[1]?.innerText.trim(),onclick:a.getAttribute("onclick")})),images:Array.from(document.images).filter(i=>/^https?:/.test(i.src)&&!/(sso|login|ticket|token|oauth)/i.test(i.src)).map(i=>({src:i.src,alt:i.alt,width:i.naturalWidth,height:i.naturalHeight}))})')
    target = OUT / folder; target.mkdir(parents=True, exist_ok=True)
    save(target / 'page.json', value)
    (target / 'page.txt').write_text(value['text'], encoding='utf8')
    ab('screenshot', 'body', (target / 'page.png').as_posix(), '--full')
    save(target / 'provenance.json', {'source_url': value['url'], 'captured_at': value['captured_at'],
        'files': {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
                  for p in target.iterdir() if p.is_file() and p.name != 'provenance.json'}})
    print(json.dumps({'capture': folder, 'url': value['url'], 'title': value['title'], 'text': value['text'][:1800]}, ensure_ascii=False))


def native_download(locality,index):
    page=json.loads((OUT/locality/'formal-controls/page.json').read_text('utf8'))
    control=page['download_controls'][int(index)]
    url=re.search(r"downloadClyb\('([^']+)'",control['onclick'])[1]
    guid=parse_qs(urlsplit(url).query)['attachGuid'][0]
    kind='blank' if control['label']=='空白表格' else 'sample'
    folder=OUT/locality/'native-download';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(guid+'.download')
    result=ab('download',f'a.{"kbbg" if kind=="blank" else "slyb"}[onclick*="{guid}"]',path.as_posix())
    record={'source_url':page['url'],'control':control,'download_url':url,'kind':kind,
            'downloaded_at':datetime.now(timezone.utc).isoformat(),'browser_result':result,
            'file':path.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    save(folder/(guid+'.json'),record)
    print(json.dumps(record,ensure_ascii=False))


def downloads(locality):
    page=json.loads((OUT/locality/'formal-controls/page.json').read_text('utf8'))
    requests=[]
    for control in page['download_controls']:
        url=re.search(r"downloadClyb\('([^']+)'",control['onclick'])[1]
        requests.append((url,'blank' if control['label']=='空白表格' else 'sample',control['material'],control['label']))
    flow=OUT/locality/'flow-image/page.json'
    if flow.exists():requests.append((json.loads(flow.read_text('utf8'))['url'],'instruction','办理流程图','实际点击流程图'))
    rows=[]
    for url,kind,material,label in requests:
        parts=urlsplit(url)
        if not (parts.hostname or '').endswith('.gov.cn'):raise ValueError('Only the observed official URL is permitted')
        guid=parse_qs(parts.query)['attachGuid'][0]
        record={'source_url':page['url'],'source_capture':locality+'/formal-controls/page.json',
                'requested_url':url,'official_kind':kind,'material_name':material,'control_label':label,'annex_id':guid,
                'requested_at':datetime.now(timezone.utc).isoformat(),'method':'normal_unauthenticated_GET_of_observed_public_control_URL'}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':page['url']}),timeout=20) as response:
                final=urlsplit(response.url)
                if re.search(r'sso|login|oauth|auth\.', final.hostname+final.path, re.I):
                    record.update(status='auth_required',final_origin=final.scheme+'://'+final.netloc,final_path=final.path)
                    raise ValueError('Stopped at authentication boundary; no body or session URL retained')
                body=response.read(50*1024*1024+1);record.update(http_status=response.status,final_url=response.url,
                    content_type=response.headers.get('Content-Type'),content_disposition=response.headers.get('Content-Disposition'))
            if len(body)>50*1024*1024:raise ValueError('Attachment exceeds bounded collection size')
            extension=None
            for magic,ext in [(b'%PDF','.pdf'),(b'\xd0\xcf','.doc'),(b'\xff\xd8','.jpg'),(b'\x89PNG','.png')]:
                if body.startswith(magic):extension=ext;break
            if body.startswith(b'PK'):
                with zipfile.ZipFile(io.BytesIO(body)) as package:
                    names=package.namelist();extension='.docx' if 'word/document.xml' in names else '.xlsx' if 'xl/workbook.xml' in names else '.zip'
            if extension is None:raise ValueError('Response is not a recognised official attachment; no HTML body retained')
            header=email.message.Message();header['Content-Disposition']=record.get('content_disposition') or ''
            name=header.get_filename()
            if name:
                name=unquote(name)
                try:name=name.encode('latin1').decode('utf8')
                except (UnicodeError,AttributeError):pass
                name=Path(name.replace('\\','/')).name
            path=OUT/locality/'originals'/kind/guid/(name or guid+extension)
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():raise ValueError('Original already exists; never overwritten')
            path.write_bytes(body)
            record.update(status='downloaded',original_name=name,file=path.relative_to(OUT).as_posix(),
                          sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),file_type=extension.lstrip('.'),
                          downloaded_at=datetime.now(timezone.utc).isoformat(),content_review='pending',can_generate=False)
        except Exception as exc:
            record.setdefault('status','failed');record['error']=str(exc)
        rows.append(record);save(OUT/locality/'DOWNLOADS.json',rows)
        print(json.dumps(record,ensure_ascii=False),flush=True);time.sleep(3)


def boundary(locality):
    source=json.loads((OUT/locality/'formal-controls/page.json').read_text('utf8'))
    observed=ev('({captured_at:new Date().toISOString(),origin:location.origin,path:location.pathname,title:document.title,login_visible:/个人登录|法人登录|密码登录|扫码登录|用户登录|请先登录|统一身份认证/.test(document.body?.innerText||""),captcha_visible:/验证码/.test(document.body?.innerText||""),password_input_count:document.querySelectorAll("input[type=password]").length,frames:Array.from(document.querySelectorAll("iframe[src]")).map(f=>{let u=new URL(f.src,location.href);return {origin:u.origin,path:u.pathname}})})')
    auth=bool(re.search(r'sso|login|oauth|auth\.|rzsc\.',observed['origin']+observed['path'],re.I) or observed['login_visible'])
    value={'source_url':source['url'],'clicked_native_control':'在线办理','status':'auth_required' if auth else 'unverified',
           'submitted':False,'post_login_flow':'unknown','raw_query_or_session_not_saved':True,**observed}
    save(OUT/locality/'online-boundary.json',value)
    print(json.dumps(value,ensure_ascii=False))


if __name__ == '__main__':
    action, *args = sys.argv[1:]
    if action == 'capture': capture(*args)
    elif action == 'native-download': native_download(*args)
    elif action == 'downloads': downloads(*args)
    elif action == 'boundary': boundary(*args)
    elif action == 'eval': print(json.dumps(ev(args[0]), ensure_ascii=False, indent=2))
    else:
        result = ab(action, *args)
        print(result['snapshot'] if 'snapshot' in result else json.dumps(result, ensure_ascii=False, indent=2))
