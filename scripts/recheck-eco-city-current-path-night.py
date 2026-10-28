"""Trace the current own service catalogue to its exact official guide and tabs."""
import importlib
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city/current-path-0320'


def click(text):
    snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/('snapshot-'+str(len(list(OUT.glob('snapshot-*.json'))))+'.json'),snapshot)
    match=re.search(r'(?:link|button) "'+re.escape(text)+r'"[^\n]*\[ref=(\w+)\]',snapshot)
    if not match:raise ValueError('Actual control not found: '+text)
    c.browser('click','@'+match.group(1))


def activate(path):
    for attempt in range(20):
        tabs=c.browser('tab');c.save(OUT/(path.rsplit('/',1)[-1]+f'-tabs-{attempt}.json'),tabs)
        for tab in tabs.get('tabs',[]):
            url=urlsplit(tab.get('url',''))
            if url.hostname=='www.eco-city.gov.cn' and url.path==path:
                c.browser('tab',tab['tabId']);return
        time.sleep(.3)
    raise ValueError('Actual opened official tab not observed: '+path)


def capture(name):
    raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/(name+'.json'),raw)
    c.browser('screenshot',str(OUT/(name+'.png')));return raw


def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=OUT);a=p.parse_args();OUT=a.output.resolve()
    if not OUT.is_relative_to((ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city').resolve()):raise ValueError('Own source evidence folder required')
    if OUT.exists():raise ValueError('Fresh own evidence required')
    OUT.mkdir(parents=True);c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-eco-city-current-path-20261024-0320'}
    try:
        c.browser('open','https://www.eco-city.gov.cn/p1/rcfw.html')
        # The own link is inside the initially hidden 办事指南 panel. Waiting for
        # its visible text before selecting the panel can never succeed.
        c.browser('wait','--text','办事指南');capture('current-service-initial')
        # This tab is a plain <li>, absent from the interactive-only tree.
        # Native text targeting uses the observed visible DOM label.
        c.browser('click','li.mb10:has(span[class*="icon-办事指南"])');c.browser('wait','--text','申请劳动仲裁')
        portal=capture('current-service-portal')
        click('申请劳动仲裁');activate('/p1/sqldzc.html');c.browser('wait','--url','**/sqldzc.html');listing=capture('current-list')
        click('劳动争议仲裁申请');activate('/p1/sqldzc/20171010/461.html');c.browser('wait','--url','**/20171010/461.html');guide=capture('guide')
        if guide['url']!='https://www.eco-city.gov.cn/p1/sqldzc/20171010/461.html' or '中新天津生态城内注册' not in guide['text']:raise ValueError('Own locality or guide mismatch')
        c.browser('click','#erlanmu > a:nth-child(2)');c.browser('wait','--text','此事项未开通在线受理功能');online=capture('online-channel')
        c.browser('click','#erlanmu > a:nth-child(3)');c.browser('wait','--text','劳动仲裁申请书样式');files=capture('official-annexes')
        c.save(OUT/'manifest.json',{'source_url':guide['url'],'verified_at':files['captured_at'],'trace':['current-service-portal.json','current-list.json','guide.json','online-channel.json','official-annexes.json'],
                  'actual_online_text':'此事项未开通在线受理功能。','current_portal':portal['url'],
                  'published':False,'can_generate':False,'note':'Current catalogue still links the own guide; information date and differing own contact numbers remain explicit uncertainties'})
        print(json.dumps({'own_current_path':True,'online':'explicitly_not_open','captures':5}))
    except Exception as exc:
        c.save(OUT/'failure-reason.json',{'at':c.NOW(),'reason':str(exc)});capture('failure');print('Own current path incomplete: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
