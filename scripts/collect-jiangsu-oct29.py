"""Explicit public DOM capture from the independent js-oct29-verify session.

No HAR, headers, cookies, HTML, authentication state or private data are saved.
Navigation and native interaction are performed separately after observing DOM.
"""
import argparse
import base64
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/nationwide-verification-20261029/jiangsu'
BROWSER = Path('D:/Apps/agent-browser/node_modules/agent-browser/bin/agent-browser-win32-x64.exe')


def browser(*args):
    run = subprocess.run([str(BROWSER), '--session', 'js-oct29-verify', *args],
                         capture_output=True, encoding='utf-8', timeout=45)
    if run.returncode:
        raise RuntimeError(run.stderr or run.stdout)
    return run.stdout.strip()


def capture(code, name):
    if code not in {'320803', '320812'} or not name.replace('-', '').isalnum():
        raise ValueError('Explicit locality and safe capture label required')
    portal, webid = {'320803': ('https://haha.jszwfw.gov.cn/', '86'),
                     '320812': ('https://haqjp.jszwfw.gov.cn/', '85')}[code]
    allowed = {portal, 'https://xzyl.jszwfw.gov.cn/jszwfw/publicservice/itemlist/gg_index.do?'
                      f'webId={webid}&themid=&deptid=&fwtype='}
    if browser('get', 'url') not in allowed:
        raise ValueError('Capture is limited to the observed own public entry and directory URLs')
    js = '''JSON.stringify({url:location.href,title:document.title,
      body_text:document.body.innerText,
      visible_queries:Array.from(document.querySelectorAll('input[type=text]')).filter(e=>
      e.id.startsWith('word')&&e.getBoundingClientRect().width>0).map(e=>({id:e.id,value:e.value})),
      public_links:Array.from(document.querySelectorAll('a[href]')).filter(a=>
      /^https?:/.test(a.href)&&!/(login|jsjis|sso|gotoUrl|token|auth)/i.test(a.href))
      .map(a=>({text:a.innerText.trim(),url:a.href}))})'''
    raw = browser('eval', '-b', base64.b64encode(js.encode()).decode())
    value = json.loads(raw)
    if isinstance(value, str):
        value = json.loads(value)
    value['captured_at'] = datetime.now(timezone.utc).isoformat()
    value['capture_method'] = 'agent-browser 0.38.2 rendered public DOM; sanitized links'
    target = OUT / code
    target.mkdir(parents=True, exist_ok=True)
    file = target / (name + '.json')
    file.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    browser('scroll', 'top')
    browser('eval', 'new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(true))))')
    # The installed CLI's selector-element screenshot omits this page's lower
    # composite layers. Its native full-page capture includes them correctly.
    shot = browser('screenshot', '--full')
    screenshot_path = shot.split('Screenshot saved to ', 1)[1].strip()
    shutil.copy2(screenshot_path, target / (name + '.png'))
    print(json.dumps({'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                      'url':value['url'],'chars':len(value['body_text'])}, ensure_ascii=False))


def finalize():
    """Verify public evidence and write discovery-only handoff; no guide import."""
    config = ROOT / 'config/regional_candidates.json'
    candidates = json.loads(config.read_text(encoding='utf-8-sig'))
    specs = {
        '320812': ('清江浦区', '85', 'https://haqjp.jszwfw.gov.cn/', 3, 33, 80,
                   ['社会保障卡信息查询', '协助外地退休人员领取待遇资格认证', '工伤事故备案'],
                   'https://www.haqjp.gov.cn/col/14904_253552/art/17224416/1722578818873BL6nFZHU.html'),
        '320803': ('淮安区', '86', 'https://haha.jszwfw.gov.cn/', 4, 43, 121,
                   ['社会保障卡信息查询', '一次性见习补贴申领', '保留人员职业年金待遇申领', '转诊转院申请确认'],
                   'https://www.zghaq.gov.cn/col/904_568817/art/17487072/1750319580035XG8jiYvx.html'),
    }
    allow = []
    checks = []
    for code, (district, webid, portal, count, matters, guides, markers, supplement) in specs.items():
        assert not any(c.get('region_code') == code or c.get('district') == district for c in candidates)
        directory = f'https://xzyl.jszwfw.gov.cn/jszwfw/publicservice/itemlist/gg_index.do?webId={webid}&themid=&deptid=&fwtype='
        names = ['portal-entry', 'arbitration-search-final', 'full-title-search-final']
        names += [f'directory-page{n}-final' for n in range(1, count + 1)]
        times = []
        for name in names:
            file = OUT / code / (name + '.json')
            value = json.loads(file.read_text(encoding='utf8'))
            assert value['url'] == (portal if name == 'portal-entry' else directory)
            assert district in value['body_text']
            assert not any(any(term in link['url'].lower() for term in ['login', 'jsjis', 'sso', 'token', 'auth']) for link in value['public_links'])
            if name.startswith('directory-page'):
                n = int(name.split('page')[1].split('-')[0])
                assert markers[n - 1] in value['body_text']
                assert f'事项：{matters}' in value['body_text'] and f'办事指南：{guides}' in value['body_text']
                assert '仲裁' not in value['body_text']
            if 'search-final' in name:
                assert '事项：0' in value['body_text'] and '办事指南：0' in value['body_text']
                expected = '劳动人事争议仲裁申请' if name == 'full-title-search-final' else '仲裁'
                assert any(q['value'] == expected for q in value['visible_queries'])
            if name == 'portal-entry':
                assert any(link['url'] == directory for link in value['public_links'])
            times.append(value['captured_at'])
            for suffix in ['.json', '.png']:
                path = OUT / code / (name + suffix)
                assert path.exists() and path.stat().st_size > 100
                allow.append(path)
        status = {
            'province': 'jiangsu', 'city': '淮安市', 'district': district, 'region_code': code,
            'status': 'discovery_only', 'official_guide_status': 'not_found_in_checked_sources',
            'template_status': 'not_found_in_checked_sources', 'published': False,
            'can_generate': False, 'candidate_guide_created': False, 'source_id': None,
            'formal_guide_url': None, 'authority_binding': None, 'templates': [], 'downloaded_files': [],
            'checked_sources': [{'url': portal, 'purpose': '自身门户及公共服务目录入口'},
                                {'url': directory, 'purpose': '完整/短关键词及自身区人社局全部页',
                                 'department': '区人社局', 'pages_checked': count,
                                 'portal_matter_count': matters, 'portal_guide_count': guides}],
            'supplemental_attempt': {'url': supplement, 'browser_error': 'net::ERR_CERT_AUTHORITY_INVALID',
                                     'content_used_for_requirements': False, 'bypass_attempted': False},
            'capture_interval_utc': {'first': min(times), 'last': max(times)},
            'online_submission_status': 'not_verified', 'web_qa_status': 'NOT_RUN',
            'layout_qa_status': 'NOT_APPLICABLE_NO_OWN_TEMPLATE',
            'adapter_status': 'NOT_APPLICABLE_NO_OWN_TEMPLATE',
            'next_action': '从本区其他正式官方入口定位本区劳动人事争议仲裁实施指南；取得材料与原件前不注册、不适配。',
            'limitations': ['目录搜索未找到不证明当地没有服务或模板。',
                            '补充新闻/迁址公告不是正式申请指南。',
                            '不得借用市级、邻区或相同省份模板与要求。'],
            'queue_check': {'file': 'config/regional_candidates.json',
                            'sha256': hashlib.sha256(config.read_bytes()).hexdigest(),
                            'already_candidate': False},
        }
        target = OUT / code / 'DISCOVERY-STATUS.json'
        target.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        allow.append(target)
        checks.append({'region_code': code, 'district': district, 'status': 'PASS',
                       'checked_public_captures': len(names), 'directory_pages': count,
                       'own_templates': 0, 'guides_created': 0})
    report = {'scope': 'public_evidence_integrity_only', 'result': 'PASS', 'regions': checks,
              'product_tests': 'NOT_RUN_NO_PRODUCT_CODE_CHANGED',
              'candidate_web_qa': 'NOT_RUN', 'published_delta': 0, 'generation_delta': 0}
    target = OUT / 'evidence-checks.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    allow.append(target)
    allow.append(ROOT / 'scripts/collect-jiangsu-oct29.py')
    handoff = OUT / 'HANDOFF.md'
    if handoff.exists():
        allow.append(handoff)
    manifest = {'schema_version': 1, 'scope': 'public_discovery_evidence_only',
                'excluded': ['所有非本白名单文件，含早期空白/不完整截图与中间捕获',
                             '原始HAR/HTML/headers/cookies/SSO状态（本批未保存）'],
                'files': [{'file': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
                           'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in allow]}
    (OUT / 'public-file-allowlist.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('code', nargs='?')
    parser.add_argument('name', nargs='?')
    parser.add_argument('--finalize', action='store_true')
    args = parser.parse_args()
    if args.finalize:
        finalize()
    else:
        capture(args.code, args.name)
