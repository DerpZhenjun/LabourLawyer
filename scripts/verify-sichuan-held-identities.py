"""Read-only real-browser identity recheck; never recollect successful raw files."""
import importlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
browser=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/batches/held-identities-0135/official-recheck'

def main():
    if OUT.exists():raise ValueError('Fresh evidence directory required')
    OUT.mkdir(parents=True);browser.OUT=OUT
    browser.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-held-identities-20261024-0135'}
    checks=[]
    try:
        for code,parent,city,district,header in [
            ('511411000000','511400000000','眉山市','天府新区','天府新区（眉山片区）'),
            ('513422000000','513400000000','凉山州','木里县','木里藏族自治县')]:
            old=ROOT/'reports/nationwide-localization-20261023-night/sichuan'
            guide=json.loads((old/'captures'/code/'guide.json').read_text('utf8'))
            tree=json.loads((old/'directory'/f'{parent}.json').read_text('utf8'))
            group=tree['response']['data']['group']
            metadata=next(a for a in group['sonAreas'] if a['areaCode']==code)
            assert group['shortName']==city and metadata['shortName']==district and metadata['name']==header
            browser.browser('open',guide['source_url']);browser.browser('wait','--text','劳动人事争议仲裁申请')
            browser.browser('wait','--fn','document.querySelector("#cityName")?.textContent.trim()==='+json.dumps(header))
            observed=browser.evaluate('({url:location.href,title:document.title,at:new Date().toISOString(),header:document.querySelector("#cityName")?.textContent.trim(),selected:Array.from(document.querySelectorAll(".selected[data-code]")).map(x=>({code:x.getAttribute("data-code"),name:x.getAttribute("data-name")})),authority:document.body.innerText.includes('+json.dumps(guide['authority'])+')})')
            assert observed['url']==guide['source_url'] and observed['header']==header and observed['authority']
            assert any(x['code']==code for x in observed['selected'])
            assert any(x['name']==city for x in observed['selected'])
            browser.save(OUT/f'{code}-identity.json',{'observed':observed,'official_directory':tree['source_url'],'directory_metadata':metadata,'status':'identity_only_not_generation_approval'})
            browser.save(OUT/f'{code}-snapshot.json',browser.browser('snapshot','-i'))
            browser.browser('screenshot',str(OUT/f'{code}.png'))
            checks.append({'code':code,'city':city,'district':district,'header':header,'passed':True})
            print(json.dumps(checks[-1],ensure_ascii=False),flush=True)
    finally:
        browser.save(OUT/'result.json',{'checks':checks,'model_calls':0,'login_or_submission':False})
        browser.browser('close')

if __name__=='__main__':main()
