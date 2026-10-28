"""Native public Chaoyang guide controls; no application submission or login."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
from importlib import import_module
SOURCE=import_module('capture-beijing-chaoyang-own-night').SOURCE
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-chaoyang/sections-round23'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-chaoyang-round23-20261024'}
def snap():return c.browser('snapshot','-i')['snapshot']
def capture(name):
    c.save(OUT/(name+'.json'),c.evaluate(c.CAPTURE_JS));c.save(OUT/(name+'-snapshot.json'),c.browser('snapshot','-i'))
def click_name(name):
    m=re.search(r'(?:link|generic) "'+re.escape(name)+r'" \[ref=(\w+)\]',snap())
    if not m:raise ValueError('Own control missing '+name)
    c.browser('click','@'+m[1])
def expand_visible():
    while True:
        m=re.search(r'generic "【展开】" \[ref=(\w+)\]',snap())
        if not m:break
        c.browser('click','@'+m[1])
def main():
    if OUT.exists():raise ValueError('Preserve completed own capture')
    OUT.mkdir(parents=True)
    try:
        c.browser('open',SOURCE);c.browser('wait','--text','北京市朝阳区人力资源和社会保障局')
        for i,name in enumerate(['基本信息','申请材料','办理流程','结果名称及样本','设定依据','收费依据及标准','常见问题']):
            click_name(name);capture('section-'+str(i))
        click_name('基本信息');c.browser('click','.more:not(._hidden)');capture('basic-expanded')
        c.browser('scroll','up','3000');c.browser('screenshot',str(OUT/'own-heading.png'))
        click_name('申请材料');c.browser('click','a.lookall');expand_visible();capture('materials-final')
        c.browser('screenshot',str(OUT/'materials.png'))
        for i in range(3):
            refs=re.findall(r'link "样例下载" \[ref=(\w+)\]',snap());c.browser('click','@'+refs[i])
            c.save(OUT/f'sample-click-{i}.json',{'at':c.NOW(),'result':c.browser('tab','list')})
        c.save(OUT/'sample-click-errors.json',c.browser('errors'))
        c.save(OUT/'sample-controls.json',c.evaluate("Array.from(document.querySelectorAll('#apply-table a.kb')).map(e=>({text:e.textContent.trim(),html:e.outerHTML}))"))
        click_name('办理流程');expand_visible();capture('flow-final');c.browser('screenshot',str(OUT/'flow.png'))
        c.save(OUT/'before-online.json',c.evaluate(c.CAPTURE_JS));click_name('网上办理')
        c.browser('wait','--text','请选择登录');capture('online-after');c.browser('screenshot',str(OUT/'online-boundary.png'))
        print(json.dumps({'sections':7,'materials':3,'own_online_state':'login_choice_only','models':0}))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        capture('failed-state');raise
    finally:c.browser('close')
if __name__=='__main__':main()
