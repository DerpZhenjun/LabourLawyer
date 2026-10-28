"""Capture the own native online click; stop at the official login form."""
import importlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'
OUT=BASE/'online-boundary-0345'


def main():
    if OUT.exists():raise ValueError('Preserve prior own evidence')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-dafeng-online-20261024-0345'}
    source=json.loads((BASE/'guide.json').read_text('utf8'))['source_url']
    try:
        try:c.browser('open',source)
        except RuntimeError as exc:
            actual=c.evaluate(c.CAPTURE_JS);c.save(OUT/'navigation-timeout.json',{'reason':str(exc),'page':actual})
            if actual['url'].split('#')[0]!=source.split('#')[0] or '盐城市大丰区人力资源和社会保障局' not in actual['text']:raise
        before=c.evaluate(c.CAPTURE_JS);c.save(OUT/'before.json',before)
        if before['url'].split('#')[0]!=source.split('#')[0]:raise ValueError('Own guide not loaded')
        snap=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'before-snapshot.json',snap)
        match=re.search(r'(?:link|button) "在线办理"[^\n]*\[ref=(\w+)\]',snap)
        if not match:raise ValueError('Actual own online button not observed')
        c.browser('click','@'+match[1])
        selected=False
        for attempt in range(20):
            tabs=c.browser('tab');c.save(OUT/f'tabs-{attempt}.json',tabs)
            for tab in tabs.get('tabs',[]):
                address=urlsplit(tab.get('url',''))
                if address.hostname=='www.jszwfw.gov.cn' and address.path=='/jsjis/front/login.do':
                    c.browser('tab',tab['tabId']);selected=True;break
            if selected:break
            time.sleep(.5)
        c.browser('wait','--fn','location.href !== '+json.dumps(before['url'])+' && !!document.querySelector("input[type=password]")')
        after=c.evaluate(c.CAPTURE_JS);c.save(OUT/'after.json',after)
        c.browser('screenshot',str(OUT/'authentication-boundary.png'))
        c.save(OUT/'capture-only.json',{'actual_click':True,'source_url':source,'captured_at':after['captured_at'],
            'needs_strict_identity_validation':True,'published':False,'no_login_or_submission':True})
        print('Own native online click reached login DOM; strict callback validation pending',flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS))
        c.browser('screenshot',str(OUT/'failure.png'));print('Own online capture incomplete: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
