"""Finish the actual county chooser and inspect its own formal guide in one session."""
import argparse,hashlib,importlib,json,os,re,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'
OUT=BASE/'formal-0510'

def open_observed_own_guide(url):
    try:c.browser('open',url)
    except RuntimeError as exc:
        # Official long-lived resources can outlast navigation's load wait.
        # Accept only the already observed exact URL and complete own authority.
        doctor=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
        (OUT/'open-timeout-doctor.log').write_text(doctor.stdout+'\n'+doctor.stderr,encoding='utf8')
        actual=c.evaluate(c.CAPTURE_JS)
        c.save(OUT/'open-timeout-actual.json',{'reason':str(exc),'page':actual})
        if actual['url']!=url or '海州区人力资源和社会保障局' not in actual['text'] or '业务办理项编码' not in actual['text']:raise

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--iteration',default='formal-0510');parser.add_argument('--saved-guide',action='store_true');args=parser.parse_args()
    if not re.fullmatch(r'formal-[a-z0-9-]+',args.iteration):raise ValueError('Invalid own iteration')
    OUT=BASE/args.iteration
    if OUT.exists():raise ValueError('Preserve successful own formal guide capture')
    search=json.loads((BASE/'result-0505/dom.json').read_text(encoding='utf8'))['url']
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-haizhou-formal-20261024-0510'}
    try:
        if args.saved_guide:
            known=json.loads((BASE/'formal-0515/actual-failure-page.json').read_text(encoding='utf8'))
            if urlsplit(known['url']).hostname!='lyghz.jszwfw.gov.cn':raise ValueError('Saved own navigation not county portal')
            open_observed_own_guide(known['url'])
        else:
            c.browser('open',search);c.browser('wait','--text','当前搜索范围：海州区')
            c.browser('click','span.matter_button[data-basecode="002014302002"]')
            c.browser('wait','--text','选择办理地点')
            choice=c.evaluate(c.CAPTURE_JS);c.save(OUT/'chooser.json',choice)
            if '海州区' not in choice['text']:raise ValueError('County chooser identity missing')
            c.browser('screenshot',str(OUT/'chooser.png'))
            c.browser('click','.tck_bottom .sure.right')
            tabs=c.browser('tab');c.save(OUT/'after-confirm-tabs.json',tabs)
            candidates=[t for t in tabs['tabs'] if t['url']!=search and (urlsplit(t['url']).hostname or '').endswith('.jszwfw.gov.cn')]
            if candidates:c.browser('tab',candidates[-1]['tabId'])
            c.browser('wait','--fn','location.href !== '+json.dumps(search)+' && document.body !== null')
        c.browser('wait','--text','办理材料')
        first=c.evaluate(c.CAPTURE_JS);c.save(OUT/'initial-guide.json',first)
        if (not (urlsplit(first['url']).hostname or '').endswith('.jszwfw.gov.cn')
            or '海州区人力资源和社会保障局' not in first['text']
            or '劳动人事争议仲裁申请' not in first['text']):raise ValueError('Resolved guide is not this county authority and item')
        snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'initial-snapshot.json',snapshot)
        sections=re.findall(r'link "(基本信息|部门信息|窗口办理|受理标准|办理材料|办理流程|办理时限|收费情况|办理结果|法律依据|常见问题|咨询投诉)" \[ref=(\w+)\]',snapshot)
        for name,ref in sections:c.browser('click','@'+ref)
        details=re.findall(r'cell "查看更多" \[ref=(\w+)\]',c.browser('snapshot','-i')['snapshot'])
        for index,ref in enumerate(details,1):
            c.browser('click','@'+ref);c.browser('wait','--text','办理材料详情')
            c.save(OUT/f'material-{index}.json',c.evaluate(c.CAPTURE_JS));c.browser('screenshot',str(OUT/f'material-{index}.png'))
            current=c.browser('snapshot','-i')['snapshot']
            close=re.search(r'cell "查看更多 办理材料详情"[^\n]*\n\s+- link \[ref=(\w+)\]',current)
            if not close:raise ValueError('Observed material close control missing')
            c.browser('click','@'+close[1])
        final=c.evaluate(c.CAPTURE_JS);c.save(OUT/'formal-guide-final.json',final)
        c.browser('screenshot',str(OUT/'formal-guide.png'))
        c.save(OUT/'manifest.json',{'source_url':final['url'],'province':'jiangsu','city':'连云港市','district':'海州区',
            'captured_at':final['captured_at'],'sections_clicked':[n for n,_ in sections],'material_dialogs':len(details),
            'capture_sha256':hashlib.sha256((OUT/'formal-guide-final.json').read_bytes()).hexdigest(),
            'state':'own_raw_formal_guide_requires_original_downloads_and_parser','published':False,'models':0,
            'note':'Official search page shows an automatic AI summary. It is not used as evidence; only formal guide sections collected.'})
        print(json.dumps({'url':final['url'],'sections':len(sections),'materials':len(details),'text':final['text'][:4500]},ensure_ascii=True))
    except Exception as exc:
        c.save(OUT/'failure.json',{'reason':str(exc),'at':c.NOW(),'guide_verified':False})
        # Diagnose unexpected CLI failures before any further browser command.
        doctor=subprocess.run([c.CLI,'doctor','--offline','--quick'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
        (OUT/'doctor.log').write_text(doctor.stdout+'\n'+doctor.stderr,encoding='utf8')
        c.save(OUT/'failed-tabs.json',c.browser('tab'))
        c.save(OUT/'actual-failure-page.json',c.evaluate(c.CAPTURE_JS))
        c.browser('screenshot',str(OUT/'actual-failure.png'))
        print('Saved pending own navigation: '+str(exc))
        raise
    finally:c.browser('close')

if __name__=='__main__':main()
