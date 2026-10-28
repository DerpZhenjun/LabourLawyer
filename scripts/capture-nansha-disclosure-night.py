"""Follow the material notice's actual public disclosure link, no auth/submission."""
import importlib,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
SOURCE=importlib.import_module('capture-nansha-own-night').SOURCE
WINDOWS=sys.argv[1:]==['--windows']
if WINDOWS:SOURCE='https://www.gzns.gov.cn/gzjg/gzsnsq/qzfgzbm/qrlzyhshbzj/ldrszyzc/content/post_7330888.html'
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha'/('windows-round23' if WINDOWS else 'disclosure-round23')
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-nansha-disclosure-round23'}
def main():
    if OUT.exists():raise ValueError('Preserve completed disclosure capture')
    OUT.mkdir()
    try:
        c.browser('open',SOURCE);c.browser('wait','--text','仲裁公开（人员、场所、流程、文书等）' if WINDOWS else '仲裁告知事项及申请材料下载')
        snapshot=c.browser('snapshot','-i');c.save(OUT/'before-snapshot.json',snapshot)
        label='广州市南沙区劳动人事争议仲裁机构设置和收件窗口' if WINDOWS else '【置顶】仲裁公开（人员、场所、流程、文书等）'
        ref=re.search(r'link "'+re.escape(label)+r'" \[ref=(\w+)\]',snapshot['snapshot'])
        if not ref:raise ValueError('Own disclosure link no longer visible')
        c.browser('click','@'+ref[1]);c.browser('wait','--text',label)
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'dom.json',raw)
        c.save(OUT/'snapshot.json',c.browser('snapshot','-i'));c.browser('screenshot',str(OUT/'heading.png'))
        c.browser('scroll','down','700');c.browser('screenshot',str(OUT/'content.png'))
        c.save(OUT/'manifest.json',{'source_url':raw['url'],'captured_at':raw['captured_at'],'title':raw['title'],
            'state':'supplementary_own_raw_not_parsed_or_published','models':0})
        print(raw['url'],raw['title'])
    except Exception as exc:
        run=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(run.stdout+b'\n'+run.stderr);c.save(OUT/'failure.json',{'reason':str(exc),'at':c.NOW()});raise
    finally:c.browser('close')
if __name__=='__main__':main()
