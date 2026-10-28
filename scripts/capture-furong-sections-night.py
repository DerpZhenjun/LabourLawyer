"""Read actual guide tabs, expansions and material exemption explanations."""
import importlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong/sections-round26'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-furong-own-round26'}
def capture(name):
    page=c.evaluate(c.CAPTURE_JS);c.save(OUT/(name+'.json'),page)
    c.save(OUT/(name+'-snapshot.json'),c.browser('snapshot','-i'))
    c.browser('screenshot',str(OUT/(name+'.png')))
    return page
def main():
    if OUT.exists():raise ValueError('Preserve actual section evidence')
    OUT.mkdir()
    try:
        s=c.browser('snapshot','-i');c.save(OUT/'before.json',s)
        refs=re.findall(r'emphasis .*?\[ref=(\w+)\].*clickable',s['snapshot'])
        if len(refs)!=2:raise ValueError('Expected own two material standard expansion controls')
        for i,ref in enumerate(refs,1):c.click_material(ref);capture('material-standard-'+str(i))
        for name in ['权利与义务','结果样本','常见问题','法律依据']:
            c.browser('find','text',name,'click','--exact');capture(name)
        # The guide labels two specific materials as potentially exempt; record the actual explanation.
        s=c.browser('snapshot','-i');buttons=re.findall(r'button "该材料可免提交" \[ref=(\w+)\]',s['snapshot'])
        if len(buttons)!=2:raise ValueError('Exemption controls changed')
        c.click_material(buttons[0]);exemption=capture('identity-exemption')
        capture('final-guide')
        c.save(OUT/'manifest.json',{'at':c.NOW(),'material_expansions':2,'tabs_clicked':['权利与义务','结果样本','常见问题','法律依据'],'potential_exemption_controls':2,'state':'own_sections_captured_not_parsed_or_published','models':0,'session_left_open':True})
        print(json.dumps({'url':exemption['url'],'text':exemption['text'][-12000:]},ensure_ascii=False))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)});c.browser('close');raise
if __name__=='__main__':main()
