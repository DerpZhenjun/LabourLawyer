"""Own-session public official evidence; no DB, models, services or auth."""
import base64
import hashlib
import json
import os
import subprocess
import sys
import re
import time
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.stdout.reconfigure(encoding='utf8')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/nationwide-verification-20261029-b/guangdong'
CLI=r'D:\Apps\agent-browser\node_modules\agent-browser\bin\agent-browser-win32-x64.exe'
ENV={**os.environ,'AGENT_BROWSER_SESSION':'gd-oct29b'}
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def ab(*args):
    p=subprocess.run([CLI,*args,'--json'],env=ENV,capture_output=True,timeout=55)
    result=json.loads(p.stdout.decode('utf8','replace'))
    if not result.get('success'):raise RuntimeError(result.get('error',p.stderr.decode('utf8','replace')))
    return result['data']
def ev(js):return ab('eval','-b',base64.b64encode(js.encode()).decode())['result']
def capture(name):
    value=ev('({url:location.href,title:document.title,captured_at:new Date().toISOString(),text:document.body.innerText,links:Array.from(document.querySelectorAll("a[href]")).filter(a=>/^https?:/.test(a.href)&&!/(sso|login|token|ticket|userspace)/i.test(a.href)).map(a=>({text:a.innerText,href:a.href})),tables:Array.from(document.querySelectorAll("table")).map(t=>Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.innerText)))})')
    if not (urlsplit(value['url']).hostname or '').endswith('.gov.cn') or any(term in value['url'].lower() for term in ['sso','token','ticket','login']):
        raise ValueError('Only public government pages are captured; auth boundaries must be sanitised summaries')
    folder=OUT/name
    folder.mkdir(parents=True,exist_ok=True)
    save(folder/'public-source.json',value)
    (folder/'page.txt').write_text(value['text'],encoding='utf8')
    ab('screenshot',(folder/'page.png').as_posix(),'--full')
    save(folder/'provenance.json',{'source_url':value['url'],'captured_at':value['captured_at'],'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file() and p.name!='provenance.json'}})
    print(json.dumps({'capture':name,'url':value['url'],'text':value['text'][:1500]},ensure_ascii=False))
def downloads(name,source_folder):
    source=json.loads((OUT/name/source_folder/'public-source.json').read_text(encoding='utf8'))
    records=[]
    folder=OUT/name/'downloads';folder.mkdir(parents=True,exist_ok=True)
    for index,link in enumerate([a for a in source['links'] if re.search(r'\.(docx?|pdf|zip|rar)(?:$|\?)',a['href'],re.I)],1):
        url=link['href'];parsed=urlsplit(url)
        if not (parsed.hostname or '').endswith('.gov.cn'):continue
        filename=re.sub(r'^\s*\d+[、.：:]\s*','',link['text'].strip()) or Path(parsed.path).name
        record={'source_url':source['url'],'source_capture':(OUT/name/source_folder/'public-source.json').relative_to(ROOT).as_posix(),
                'official_label':link['text'],'original_name':filename,'download_url':url,
                'classification':'sample' if any(t in filename for t in ['样式','样本','样表']) else 'unreviewed_blank_or_instruction',
                'downloaded_at':datetime.now(timezone.utc).isoformat()}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':source['url']}),timeout=30) as response:
                body=response.read();record.update(http_status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'),content_disposition=response.headers.get('Content-Disposition'))
            if not body.startswith((b'PK',b'\xd0\xcf',b'%PDF',b'Rar!',b'\x89PNG',b'\xff\xd8')):raise ValueError('Not a recognised attachment file')
            path=folder/(f'{index:02}-'+filename)
            if path.exists():raise ValueError('Evidence already exists; not overwritten')
            path.write_bytes(body);record.update(status='downloaded',file=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),visual_qa='pending')
        except Exception as error:record.update(status='failed',error=str(error))
        records.append(record);save(folder/'manifest.json',records)
        print(json.dumps(record,ensure_ascii=False),flush=True);time.sleep(3)
if __name__=='__main__':
    action,*args=sys.argv[1:]
    if action=='capture':capture(*args)
    elif action=='downloads':downloads(*args)
    elif action=='eval':print(json.dumps(ev(args[0]),ensure_ascii=False,indent=2))
    else:
        result=ab(action,*args)
        print(result['snapshot'] if 'snapshot' in result else json.dumps(result,ensure_ascii=False,indent=2))
