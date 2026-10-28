"""Native guide click for the observed arbitration item, never its mediation row."""
import importlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'
OUT=BASE/'guide-navigation-0508'

def main():
    if OUT.exists():raise ValueError('Preserve observed navigation')
    actual=json.loads((BASE/'result-0505/dom.json').read_text(encoding='utf8'))['url']
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-haizhou-guide-20261024-0508'}
    try:
        c.browser('open',actual);c.browser('wait','--text','当前搜索范围：海州区')
        c.save(OUT/'before.json',c.browser('snapshot','-i'))
        # Selector attributes and exact basecode were read from the saved live DOM.
        c.browser('click','span.matter_button[data-basecode="002014302002"]')
        c.browser('wait','--fn','document.body !== null')
        tabs=c.browser('tab');c.save(OUT/'tabs.json',tabs)
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page)
        snap=c.browser('snapshot','-i');c.save(OUT/'snapshot.json',snap)
        c.browser('screenshot',str(OUT/'source.png'))
        print(json.dumps({'tabs':tabs,'url':page['url'],'title':page['title'],'text':page['text'][:7500],'snapshot':snap.get('snapshot','')[:6500]},ensure_ascii=True))
    except Exception as exc:c.save(OUT/'failure.json',{'reason':str(exc),'guide_verified':False});raise
    finally:c.browser('close')

if __name__=='__main__':main()
