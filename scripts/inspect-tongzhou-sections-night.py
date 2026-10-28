"""Own-session read-only public UI inspection. Does not submit an application."""
import importlib, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
from importlib import import_module
source=import_module('capture-beijing-tongzhou-own-night').SOURCE
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-tongzhou/sections-0650'
c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-tongzhou-sections-20261024-0650'}
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=False)
    c.browser('open',source)
    c.browser('wait','--text','仲裁申请书')
    c.save(OUT/'initial-snapshot.json',c.browser('snapshot','-i'))
    c.save(OUT/'controls.json',c.evaluate("Array.from(document.querySelectorAll('a,span,div')).filter(e=>['显示更多','查看全部材料','【展开】','样例下载'].includes(e.textContent.trim())).map(e=>({tag:e.tagName,id:e.id,cls:e.className,html:e.outerHTML.slice(0,2200)}))"))
    print(json.dumps(json.loads((OUT/'controls.json').read_text(encoding='utf8')),ensure_ascii=False))
