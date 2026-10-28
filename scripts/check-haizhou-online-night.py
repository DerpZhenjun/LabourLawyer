"""Own actual online button; stop at authentication/captcha, never submit."""
import importlib,json,os,re,subprocess,sys,time
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
capture=importlib.import_module('capture-haizhou-formal-night')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'
OUT=BASE/'online-boundary-0530'


def main():
    if OUT.exists():raise ValueError('Preserve own actual boundary capture')
    OUT.mkdir();c.OUT=OUT;capture.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-haizhou-online-20261024-0530'}
    source=json.loads((BASE/'guide.json').read_text('utf8'))['source_url']
    try:
        capture.open_observed_own_guide(source)
        c.browser('wait','--text','劳动人事争议仲裁申请')
        before=c.evaluate(c.CAPTURE_JS);c.save(OUT/'before.json',before)
        snap=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'before-snapshot.json',snap)
        match=re.search(r'(?:link|button) "在线办理"[^\n]*\[ref=(\w+)\]',snap)
        if not match:raise ValueError('Own actual online control missing')
        c.browser('click','@'+match[1])
        for attempt in range(20):
            tabs=c.browser('tab');c.save(OUT/f'tabs-{attempt}.json',tabs)
            found=[t for t in tabs['tabs'] if urlsplit(t['url']).path=='/jsjis/front/login.do'
                   and urlsplit(t['url']).hostname=='www.jszwfw.gov.cn']
            if found:
                c.browser('tab',found[-1]['tabId']);break
            time.sleep(.5)
        c.browser('wait','--fn','!!document.querySelector("input[type=password]")')
        after=c.evaluate(c.CAPTURE_JS);c.save(OUT/'after.json',after)
        c.browser('screenshot',str(OUT/'authentication-boundary.png'))
        c.save(OUT/'capture-only.json',{'actual_click':True,'source_url':source,'at':after['captured_at'],
            'needs_strict_identity_validation':True,'published':False,'no_login_or_submission':True,'models':0})
        print('Own actual authentication boundary captured; strict callback matching pending',flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        result=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
        (OUT/'doctor.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf8')
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS));c.save(OUT/'actual-tabs.json',c.browser('tab'))
        c.browser('screenshot',str(OUT/'failure.png'));raise
    finally:c.browser('close')


if __name__=='__main__':main()
