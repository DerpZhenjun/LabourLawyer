"""Revisit the existing Tianjin function-area official archive, read-only."""
import importlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city/discovery-0303'


def main():
    if OUT.exists():raise ValueError('Fresh evidence required')
    OUT.mkdir(parents=True);c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-eco-city-own-guide-20261024-0303'}
    sources=json.loads((ROOT/'frontend/src/data/provinceCatalog.json').read_text('utf8'))
    source=next(p for p in sources if p['slug']=='tianjin')['source_url']
    try:
        try:c.browser('open',source)
        except RuntimeError as exc:c.save(OUT/'navigation-error.json',{'at':c.NOW(),'reason':str(exc)})
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'official-page.json',raw)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.save(OUT/'public-links.json',c.evaluate('Array.from(document.querySelectorAll("a[href]")).map(a=>({text:a.innerText,url:a.href})).filter(a=>a.text.includes("仲裁")||/\\.(docx?|pdf|zip)(?:[?#]|$)/i.test(a.url))'))
        c.browser('screenshot',str(OUT/'official-page.png'))
        print(json.dumps({'title':raw['title'],'url':raw['url'],'text_prefix':raw['text'][:180]},ensure_ascii=False))
    finally:c.browser('close')


if __name__=='__main__':main()
