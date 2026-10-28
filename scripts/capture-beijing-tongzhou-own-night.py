"""Initial actual own public guide capture, not yet a verified normalized candidate."""
import hashlib,importlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-tongzhou/formal-0640'
SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110112000000/c692cfd3-1a9d-4734-8f16-86b3a0dbafee.html?locationCode=110112000000&serverType=1002'


def main():
    if OUT.exists():raise ValueError('Preserve own public raw guide')
    OUT.mkdir(parents=True);c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-tongzhou-guide-20261024-0640'}
    try:
        try:c.browser('open',SOURCE)
        except RuntimeError as exc:
            result=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
            (OUT/'doctor.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf8')
            c.save(OUT/'navigation-warning.json',{'reason':str(exc)})
        c.browser('wait','--fn','document.body && document.body.innerText.includes("仲裁申请书") && document.body.innerText.includes("通州")')
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'page.json',raw)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        links=c.evaluate("Array.from(document.querySelectorAll('a')).filter(a=>/下载|办理|材料|受理|流程|展开/.test(a.textContent)).map(a=>({text:a.textContent.trim(),url:a.href,onclick:a.getAttribute('onclick')}))")
        c.save(OUT/'links.json',links);c.browser('screenshot',str(OUT/'page.png'))
        c.save(OUT/'manifest.json',{'source_url':raw['url'],'title':raw['title'],'captured_at':raw['captured_at'],
            'capture_sha256':hashlib.sha256((OUT/'page.json').read_bytes()).hexdigest(),
            'state':'own_raw_only_requires_sections_material_details_directory_identity_annex_review',
            'published':False,'models':0})
        print(json.dumps({'url':raw['url'],'title':raw['title'],'text':raw['text'][:8500],'links':links[:15]},ensure_ascii=True),flush=True)
    except Exception as exc:
        result=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
        (OUT/'failure-doctor.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf8')
        c.save(OUT/'failure.json',{'reason':str(exc),'at':c.NOW()})
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS));c.browser('screenshot',str(OUT/'failure.png'));raise
    finally:c.browser('close')


if __name__=='__main__':main()
