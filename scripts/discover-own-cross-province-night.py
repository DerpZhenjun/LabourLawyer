"""Actual browser search for further own official sources, never coverage data."""
import hashlib,importlib,json,os,subprocess,sys
from pathlib import Path
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/discovery-cross-province-0630'
QUERIES=[('zhejiang-yuhang','site:yuhang.gov.cn 劳动仲裁 申请书 证据清单'),
         ('fujian-siming','site.siming.gov.cn 劳动仲裁 申请书 证据目录')]


def main():
    if OUT.exists():raise ValueError('Preserve own search evidence')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-cross-province-discovery-20261024-0630'}
    results=[]
    try:
        for name,query in QUERIES:
            url='https://www.bing.com/search?'+urlencode({'q':query})
            try:c.browser('open',url)
            except RuntimeError as exc:
                result=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
                (OUT/(name+'-doctor.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf8')
                c.save(OUT/(name+'-navigation-warning.json'),{'reason':str(exc)})
            c.browser('wait','--fn','document.body !== null')
            page=c.evaluate(c.CAPTURE_JS);target=OUT/(name+'-search.json');c.save(target,page)
            c.save(OUT/(name+'-snapshot.json'),c.browser('snapshot','-i'))
            c.browser('screenshot',str(OUT/(name+'-search.png')))
            links=c.evaluate("Array.from(document.querySelectorAll('#b_results .b_algo h2 a')).map(a=>({title:a.innerText,url:a.href}))")
            c.save(OUT/(name+'-results.json'),links)
            results.append({'name':name,'query':query,'url':page['url'],'title':page['title'],'captured_at':page['captured_at'],
                'capture_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'results':links,
                'state':'search_results_only_not_official_guide','published':False,'models':0})
            c.save(OUT/'manifest.json',results)
            print(json.dumps(results[-1],ensure_ascii=True),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
