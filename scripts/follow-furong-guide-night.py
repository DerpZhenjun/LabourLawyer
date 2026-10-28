"""Click the actual arbitration row's own guide (not adjacent mediation)."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong/formal-round26'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-furong-own-round26'}
def main():
    if OUT.exists():raise ValueError('Preserve guide evidence')
    OUT.mkdir()
    try:
        # e82 was read in the same named session: arbitration row66, not mediation row65/e78.
        c.browser('click','@e82');tabs=c.browser('tab','list');c.save(OUT/'tabs.json',tabs)
        if len(tabs['tabs'])>1:c.browser('tab',tabs['tabs'][-1]['tabId'])
        c.browser('wait','--load','domcontentloaded');c.browser('wait','--text','劳动人事争议仲裁申请')
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'heading.png'));c.browser('scroll','down','650');c.browser('screenshot',str(OUT/'content.png'))
        c.save(OUT/'manifest.json',{'at':page['captured_at'],'url':page['url'],'state':'own_formal_raw_not_yet_complete_or_parsed','models':0,'session_left_open':True})
        print(json.dumps({'url':page['url'],'title':page['title'],'text':page['text'][:26000]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.browser('close');raise
if __name__=='__main__':main()
