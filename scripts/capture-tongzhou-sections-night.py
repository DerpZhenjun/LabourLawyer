"""Capture observed Tongzhou guide tabs and material controls natively."""
import importlib,json,os,re,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-tongzhou/sections-0650'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-tongzhou-sections-20261024-0650'}
def capture(name):
    c.save(OUT/(name+'.json'),c.evaluate(c.CAPTURE_JS))
    c.save(OUT/(name+'-snapshot.json'),c.browser('snapshot','-i'))
def click_name(name):
    snap=c.browser('snapshot','-i')['snapshot']
    m=re.search(r'(?:link|generic) "'+re.escape(name)+r'" \[ref=(\w+)\]',snap)
    if not m:raise ValueError('Missing actual control '+name)
    c.browser('click','@'+m[1])
if __name__=='__main__':
    try:
        for i,name in enumerate(['基本信息','申请材料','办理流程','结果名称及样本','设定依据','收费依据及标准','常见问题']):
            click_name(name);capture('section-'+str(i))
        click_name('基本信息');c.browser('click','.more:not(._hidden)');capture('basic-expanded')
        c.browser('screenshot',str(OUT/'basic-expanded.png'))
        click_name('申请材料');c.browser('click','a.lookall');capture('materials-all')
        print(c.browser('snapshot','-i')['snapshot'],flush=True)
        c.browser('screenshot',str(OUT/'materials-all.png'))
    except Exception:
        run=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(run.stdout+b'\n'+run.stderr)
        capture('unexpected-state');raise
