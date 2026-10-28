"""Discover only on the independently identified county portal; not guide data."""
import importlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou/discovery-0500'

def main():
    if OUT.exists():raise ValueError('Preserve successful own portal discovery')
    OUT.mkdir(parents=True);c.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-haizhou-discovery-20261024-0500'}
    try:
        c.browser('open','https://lyghz.jszwfw.gov.cn/')
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'root-dom.json',page)
        snap=c.browser('snapshot','-i');c.save(OUT/'root-snapshot.json',snap)
        c.browser('screenshot',str(OUT/'root.png'))
        inputs=c.evaluate("Array.from(document.querySelectorAll('input')).filter(e=>e.getBoundingClientRect().height>0).map(e=>({id:e.id,type:e.type,placeholder:e.placeholder,aria:e.getAttribute('aria-label')}))")
        c.save(OUT/'visible-inputs.json',inputs)
        c.save(OUT/'status.json',{'url':page['url'],'title':page['title'],'captured_at':page['captured_at'],
            'state':'actual_county_portal_root_only_not_a_verified_arbitration_guide','published':False,
            'note':'Search engine arbitration result was Lianyungang city-level, not this county; not reused.',
            'models':0})
        print(json.dumps({'url':page['url'],'title':page['title'],'visible_inputs':inputs,'snapshot':snap},ensure_ascii=True))
    finally:c.browser('close')

if __name__=='__main__':main()
