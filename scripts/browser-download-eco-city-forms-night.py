"""Bounded native-browser retry after the HTTP client's TLS handshake failed."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city'
OUT=BASE/'browser-download-0308'


def main():
    if OUT.exists():raise ValueError('Fresh evidence required')
    OUT.mkdir(parents=True);c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-eco-city-forms-20261024-0308'}
    source=json.loads((BASE/'discovery-0303/official-page.json').read_text('utf8'))['url']
    links=json.loads((BASE/'discovery-0303/public-links.json').read_text('utf8'))
    result=[]
    try:
        try:c.browser('open',source)
        except RuntimeError as exc:c.save(OUT/'navigation-error.json',{'at':c.NOW(),'reason':str(exc)})
        actual=c.evaluate(c.CAPTURE_JS);c.save(OUT/'before.json',actual)
        if actual['url']!=source or '中新天津生态城内注册' not in actual['text']:raise ValueError('Own archive identity changed')
        snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'snapshot-before.json',snapshot)
        tab=re.search(r'link "表格下载"[^\n]*\[ref=(\w+)\]',snapshot)
        if not tab:raise ValueError('Actual table-download tab not found')
        c.browser('click','@'+tab.group(1));c.browser('wait','--text','劳动仲裁申请书样式')
        c.save(OUT/'download-panel.json',c.evaluate(c.CAPTURE_JS))
        c.browser('screenshot',str(OUT/'download-panel.png'))
        for item in links:
            if '申请书' not in item['text'] and '证据清单' not in item['text']:continue
            name=Path(urlsplit(item['url']).path).name
            record={'source_url':source,'download_url':item['url'],'official_display_name':item['text'],
                    'attempted_at':c.NOW(),'official_kind':'unverified_form_style','can_generate':False}
            dest=ROOT/'templates/_docx/_regional/function-tianjin-eco-city'/name
            if dest.exists():raise ValueError('Preserve existing original')
            dest.parent.mkdir(parents=True,exist_ok=True)
            try:
                c.browser('download','a[href$="'+name+'"]',str(dest))
                body=dest.read_bytes()
                if not body.startswith((b'PK',b'\xd0\xcf')):raise ValueError('Not an original Office file')
                record.update(file=dest.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(body).hexdigest(),
                              bytes=len(body),download_status='downloaded',downloaded_at=c.NOW(),original_name=name)
            except Exception as exc:record.update(download_status='failed',reason=str(exc))
            result.append(record);c.save(OUT/'files.json',result)
            print(item['text'],record['download_status'],flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS));c.browser('screenshot',str(OUT/'failure.png'))
        print('Own archive retry incomplete: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
