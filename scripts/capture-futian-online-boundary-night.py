"""Visit only the public URL actually printed by the municipal FAQ; stop before login."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian'
OUT=BASE/'online-boundary-round25';c.OUT=OUT
c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-futian-online-boundary-round25'}
APPLY=sys.argv[1:]==['--apply-click']
ARBITRATION=APPLY or sys.argv[1:]==['--arbitration-click']
if ARBITRATION:
    OUT=BASE/'arbitration-click-round25';c.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-futian-arbitration-click-round25'}
if APPLY:
    OUT=BASE/'apply-click-round25';c.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-futian-apply-click-round25'}
def main():
    if OUT.exists():raise ValueError('Preserve actual boundary evidence')
    OUT.mkdir()
    raw=json.loads((BASE/'channel-recovery-round25/channel/dom.json').read_text('utf8'))
    urls=re.findall(r'https://hrsspub\.sz\.gov\.cn/szldzc/login',raw['text'])
    if len(urls)!=1 or '福田区、罗湖区' not in raw['text']:raise ValueError('Own district/channel attribution missing')
    try:
        c.browser('open',urls[0]);c.browser('wait','--text','登录')
        if ARBITRATION:
            c.save(OUT/'before-snapshot.json',c.browser('snapshot','-i'))
            c.browser('find','text','我要仲裁','click','--exact')
            c.browser('wait','--text','登录')
        if APPLY:
            c.save(OUT/'before-apply-snapshot.json',c.browser('snapshot','-i'))
            c.browser('find','text','申请仲裁','click','--exact')
            c.save(OUT/'after-apply-snapshot.json',c.browser('snapshot','-i'))
        # Public text only: do not persist hidden login tokens, account data or cookies.
        page=c.evaluate('({url:location.href,title:document.title,text:document.body.innerText,captured_at:new Date().toISOString()})')
        c.save(OUT/'public-page.json',page);c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot','--full',str(OUT/'login-boundary.png'))
        c.save(OUT/'manifest.json',{'source':raw['url'],'observed_entry':urls[0],'actual_url':page['url'],'at':page['captured_at'],'state':'public_entry_boundary_only_not_authenticated_submission','login_attempted':False,'models':0})
        print(json.dumps(page,ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});raise
    finally:c.browser('close')
if __name__=='__main__':main()
