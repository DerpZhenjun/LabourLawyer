"""Follow Kaifu's own filtered official result, not the prior Furong guide."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-kaifu/formal-round27'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-hunan-next-round27'}
def main():
    if OUT.exists():raise ValueError('Preserve own formal evidence')
    OUT.mkdir(parents=True)
    try:
        before=c.evaluate(c.CAPTURE_JS);assert 'areacode=430105999000' in before['url']
        c.save(OUT/'before-result.json',before);s=c.browser('snapshot','-i');c.save(OUT/'before-snapshot.json',s)
        refs=re.findall(r'link "办事指南" \[ref=(\w+)\]',s['snapshot']);assert len(refs)==1
        c.browser('click','@'+refs[0]);tabs=c.browser('tab','list');c.save(OUT/'tabs.json',tabs)
        if len(tabs['tabs'])>1:c.browser('tab',tabs['tabs'][-1]['tabId'])
        c.browser('wait','--fn',"location.href.includes('approve_id=') && document.body.innerText.includes('开福区')")
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',page);c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'heading.png'));c.browser('scroll','down','600');c.browser('screenshot',str(OUT/'content.png'))
        c.save(OUT/'manifest.json',{'at':c.NOW(),'source_url':page['url'],'own_result_region':'430105999000','published':False,'candidate':False,'models':0,'session_left_open':True})
        print(json.dumps({'url':page['url'],'title':page['title'],'text':page['text'][:14000]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});c.browser('close');raise
if __name__=='__main__':main()
