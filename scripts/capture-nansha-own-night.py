"""Read the independently discovered official Nansha public material page."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
SOURCE='https://www.gzns.gov.cn/gzjg/gzsnsq/qzfgzbm/qrlzyhshbzj/ldrszyzc/content/post_5801798.html'
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha/source-round23'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-nansha-own-round23-20261024'}
def main():
    if OUT.exists():raise ValueError('Do not overwrite own source evidence')
    OUT.mkdir(parents=True)
    try:
        c.browser('open',SOURCE);c.browser('wait','--text','仲裁告知事项及申请材料下载')
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'heading.png'))
        c.browser('scroll','down','700');c.browser('screenshot',str(OUT/'materials.png'))
        c.browser('scroll','down','1100');c.browser('screenshot',str(OUT/'annexes.png'))
        c.save(OUT/'manifest.json',{'at':c.NOW(),'source_url':SOURCE,'capture':'dom.json','state':'own_raw_only_not_published','model_calls':0})
        print(json.dumps({'url':page.get('url'),'title':page.get('title'),'at':c.NOW(),'state':'own_raw_only'},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr)
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        raise
    finally:c.browser('close')
if __name__=='__main__':main()
