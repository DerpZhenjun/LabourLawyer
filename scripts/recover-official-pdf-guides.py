"""Re-fetch registered official PDFs and capture the actual labour chapter.

Run only after the provincial portal/browser attempts fail. Source scope is
retained; a departmental/county guide never becomes a province-wide template.
Uses bundled artifact Python. No model output changes the extracted facts.
"""
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from province_documents import PROVINCE_DOCUMENTS
from openclaw_browser_tasks import TASK_ROOT,save,official_url
from province_experience import valid_guide,guide_belongs_to_province
HIDDEN=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

def labour_chapter(texts):
    # Exclude contents pages and unrelated chapters in large service handbooks.
    for index,text in enumerate(texts):
        compact=re.sub(r'\s+','',text)
        if not re.search('劳动(?:人事争议)?(?:仲裁|争议)',compact[:220]):continue
        if not re.search('办理材料|受理条件|事项简述',compact):continue
        selected=[index]
        for following in range(index+1,min(index+5,len(texts))):
            after=re.sub(r'\s+','',texts[following])
            if re.search('事项名称|事项类型',after[:650]):break
            selected.append(following)
        return selected
    raise ValueError('No identifiable labour guide chapter; PDF retained without publication')

def capture(slug,run):
    meta=PROVINCE_DOCUMENTS[slug]
    catalog=json.loads((ROOT/'config/province_official_template_catalog.json').read_text(encoding='utf8'))
    entry=next(p for p in catalog['provinces'] if p['province_zh']==meta['name'])
    urls=list(dict.fromkeys([entry['source_url']]+[d['url'] for d in entry.get('documents',[]) if d.get('document_type')=='guide' and d.get('url')]))
    folder=run/'official-pdf-recovery'/slug;folder.mkdir(parents=True,exist_ok=True)
    cached=folder/'verified-guide.json'
    if cached.exists():return json.loads(cached.read_text(encoding='utf8'))
    attempts=[];path=folder/'source.pdf';headers=folder/'source.headers'
    for url in urls:
        if not official_url(url):continue
        p=subprocess.run(['curl.exe','--silent','--show-error','--location','--connect-timeout','5','--max-time','30','--max-filesize','50000000','--output',str(path),'--dump-header',str(headers),'--write-out','%{http_code} %{url_effective}',url],capture_output=True,timeout=35,creationflags=HIDDEN)
        outcome=p.stdout.decode('utf8',errors='replace');attempts.append({'url':url,'returncode':p.returncode,'outcome':outcome,'error':p.stderr.decode('utf8',errors='replace')[:600]})
        save(folder/'requests.json',attempts)
        if p.returncode==0 and outcome.startswith('200 ') and path.read_bytes().startswith(b'%PDF-'):
            actual=outcome.split(' ',1)[1]
            if not official_url(actual):raise ValueError('PDF redirected outside government source')
            break
    else:raise RuntimeError('Registered PDF unavailable; see '+str(folder/'requests.json'))
    texts=[page.extract_text() for page in PdfReader(path).pages];pages=labour_chapter(texts)
    save(folder/'chapter.json',[{'page':i+1,'text':texts[i]} for i in pages])
    spec=importlib.util.spec_from_file_location('office_renderer',ROOT/'scripts/validate_acquired_templates.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
    subprocess.run([str(renderer.PDFTOPPM),'-f',str(pages[0]+1),'-l',str(pages[-1]+1),'-r','110','-png',str(path),str(folder/'page')],check=True,timeout=40,creationflags=HIDDEN)
    images=sorted(folder.glob('page-*.png'));text='\n'.join(texts[i] for i in pages);compact=re.sub(r'\s+','',text)
    material_index=next((j for j,i in enumerate(pages) if re.search('申请材料|办理材料',re.sub(r'\s+','',texts[i]))),0)
    observations=[]
    for stage,image in [('official-pdf-templates',images[material_index]),('official-pdf-flow',images[0])]:
        (folder/(stage+'.txt')).write_text(text,encoding='utf8')
        shutil.copyfile(image,folder/(stage+'.png'))
        observations.append({'stage':stage,'final_url':actual,'requested_url':url,'action':'重新获取登记官方PDF，定位劳动争议事项正文','http_status':200,'screenshot':stage+'.png','screenshot_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'text_file':stage+'.txt','template_links':[],'source_pdf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pdf_pages':[i+1 for i in pages],'page_problem':None})
    save(folder/'observations.json',observations)
    materials=[name for name in ('仲裁申请书','证据','居民身份证','授权委托书','营业执照') if name in compact]
    guide={'id':hashlib.sha256(actual.encode()).hexdigest()[:20],'province':slug,'province_name':meta['name'],'guide_url':actual,'service_name':'劳动人事争议仲裁申请' if '劳动人事争议仲裁申' in compact else '劳动仲裁','region_name':entry.get('scope',''),'authority':entry.get('authority',''),'jurisdiction_status':'registered_department_source','workflow_text':'','steps':[],'materials':materials,'materials_complete':False,'templates':[],'downloaded_files':[],'stage':'official-pdf-templates','screenshot':'official-pdf-templates.png','flow_screenshot':'official-pdf-flow.png','captured_at':datetime.now().astimezone().isoformat(),'source_kind':'registered_official_pdf_fallback','source_pdf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_pdf':'source.pdf','pdf_pages':[i+1 for i in pages],'scope_note':'采用所载部门/区县指南；不视为全省统一模板。流程图仅保留画面，不猜测顺序。'}
    if not valid_guide(guide) or not guide_belongs_to_province(guide,slug):raise ValueError('PDF guide evidence failed ownership/content check')
    save(cached,guide);return guide

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--provinces',default='guangxi,qinghai');args=p.parse_args()
    run=args.run.resolve()
    if not run.is_relative_to(TASK_ROOT.resolve()):raise ValueError('Output must stay in native task evidence')
    temp=run/'temp';temp.mkdir(exist_ok=True);os.environ.update(TEMP=str(temp),TMP=str(temp))
    results_path=run/'official-pdf-recovery/results.json'
    results=json.loads(results_path.read_text(encoding='utf8')) if results_path.exists() else {}
    for slug in args.provinces.split(','):
        try:g=capture(slug,run);results[slug]={'state':'captured','guide':g};print(slug,'captured',g['pdf_pages'],flush=True)
        except Exception as exc:results[slug]={'state':'failed','error':str(exc)};print(slug,str(exc),flush=True)
        save(run/'official-pdf-recovery/results.json',results)
