"""Inspect the exact native-click target after a locality wait failed; never relabel it."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-kaifu'
OUT=BASE/'observed-generic-target-round27';c.OUT=OUT
c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-kaifu-observed-target-round27'}
def main():
    if OUT.exists():raise ValueError('Preserve native target evidence')
    OUT.mkdir(parents=True)
    try:
        tabs=json.loads((BASE/'formal-round27/tabs.json').read_text('utf8'))['tabs'];source=next(t['url'] for t in tabs if t['active'])
        c.browser('open',source);c.browser('wait','--text','办理部门');c.browser('wait','1500')
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page);c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'heading.png'));c.browser('scroll','down','560');c.browser('screenshot',str(OUT/'content.png'))
        c.save(OUT/'manifest.json',{'at':c.NOW(),'source_url':page['url'],'source_role':'actual_native_click_target_not_confirmed_own_guide',
            'candidate':False,'published':False,'models':0})
        print(json.dumps({'url':page['url'],'title':page['title'],'text':page['text'][:5500]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});raise
    finally:c.browser('close')
if __name__=='__main__':main()
