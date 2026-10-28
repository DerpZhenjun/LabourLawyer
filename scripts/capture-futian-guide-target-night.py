"""Complete Futian directory's observed external-link confirmation, public pages only."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
SOURCE=importlib.import_module('capture-futian-index-night').SOURCE
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian/guide-target-round24'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-futian-target-round24-20261024'}
def main():
    if OUT.exists():raise ValueError('Preserve existing target evidence')
    OUT.mkdir()
    try:
        c.browser('open',SOURCE);c.browser('wait','--text','劳动人事争议仲裁申请')
        c.browser('find','text','劳动人事争议仲裁申请','click');c.browser('wait','--text','继续访问')
        c.save(OUT/'confirmation.json',c.browser('snapshot','-i'))
        c.browser('find','text','继续访问','click')
        tabs=c.browser('tab','list');c.save(OUT/'tabs.json',tabs)
        target=next((t for t in tabs['tabs'] if 'gdzwfw.gov.cn' in t.get('url','')),None)
        if target:c.browser('tab',target['tabId'])
        c.browser('wait','--load','domcontentloaded')
        c.browser('wait','--text','劳动人事争议仲裁申请')
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'guide-target.png'))
        c.save(OUT/'manifest.json',{'source_index':SOURCE,'target_url':page['url'],'at':c.NOW(),'state':'target_identity_not_yet_verified','models':0})
        print(json.dumps({'url':page['url'],'title':page['title'],'text':page['text'][:22000]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr)
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        raise
    finally:c.browser('close')
if __name__=='__main__':main()
