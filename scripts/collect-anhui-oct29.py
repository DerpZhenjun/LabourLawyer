"""Own-session official public evidence. No database, model, auth or service work."""
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf8')

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/nationwide-verification-20261029/anhui'
CLI = r'D:\Apps\agent-browser\node_modules\agent-browser\bin\agent-browser-win32-x64.exe'
ENV = {**os.environ, 'AGENT_BROWSER_SESSION': 'ah-oct29-verify'}

def now():
    return datetime.now(timezone.utc).isoformat()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def ab(*args):
    result = subprocess.run([CLI, *args, '--json'], env=ENV, capture_output=True, timeout=55)
    value = json.loads(result.stdout.decode('utf8', 'replace'))
    if not value.get('success'):
        raise RuntimeError(value.get('error', result.stderr.decode('utf8', 'replace')))
    return value['data']

def ev(script):
    return ab('eval', '-b', base64.b64encode(script.encode()).decode())['result']

def capture(name):
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    value = ev('({url:location.origin+location.pathname+location.search,title:document.title,captured_at:new Date().toISOString(),text:document.body.innerText,tables:Array.from(document.querySelectorAll("table")).map(t=>Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.innerText))),sections:Array.from(document.querySelectorAll("[id^=section]")).map(s=>({id:s.id,text:s.innerText})),links:Array.from(document.querySelectorAll("a[href]")).filter(a=>/^https?:/.test(a.href)&&!/(sso|login|token|ticket)/i.test(a.href)).map(a=>({text:a.innerText,href:a.href}))})')
    # This function is only for public guide pages. Auth boundaries use a hand-written,
    # stripped status record and screenshot, never SSO queries or session state.
    if 'applicationMaterial.html' not in value['url'] and 'search-results.do' not in value['url']:
        raise ValueError('Public source allowlist does not include this page')
    save(folder / 'public-source.json', value)
    (folder / 'page.txt').write_text(value['text'], encoding='utf8')
    ab('screenshot', str(folder / 'page.png'), '--full')
    save(folder / 'provenance.json', {'source_url':value['url'], 'captured_at':value['captured_at'], 'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file() and p.name != 'provenance.json'}})
    print(json.dumps({'capture':name,'url':value['url'],'sections':value['sections']}, ensure_ascii=False))

def model(name):
    ab('find','role','link','click','--name','申请材料','--exact')
    ab('wait','--text','材料名称')
    data = ev('document.querySelector("#section3").__vue__.$props.detailsDatas')
    value = {'source_url':ev('location.href'), 'captured_at':now(), 'data':data}
    save(OUT / name / 'public-guide-viewmodel.json', value)
    print(json.dumps({'source_url':value['source_url'],'keys':list(data)}, ensure_ascii=False))

def sections(name):
    for label, folder in [('受理条件','conditions'),('申请材料','materials'),('办理流程','process'),('中介服务','intermediary'),('常见问题','faq'),('办事评价','evaluation')]:
        ab('find','role','link','click','--name',label,'--exact')
        ab('wait','--fn','!document.querySelector(".v-enter-active,.dialog-fade-leave-active")')
        capture(name+'/'+folder)
        time.sleep(2)
    model(name)

def downloads(name):
    source = json.loads((OUT / name / 'public-guide-viewmodel.json').read_text(encoding='utf8'))
    items = []
    for row in source['data']['clJson']:
        for field, kind in [('materialEmpty','blank'),('materialSample','sample')]:
            items.extend({**f,'classification':kind,'material':row['materialName']} for f in row['json'][field])
    items.extend({**f,'classification':'instruction','material':'办理流程图'} for f in source['data'].get('processImgJson',[]))
    manifest = []
    for entry in items:
        url = entry['filePath']
        if not url.startswith('https://hf.ahzwfw.gov.cn/intranet/group'):
            raise ValueError('Own official public attachment required')
        record = {**entry,'source_url':source['source_url'],'requested_url':url,'downloaded_at':now()}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':source['source_url']}),timeout=30) as response:
                body=response.read()
                record.update(http_status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'))
            if not body.startswith((b'PK',b'\xd0\xcf',b'%PDF',b'\x89PNG',b'\xff\xd8')):
                raise ValueError('Unexpected file signature')
            path=OUT/name/'downloads'/(entry['id']+'-'+entry['fileName'])
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                raise ValueError('Evidence exists; refusing overwrite')
            path.write_bytes(body)
            record.update(status='downloaded',path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),visual_qa='pending')
        except Exception as exc:
            record.update(status='failed',error=str(exc))
        manifest.append(record)
        save(OUT/name/'downloads/manifest.json',manifest)
        print(json.dumps(record,ensure_ascii=False),flush=True)
        time.sleep(2)

def details(name):
    rows=ev('document.querySelectorAll("#section3 tr.el-table__row").length')
    for n in range(1,rows+1):
        ab('click',f'#section3 tr.el-table__row:nth-child({n}) a:not(.material-sample)')
        ab('wait','--text','材料依据')
        capture(name+f'/detail-{n}')
        ab('find','role','button','click','--name','Close','--exact')
        ab('wait','--fn','!document.querySelector(".dialog-fade-leave-active")')
        time.sleep(2)

def boundary(name):
    source=ev('location.href')
    ab('find','role','link','click','--name','在线办理','--exact')
    ab('wait','--fn','!!document.querySelector("input[type=password]")')
    value=ev('({origin:location.origin,path:location.pathname,login_visible:!!document.querySelector("input[type=password]"),title:document.title,captured_at:new Date().toISOString()})')
    value.update(source_url=source,observed_status='auth_required',authenticated=False,post_login_capability='unverified',query_omitted=True)
    folder=OUT/name/'online-boundary';folder.mkdir(parents=True,exist_ok=True)
    save(folder/'public-summary.json',value)
    ab('screenshot',str(folder/'page.png'),'--full')
    print(json.dumps(value,ensure_ascii=False))

if __name__ == '__main__':
    action,*args=sys.argv[1:]
    if action=='capture':capture(*args)
    elif action=='model':model(*args)
    elif action=='sections':sections(*args)
    elif action=='downloads':downloads(*args)
    elif action=='details':details(*args)
    elif action=='boundary':boundary(*args)
    elif action=='eval':print(json.dumps(ev(args[0]),ensure_ascii=False,indent=2))
    else:
        result=ab(action,*args)
        print(result['snapshot'] if 'snapshot' in result else json.dumps(result,ensure_ascii=False,indent=2))
