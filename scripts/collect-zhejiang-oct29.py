"""Own-session public visible-page captures only; never saves cookies or HAR."""
import argparse, datetime, hashlib, json, pathlib, subprocess, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/nationwide-verification-20261029/zhejiang'
SESSION = 'zj-oct29-verify'
BROWSER = r'D:\Apps\agent-browser\node_modules\agent-browser\bin\agent-browser-win32-x64.exe'

def browser(*args):
    p = subprocess.run([BROWSER, '--session', SESSION, *args], capture_output=True, text=True, encoding='utf8', timeout=65)
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    return p.stdout.strip()

def capture(name):
    target = REPORT / name
    target.mkdir(parents=True, exist_ok=True)
    # Read only visible public content and links. Exclude scripts, cookies, network
    # traffic, HTML form values and authentication pages from the saved evidence.
    expression = '''JSON.stringify({url:location.href,title:document.title,text:document.body.innerText,links:Array.from(document.querySelectorAll('a')).map(a=>({text:a.innerText,href:a.getAttribute('href'),title:a.title,localInnerCode:a.getAttribute('data-local-inner-code'),standard:a.getAttribute('data-stdcateguid')}))})'''
    raw = json.loads(browser('eval', expression))
    page = json.loads(raw) if isinstance(raw, str) else raw
    if 'user.zjzwfw.gov.cn' in page['url']:
        raise ValueError('Authentication boundary: do not persist login DOM')
    page['captured_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (target / 'page.json').write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding='utf8')
    (target / 'page.txt').write_text(page['text'], encoding='utf8')
    (target / 'snapshot.txt').write_text(browser('snapshot', '-i'), encoding='utf8')
    browser('screenshot', '--full', str(target / 'page.png'))
    entries = {p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in target.iterdir() if p.is_file() and p.name!='manifest.json'}
    (target / 'manifest.json').write_text(json.dumps({'captured_at':page['captured_at'],'source_url':page['url'],'files':entries},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'capture':name,'url':page['url'],'captured_at':page['captured_at'],'files':len(entries)},ensure_ascii=False))

def download_observed(district, filename, original_name, url, kind, source):
    """Download only URL separately observed from this district's own browser action."""
    if not url.startswith('https://portal.zjzwfw.gov.cn/media/oss/'):
        raise ValueError('Not the observed official public attachment origin')
    target = REPORT / district / 'originals' / kind / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=25) as response:
        body=response.read(); content_type=response.headers.get('Content-Type'); final=response.url
    target.write_bytes(body)
    record={'source_url':source,'download_url':url,'final_url':final,'original_name':original_name,'local_path':target.relative_to(REPORT).as_posix(),'kind':kind,'downloaded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'content_type':content_type,'method':'public_http_after_own_browser_control_and_URL_observed'}
    if district=='haishu':record['browser_download_limit']='native browser download canceled; public source fetched without cookies'
    target.with_suffix(target.suffix+'.source.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(record,ensure_ascii=False))

def save_download_observation(district):
    expression = '''JSON.stringify({source_url:location.href,downloads:window.publicDownloads,public_fetches:performance.getEntriesByType('resource').map(e=>e.name).filter(u=>u.startsWith('https://portal.zjzwfw.gov.cn/media/oss/'))})'''
    raw=json.loads(browser('eval',expression)); data=json.loads(raw) if isinstance(raw,str) else raw
    data['captured_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (REPORT/district/'download-observation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

def save_boundary(district):
    expression = '''JSON.stringify({origin:location.origin,path:location.pathname,personalLogin:document.body.innerText.includes('个人用户登录'),passwordInputs:document.querySelectorAll('input[type=password]').length})'''
    raw=json.loads(browser('eval',expression)); data=json.loads(raw) if isinstance(raw,str) else raw
    if data['origin']!='https://user.zjzwfw.gov.cn' or data['path']!='/pc/login':raise ValueError('Not the observed login boundary')
    data.update({'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'authentication_required','queried_or_submitted':False,'redaction':'SSO query, cookies and login DOM are not retained'})
    (REPORT/district/'online-boundary.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    browser('screenshot',str(REPORT/district/'online-boundary.png'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('capture'); args=parser.parse_args(); capture(args.capture)
