"""Observe own guide header/flow and public original template/sample controls."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
MODE=sys.argv[1];assert MODE in {'top-flow','template','sample','flow-recovery'}
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong'/('control-'+MODE+'-round26')
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-furong-own-round26'}
def capture(name):
    p=c.evaluate(c.CAPTURE_JS);c.save(OUT/(name+'.json'),p);c.save(OUT/(name+'-snapshot.json'),c.browser('snapshot','-i'))
    c.browser('screenshot',str(OUT/(name+'.png')));return p
def main():
    if OUT.exists():raise ValueError('Preserve actual control evidence')
    OUT.mkdir()
    try:
        tabs=c.browser('tab','list');guide=next((t for t in tabs['tabs'] if 'approve_id=0661f202529745928ad2d4bc532e233a' in t['url']),None)
        if guide is None:
            source=json.loads((OUT.parent/'formal-round26/dom.json').read_text('utf8'))['url']
            c.browser('open',source)
            c.browser('wait','--fn',"document.body.innerText.includes('芙蓉区人力资源和社会保障局')")
            guide=next(t for t in c.browser('tab','list')['tabs'] if 'approve_id=0661f202529745928ad2d4bc532e233a' in t['url'])
        c.browser('tab',guide['tabId'])
        if MODE in {'top-flow','flow-recovery'}:
            c.browser('press','Control+Home');c.browser('wait','--text','芙蓉区人力资源和社会保障局')
            page=capture('stable-header');print(json.dumps({'text':page['text'][:1800]},ensure_ascii=False),flush=True)
            if MODE=='flow-recovery':
                # Scoped CSS was observed in the failed run's saved public DOM; use a native click.
                c.browser('scrollintoview','.guide-img-container .toggle-btn')
                c.browser('click','.guide-img-container .toggle-btn')
            else:c.browser('find','text','展开全部','click','--exact')
            page=capture('flow-expanded')
        else:
            label='模板' if MODE=='template' else '示例'
            s=c.browser('snapshot','-i');ref=re.search(r'generic "'+label+r'" \[ref=(\w+)\]',s['snapshot'])
            if not ref:raise ValueError('Own material control not visible')
            c.save(OUT/'before-snapshot.json',s);c.click_material(ref[1])
            c.save(OUT/'tabs-after-click.json',c.browser('tab','list'));page=capture('after-click')
        c.save(OUT/'manifest.json',{'at':c.NOW(),'mode':MODE,'actual_url':page['url'],'state':'public_control_only_not_downloaded_or_classified','models':0})
        print(json.dumps({'url':page['url'],'text':page['text'][-5000:],'frames':c.evaluate("Array.from(document.querySelectorAll('iframe')).map(f=>({src:f.src,title:f.title}))")},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});c.browser('close');raise
if __name__=='__main__':main()
