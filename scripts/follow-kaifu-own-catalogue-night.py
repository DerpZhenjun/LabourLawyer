"""Alternative actual own portal catalogue navigation after unified target lost scope."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-kaifu/legacy-catalogue-round27'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-kaifu-public-search-round27'}
def main():
    if OUT.exists():raise ValueError('Preserve own alternative catalogue')
    OUT.mkdir()
    try:
        source=json.loads((ROOT/'reports/nationwide-localization-20261023-night/discovery-hunan-round27/go-kaifu/dom.json').read_text('utf8'))['url']
        c.browser('open',source);c.browser('wait','--text','政务服务事项清单')
        c.browser('find','role','link','click','--name','政务服务事项清单','--exact')
        tabs=c.browser('tab','list');c.save(OUT/'tabs.json',tabs)
        if len(tabs['tabs'])>1:c.browser('tab',tabs['tabs'][-1]['tabId'])
        c.browser('wait','1500');page=c.evaluate(c.CAPTURE_JS);snap=c.browser('snapshot','-i')
        c.save(OUT/'dom.json',page);c.save(OUT/'snapshot.json',snap);c.browser('screenshot',str(OUT/'page.png'))
        print(json.dumps({'url':page['url'],'snapshot':snap['snapshot'][:15000]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});c.browser('close');raise
if __name__=='__main__':main()
