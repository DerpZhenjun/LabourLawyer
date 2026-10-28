"""Capture the existing Jiangsu source's actual locality in a real browser.

Uses an owned Agent Browser session, never logs in or submits an application.
Only staging evidence is written; this cannot publish or enable a generator.
"""
import hashlib
import json
import os
import re
from importlib import import_module
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
c=import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-xishan'
c.OUT=OUT
c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-cross-province-20261023'}


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    # The session was navigated through the actual "查看详版指南" control.
    capture=c.evaluate(c.CAPTURE_JS)
    if '11320205014038763X400201430200201' not in capture['text'] or '锡山区人力资源和社会保障局' not in capture['text']:
        raise ValueError('Not the actual Xishan formal guide; do not infer locality from old labels')
    if not (OUT/'formal-guide.json').exists():
        c.save(OUT/'formal-guide.json',capture)
    snapshot=c.browser('snapshot','-i')['snapshot']
    sections=re.findall(r'link "(基本信息|部门信息|窗口办理|受理标准|办理材料|办理流程|办理时限|收费情况|办理结果|法律依据|常见问题|咨询投诉)" \[ref=(\w+)\]',snapshot)
    for name,ref in sections:
        c.browser('click','@'+ref)
    details=re.findall(r'cell "查看更多" \[ref=(\w+)\]',c.browser('snapshot','-i')['snapshot'])
    for index,ref in enumerate(details,1):
        c.browser('click','@'+ref)
        c.browser('wait','--text','办理材料详情')
        c.save(OUT/f'material-{index}.json',c.evaluate(c.CAPTURE_JS))
        c.browser('screenshot',str((OUT/f'material-{index}.png').relative_to(ROOT)))
        # Each row has its own hidden dialog: a shared CSS class picks an old
        # invisible close control. Use the current visible dialog's actual ref.
        dialog=c.browser('snapshot','-i')['snapshot']
        close=re.search(r'cell "查看更多 办理材料详情"[^\n]*\n\s+- link \[ref=(\w+)\]',dialog)
        if not close:raise ValueError('Current visible material close control not found')
        c.browser('click','@'+close.group(1))
    c.browser('screenshot',str((OUT/'formal-guide.png').relative_to(ROOT)))
    final=c.evaluate(c.CAPTURE_JS)
    c.save(OUT/'formal-guide-final.json',final)
    c.save(OUT/'capture-manifest.json',{
        'region_code':'320205','province':'jiangsu','city':'无锡市','district':'锡山区',
        'source_url':final['url'],'captured_at':final['captured_at'],
        'sections_clicked':[name for name,_ in sections], 'material_dialogs_opened':len(details),
        'capture_file':'formal-guide-final.json',
        'capture_sha256':hashlib.sha256((OUT/'formal-guide-final.json').read_bytes()).hexdigest(),
        'status':'staged_not_published','no_login_or_submission':True})
    print(json.dumps({'sections':len(sections),'materials':len(details),'url':final['url']},ensure_ascii=False))


if __name__=='__main__':run()
