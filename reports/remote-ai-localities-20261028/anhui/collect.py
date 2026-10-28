"""Own locality browser evidence; public files never contain session headers/state."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qsl

OUT = Path(__file__).resolve().parent
CLI = r'D:\Apps\agent-browser\node_modules\agent-browser\bin\agent-browser-win32-x64.exe'
ENV = {**os.environ, 'AGENT_BROWSER_SESSION': 'remote-ah-20261028-bce456318685'}
NOW = lambda: datetime.now(timezone.utc).isoformat()
SENSITIVE = re.compile(r'__ssoSeq__|[;?&](?:jsessionid|ticket|token|accesskey|access_token|refresh_token|id_token|code|oauth_state|sessionid)\s*[=:]\s*[^\s\"\'<>;&]+', re.I)

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError('Evidence output exists; choose a new path')
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def browser(*args):
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        run = subprocess.run([CLI, *args, '--json'], env=ENV, stdout=output, stderr=errors, timeout=55)
        output.seek(0); errors.seek(0)
        raw = output.read().decode('utf-8', 'replace')
        error = errors.read().decode('utf-8', 'replace')
    data = json.loads(raw)
    # Arguments and results can contain opaque redirects. The public action log is metadata only.
    with (OUT/'browser-actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'at': NOW(), 'command': args[0], 'success': data.get('success'), 'exit_code': run.returncode})+'\n')
    if not data.get('success'):
        raise RuntimeError(str(data.get('error', error))[:500])
    return data['data']

def evaluate(js):
    return browser('eval', '-b', base64.b64encode(js.encode()).decode())['result']

def persist_checked(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2)+'\n'
    if SENSITIVE.search(raw):
        sealed = OUT/'.private-sealed'
        sealed.mkdir(exist_ok=True)
        (sealed/'.gitignore').write_text('*\n', encoding='utf-8')
        private = sealed/path.relative_to(OUT)
        save(private, value)
        return {'status': 'withheld_private', 'sha256': hashlib.sha256(private.read_bytes()).hexdigest(), 'bytes': private.stat().st_size, 'reason': 'opaque URL/session context'}
    save(path, value)
    return {'status': 'public', 'path': path.relative_to(OUT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}

def capture(name):
    folder = OUT/name
    folder.mkdir(parents=True, exist_ok=True)
    value = evaluate('''({url:location.href,title:document.title,captured_at:new Date().toISOString(),html:document.documentElement.outerHTML,text:document.body.innerText,tables:Array.from(document.querySelectorAll('table')).map(t=>Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.innerText))),iframes:Array.from(document.querySelectorAll('iframe')).map(f=>({src:f.src,html:f.contentDocument?.documentElement.outerHTML,text:f.contentDocument?.body.innerText}))})''')
    records = {'dom': persist_checked(folder/'dom.json', value)}
    rendered = {k: value[k] for k in ('url', 'title', 'captured_at', 'text', 'tables')}
    records['rendered'] = persist_checked(folder/'rendered.json', rendered)
    records['snapshot'] = persist_checked(folder/'snapshot.json', browser('snapshot'))
    browser('screenshot', str(folder/'page.png'), '--full')
    records['screenshot'] = {'path': (folder/'page.png').relative_to(OUT).as_posix(), 'sha256': hashlib.sha256((folder/'page.png').read_bytes()).hexdigest(), 'bytes': (folder/'page.png').stat().st_size}
    source = value['url'] if not SENSITIVE.search(value['url']) else urlsplit(value['url']).scheme+'://'+urlsplit(value['url']).netloc+urlsplit(value['url']).path
    save(folder/'provenance.json', {'source_url': source, 'captured_at': value['captured_at'], 'records': records})
    print(json.dumps({'folder': name, 'source_url': source, 'text_excerpt': value['text'][:180], 'records': records}, ensure_ascii=False))

if __name__ == '__main__':
    if sys.argv[1]=='capture':
        capture(sys.argv[2])
    elif sys.argv[1]=='record':
        value = evaluate(sys.argv[3])
        print(json.dumps(persist_checked(OUT/sys.argv[2], {'captured_at': NOW(), 'data': value}), ensure_ascii=False))
    elif sys.argv[1]=='eval':
        result = evaluate(sys.argv[2])
        raw = json.dumps(result, ensure_ascii=False)
        if SENSITIVE.search(raw):
            print('WITHHELD_OPAQUE_CONTEXT')
        else:
            print(raw)
    else:
        result = browser(*sys.argv[1:])
        raw = result['snapshot'] if sys.argv[1]=='snapshot' else json.dumps(result, ensure_ascii=False)
        if SENSITIVE.search(raw):
            print('WITHHELD_OPAQUE_CONTEXT')
        else:
            print(raw)
