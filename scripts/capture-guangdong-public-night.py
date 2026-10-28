"""Low-rate real-browser acquisition of independently discovered county sources.

Read-only public pages; no authentication, models, database writes or publication.
"""
import importlib
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf8', errors='backslashreplace')
sys.path.insert(0, str(ROOT / 'scripts'))
c = importlib.import_module('collect-chengdu-districts')
BASE = ROOT / 'reports/nationwide-localization-20261023-night/cross-province'
TARGETS = [
    ('guangdong-baiyun', 'https://www.by.gov.cn/gzjg/qrlzyhshbzj/zcgg/cjgg/content/post_10451075.html','source-0405'),
    ('guangdong-heshan', 'https://www.heshan.gov.cn/zwgk/xxgk/hssrlzyhshbzj/qt/tzgg/content/post_3472991.html','source-0405'),
    ('jiangxi-rongjiang', 'https://rjxq.ganzhou.gov.cn/rjxq/tzgg/202606/f931ffb78c85406cbf9636a3489296b5.shtml','source-0425'),
]
LINKS = """Array.from(document.querySelectorAll('a[href]')).map(a=>({text:a.innerText.trim(),url:a.href,download:a.getAttribute('download')}))"""


def main():
    for name, url, capture_folder in TARGETS:
        out = BASE / name / capture_folder
        if out.exists():
            print(name, 'existing capture preserved', flush=True)
            continue
        out.mkdir(parents=True)
        c.OUT = out
        c.ENV = {**os.environ, 'AGENT_BROWSER_SESSION': 'labourlawyer-' + name + '-20261024-0405'}
        try:
            try:
                c.browser('open', url)
            except RuntimeError as exc:
                c.save(out / 'navigation-warning.json', {'at': c.NOW(), 'reason': str(exc)})
            raw = c.evaluate(c.CAPTURE_JS)
            c.save(out / 'dom.json', raw)
            c.save(out / 'snapshot.json', c.browser('snapshot', '-i'))
            c.save(out / 'links.json', c.evaluate(LINKS))
            c.browser('screenshot', '--full', str(out / 'source.png'))
            c.save(out / 'capture-only.json', {'requested_url': url, 'actual_url': raw['url'],
                'title': raw['title'], 'collected_at': raw['captured_at'], 'published': False,
                'official_guide_verified': False, 'no_login_or_submission': True})
            print(name, raw['title'], raw['url'], raw['text'][:12000], flush=True)
        except Exception as exc:
            c.save(out / 'failure.json', {'at': c.NOW(), 'reason': str(exc)})
            print(name, 'PENDING', str(exc), flush=True)
        finally:
            c.browser('close')
        time.sleep(2)


if __name__ == '__main__':
    main()
