"""Independently inspect Dongcheng's public official source and controls."""
import hashlib,importlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110101000000/63fb2f78-f61a-434e-a834-ac398cd29417.html?locationCode=110101000000'
MODE=sys.argv[1] if len(sys.argv)>1 else 'formal'
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-dongcheng'/('capture-'+MODE+'-round28')
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-dongcheng-own-round28'}
def capture(name):
    page=c.evaluate(c.CAPTURE_JS);c.save(OUT/(name+'.json'),page);c.save(OUT/(name+'-snapshot.json'),c.browser('snapshot','-i'));return page
def snap():return c.browser('snapshot','-i')['snapshot']
def click_name(name):
    m=re.search(r'(?:link|generic) "'+re.escape(name)+r'" \[ref=(\w+)\]',snap());assert m,'Own control missing '+name
    c.browser('click','@'+m[1])
def expand():
    for _ in range(25):
        m=re.search(r'generic "【展开】" \[ref=(\w+)\]',snap())
        if not m:return
        c.browser('click','@'+m[1])
    raise ValueError('Unexpected repeated expansion')
def main():
    if OUT.exists():raise ValueError('Preserve own capture evidence')
    OUT.mkdir(parents=True)
    try:
        if MODE=='formal':
            c.browser('open',SOURCE);c.browser('wait','--text','北京市东城区人力资源和社会保障局')
            page=capture('page');c.browser('screenshot',str(OUT/'page.png'))
            print(json.dumps({'url':page['url'],'title':page['title'],'text':page['text'][:14000],'snapshot':snap()[:6000]},ensure_ascii=False))
        elif MODE in {'sections','remaining'}:
            if MODE=='remaining':
                previous=OUT.parent/'capture-sections-round28';reused=[]
                for name in [f'section-{i}.json' for i in range(7)]+['basic-expanded.json']:
                    p=previous/name;shutil.copyfile(p,OUT/name);reused.append({'source':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
                c.save(OUT/'reused-own-captures.json',reused)
                c.browser('open',SOURCE);c.browser('set','viewport','1920','1080');c.browser('wait','--text','北京市东城区人力资源和社会保障局')
            else:
                for i,name in enumerate(['基本信息','申请材料','办理流程','结果名称及样本','设定依据','收费依据及标准','常见问题']):
                    click_name(name);capture('section-'+str(i))
                click_name('基本信息');c.browser('click','.more:not(._hidden)');capture('basic-expanded')
            c.browser('press','Control+Home');c.browser('screenshot',str(OUT/'own-heading.png'))
            click_name('申请材料');c.browser('click','a.lookall');expand();capture('materials-final')
            c.browser('screenshot',str(OUT/'materials.png'))
            refs=re.findall(r'link "样例下载" \[ref=(\w+)\]',snap());assert len(refs)==3
            for i in range(3):
                refs=re.findall(r'link "样例下载" \[ref=(\w+)\]',snap());c.browser('click','@'+refs[i]);c.save(OUT/f'sample-click-{i}.json',c.browser('tab','list'))
            c.save(OUT/'sample-controls.json',c.evaluate("Array.from(document.querySelectorAll('#apply-table a.kb')).map(e=>({text:e.textContent.trim(),html:e.outerHTML}))"))
            click_name('办理流程');expand();capture('flow-final');c.browser('screenshot',str(OUT/'flow.png'))
            capture('before-online');click_name('网上办理');c.browser('wait','--text','请选择登录')
            capture('online-after');c.browser('screenshot',str(OUT/'online-boundary.png'))
            print(json.dumps({'sections':7,'samples':3,'online':'login_choice_only','models':0}))
            c.browser('close')
        else:raise ValueError('Unknown observed workflow')
    except Exception as exc:
        r=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,timeout=45)
        (OUT/'doctor.log').write_bytes(r.stdout+b'\n'+r.stderr);c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        try:capture('failure-state');c.browser('screenshot',str(OUT/'failure.png'))
        finally:c.browser('close')
        raise
if __name__=='__main__':main()
