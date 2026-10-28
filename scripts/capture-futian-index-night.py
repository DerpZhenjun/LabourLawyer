"""Native public navigation from Futian's own arbitration directory; no login or submission."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
SOURCE='https://www.szft.gov.cn/msfw/jyefw/ldzc/bszn/index.html'
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian/discovery-round24'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-futian-own-round24-20261024'}
def main():
    if OUT.exists():raise ValueError('Preserve existing evidence')
    OUT.mkdir(parents=True)
    try:
        c.browser('open',SOURCE);c.browser('wait','--text','劳动人事争议仲裁申请')
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'index.json',raw)
        c.save(OUT/'index-snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'index.png'))
        c.browser('find','text','劳动人事争议仲裁申请','click')
        c.save(OUT/'tabs-after-native-click.json',c.browser('tab','list'))
        c.save(OUT/'after-native-click.json',c.evaluate(c.CAPTURE_JS))
        c.save(OUT/'after-native-click-snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'after-native-click.png'))
        c.save(OUT/'manifest.json',{'at':c.NOW(),'source_url':SOURCE,'state':'discovery_only_not_verified_or_published','models':0})
        print(json.dumps({'index_links':raw.get('links'),'after':c.evaluate('({url:location.href,title:document.title,text:document.body.innerText})')},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr)
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        raise
    finally:c.browser('close')
if __name__=='__main__':main()
