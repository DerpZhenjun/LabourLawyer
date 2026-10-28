"""Read only the exact public callback observed at the auth boundary; no login."""
import base64,importlib,json,os,subprocess,sys
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'
OUT=BASE/'callback-source-0605'


def main():
    if OUT.exists():raise ValueError('Preserve own callback capture')
    after=json.loads((BASE/'online-boundary-0530/after.json').read_text('utf8'))
    source=base64.b64decode(parse_qs(urlsplit(after['url']).query)['gotoUrl'][0],validate=True).decode('utf8')
    address=urlsplit(source);query=parse_qs(address.query)
    if ((address.scheme,address.hostname,address.path)!=('http','lyghz.jszwfw.gov.cn','/jszwfw/publicservice/itemlist/showDetail.do')
        or query.get('iddept_yw_inf')!=['11320706014267312C400201430200201']
        or query.get('iddept_ql_inf')!=['11320706014267312C4002014302002']):
        raise ValueError('Unrecognized own observed callback')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-haizhou-callback-20261024-0605'}
    try:
        try:c.browser('open',source)
        except RuntimeError as exc:
            doctor=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
            (OUT/'doctor.log').write_text(doctor.stdout+'\n'+doctor.stderr,encoding='utf8')
            page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'navigation-timeout.json',{'reason':str(exc),'page':page})
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'callback-page.json',raw)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        c.browser('screenshot',str(OUT/'callback-page.png'))
        c.save(OUT/'capture-only.json',{'observed_callback':source,'actual_final_url':raw['url'],'at':raw['captured_at'],
            'identity_validation':'pending','published':False,'no_credentials_or_submission':True,'models':0})
        print(json.dumps({'url':raw['url'],'title':raw['title'],'text':raw['text'][:1800]},ensure_ascii=True),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
