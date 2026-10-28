"""Resume remaining native controls at wider viewport; retain successful captures."""
import hashlib,importlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
m=importlib.import_module('capture-chaoyang-sections-night');c=m.c
OLD=m.OUT;m.OUT=OLD.parent/'sections-round23-resumed';c.OUT=m.OUT
def main():
    if m.OUT.exists():raise ValueError('Preserve resumed capture')
    m.OUT.mkdir();reused=[]
    for name in [f'section-{i}.json' for i in range(7)]+['basic-expanded.json']:
        p=OLD/name;q=m.OUT/name;shutil.copyfile(p,q)
        reused.append({'original':p.relative_to(ROOT).as_posix(),'copy':q.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    c.save(m.OUT/'reused-captures.json',reused)
    try:
        c.browser('open',m.SOURCE);c.browser('set','viewport','1920','1080')
        c.browser('wait','--text','北京市朝阳区人力资源和社会保障局')
        c.browser('screenshot',str(m.OUT/'own-heading.png'))
        m.click_name('申请材料');c.browser('click','a.lookall');m.expand_visible();m.capture('materials-final')
        c.browser('screenshot',str(m.OUT/'materials.png'))
        for i in range(3):
            import re
            refs=re.findall(r'link "样例下载" \[ref=(\w+)\]',m.snap())
            r=c.browser('click','@'+refs[i]);c.save(m.OUT/f'sample-click-{i}.json',{'at':c.NOW(),'clicked':r,'tabs':c.browser('tab','list')})
        c.save(m.OUT/'sample-click-errors.json',c.browser('errors'))
        c.save(m.OUT/'sample-controls.json',c.evaluate("Array.from(document.querySelectorAll('#apply-table a.kb')).map(e=>({text:e.textContent.trim(),html:e.outerHTML}))"))
        m.click_name('办理流程');m.expand_visible();m.capture('flow-final');c.browser('screenshot',str(m.OUT/'flow.png'))
        c.save(m.OUT/'before-online.json',c.evaluate(c.CAPTURE_JS));m.click_name('网上办理')
        c.browser('wait','--text','请选择登录');m.capture('online-after');c.browser('screenshot',str(m.OUT/'online-boundary.png'))
        print(json.dumps({'reused_successful_captures':len(reused),'remaining_native_controls':'complete','models':0}))
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (m.OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(m.OUT/'failure.json',{'reason':str(exc),'at':c.NOW()});m.capture('failed-state');raise
    finally:c.browser('close')
if __name__=='__main__':main()
