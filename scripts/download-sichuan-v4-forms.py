"""Actual own official sample controls -> browser downloads, no inferred endpoint."""
import argparse
import hashlib
import importlib
import json
import os
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'backend'))
c=importlib.import_module('collect-chengdu-districts')
from regional_guides import now


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve()
    base=ROOT/'reports/nationwide-localization-20261023-night'
    if not out.is_relative_to((base/'batches').resolve()) or out.exists():raise ValueError('Fresh own night batch required')
    out.mkdir(parents=True);c.OUT=out
    c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-v4-own-form-downloads-20261024-0215'}
    checks=[]
    try:
        for code in ['510704000000','510723000000']:
            folder=out/code;folder.mkdir()
            guide=json.loads((base/'batches/v4-guides-0205/guides'/code/'guide.json').read_text('utf8'))
            target=next(t for t in guide['templates'] if t['original_name']=='仲裁申请书(模板).docx')
            try:
                manifest=json.loads((base/'sichuan/v4/captures'/code/'manifest.json').read_text('utf8'))
                c.browser('open',manifest['summary_url']);c.browser('set','viewport','1440','1000')
                c.browser('wait','--text','劳动人事争议仲裁申请')
                snapshot=c.browser('snapshot','-i')['snapshot']
                line=next(line for line in snapshot.splitlines() if 'link "进入详细指南"' in line)
                c.browser('click','@'+re.search(r'ref=(\w+)',line).group(1))
                c.browser('wait','--text','进入简版指南')
                c.browser('wait','--fn','document.querySelector("#cityName")?.textContent.trim()==='+json.dumps(guide['district']))
                c.browser('wait','--fn','document.querySelectorAll(".content3_text_all>.content3_text").length===8')
                c.browser('wait','--fn','typeof jQuery === "undefined" || jQuery.active === 0')
                c.browser('click','.content3 .content3_title_list li:nth-child(2)')
                c.browser('wait','--text','材料必要性')
                observed=c.evaluate('({url:location.href,at:new Date().toISOString(),header:document.querySelector("#cityName")?.textContent.trim(),rows:Array.from(document.querySelectorAll("#material .tr_content")).map(r=>({id:r.id,cells:Array.from(r.querySelectorAll(":scope>td")).map(t=>t.innerText)})),handler:typeof downloadAnnexFile==="function"?downloadAnnexFile.toString():null})')
                assert observed['url']==guide['source_url'] and observed['header']==guide['district']
                row=next(r for r in observed['rows'] if r['cells'][1].strip()=='劳动人事争议仲裁申请书')
                assert re.fullmatch(r'mat_\d+',row['id'])
                c.save(folder/'material-controls.json',observed)
                c.browser('click','#'+row['id']+' .biao2')
                c.browser('wait','--text','仲裁申请书(模板).docx')
                popup=c.evaluate('Array.from(document.querySelectorAll(".material_example")).filter(e=>getComputedStyle(e).display!=="none").map(e=>({text:e.innerText,links:Array.from(e.querySelectorAll("a[onclick]")).map(a=>({text:a.innerText,handler:a.getAttribute("onclick")}))}))')
                assert len(popup)==1
                assert popup[0]['links']==[{'text':'下载','handler':"downloadAnnexFile('"+target['id']+"');"}] or popup[0]['links']==[{'text':'下载','handler':"downloadAnnexFile('"+target['id']+"')"}]
                c.save(folder/'actual-sample-popup.json',popup)
                snapshot=c.browser('snapshot','-i')['snapshot'];c.save(folder/'snapshot.json',{'snapshot':snapshot})
                c.browser('screenshot',str(folder/'official-sample-popup.png'))
                # The page also has a different "download guide" header action.
                # Match this exact observed annex handler, not first/last label.
                handler=popup[0]['links'][0]['handler']
                selector='a[onclick='+json.dumps(handler)+']'
                count=c.browser('get','count',selector)
                c.save(folder/'download-control-count.json',count)
                if count.get('count')!=1:raise ValueError('该附件下载控件不唯一：'+str(count))
                relative=Path('templates/_docx/_regional')/code/(target['id']+'-'+target['original_name'])
                file=ROOT/relative
                if file.exists():raise ValueError('Existing own annex preserved; review separately')
                file.parent.mkdir(parents=True,exist_ok=True)
                response=c.browser('download',selector,str(file))
                c.save(folder/'download-response.json',response)
                network=c.browser('network','requests');c.save(folder/'download-network.json',network)
                body=file.read_bytes()
                if not body.startswith(b'PK'):raise ValueError('Downloaded bytes are not DOCX ZIP')
                result={**target,'file':relative.as_posix(),'sha256':hashlib.sha256(body).hexdigest(),
                        'bytes':len(body),'download_status':'downloaded','downloaded_at':now(),
                        'download_evidence':str((folder/'download-response.json').relative_to(ROOT)),
                        'network_evidence':str((folder/'download-network.json').relative_to(ROOT)),
                        'popup_evidence':str((folder/'actual-sample-popup.json').relative_to(ROOT)),
                        'source_url':guide['source_url'],'generation_enabled':False}
                c.save(folder/'downloaded-template.json',result)
                checks.append({'code':code,'passed':True,'sha256':result['sha256'],'file':result['file']})
                print(json.dumps(checks[-1],ensure_ascii=False),flush=True)
            except Exception as exc:
                c.save(folder/'failure.json',{'reason':str(exc),'at':now()})
                c.save(folder/'actual-page.json',c.evaluate(c.CAPTURE_JS))
                c.save(folder/'actual-network.json',c.browser('network','requests'))
                c.browser('screenshot',str(folder/'failure.png'))
                checks.append({'code':code,'passed':False,'reason':str(exc)})
                print(json.dumps(checks[-1],ensure_ascii=False),flush=True)
    finally:
        c.save(out/'result.json',{'at':now(),'checks':checks,'model_calls':0,'submitted':False})
        c.browser('close')


if __name__=='__main__':main()
