"""Native own-guide online link inspection, stopping before authentication."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong/online-recovery-round26'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-furong-own-round26'}
def capture(name):
    page=c.evaluate(c.CAPTURE_JS);c.save(OUT/(name+'.json'),page)
    c.save(OUT/(name+'-snapshot.json'),c.browser('snapshot','-i'))
    c.browser('screenshot',str(OUT/(name+'.png')));return page
def main():
    if OUT.exists():raise ValueError('Preserve actual online evidence')
    OUT.mkdir()
    try:
        source=json.loads((OUT.parent/'formal-round26/dom.json').read_text('utf8'))['url']
        c.browser('open',source);c.browser('wait','--fn',"document.body.innerText.includes('芙蓉区人力资源和社会保障局')")
        guide=next(t for t in c.browser('tab','list')['tabs'] if 'approve_id=0661f202529745928ad2d4bc532e233a' in t['url'])
        c.browser('tab',guide['tabId']);s=c.browser('snapshot','-i');c.save(OUT/'before-snapshot.json',s)
        ref=re.search(r'link "在线办理" \[ref=(\w+)\]',s['snapshot']);assert ref
        c.browser('scrollintoview','@'+ref[1]);c.browser('click','@'+ref[1])
        c.browser('wait','--text','个人登录')
        # Wait only for public DOM, never enter identity or application data.
        tabs=c.browser('tab','list');c.save(OUT/'tabs.json',tabs)
        if len(tabs['tabs'])>1:
            current=next((t for t in tabs['tabs'] if t.get('active')),tabs['tabs'][-1]);c.browser('tab',current['tabId'])
        first=capture('boundary');c.save(OUT/'manifest.json',{'at':c.NOW(),'source_url':guide['url'],
            'observed_url':first['url'],'native_link_clicked':True,'authentication_completed':False,'submission_tested':False,'models':0})
        print(json.dumps({'url':first['url'],'title':first['title'],'text':first['text'][:3200]},ensure_ascii=True))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});raise
    finally:c.browser('close')
if __name__=='__main__':main()
