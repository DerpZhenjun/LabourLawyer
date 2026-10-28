"""Collect observed capital-department guides after portal recovery fails.

Native OpenClaw collects HTML, controls and screenshots. Embedded PDF URLs
come only from the captured DOM; numbered materials come only from its text.
The cached capture option resumes successful collection without revisiting it.
Run with the artifact Python (pypdf/Pillow), never starts a local model.
"""
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
from pathlib import Path
from urllib.parse import urljoin,urlsplit,parse_qs
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from openclaw_browser_tasks import BrowserLane,save,official_url
from province_experience import valid_guide,guide_belongs_to_province
from portal_workflows import section_text
HIDDEN=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

def pdf_form_reference(folder,guide,observations):
    """Retain an actual application-form page embedded in a service handbook."""
    source=folder/'source.pdf';text_path=folder/'pdf-text.json'
    if not source.is_file() or not text_path.is_file():return
    texts=json.loads(text_path.read_text('utf8'))
    index=next((i for i,t in enumerate(texts) if '仲裁申请书的格式模版' in re.sub(r'\s+','',t) and '目录' not in t[:100] and '申请人' in t and '被申请人' in t),None)
    if index is None:return
    pdf_url=next((o.get('source_pdf_url') for o in observations if o.get('source_pdf_url')),None)
    if not pdf_url:return
    stage='department-form-templates';image=folder/(stage+'.png')
    if not image.is_file():
        spec=importlib.util.spec_from_file_location('form_renderer',ROOT/'scripts/validate_acquired_templates.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
        subprocess.run([str(renderer.PDFTOPPM),'-f',str(index+1),'-l',str(index+1),'-singlefile','-r','110','-png',str(source),str(folder/stage)],check=True,timeout=30,creationflags=HIDDEN)
    (folder/(stage+'.txt')).write_text(texts[index],'utf8')
    template={'material_name':'仲裁申请书格式（官方手册PDF第'+str(index+1)+'页）','text':'官方手册内申请书格式','url':pdf_url+'#page='+str(index+1),'kind':'reference_pdf','source_pdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pdf_pages':[index+1],'content_note':'表格在PDF手册内，供下载参考；尚未适配为在线填写模板。'}
    guide['templates']=[template]
    if not any(o['stage']==stage for o in observations):observations.append({'stage':stage,'final_url':guide['guide_url'],'source_pdf_url':pdf_url,'pdf_pages':[index+1],'action':'定位官方PDF实际申请书格式页','screenshot':image.name,'screenshot_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'text_file':stage+'.txt','template_links':[template],'page_problem':None})

def numbered_materials(text):
    section=section_text(text,('申请材料','五、申请材料'),('收费依据','收费依据及标准','六、办理期限','办事时间','收费标准'))
    return [re.sub(r'^\d+[.、]\s*','',line).split('：',1)[0].rstrip('。') for line in section.splitlines() if re.match(r'^\d+[.、]',line)]

def recover(slug,run,cached=None):
    entry=json.loads((ROOT/'config/province_guide_fallbacks.json').read_text('utf8'))[slug]
    folder=run/'department-guide-recovery'/slug;folder.mkdir(parents=True,exist_ok=True)
    ready=folder/'verified-guide.json'
    if ready.is_file():
        observed=folder/'observations.json'
        if not observed.is_file():raise ValueError('Cached guide lacks observations; existing evidence retained')
        guide=json.loads(ready.read_text('utf8'));observations=json.loads(observed.read_text('utf8'))
        if not isinstance(observations,list) or not observations:raise ValueError('Cached guide has no actual observations')
        for o in observations:
            image=(folder/o.get('screenshot','')).resolve()
            if not image.is_relative_to(folder.resolve()) or not image.is_file() or hashlib.sha256(image.read_bytes()).hexdigest()!=o.get('screenshot_sha256'):
                raise ValueError('Cached guide screenshot missing or hash changed; evidence retained')
        pdf_form_reference(folder,guide,observations);save(ready,guide);save(folder/'normalized-guide.json',guide);save(folder/'observations.json',observations);return guide
    if cached:
        source=cached/slug;details=json.loads((source/'details.json').read_text('utf8'));state=json.loads((source/'state.json').read_text('utf8'))
        for f in source.iterdir():
            if f.is_file():shutil.copy2(f,folder/f.name)
    else:
        with BrowserLane(folder/'browser') as lane:
            target=lane.call('open',entry['url'])['targetId'];lane.call('resize','1440','1000','--target-id',target);lane.call('wait','--time','4500','--target-id',target)
            state=lane.snapshot(target);save(folder/'state.json',state);lane.screenshot(target,folder/'source.png')
            result=lane.call('evaluate','--target-id',target,'--fn',"() => ({text:document.body.innerText,html:document.documentElement.outerHTML,links:Array.from(document.querySelectorAll('a')).map(n=>({text:n.innerText,url:n.href}))})")
            details=result.get('result',result);save(folder/'details.json',details)
    actual=state['document']['url'];text=details['text']
    if entry['authority'] not in text or not official_url(actual):raise ValueError('Department authority/source not confirmed in captured page')
    (folder/'source.html').write_text(details['html'],'utf8');pdf_urls=[]
    from lxml import html
    tree=html.fromstring(details['html'])
    for node in tree.xpath('//embed[@src]|//iframe[@src]'):
        viewer=urljoin(actual,node.get('src'));file=parse_qs(urlsplit(viewer).query).get('file',[])
        if file:pdf_urls.append(urljoin(viewer,file[0]))
    pdf_urls += [a['url'] for a in details.get('links',[]) if '.pdf' in a['url'].lower() and re.search('劳动|仲裁|调解',a.get('text',''))]
    materials=[];pages=[];flow='';representation='not_detected';observations=[]
    if pdf_urls:
        from pypdf import PdfReader
        url=next((u for u in pdf_urls if official_url(u)),None)
        if not url:raise ValueError('No observed official PDF')
        path=folder/'source.pdf'
        if not path.is_file():
            p=subprocess.run(['curl.exe','--silent','--show-error','--location','--connect-timeout','5','--max-time','30','--max-filesize','50000000','--output',str(path),'--dump-header',str(folder/'pdf.headers'),'--write-out','%{http_code} %{url_effective}',url],capture_output=True,timeout=35,creationflags=HIDDEN)
            outcome=p.stdout.decode('utf8',errors='replace');save(folder/'pdf-request.json',{'url':url,'returncode':p.returncode,'outcome':outcome,'error':p.stderr.decode('utf8',errors='replace')})
            if p.returncode or not outcome.startswith('200 ') or not official_url(outcome.split(' ',1)[1]):raise RuntimeError('Official PDF request failed')
        if not path.read_bytes().startswith(b'%PDF-'):raise ValueError('Downloaded file is not PDF')
        texts=[p.extract_text() or '' for p in PdfReader(path).pages];save(folder/'pdf-text.json',texts)
        material_page=next((i for i,t in enumerate(texts) if ('申请材料' in t or '（一）仲裁申请书' in t or '(一)仲裁申请书' in t) and '目录' not in t[:100]),None)
        if material_page is None:raise ValueError('Actual PDF has no identifiable material page')
        materials=numbered_materials(texts[material_page])
        if not materials:
            # Multi-column booklets cannot safely be flattened into complete
            # lists. Keep literal employee material labels and the original PDF.
            compact=re.sub(r'\s+','',texts[material_page]);materials=[name for name in ('仲裁申请书','本人居民身份证复印件','授权委托书','工商行政管理部门登记的注册信息') if name in compact]
        flow_page=next((i for i,t in enumerate(texts) if '工作流程图' in t and '目录' not in t[:100]),material_page)
        representation='official_flowchart_image' if flow_page!=material_page else 'not_detected';pages=sorted({material_page+1,flow_page+1})
        spec=importlib.util.spec_from_file_location('renderer',ROOT/'scripts/validate_acquired_templates.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
        for stage,index in [('department-templates',material_page),('department-flow',flow_page)]:
            prefix=folder/stage;subprocess.run([str(renderer.PDFTOPPM),'-f',str(index+1),'-l',str(index+1),'-singlefile','-r','110','-png',str(path),str(prefix)],check=True,timeout=30,creationflags=HIDDEN)
            (folder/(stage+'.txt')).write_text(texts[index],'utf8');observations.append({'stage':stage,'final_url':actual,'source_pdf_url':url,'pdf_pages':[index+1],'action':'打开原生浏览器捕获DOM中实际公布的PDF，定位材料/流程正文','http_status':200,'screenshot':stage+'.png','screenshot_sha256':hashlib.sha256((folder/(stage+'.png')).read_bytes()).hexdigest(),'source_pdf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'text_file':stage+'.txt','template_links':[],'page_problem':None})
    else:
        materials=numbered_materials(text)
        flow=''
        with BrowserLane(folder/'evidence-browser') as lane:
            target=lane.call('open',actual)['targetId'];lane.call('resize','1440','1000','--target-id',target);lane.call('wait','--time','3500','--target-id',target)
            for stage,label in [('department-templates','五、申请材料'),('department-flow','六、办理期限')]:
                lane.call('evaluate','--target-id',target,'--fn',"() => {const n=Array.from(document.querySelectorAll('p,h2,h3')).find(n=>n.innerText.trim()=="+json.dumps(label,ensure_ascii=False)+"); if(!n)throw Error('Actual heading absent');n.scrollIntoView({block:'start'});return n.innerText}")
                lane.screenshot(target,folder/(stage+'.png'));(folder/(stage+'.txt')).write_text(text,'utf8');observations.append({'stage':stage,'final_url':actual,'action':'定位当前官方指南的材料/办理期限原文','screenshot':stage+'.png','screenshot_sha256':hashlib.sha256((folder/(stage+'.png')).read_bytes()).hexdigest(),'text_file':stage+'.txt','template_links':[],'page_problem':None})
    guide={'id':hashlib.sha256(actual.encode()).hexdigest()[:20],'province':slug,'province_name':__import__('province_documents').PROVINCE_DOCUMENTS[slug]['name'],'guide_url':actual,'service_name':'劳动人事争议仲裁申请' if slug=='hebei' else '劳动人事争议调解仲裁','region_name':entry['region_name'],'region_code':'','authority':entry['authority'],'jurisdiction_status':'capital_department_published_source','workflow_text':flow,'workflow_representation':representation,'steps':[],'materials':materials,'materials_complete':False,'templates':[],'downloaded_files':[],'stage':'department-templates','screenshot':'department-templates.png','flow_screenshot':'department-flow.png','captured_at':datetime.now().astimezone().isoformat(),'source_kind':'capital_official_department_fallback','source_pdf':'source.pdf' if pdf_urls else None,'pdf_pages':pages,'scope_note':'采用所载省会人社部门指南；不作为全省统一模板。PDF材料列表请对照原件；图像流程不猜测分支。'}
    if not valid_guide(guide) or not guide_belongs_to_province(guide,slug):raise ValueError('Guide failed province/content validation')
    pdf_form_reference(folder,guide,observations)
    save(folder/'observations.json',observations);save(ready,guide);save(folder/'normalized-guide.json',guide);return guide

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--provinces',default='hebei,shandong,henan');p.add_argument('--cached-capture',type=Path);a=p.parse_args();run=a.run.resolve()
    from openclaw_browser_tasks import TASK_ROOT
    if not run.is_relative_to(TASK_ROOT.resolve()):raise ValueError('Output must stay in task evidence')
    os.environ.update(TEMP=str(run/'temp'),TMP=str(run/'temp'))
    for slug in a.provinces.split(','):
        try:g=recover(slug,run,a.cached_capture);print(slug,'ACQUIRED',g['materials'],flush=True)
        except Exception as e:print(slug,'FAILED',str(e),flush=True);save(run/'department-guide-recovery'/slug/'error.json',{'error':str(e)})
