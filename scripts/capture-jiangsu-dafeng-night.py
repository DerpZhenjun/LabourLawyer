"""Own Dafeng source discovered on official-domain search, actual browser capture."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'
URL='https://www.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?iddept_ql_inf=11320982553776482X4002014302002&iddept_yw_inf=11320982553776482X400201430200201&webId=94'


def main():
    if OUT.exists():raise ValueError('Do not replace existing own capture')
    OUT.mkdir();c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-dafeng-own-20261024-0341'}
    try:
        try:c.browser('open',URL)
        except RuntimeError as exc:
            raw=c.evaluate(c.CAPTURE_JS);c.save(OUT/'navigation-timeout.json',{'reason':str(exc),'page':raw})
            if raw['url']!=URL or '盐城市大丰区人力资源和社会保障局' not in raw['text']:raise
        c.browser('set','viewport','1440','1000');c.browser('wait','--text','劳动人事争议仲裁申请')
        first=c.evaluate(c.CAPTURE_JS);c.save(OUT/'formal-guide.json',first)
        identity=c.evaluate('({url:location.href,header:document.querySelector(".area_local")?.innerText,at:new Date().toISOString()})')
        c.save(OUT/'identity.json',identity)
        if ('大丰区' not in identity.get('header','') or '盐城市大丰区人力资源和社会保障局' not in first['text']
                or '11320982553776482X400201430200201' not in first['text']):raise ValueError('Own county/task identity not verified')
        snapshot=c.browser('snapshot','-i')['snapshot'];c.save(OUT/'snapshot.json',snapshot)
        sections=re.findall(r'link "(基本信息|部门信息|窗口办理|受理标准|办理材料|办理流程|办理时限|收费情况|办理结果|法律依据|常见问题|咨询投诉)" \[ref=(\w+)\]',snapshot)
        for name,ref in sections:c.browser('click','@'+ref)
        details=re.findall(r'cell "查看更多" \[ref=(\w+)\]',c.browser('snapshot','-i')['snapshot'])
        for index,ref in enumerate(details,1):
            c.browser('click','@'+ref);c.browser('wait','--text','办理材料详情')
            c.save(OUT/f'material-{index}.json',c.evaluate(c.CAPTURE_JS));c.browser('screenshot',str(OUT/f'material-{index}.png'))
            current=c.browser('snapshot','-i')['snapshot']
            close=re.search(r'cell "查看更多 办理材料详情"[^\n]*\n\s+- link \[ref=(\w+)\]',current)
            if not close:raise ValueError('Own visible material dialog close not found')
            c.browser('click','@'+close[1])
        final=c.evaluate(c.CAPTURE_JS);c.save(OUT/'formal-guide-final.json',final)
        c.browser('screenshot',str(OUT/'formal-guide.png'))
        result={'province':'jiangsu','city':'盐城市','district':'大丰区','region_code':'320904',
            'source_url':URL,'discovery_keyword':'劳动仲裁 办事指南 申请书 证据清单 区 人社局 下载 site:gov.cn',
            'discovery':'Official-domain search result, then own actual formal guide opened, no copied neighbour rules',
            'captured_at':final['captured_at'],'sections_clicked':[name for name,_ in sections],
            'material_dialogs_opened':len(details),'capture_file':'formal-guide-final.json',
            'capture_sha256':hashlib.sha256((OUT/'formal-guide-final.json').read_bytes()).hexdigest(),
            'state':'raw_browser_capture_requires_own_parser','published':False,'can_generate':False}
        c.save(OUT/'capture-manifest.json',result);print(json.dumps(result,ensure_ascii=False),flush=True)
    except Exception as exc:
        c.save(OUT/'failure.json',{'at':c.NOW(),'reason':str(exc)})
        c.save(OUT/'actual-page.json',c.evaluate(c.CAPTURE_JS));c.browser('screenshot',str(OUT/'failure.png'))
        print('Own capture pending: '+str(exc),flush=True)
    finally:c.browser('close')


if __name__=='__main__':main()
