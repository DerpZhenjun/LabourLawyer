"""Read Futian's own material FAQ and the explicitly scoped municipal channel FAQ."""
import importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian/materials-channel-round25'
TARGETS=[('materials','https://www.szft.gov.cn/msfw/jyefw/cjwt/content/post_3288213.html','申请劳动人事争议仲裁须提交什么材料？'),('channel','https://hrss.sz.gov.cn/zmhd/cjwt/cjwt/ldgx/content/post_12717688.html','深圳哪些区的劳动争议调解仲裁可以在平台上申请？')]
if sys.argv[1:]==['--channel-recovery']:
    BASE=BASE.with_name('channel-recovery-round25')
    TARGETS=TARGETS[1:]
def main():
    if BASE.exists():raise ValueError('Preserve successful own captures')
    BASE.mkdir()
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-futian-'+BASE.name}
    for name,url,label in TARGETS:
        out=BASE/name;out.mkdir();c.OUT=out
        try:
            c.browser('open',url);c.browser('wait','--text',label)
            page=c.evaluate(c.CAPTURE_JS);c.save(out/'dom.json',page)
            c.save(out/'snapshot.json',c.browser('snapshot','-i'))
            c.save(out/'links.json',c.evaluate("Array.from(document.querySelectorAll('a[href]')).map(a=>({text:a.innerText.trim(),url:a.href})).filter(a=>a.text)"))
            c.browser('screenshot',str(out/'heading.png'));c.browser('scroll','down','650');c.browser('screenshot',str(out/'content.png'))
            c.save(out/'manifest.json',{'url':page['url'],'at':page['captured_at'],'state':'public_source_not_yet_parsed_or_candidate','models':0})
            print(json.dumps({'name':name,'url':page['url'],'text':page['text']},ensure_ascii=False),flush=True)
        except Exception as exc:
            r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
            (out/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(out/'failure.json',{'at':c.NOW(),'reason':str(exc)});raise
        finally:c.browser('close')
if __name__=='__main__':main()
