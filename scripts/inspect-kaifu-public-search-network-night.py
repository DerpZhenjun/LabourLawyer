"""Read only public catalogue response metadata, never auth/session material."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-kaifu'
OUT=BASE/('public-search-network-recovery-round27' if sys.argv[1:]==['--recovery'] else 'public-search-network-round27');c.OUT=OUT
c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-kaifu-public-search-round27'}
def main():
    if OUT.exists():raise ValueError('Preserve own public request evidence')
    OUT.mkdir()
    try:
        source=json.loads((ROOT/'reports/nationwide-localization-20261023-night/discovery-hunan-round27/kaifu-human-resources/dom.json').read_text('utf8'))['url']
        c.browser('open',source);c.browser('wait','--text','按主题')
        c.browser('find','role','link','click','--name','全部','--exact')
        c.browser('wait','--fn',"Array.from(document.querySelectorAll('.el-loading-mask')).every(e=>getComputedStyle(e).display==='none')")
        snap=c.browser('snapshot','-i');ref=re.search(r'textbox "请输入关键字" \[ref=(\w+)\]',snap['snapshot']);assert ref
        c.browser('fill','@'+ref[1],'劳动人事争议仲裁');c.browser('click','.filter-right .btn-click');c.browser('wait','1500')
        request=c.browser('network','requests','--type','xhr,fetch')
        safe=[{k:r[k] for k in ['requestId','method','url','status','resourceType'] if k in r} for r in request['requests'] if 'hunan.gov.cn' in r['url'] and not any(x in r['url'].lower() for x in ['login','oauth','token','userinfo','auth.'])]
        c.save(OUT/'public-request-metadata.json',safe)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
        print(json.dumps(safe,ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});c.browser('close');raise
if __name__=='__main__':main()
