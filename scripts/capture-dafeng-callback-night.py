"""Visit only the actual public callback URL observed on the official login."""
import base64
import importlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs,urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'
OUT=BASE/'callback-source-0352'


def main():
    if OUT.exists():raise ValueError('Preserve completed callback capture')
    after=json.loads((BASE/'online-boundary-0345/after.json').read_text('utf8'))
    source=base64.b64decode(parse_qs(urlsplit(after['url']).query)['gotoUrl'][0],validate=True).decode('utf8')
    address=urlsplit(source)
    if (address.scheme,address.hostname,address.path)!=('https','ycdf.jszwfw.gov.cn','/jszwfw/bscx/itemlist/bszn.do'):
        raise ValueError('Do not visit an unrecognized auth callback')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-dafeng-callback-20261024-0352'}
    try:
        try:c.browser('open',source)
        except RuntimeError as exc:
            page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'navigation-timeout.json',{'reason':str(exc),'page':page})
            if page['url']!=source or '盐城市大丰区人力资源和社会保障局' not in page['text']:raise
        c.browser('wait','--text','劳动人事争议仲裁申请')
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'formal-guide.json',raw)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'formal-guide.png'))
        c.save(OUT/'capture-only.json',{'observed_callback':source,'captured_at':raw['captured_at'],
            'published':False,'identity_equivalence':'pending_parser_validation','no_login_or_submission':True})
        print('Actual public callback guide captured; no auth or application submitted')
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS))
        print('Callback pending: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
