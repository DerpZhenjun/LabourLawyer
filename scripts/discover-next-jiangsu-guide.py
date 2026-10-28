"""Bounded real-search browser evidence; never treats a result as verified guide."""
import importlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/batches/v4-forms-0215/next-province-search-full'


def main():
    if OUT.exists():raise ValueError('Fresh evidence required')
    OUT.mkdir();c.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-next-province-full-20261024-0223'}
    try:
        keyword='滨湖区 劳动人事争议仲裁 江苏政务服务网'
        c.browser('open','https://www.bing.com/search?'+urlencode({'q':keyword}))
        c.browser('wait','--load','load')
        c.browser('wait','--fn','document.querySelectorAll("h2").length>0 || /验证|challenge|Captcha/i.test(document.body.innerText)')
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'search.json',raw)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'search.png'))
        links=c.evaluate('Array.from(document.querySelectorAll("h2 a")).map(a=>({title:a.innerText,url:a.href,context:a.closest("li")?.innerText}))')
        c.save(OUT/'results.json',{'keyword':keyword,'at':raw['captured_at'],'url':raw['url'],'links':links})
        print(json.dumps({'text':raw['text'][:7000],'links':links},ensure_ascii=False),flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS))
        c.browser('screenshot',str(OUT/'failure.png'))
        print('Search requires later independent review: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
