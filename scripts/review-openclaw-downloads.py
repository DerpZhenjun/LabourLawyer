"""Inspect real downloads before counting them as document templates.

Run with the bundled artifact Python. Files and decisions stay on D drive.
PDF opinions come through OpenClaw / Ubuntu; they do not enable fill adapters.
"""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys,time,zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from openclaw_browser_tasks import TASK_ROOT,save,MODEL,SERVER,HIDDEN
from template_acquisition.openclaw_bridge import describe_image
REVIEW_VERSION=2

def classify_word_text(text):
    compact=re.sub(r'\s+','',text)
    if '服务指南' in compact[:150] and re.search('适用范围|事项代码|受理机构',compact):
        return {'kind':'service_guide','reason':'Word begins with a service-guide title and contains guide sections; appended application forms do not make the whole file a blank form'}
    if '文书参考模板目录' in compact[:150]:
        return {'kind':'other','form_state':'reference_bundle','reason':'File is a reference bundle containing multiple documents and examples, not a standalone blank application'}
    if '申请书' in compact and all(word in compact for word in ('申请人','请求','事实')):
        example=bool(re.search('样本|样表|示样|所填写内容仅供参考',compact[:160]) or re.search(r'申请人[：:].{0,10}[\u4e00-\u9fff][X×某]',compact[:400]))
        return {'kind':'application_form','form_state':'filled_example' if example else 'unfilled_or_not_confirmed','reason':'Word contains application parties, requests and facts fields'+('; observed example content remains in the file' if example else '')}
    if re.search('证据清单|证据目录',compact) and re.search('证明|目的',compact):return {'kind':'evidence_list','reason':'Word contains evidence headings and proof-purpose fields'}
    return {'kind':'uncertain','reason':'No confirmed standalone form or guide structure'}

