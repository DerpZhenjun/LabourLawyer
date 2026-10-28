"""Next own locality raw capture only. No neighbour rules, DB writes or models."""
import hashlib,importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-chaoyang/formal-0720'
SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110105000000/75d01c1c-dc66-49fe-93a1-7003eaaedd8a.html'
def main():
    if OUT.exists():raise ValueError('Preserve own initial source')
    OUT.mkdir(parents=True);c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-chaoyang-20261024-0720'}
    try:
        c.browser('open',SOURCE)
        c.browser('wait','--fn','document.body && document.body.innerText.includes("仲裁申请书") && document.body.innerText.includes("北京市朝阳区人力资源和社会保障局")')
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'page.json',raw)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.save(OUT/'links.json',c.evaluate("Array.from(document.querySelectorAll('a')).filter(a=>/下载|办理|材料|受理|流程|展开/.test(a.textContent)).map(a=>({text:a.textContent.trim(),url:a.href,html:a.outerHTML.slice(0,1000)}))"))
        c.browser('screenshot',str(OUT/'page.png'))
        c.save(OUT/'manifest.json',{'source_url':raw['url'],'title':raw['title'],'captured_at':raw['captured_at'],
            'capture_sha256':hashlib.sha256((OUT/'page.json').read_bytes()).hexdigest(),
            'state':'own_raw_only_not_parsed_staged_or_published','models':0})
        print(json.dumps({'title':raw['title'],'source_url':raw['url'],'sha256':hashlib.sha256((OUT/'page.json').read_bytes()).hexdigest()}))
    except Exception as exc:
        run=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(run.stdout+b'\n'+run.stderr)
        c.save(OUT/'failure.json',{'reason':str(exc),'at':c.NOW()});raise
    finally:c.browser('close')
if __name__=='__main__':main()
