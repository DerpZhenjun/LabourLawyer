"""Follow only Futian's observed own public guidance links, not the failed external guide."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
SOURCE=importlib.import_module('capture-futian-index-night').SOURCE
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian/articles-round25'
TARGETS=[('jurisdiction','深圳市、区劳动人事仲裁委员会的管辖范围如何划分？','post_12840398.html'),('query','劳动人事争议仲裁信息可以网上查询吗？','post_12840380.html')]
LINKS="Array.from(document.querySelectorAll('a[href]')).map(a=>({text:a.innerText.trim(),url:a.href})).filter(a=>a.text)"
def main():
    if BASE.exists():raise ValueError('Preserve successful own article captures')
    BASE.mkdir()
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-futian-articles-round25-20261024'}
    for name,label,tail in TARGETS:
        out=BASE/name;out.mkdir();c.OUT=out
        try:
            c.browser('open',SOURCE);c.browser('wait','--text',label)
            c.save(out/'before-snapshot.json',c.browser('snapshot','-i'))
            c.browser('find','text',label,'click','--exact')
            tabs=c.browser('tab','list');c.save(out/'tabs.json',tabs)
            target=next((t for t in tabs['tabs'] if t['url'].endswith(tail)),None)
            if target:c.browser('tab',target['tabId'])
            c.browser('wait','--text',label)
            page=c.evaluate(c.CAPTURE_JS)
            if not page['url'].endswith(tail):raise ValueError('Native click did not reach own observed article')
            c.save(out/'dom.json',page);c.save(out/'links.json',c.evaluate(LINKS))
            c.save(out/'snapshot.json',c.browser('snapshot','-i'));c.browser('screenshot',str(out/'heading.png'))
            c.browser('scroll','down','650');c.browser('screenshot',str(out/'content.png'))
            c.save(out/'manifest.json',{'url':page['url'],'at':page['captured_at'],'state':'supplementary_own_article_not_formal_guide_or_coverage','models':0})
            print(json.dumps({'name':name,'url':page['url'],'text':page['text']},ensure_ascii=False),flush=True)
        except Exception as exc:
            r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
            (out/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(out/'failure.json',{'at':c.NOW(),'reason':str(exc)});raise
        finally:c.browser('close')
if __name__=='__main__':main()
