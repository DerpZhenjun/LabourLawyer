"""Supplementary visible contact evidence; preserve the successful guide trace."""
import importlib
import os
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city/contact-visible-0345'


def main():
    if OUT.exists():raise ValueError('Preserve prior evidence')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-eco-city-contact-0345'}
    try:
        c.browser('open','https://www.eco-city.gov.cn/p1/rcfw.html')
        c.browser('wait','--text','中新天津生态城劳动人事争议调解中心')
        snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'snapshot.json',snapshot)
        match=re.search(r'heading "中新天津生态城劳动人事争议调解中心"[^\n]*\bref=(\w+)',snapshot)
        if not match:raise ValueError('Own contact heading not observed')
        c.browser('scrollintoview','@'+match[1]);c.browser('screenshot',str(OUT/'contact.png'))
        raw=c.evaluate(c.CAPTURE_JS)
        assert '022-66328970' in raw['text'] and raw['url']=='https://www.eco-city.gov.cn/p1/rcfw.html'
        c.save(OUT/'contact.json',raw);print('Actual own contact section captured; no phone normalization or source replacement')
    finally:c.browser('close')


if __name__=='__main__':main()
