"""Actual Hunan official department service list discovery, not verified guide data."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
SOURCE='https://zwfw-new.hunan.gov.cn/onething/service/hnservicepowerinfo.jsp?areacode=430102999000&business_activity_classificati=&charName=&dghy=&life_event=&main=1&make_transaction=&minSeq=&orgId=b64b25bb2e0a449fb82212e04984cee8&pager.desc=true&pager.offset=60&themesType=&transact_level=&type=xndtbm&typeIds=&typeid=&word='
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong/list-round26'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-furong-own-round26'}
def main():
    if OUT.exists():raise ValueError('Preserve existing evidence')
    OUT.mkdir(parents=True)
    try:
        c.browser('open',SOURCE);c.browser('wait','--text','劳动人事争议仲裁申请')
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'list.png'))
        c.save(OUT/'manifest.json',{'url':page['url'],'at':page['captured_at'],'state':'own_department_list_not_formal_guide','models':0,'session_left_open_for_native_follow':True})
        print(json.dumps({'url':page['url'],'text':page['text'][:18000]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.browser('close');raise
if __name__=='__main__':main()
