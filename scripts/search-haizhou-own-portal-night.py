"""Native search from the observed county portal textbox; no invented item URL."""
import importlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'
OUT=BASE/'search-0502'

def main():
    if OUT.exists():raise ValueError('Preserve actual search evidence')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-haizhou-search-20261024-0502'}
    try:
        c.browser('open','https://lyghz.jszwfw.gov.cn/')
        snap=c.browser('snapshot','-i');c.save(OUT/'before.json',snap)
        refs=snap.get('refs',{})
        search=next((k for k,v in refs.items() if v['role']=='button' and v.get('name','').replace(' ','')=='搜索'),None)
        state=c.evaluate("Array.from(document.querySelectorAll('input')).filter(e=>e.getBoundingClientRect().height>0).map(e=>({id:e.id,value:e.value}))")
        box=next((i for i in state if i['value']=='请输入要办理的事项名称'),None)
        if not search or not box or not box['id']:raise ValueError('Observed own search controls changed')
        keyword='劳动人事争议仲裁申请'
        c.browser('fill','#'+box['id'],keyword);c.browser('click','@'+search)
        tabs=c.browser('tab');c.save(OUT/'tabs.json',tabs)
        page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'active-dom.json',page)
        c.save(OUT/'after.json',c.browser('snapshot','-i'));c.browser('screenshot',str(OUT/'active.png'))
        c.save(OUT/'status.json',{'keyword':keyword,'actual_active_url':page['url'],'actual_title':page['title'],
            'captured_at':page['captured_at'],'guide_verified':False,'published':False,'models':0,
            'note':'Native county search clicked; determine actual result tab and locality before treating any item as a county guide.'})
        print(json.dumps({'tabs':tabs,'active_url':page['url'],'title':page['title'],'text':page['text'][:5000]},ensure_ascii=True))
    finally:c.browser('close')

if __name__=='__main__':main()
