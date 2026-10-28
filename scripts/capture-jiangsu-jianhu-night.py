"""Stage Jianhu's own publicly discovered formal guide via actual browser clicks."""
import hashlib
import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu'
URL='https://ycjh.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?iddept_ql_inf=11320925014387568C4002014302002&iddept_yw_inf=11320925014387568C400201430200201&ql_kind=20&webId=99'


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args();OUT=args.output.resolve()
    if not OUT.is_relative_to((ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu').resolve()):raise ValueError('Own Jianhu evidence folder required')
    if OUT.exists():raise ValueError('Fresh own-region capture required')
    OUT.mkdir(parents=True);c.OUT=OUT
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-jianhu-official-20261024-0225'}
    try:
        try:c.browser('open',URL)
        except RuntimeError as exc:
            # Slow secondary resources may exceed navigation timeout while the
            # actual public guide is rendered. Inspect, never assume it loaded.
            actual=c.evaluate(c.CAPTURE_JS);c.save(OUT/'navigation-timeout-page.json',actual)
            if actual['url']!=URL or actual['title']!='劳动人事争议仲裁申请' or '建湖县' not in actual['text']:raise
            c.save(OUT/'navigation-recovery.json',{'reason':str(exc),'actual_url':actual['url'],'at':actual['captured_at'],'state':'actual_guide_rendered_secondary_load_incomplete'})
        c.browser('set','viewport','1440','1000')
        c.browser('wait','--text','劳动人事争议仲裁申请')
        raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'formal-guide.json',raw)
        observed=c.evaluate('({url:location.href,header:document.querySelector(".area_local")?.innerText,headings:Array.from(document.querySelectorAll("h1,h2,h3")).map(e=>e.innerText),at:new Date().toISOString()})')
        c.save(OUT/'identity.json',observed)
        if observed['url']!=URL or '建湖县' not in raw['text'] or '11320925014387568C400201430200201' not in raw['text']:
            raise ValueError('Actual formal source/locality/task identity not established')
        snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'snapshot.json',{'snapshot':snapshot})
        sections=re.findall(r'link "(基本信息|部门信息|窗口办理|受理标准|办理材料|办理流程|办理时限|收费情况|办理结果|法律依据|常见问题|咨询投诉)" \[ref=(\w+)\]',snapshot)
        for name,ref in sections:c.browser('click','@'+ref)
        details=re.findall(r'cell "查看更多" \[ref=(\w+)\]',c.browser('snapshot','-i')['snapshot'])
        for index,ref in enumerate(details,1):
            c.browser('click','@'+ref);c.browser('wait','--text','办理材料详情')
            c.save(OUT/f'material-{index}.json',c.evaluate(c.CAPTURE_JS))
            c.browser('screenshot',str(OUT/f'material-{index}.png'))
            current=c.browser('snapshot','-i')['snapshot']
            close=re.search(r'cell "查看更多 办理材料详情"[^\n]*\n\s+- link \[ref=(\w+)\]',current)
            if not close:raise ValueError('Own visible material dialog close not found')
            c.browser('click','@'+close.group(1))
        final=c.evaluate(c.CAPTURE_JS);c.save(OUT/'formal-guide-final.json',final)
        c.browser('screenshot',str(OUT/'formal-guide.png'))
        result={'province':'jiangsu','city':'盐城市','district':'建湖县','region_code':'320925',
                'source_url':URL,'discovery':'official-domain web search after browser search did not render usable results',
                'captured_at':final['captured_at'],'sections_clicked':[name for name,_ in sections],
                'material_dialogs_opened':len(details),'capture_file':'formal-guide-final.json',
                'capture_sha256':hashlib.sha256((OUT/'formal-guide-final.json').read_bytes()).hexdigest(),
                'state':'raw_browser_capture_requires_independent_parser','published':False,'generation_enabled':False,
                'no_login_or_submission':True}
        c.save(OUT/'capture-manifest.json',result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS))
        c.browser('screenshot',str(OUT/'failure.png'))
        print('Jianhu staging incomplete: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
