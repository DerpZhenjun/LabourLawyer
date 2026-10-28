"""Observed Sichuan public search + real Agent Browser collection; no DB writes/models.

Resume preserves successful captures; every locality obtains its own guide and files.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'scripts'))
from chengdu_collection import select_service
from regional_capture import parse_sichuan_capture
from regional_guides import resolve_channel
from importlib import import_module
public_get = import_module('import-regional-captures').public_get

OUT = ROOT / 'reports/chengdu-district-expansion-20261023'
CLI = r'D:\Apps\agent-browser\node_modules\agent-browser\bin\agent-browser-win32-x64.exe'
ENV = {**os.environ, 'AGENT_BROWSER_SESSION': 'labourlawyer-chengdu-20261023'}
TREE = 'https://www.sczwfw.gov.cn/jiq/interface/jitem/find-by-code?code=510100000000&deptType=1&jsonpCallback=jsonpcallback'
SEARCH = 'https://www.sczwfw.gov.cn/jsearchfront/interfaces/searchMatterUrl.do?'
NOW = lambda: datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def browser(*args):
    # A newly launched native daemon can inherit stdout/stderr. Pipes then never
    # reach EOF even after the CLI exits; regular files let timeout/wait stay bounded.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        run = subprocess.run([CLI, *args, '--json'], env=ENV, stdout=output, stderr=errors, timeout=50)
        output.seek(0); errors.seek(0)
        stdout=output.read().decode('utf8',errors='replace')
        stderr=errors.read().decode('utf8',errors='replace')
    result = json.loads(stdout)
    if not result.get('success'):
        raise RuntimeError(str(result.get('error', stderr)))
    with (OUT / 'browser-actions.jsonl').open('a', encoding='utf8') as log:
        log.write(json.dumps({'time': NOW(), 'args': list(args)[:3], 'success': True}, ensure_ascii=False) + '\n')
    return result['data']


def evaluate(js):
    return browser('eval', '-b', base64.b64encode(js.encode()).decode())['result']


def click_material(ref):
    # Official sticky banner can cover a target that native scrolling considers visible.
    browser('scrollintoview', '@' + ref)
    browser('scroll', 'up', '240')
    browser('click', '@' + ref)


def discover():
    raw = public_get(TREE)[0].decode('utf8')
    tree = json.loads(raw[raw.index('(') + 1:raw.rindex(')')])
    save(OUT / 'official-region-tree.json', {'source_url': TREE, 'collected_at': NOW(), 'response': tree})
    targets = []
    for area in tree['data']['group']['sonAreas']:
        code, name = area['areaCode'], area['shortName']
        url = SEARCH + urlencode({'title': '劳动人事争议仲裁申请', 'websiteid': code + '000'})
        response = json.loads(public_get(url)[0])
        save(OUT / 'discovery' / f'{code}.json', {'url': url, 'collected_at': NOW(), 'response': response})
        item = select_service(response, code)
        targets.append({'district': name, 'region_code': code, 'search_url': url, 'service': item,
                        'status': 'existing' if name in {'天府新区', '锦江区', '武侯区'} else 'discovered' if item else 'not_found'})
        save(OUT / 'TARGETS.json', targets)
        print(name, 'found' if item else 'NOT_FOUND', flush=True)
        time.sleep(1)
    return targets


CAPTURE_JS = """({url:location.href,title:document.title,captured_at:new Date().toISOString(),
html:document.documentElement.outerHTML,text:document.body.innerText,
tables:Array.from(document.querySelectorAll('table')).map(t=>Array.from(t.querySelectorAll('tr')).map(r=>Array.from(r.querySelectorAll(':scope > td,:scope > th')).map(c=>c.textContent.trim())))})"""


def capture(target):
    code, name = target['region_code'], target['district']
    folder = OUT / 'captures' / code
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'guide.json').exists():
        return json.loads((folder / 'guide.json').read_text(encoding='utf8'))
    metadata = target.get('region_metadata')
    if not metadata:
        tree = json.loads((OUT / 'official-region-tree.json').read_text(encoding='utf8'))
        metadata = next(a for a in tree['response']['data']['group']['sonAreas'] if a['areaCode'] == code)
    browser('open', target['service']['url'])
    browser('wait', '--text', '劳动人事争议仲裁申请')
    browser('wait', '--fn', json.dumps([name, metadata['name'], '四川' + name]) + ".includes(document.querySelector('#cityName')?.textContent.trim())")
    snapshot = browser('snapshot', '-i')['snapshot']
    for section in ['基本信息', '申请材料', '受理条件', '办理流程', '收费标准', '设定依据', '中介服务', '常见问题']:
        match = re.search(r'listitem "' + section + r'"[^\n]*ref=(\w+)', snapshot)
        if not match:
            raise ValueError('未找到真实栏目：' + section)
        browser('click', '@' + match.group(1))
        browser('wait', '--fn', 'typeof jQuery === "undefined" || jQuery(":animated").length === 0')
    # Material details and sample/blank download panels are actual public controls.
    snapshot = browser('snapshot', '-i')['snapshot']
    details = re.findall(r'link "查看更多" \[ref=(\w+)\]', snapshot)
    for ref in details:
        click_material(ref)
        browser('click', '.zhezhao3[style=""] .top em')
    panels = re.findall(r'link "(示例样表|空白表格)" \[ref=(\w+)\]', snapshot)
    for kind, ref in panels:
        click_material(ref)
        cls = '.zhezhao2' if kind == '示例样表' else '.zhezhao4'
        browser('click', cls + '[style=""] .top em')
    browser('find', 'text', '仲裁申请书', 'click', '--exact')
    browser('screenshot', str(folder / 'materials.png'))
    capture = evaluate(CAPTURE_JS)
    save(folder / 'dom.json', capture)
    guide = parse_sichuan_capture(capture, target.get('city', '成都市'), name, region_metadata=metadata)
    guide['evidence'] = {'capture_file': str((folder / 'dom.json').relative_to(ROOT)).replace('\\', '/'),
                         'capture_sha256': hashlib.sha256((folder / 'dom.json').read_bytes()).hexdigest(),
                         'screenshot': str((folder / 'materials.png').relative_to(ROOT)).replace('\\', '/')}
    for template in guide['templates']:
        try:
            response = json.loads(public_get(template['download_endpoint'])[0])
            if str(response.get('code')) != '0':
                raise ValueError('附件接口未返回公开下载地址')
            body, final = public_get(response['data'])
            if not body.startswith((b'PK', b'%PDF', b'\xff\xd8', b'\xd0\xcf')):
                raise ValueError('不是可识别的文书或图片')
            safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', template['original_name'])[:140]
            relative = Path('templates/_docx/_regional') / code / (template['id'] + '-' + safe)
            path = ROOT / relative
            if path.exists() and path.read_bytes() != body:
                raise ValueError('同名附件字节发生变化，需保留旧版并人工复核，未覆盖')
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(body)
            template.update(file=relative.as_posix(), sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                            download_status='downloaded', verified_at=NOW(), download_url=response['data'], final_download_url=final)
        except Exception as exc:
            template.update(download_status='failed', download_error=str(exc))
        time.sleep(1)
    save(folder / 'guide.json', guide)
    return guide


def check_online(target):
    folder = OUT / 'captures' / target['region_code']
    path = folder / 'guide.json'
    if not path.exists():
        return
    guide = json.loads(path.read_text(encoding='utf8'))
    if guide['channel']['form'] not in {'online', 'window_and_online'} or guide['channel']['entry_check']:
        return
    browser('open', guide['source_url'])
    browser('wait', '--text', '劳动人事争议仲裁申请')
    snapshot = browser('snapshot', '-i')['snapshot']
    match = re.search(r'listitem "在线申请"[^\n]*ref=(\w+)', snapshot)
    if not match:
        raise ValueError('页面未显示在线申请控件，不能认定入口有效')
    browser('click', '@' + match.group(1))
    browser('wait', '--fn', "document.body.innerText.includes('用户未登录') || location.href.includes('/logon/')")
    observed = evaluate('({url:location.href,text:document.body.innerText.slice(-2500)})')
    browser('screenshot', str(folder / 'online-login-boundary.png'))
    check = {'url': guide['source_url'], 'status': 'auth_required', 'official_link': True,
             'checked_at': NOW(), 'screenshot': str((folder / 'online-login-boundary.png').relative_to(ROOT)).replace('\\', '/'),
             'observed_url': observed['url'], 'result': '用户未登录；未填写账号、验证码或提交申请'}
    save(folder / 'online-check.json', check)
    if '用户未登录' in observed['text']:
        browser('find', 'text', '取消', 'click', '--exact')
    raw = {k: v['raw_value'] for k, v in guide['fields'].items()}
    flow = guide['sections']['办理流程'] + '\n' + guide['sections']['常见问题']
    guide['channel'] = resolve_channel(raw, flow, check)
    save(path, guide)
    print(target['district'], 'online auth_required', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--discover', action='store_true')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--district')
    parser.add_argument('--check-online', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    targets = discover() if args.discover else json.loads((OUT / 'TARGETS.json').read_text(encoding='utf8'))
    count = 0
    for target in targets:
        if args.district and target['district'] != args.district:
            continue
        if args.check_online:
            try:
                check_online(target)
            except Exception as exc:
                print(target['district'], 'ONLINE_UNVERIFIED', str(exc), flush=True)
            continue
        if target['status'] in {'existing', 'not_found'} or count >= args.limit:
            continue
        try:
            guide = capture(target)
            if target.get('error'):
                target.setdefault('resolved_errors', []).append(target.pop('error'))
            target.update(status='captured', materials=len(guide['materials']), templates=len(guide['templates']))
            print(target['district'], target['status'], target['materials'], target['templates'], flush=True)
        except Exception as exc:
            target.update(status='failed', error=str(exc))
            print(target['district'], 'FAILED', str(exc), flush=True)
        save(OUT / 'TARGETS.json', targets)
        count += 1
        time.sleep(2)


if __name__ == '__main__':
    main()
