"""Resume the actual new-tab URL; wait for DOM instead of rerunning the search."""
import importlib,json,os,sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'
OUT=BASE/'result-0505'

def main():
    if OUT.exists():raise ValueError('Preserve own result capture')
    tabs=json.loads((BASE/'search-0502/tabs.json').read_text(encoding='utf8'))['tabs']
    actual=next(t['url'] for t in tabs if t['active'])
    url=urlsplit(actual)
    if url.hostname!='ydzt.jszwfw.gov.cn' or parse_qs(url.query).get('websiteid')!=['320706000000000']:
        raise ValueError('Actual search navigation identity changed')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-haizhou-result-20261024-0505'}
    try:
        c.browser('open',actual);c.browser('wait','--fn','document.body !== null')
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'));c.browser('screenshot',str(OUT/'source.png'))
        c.save(OUT/'links.json',c.evaluate("Array.from(document.querySelectorAll('a[href]')).map(a=>({text:a.innerText,url:a.href}))"))
        c.save(OUT/'status.json',{'url':page['url'],'title':page['title'],'captured_at':page['captured_at'],
            'guide_verified':False,'published':False,'models':0,'recovery':'actual observed new-tab URL; native DOM wait; no repeat search click'})
        print(json.dumps({'url':page['url'],'title':page['title'],'text':page['text'][:8000]},ensure_ascii=True))
    except Exception as exc:
        c.save(OUT/'failure.json',{'reason':str(exc),'guide_verified':False,'models':0});raise
    finally:c.browser('close')

if __name__=='__main__':main()
