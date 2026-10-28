"""Continue official region navigation natively; discovery is never guide coverage."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
MODE=sys.argv[1] if len(sys.argv)>1 else 'list'
OUT=ROOT/'reports/nationwide-localization-20261023-night/discovery-hunan-round27'/MODE
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-hunan-next-round27'}
def main():
    if OUT.exists():raise ValueError('Preserve official discovery evidence')
    OUT.mkdir(parents=True)
    try:
        if MODE=='list':
            source=json.loads((ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong/list-round26/dom.json').read_text('utf8'))['url']
            c.browser('open',source);c.browser('wait','--text','劳动人事争议仲裁申请')
        elif MODE=='formal-header':
            source=json.loads((ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong/formal-round26/dom.json').read_text('utf8'))['url']
            c.browser('open',source);c.browser('wait','--fn',"document.body.innerText.includes('芙蓉区人力资源和社会保障局')")
        elif MODE=='picker':
            c.browser('find','text','湖南省','click','--exact')
        elif MODE=='changsha':
            c.browser('find','text','长沙市','click','--exact')
        elif MODE=='kaifu':
            c.browser('find','text','开福区','click','--exact')
        elif MODE=='go-kaifu':
            c.browser('find','text','前往','click','--exact')
            tabs=c.browser('tab','list');c.save(OUT/'tabs.json',tabs)
            if len(tabs['tabs'])>1:c.browser('tab',tabs['tabs'][-1]['tabId'])
            c.browser('wait','--fn',"!location.href.includes('approve_id=')")
            c.browser('wait','--text','开福区')
        elif MODE=='kaifu-human-resources':
            c.browser('find','role','link','click','--name','人力资源','--exact')
            tabs=c.browser('tab','list');c.save(OUT/'tabs.json',tabs)
            if len(tabs['tabs'])>1:c.browser('tab',tabs['tabs'][-1]['tabId'])
            c.browser('wait','--fn','document.readyState === "complete"')
        elif MODE=='kaifu-page2':
            c.browser('find','text','2','click','--exact')
            c.browser('wait','--fn','document.readyState === "complete"')
        elif MODE=='kaifu-page2-settled':
            c.browser('wait','--fn',"Array.from(document.querySelectorAll('p')).some(p=>p.innerText.includes('仲裁'))")
        elif MODE=='kaifu-departments':
            source=json.loads((OUT.parent/'kaifu-human-resources/dom.json').read_text('utf8'))['url']
            c.browser('open',source);c.browser('wait','--text','按服务部门')
            c.browser('find','text','按服务部门','click','--exact');c.browser('wait','1000')
        elif MODE=='kaifu-search-short':
            snap=c.browser('snapshot','-i');ref=re.search(r'textbox "请输入关键字" \[ref=(\w+)\]',snap['snapshot']);assert ref
            c.browser('fill','@'+ref[1],'劳动仲裁');c.browser('click','.filter-right .btn-click');c.browser('wait','1500')
        elif MODE=='kaifu-search-full':
            snap=c.browser('snapshot','-i');ref=re.search(r'textbox "请输入关键字" \[ref=(\w+)\]',snap['snapshot']);assert ref
            c.browser('fill','@'+ref[1],'劳动人事争议仲裁');c.browser('click','.filter-right .btn-click');c.browser('wait','1500')
        elif MODE=='kaifu-all-topics':
            c.browser('find','role','link','click','--name','全部','--exact');c.browser('wait','1500')
        else:raise ValueError('Unobserved navigation mode')
        page=c.evaluate(c.CAPTURE_JS);snap=c.browser('snapshot','-i')
        c.save(OUT/'dom.json',page);c.save(OUT/'snapshot.json',snap);c.browser('screenshot',str(OUT/'page.png'))
        c.save(OUT/'manifest.json',{'at':c.NOW(),'url':page['url'],'title':page['title'],'state':'navigation_only_not_own_guide','models':0,'session_left_open':True})
        print(json.dumps({'url':page['url'],'snapshot':snap['snapshot'][:15000]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.browser('close');raise
if __name__=='__main__':main()
