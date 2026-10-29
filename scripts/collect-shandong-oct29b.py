"""Read-only public DOM evidence from sd-oct29b; no HAR/HTML/session data."""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/nationwide-verification-20261029-b/shandong'
BROWSER=Path('D:/Apps/agent-browser/node_modules/agent-browser/bin/agent-browser-win32-x64.exe')
ALLOWED_HOSTS={'zwfw.jinan.gov.cn','www.lixia.gov.cn','www.shizhong.gov.cn','jnhrss.jinan.gov.cn','www.jinan.gov.cn'}


def browser(*args):
    run=subprocess.run([str(BROWSER),'--session','sd-oct29b',*args],capture_output=True,encoding='utf8',timeout=45)
    if run.returncode:raise RuntimeError(run.stderr or run.stdout)
    return run.stdout.strip()


def capture(code,name):
    if code not in {'370102','370103'} or not name.replace('-','').isalnum():raise ValueError('Own district/label required')
    url=browser('get','url');parsed=urlsplit(url)
    if parsed.hostname not in ALLOWED_HOSTS or any(t in parsed.path.lower() for t in ['sso','login','auth']):
        raise ValueError('Only observed public sources may be captured')
    js='''JSON.stringify({url:location.href,title:document.title,text:document.body.innerText,
      headings:Array.from(document.querySelectorAll('h1,h2,h3,h4')).map(e=>e.innerText),
      visible_queries:Array.from(document.querySelectorAll('input[type=text],input:not([type])')).filter(e=>e.getBoundingClientRect().width>0).map(e=>({placeholder:e.placeholder,value:e.value})),
      public_links:Array.from(document.querySelectorAll('a[href]')).filter(a=>/^https?:/.test(a.href)&&!/(login|jsjis|sso|gotoUrl|token|auth)/i.test(a.href)).map(a=>({text:a.innerText.trim(),url:a.href})),
      tables:Array.from(document.querySelectorAll('table')).map(t=>Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.innerText)))})'''
    value=json.loads(browser('eval','-b',base64.b64encode(js.encode()).decode()))
    if isinstance(value,str):value=json.loads(value)
    value.update(region_code=code,captured_at=datetime.now(timezone.utc).isoformat(),method='Agent Browser rendered public DOM; no HTML or headers saved')
    folder=OUT/code;folder.mkdir(parents=True,exist_ok=True)
    target=folder/(name+'.json');target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    browser('eval','new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(true))))')
    shot=browser('screenshot','--full');shutil.copy2(shot.split('Screenshot saved to ',1)[1].strip(),folder/(name+'.png'))
    print(json.dumps({'file':target.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'url':url,'characters':len(value['text'])}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('code');parser.add_argument('name');args=parser.parse_args()
    capture(args.code,args.name)
