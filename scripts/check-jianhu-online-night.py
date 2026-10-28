"""Click the own official online control and stop before authentication."""
import importlib
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'backend'))
from regional_jiangsu import verify_jianhu_online_capture
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu'
OUT=BASE/'online-recheck-0255'


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args();OUT=args.output.resolve()
    if not OUT.is_relative_to(BASE.resolve()):raise ValueError('Own public evidence folder required')
    if OUT.exists():raise ValueError('Fresh evidence required; preserve completed attempts')
    OUT.mkdir(parents=True);c.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-jianhu-online-20261024-0255'}
    source=json.loads((BASE/'guide.json').read_text('utf8'))['source_url']
    try:
        try:c.browser('open',source)
        except RuntimeError as exc:
            raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'navigation-timeout.json',raw)
            if raw['url'].split('#')[0]!=source.split('#')[0] or '建湖县人力资源和社会保障局' not in raw['text']:raise
            c.save(OUT/'navigation-recovery.json',{'at':c.NOW(),'reason':str(exc),'actual_guide_rendered':True})
        c.browser('wait','--text','劳动人事争议仲裁申请')
        before=c.evaluate(c.CAPTURE_JS);c.save(OUT/'before.json',before)
        if before['url'].split('#')[0]!=source.split('#')[0] or '建湖县' not in before['text']:raise ValueError('Own guide identity required')
        snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'before-snapshot.json',snapshot)
        match=re.search(r'(?:link|button) "在线办理"[^\n]*\[ref=(\w+)\]',snapshot)
        if not match:raise ValueError('Actual own online control not found')
        c.browser('click','@'+match.group(1))
        tabs=c.browser('tab');c.save(OUT/'tabs-after-click.json',tabs)
        # The observed click may open a new tab. Select only its actual public
        # official URL from the owned session, never a guessed login target.
        selected=False
        for attempt in range(20):
            tabs=c.browser('tab');c.save(OUT/f'tabs-poll-{attempt}.json',tabs)
            candidates=tabs.get('tabs',[]) if isinstance(tabs,dict) else []
            for tab in candidates:
                url=tab.get('url','');host=urlsplit(url).hostname or ''
                if ('login' in url.lower() or '身份认证' in tab.get('title','')) and (host=='jszwfw.gov.cn' or host.endswith('.jszwfw.gov.cn')):
                    c.browser('tab',str(tab.get('tabId')));selected=True;break
            if selected:break
            time.sleep(.5)
        # The guide header itself includes "登录"; that is not a navigation
        # milestone. Require an actual password control and changed URL first.
        c.browser('wait','--fn','location.href !== '+json.dumps(before['url'])+' && !!document.querySelector("input[type=password]")')
        after=c.evaluate(c.CAPTURE_JS);c.save(OUT/'after.json',after)
        c.browser('screenshot',str(OUT/'authentication-boundary.png'))
        verified=verify_jianhu_online_capture(before,after)
        state=verified['status']
        result={'source_url':source,'region_code':'320925','province':'jiangsu','city':'盐城市','district':'建湖县',
                'checked_at':after['captured_at'],'official_link':state=='auth_required','url':after['url'],'status':state,
                'screenshot':(OUT/'authentication-boundary.png').relative_to(ROOT).as_posix(),
                'action':'实际点击建湖县自身官网在线办理；到认证边界即停止，未登录、未填写或提交申请'}
        c.save(OUT/'online-check.json',result)
        print(json.dumps({k:result[k] for k in ['district','status','checked_at']},ensure_ascii=False),flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS));c.browser('screenshot',str(OUT/'failure.png'))
        print('Own online check incomplete: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
