"""Fresh own-session public material checks; no application, login or JS action."""
import importlib
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/batches/v4-guides-0205/official-recheck'


def ref(snapshot,label):
    line=next((line for line in snapshot.splitlines() if label in line),None)
    if not line:raise ValueError('Missing actual control: '+label)
    return '@'+re.search(r'ref=(\w+)',line).group(1)


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args();OUT=args.output.resolve()
    if not OUT.is_relative_to((ROOT/'reports/nationwide-localization-20261023-night/batches/v4-guides-0205').resolve()):raise ValueError('Own batch evidence only')
    if OUT.exists():raise ValueError('Fresh evidence folder required')
    OUT.mkdir(parents=True);c.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-v4-material-check-20261024-0200'}
    checks=[]
    try:
        for code,expected in [('510704000000','2'),('510723000000','3')]:
            guide=json.loads((OUT.parent/'guides'/code/'guide.json').read_text('utf8'))
            c.browser('open',guide['source_url']);c.browser('set','viewport','1440','1000')
            c.browser('wait','--fn','document.querySelector("#cityName")?.textContent.trim()==='+json.dumps(guide['district']))
            c.browser('wait','--fn','typeof jQuery === "undefined" || jQuery.active === 0')
            # Two identically labelled navigation lists exist (sticky + content).
            # Select the inspected content navigation, not the first sticky clone.
            c.browser('click','.content3 .content3_title_list li:nth-child(2)')
            c.browser('wait','--text','材料必要性')
            snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/(code+'-materials-snapshot.json'),{'snapshot':snapshot})
            rows=c.evaluate('Array.from(document.querySelectorAll("#material .tr_content")).map(r=>Array.from(r.querySelectorAll(":scope >td")).map(t=>t.innerText))')
            index=next(i for i,r in enumerate(rows) if r[1].strip()=='劳动人事争议仲裁申请书')
            assert rows[index][5].strip()==expected
            links=[line for line in snapshot.splitlines() if 'link "查看更多"' in line]
            c.browser('click',ref(links[index],'link "查看更多"'))
            c.browser('wait','--text','填报须知')
            observed=c.evaluate('({url:location.href,title:document.title,at:new Date().toISOString(),text:document.body.innerText,header:document.querySelector("#cityName")?.textContent.trim()})')
            assert observed['url']==guide['source_url'] and observed['header']==guide['district']
            assert '劳动人事争议仲裁申请书' in observed['text']
            c.save(OUT/(code+'-application-detail.json'),observed)
            c.browser('screenshot',str(OUT/(code+'-application-detail.png')))
            checks.append({'code':code,'district':guide['district'],'application_copies':expected,'passed':True,'source_url':guide['source_url']})
            print(json.dumps(checks[-1],ensure_ascii=False),flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'reason':str(exc),'occurred_at':c.NOW(),'url':c.evaluate('location.href'),'state':'pending_recheck_not_official_failure'})
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS))
        c.save(OUT/'actual-snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'actual-page.png'))
        raise
    finally:
        c.save(OUT/'result.json',{'checks':checks,'model_calls':0,'login_or_submission':False})
        c.browser('close')


if __name__=='__main__':main()