def inspect_download(folder,entry):
    path=(folder/entry['file']).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():return {'kind':'uncertain','reason':'Missing evidence file'}
    digest=hashlib.sha256(path.read_bytes()).hexdigest();output=(folder/'download-reviews'/digest[:16]).resolve();output.mkdir(parents=True,exist_ok=True)
    cached=output/'review.json'
    if cached.exists():
        previous=json.loads(cached.read_text(encoding='utf8'))
        if previous.get('kind')!='uncertain' and previous.get('review_version')==REVIEW_VERSION:return previous
        cached.rename(output/('review-previous-'+str(time.time_ns())+'.json'))
    review={'kind':'uncertain','sha256':digest,'file':entry['file'],'fill_verified':False,'review_version':REVIEW_VERSION}
    if path.suffix.lower() in ('.docx','.doc'):
        if path.suffix.lower()=='.doc':
            text_path=output/'word-text.txt';pdf=output/'reference.pdf'
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/inspect-legacy-word.ps1'),'-Source',str(path),'-Text',str(text_path),'-Pdf',str(pdf)],check=True,capture_output=True,timeout=60,creationflags=HIDDEN)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Original Word changed during read-only inspection')
            text=text_path.read_text(encoding='utf-8-sig');review['reference_pdf']=str(pdf.relative_to(folder.resolve()))
        else:
            with zipfile.ZipFile(path) as archive:
                if archive.getinfo('word/document.xml').file_size>5000000:raise ValueError('Document XML too large')
                xml=ElementTree.fromstring(archive.read('word/document.xml'))
                text=''.join(node.text or '' for node in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        review.update(classify_word_text(text))
        review['text_excerpt']=text[:1200]
    elif path.suffix.lower()=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(str(path));review['pages']=len(reader.pages)
        spec=importlib.util.spec_from_file_location('renderer',ROOT/'scripts/validate_acquired_templates.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
        subprocess.run([str(renderer.PDFTOPPM),'-f','1','-l',str(min(2,len(reader.pages))),'-r','110','-png',str(path),str(output/'page')],check=True,timeout=40,creationflags=HIDDEN)
        images=sorted(output.glob('page-*.png'))
        prompt='核对实际下载文件，而不是按钮附近的材料名称。只返回JSON对象：{"kind":"application_form|evidence_list|service_guide|other|uncertain","reason":"截图中支持分类的内容","workflow_candidates":["实际可见的流程环节原文"]}。application_form必须是申请书表格本身；evidence_list必须是证据清单表格本身。包含事项编码、办理地址、材料表和流程图的整个办事指南属于service_guide，不能算证据清单模板。看不清请返回uncertain。流程只抄可见节点，不推断次序、分支或法律结论；不会直接用于前端。'
        raw=describe_image(images,output/'openclaw-raw.json',output/'openclaw',timeout_seconds=180,prompt=prompt,role='download_content_verification',base_url=SERVER)
        payload=json.loads(raw.read_text(encoding='utf8'));answer='\n'.join(o.get('text','') for o in payload['result'].get('outputs',[]))
        result=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',answer.strip()))
        if result.get('kind') not in ('application_form','evidence_list','service_guide','other','uncertain'):raise ValueError('Unexpected PDF classification')
        review.update(kind=result['kind'],reason=str(result.get('reason',''))[:600],workflow_candidates=result.get('workflow_candidates',[])[:20],model=MODEL,model_server=SERVER)
    save(cached,review);return review

def review_task(folder):
    path=folder/'task.json';task=json.loads(path.read_text(encoding='utf8'));guide=task.get('selected_guide')
    if not guide:return task
    if not (folder/'task-before-download-review.json').exists():save(folder/'task-before-download-review.json',task)
    templates=[];documents=[];pending=[]
    # Retry inconclusive downloads while reusing successful content reviews.
    entries=guide.get('templates',[])+guide.get('supporting_documents',[])
    seen=set()
    for entry in entries:
        key=entry.get('file') or entry.get('url') or str(entry)
        if key in seen:continue
        seen.add(key)
        if 'get-regulation-zip' in entry.get('url','') and '指南下载' in entry.get('context',''):
            entry['content_review']={'kind':'service_guide','reason':'Official guide export control; not a material template'}
            documents.append(entry);continue
        if entry.get('download_status')!='downloaded':templates.append(entry);continue
        try:review=inspect_download(folder,entry)
        except Exception as exc:review={'kind':'uncertain','reason':str(exc)[:600]}
        entry['content_review']=review
        if review.get('form_state')=='filled_example' and entry.get('kind')!='sample':
            entry['advertised_kind']=entry.get('kind');entry['kind']='sample'
            entry['content_note']='实际文件含填写示例，不是全空白表格。'
        if review['kind']=='uncertain':pending.append(entry.get('file','unknown file'))
        if review['kind'] in ('application_form','evidence_list'):templates.append(entry)
        else:documents.append(entry)
    guide['templates']=templates
    guide['supporting_documents']=documents
    guide['downloaded_files']=[{**f,'content_kind':next((t['content_review']['kind'] for t in templates+documents if t.get('sha256')==f.get('sha256')),'uncertain')} for f in guide.get('downloaded_files',[])]
    task['status']['template_downloaded']=any(t.get('content_review',{}).get('kind') in ('application_form','evidence_list') for t in templates)
    task['download_reviewed']=not pending
    task['pending_downloads']=pending
    save(path,task);save(folder/'verified-guide.json',guide)
    return task

def main(run):
    if not run.resolve().is_relative_to(TASK_ROOT.resolve()):raise ValueError('Run must stay in openclaw-tasks')
    temp=run/'temp';temp.mkdir(exist_ok=True);os.environ.update(TEMP=str(temp),TMP=str(temp))
    results=json.loads((run/'results.json').read_text(encoding='utf8'))
    for slug,task in list(results.items()):
        if task.get('state')=='acquired':results[slug]=review_task(run/slug)
        save(run/'results.json',results)
    save(run/'results.json',results)
    print(json.dumps({s:{'state':r['state'],'status':r['status']} for s,r in results.items()},ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);main(parser.parse_args().run)
