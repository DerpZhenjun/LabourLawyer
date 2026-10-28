"""Resume missing public guides with OpenClaw's real dedicated browser.

Every task retains snapshots, selected actions, remote model outputs and files.
Use --provinces for a targeted retry. Successful prior tasks are reused.
"""
import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import uuid
import subprocess

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from openclaw_browser_tasks import run_task,TASK_ROOT,save,check_model_available,official_url
from province_experience import PORTALS,POLICY,load_experiences,valid_guide,plain_guide,guide_rank,EXPERIENCE_ROOT,guide_belongs_to_province
from province_documents import PROVINCE_DOCUMENTS
from openclaw_job_lock import acquisition_lock
from terminal_progress import configure, emit

async def inspect_guide(port,url,folder):
    from playwright.async_api import async_playwright
    from portal_guide_navigation import body_text,capture_materials
    from portal_workflows import guide_record,service_title,capture_flow,PublicResponses,parse_public_record
    from portal_audit import sha
    from province_experience import is_guide_url
    if not is_guide_url(url):return None
    async with async_playwright() as pw:
        browser=await pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}',timeout=10000)
        page=next((p for c in browser.contexts for p in c.pages if p.url==url),None)
        if not page:return None
        text=await body_text(page)
        if not service_title(text) or not any(label in text for label in ('申请材料','办理流程','办理条件','受理条件','办理程序')):return None
        context=page.context;responses=PublicResponses(context)
        # The native agent has already loaded the guide before this inspector
        # attaches. Reload that same public URL so initial structured guide
        # responses are observed rather than silently missed.
        from portal_audit_capture import settle
        await page.reload(wait_until='domcontentloaded',timeout=25000);await settle(page)
        material=await capture_materials(page,folder,'openclaw-templates')
        if material.get('final_url')!=page.url:page=next((p for p in context.pages if p.url==material.get('final_url')),page)
        flow_text,flow=await capture_flow(page,folder,'openclaw')
        # Persist successful capture steps before optional normalization, so
        # a parser failure cannot discard the observations needed for recovery.
        save(folder/'observations.json',[material,flow])
        guide=guide_record({'slug':folder.name,'name':PROVINCE_DOCUMENTS[folder.name]['name']},material,await body_text(page),flow_text)
        guide.update(steps=flow.get('structured_steps',[]),flow_screenshot=flow.get('screenshot'))
        await responses.flush(folder)
        # Only responses for this actual guideline can supply structured fields.
        import importlib.util
        spec=importlib.util.spec_from_file_location('refresh',ROOT/'scripts/refresh-province-experiences.py');refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)
        for response in responses.records:
            parsed=parse_public_record(response)
            if parsed and refresh.response_matches(response,page.url):guide.update(parsed)
        if not valid_guide(guide) or not guide_belongs_to_province(guide,folder.name):return None
        guide['openclaw_task']=str(folder.relative_to(ROOT));guide['source_kind']='openclaw_browser_verified_page'
        files=[]
        for entry in material.get('template_links',[]):
            if entry.get('download_status')=='downloaded':
                path=folder/entry['file']
                if path.is_file():files.append({'filename':path.name,'sha256':sha(path),'bytes':path.stat().st_size,'url':entry.get('download_url'),'kind':entry.get('kind')})
        guide['downloaded_files']=files
        save(folder/'verified-guide.json',guide)
        return guide

def require_saved_evidence(folder):
    """Validate restored department evidence before promotion or publication."""
    import hashlib
    path=folder/'observations.json'
    if not path.is_file():raise ValueError('Restored guide lacks observations; evidence retained')
    observations=json.loads(path.read_text(encoding='utf8'))
    if not isinstance(observations,list) or not observations:raise ValueError('Restored guide has no actual observations')
    for observation in observations:
        image=(folder/observation.get('screenshot','')).resolve()
        if not image.is_relative_to(folder.resolve()) or not image.is_file() or hashlib.sha256(image.read_bytes()).hexdigest()!=observation.get('screenshot_sha256'):
            raise ValueError('Restored guide screenshot missing or hash changed; evidence retained')

def apply_result(run,slug,profile,result,destination):
    """Promote actual evidence, without promoting templates into fill adapters."""
    guide=result.get('selected_guide')
    if not guide or not valid_guide(guide) or not guide_belongs_to_province(guide,slug):return False
    if guide.get('downloaded_files') and not result.get('download_reviewed'):return False
    destination.mkdir(parents=True,exist_ok=True)
    for path in (run/slug).iterdir():
        if path.name in ('browser','model'):continue
        dest=destination/path.name
        if path.name=='observations.json' and dest.exists():
            previous=json.loads(dest.read_text(encoding='utf8'))
            added=json.loads(path.read_text(encoding='utf8'))
            save(dest,previous+added);continue
        if path.is_dir():shutil.copytree(path,dest,dirs_exist_ok=True)
        else:shutil.copy2(path,dest)
    profile.update(plain_guide(guide,slug,PROVINCE_DOCUMENTS[slug].get('scope','')))
    profile.update(state='fresh',selected_guide=guide,templates=guide.get('templates',[]),checked_at=result['updated_at'],capital_confirmed=not guide_rank(guide,slug)[1],openclaw_task=str((run/slug).relative_to(ROOT)))
    old=destination/'ai.json'
    if old.exists():old.rename(destination/('ai-previous-'+uuid.uuid4().hex[:6]+'.json'))
    profile['ai_review']={'state':'pending','reason':'New OpenClaw-acquired guideline screenshots'}
    save(destination/'experience.json',profile)
    return True

def supplement(profiles,destination,slugs=None,budget=900,steps=12):
    with acquisition_lock():return _supplement(profiles,destination,slugs,budget,steps)

def _supplement(profiles,destination,slugs=None,budget=900,steps=12):
    """Third browser layer after ordinary capture; sequential Ubuntu requests."""
    run=TASK_ROOT/(datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]);run.mkdir(parents=True)
    try:save(run/'model-probe.json',check_model_available())
    except Exception as exc:
        save(run/'status.json',{'state':'failed','error':str(exc),'source_run':destination.name});return run
    slugs=slugs if slugs is not None else [s for s,p in profiles.items() if p['state']!='fresh']
    results={}
    for slug in slugs:
        save(run/'status.json',{'state':'running','current':slug,'total':len(slugs),'completed':len(results),'source_run':destination.name})
        def inspect(port,url,folder):return asyncio.run(asyncio.wait_for(inspect_guide(port,url,folder),100))
        result=run_task(slug,PORTALS[slug],run/slug,POLICY['capitals'][slug],steps,budget,inspect)
        result=recover_registered_pdf(run,slug,result)
        results[slug]=result;save(run/'results.json',results)
        emit('browser',kind='region',province=slug,region_state=result['state'],message='补采结果：'+result['state'],completed=len(results),total=len(slugs),output=str(run))
        profiles[slug]['openclaw_attempt']={'run':run.name,'state':result['state'],'status':result['status'],'error':result.get('error')}
        save(destination/slug/'experience.json',profiles[slug])
        print('OPENCLAW RESULT',slug,result['state'],flush=True)
    try:results=review_downloads(run,results)
    except Exception as exc:
        save(run/'status.json',{'state':'review_incomplete','phase':'download_content','error':str(exc),'total':len(slugs),'completed':len(results),'requested_provinces':slugs,'source_run':destination.name})
        return run
    for slug,result in results.items():apply_result(run,slug,profiles[slug],result,destination/slug)
    pending={s:r.get('pending_downloads',[]) for s,r in results.items() if r.get('pending_downloads')}
    save(run/'status.json',{'state':'review_incomplete' if pending else 'complete_with_gaps' if any(r['state']!='acquired' for r in results.values()) else 'complete','pending_downloads':pending,'total':len(slugs),'completed':len(results),'acquired':sum(r['state']=='acquired' for r in results.values()),'source_run':destination.name})
    return run

def publish(run,results):
    current=load_experiences()
    improved={slug:r for slug,r in results.items() if r.get('selected_guide') and valid_guide(r['selected_guide']) and guide_belongs_to_province(r['selected_guide'],slug) and (r.get('download_reviewed') or not r['selected_guide'].get('downloaded_files'))}
    if not improved:return None
    for slug,result in improved.items():
        if result['selected_guide'].get('source_kind')=='capital_official_department_fallback':require_saved_evidence(run/slug)
    # Create a derived full batch; preserve its unmodified predecessor and dates.
    original=EXPERIENCE_ROOT/current['run_id']
    missing=[s for s in current['provinces'] if not (original/s/'experience.json').is_file() or not (original/s/'observations.json').is_file()]
    if missing:raise RuntimeError('Previous full batch is missing province evidence: '+', '.join(missing)+'. Original latest data and acquired files retained.')
    merged=EXPERIENCE_ROOT/(datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8])
    merged.mkdir(parents=True)
    for slug,profile in current['provinces'].items():
        shutil.copytree(original/slug,merged/slug)
        if slug in improved:
            apply_result(run,slug,profile,improved[slug],merged/slug)
        if slug in results:
            result=results[slug]
            plans=result.get('actions') or []
            last=plans[-1] if plans else {}
            reason=result.get('error') or result.get('portal_attempt_error') or last.get('execution_error') or last.get('rejected') or ('' if result['state']=='acquired' else '本次未取得有效指南（'+result['state']+'）')
            profile['openclaw_attempt']={'run':run.name,'state':result['state'],'status':result['status'],'error':reason,'model_reason':last.get('plan',{}).get('reason',''),'url':result.get('final_url') or last.get('url'),'updated_at':result.get('updated_at'),'official_pdf_fallback':result.get('official_pdf_fallback')}
            if slug not in improved:
                # New failed observations also deserve real screenshots and AI
                # review. Do not silently leave the old failed screenshot/date.
                screenshots=sorted((run/slug).glob('step-??.png'))
                if screenshots:
                    image=screenshots[-1];filename='openclaw-recovery-templates.png'
                    shutil.copy2(image,merged/slug/filename)
                    observation={'stage':'openclaw-recovery-templates','final_url':profile['openclaw_attempt']['url'],'action':'本次浏览器补采未取得有效指南','capture_method':result.get('directory_recovery',{}).get('method','openclaw_native_screenshot'),'screenshot':filename,'screenshot_sha256':__import__('hashlib').sha256(image.read_bytes()).hexdigest(),'template_links':[],'errors':[reason] if reason else [],'page_problem':'capture_incomplete','finished_at':result.get('updated_at')}
                    obs_path=merged/slug/'observations.json'
                    save(obs_path,json.loads(obs_path.read_text(encoding='utf8'))+[observation])
                    old=merged/slug/'ai.json'
                    if old.exists():old.rename(old.with_name('ai-previous-'+uuid.uuid4().hex[:6]+'.json'))
                    profile.update(openclaw_task=str((run/slug).relative_to(ROOT)),ai_review={'state':'pending','reason':'New failed native browser attempt screenshot'})
        save(merged/slug/'experience.json',profile)
    current.update(run_id=merged.name,parent_run=original.name,openclaw_run=run.name)
    save(merged/'experiences.json',current)
    counts={state:sum(p['state']==state for p in current['provinces'].values()) for state in ('fresh','historical','not_detected')}
    status={'state':'review_pending','counts':counts,'regions':31,'source_run':current.get('source_run'),'parent_run':original.name,'updated_at':datetime.now().astimezone().isoformat()}
    save(merged/'status.json',status)
    # Publishing is performed only after the new screenshots have AI reviews.
    return merged

def main(args):
    with acquisition_lock():return _main(args)

def recover_registered_pdf(run,slug,result):
    """After browser routes fail, preserve a verified official PDF chapter.

    This remains a department/county source, with its actual scope and images.
    Publication still requires the existing independent AI screenshot gate.
    """
    if result.get('status',{}).get('guide_found'):
        if result.get('official_pdf_fallback',{}).get('state')=='verified' and result.get('error'):
            result['portal_attempt_error']=result.pop('error');save(run/slug/'task.json',result)
        return result
    department=ROOT/'config/province_guide_fallbacks.json'
    if department.is_file() and slug in json.loads(department.read_text(encoding='utf8')):
        result=recover_department_source(run,slug,result)
        if result.get('status',{}).get('guide_found'):return result
    source=PROVINCE_DOCUMENTS[slug].get('source_url','')
    if '.pdf' not in source.lower():return result
    folder=run/'official-pdf-recovery'/slug
    cached=folder/'verified-guide.json'
    if not cached.exists() and (folder/'requests.json').exists():
        result['official_pdf_fallback']={'state':'failed','evidence':str(folder.relative_to(ROOT))};save(run/slug/'task.json',result);return result
    if not cached.exists():
        python=Path(os.getenv('LABOURLAWYER_ARTIFACT_PYTHON',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')))
        if not python.is_file():return result
        try:subprocess.run([str(python),str(ROOT/'scripts/recover-official-pdf-guides.py'),str(run),'--provinces',slug],check=True,timeout=140)
        except Exception as exc:
            result['official_pdf_fallback']={'state':'failed','error':str(exc)[:500]};save(run/slug/'task.json',result);return result
    if not cached.exists():
        result['official_pdf_fallback']={'state':'failed','evidence':str(folder.relative_to(ROOT))};save(run/slug/'task.json',result);return result
    guide=json.loads(cached.read_text(encoding='utf8'))
    if not valid_guide(guide) or not guide_belongs_to_province(guide,slug):return result
    save(run/slug/'task-before-official-pdf-recovery.json',result)
    for path in folder.iterdir():
        if path.is_file():shutil.copy2(path,run/slug/path.name)
    result.update(state='acquired',selected_guide=guide,updated_at=guide['captured_at'],official_pdf_fallback={'state':'verified','source_kind':guide['source_kind'],'pages':guide['pdf_pages']})
    if result.get('error'):result['portal_attempt_error']=result.pop('error')
    result['status']['guide_found']=True
    result['evidence']={'url':guide['guide_url'],'screenshot':{'filename':guide['screenshot'],'sha256':guide['evidence_sha256'] if guide.get('evidence_sha256') else __import__('hashlib').sha256((run/slug/guide['screenshot']).read_bytes()).hexdigest()}}
    save(run/slug/'task.json',result);return result

def recover_department_source(run,slug,result):
    """Reuse or collect a registered capital source after native portal failure."""
    folder=run/'department-guide-recovery'/slug;cached=folder/'verified-guide.json'
    if not cached.is_file() and not (folder/'error.json').is_file():
        python=Path(os.getenv('LABOURLAWYER_ARTIFACT_PYTHON',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')))
        try:
            if not python.is_file():raise RuntimeError('Artifact Python unavailable')
            subprocess.run([str(python),str(ROOT/'scripts/recover-department-guides.py'),str(run),'--provinces',slug],check=True,timeout=180)
        except Exception as exc:
            result['official_department_fallback']={'state':'failed','error':str(exc)[:500]};save(run/slug/'task.json',result);return result
    if not cached.is_file():
        result['official_department_fallback']={'state':'failed','evidence':str(folder.relative_to(ROOT))};save(run/slug/'task.json',result);return result
    guide=json.loads(cached.read_text(encoding='utf8'))
    if not valid_guide(guide) or not guide_belongs_to_province(guide,slug):return result
    require_saved_evidence(folder)
    save(run/slug/'task-before-department-recovery.json',result)
    for path in folder.iterdir():
        if path.is_file():shutil.copy2(path,run/slug/path.name)
    result.update(state='acquired',selected_guide=guide,updated_at=guide['captured_at'],download_reviewed=True,pending_downloads=[],official_department_fallback={'state':'verified','source_kind':guide['source_kind'],'evidence':str(folder.relative_to(ROOT))})
    if result.get('error'):result['portal_attempt_error']=result.pop('error')
    result['status']['guide_found']=True
    save(run/slug/'task.json',result);return result

def review_downloads(run,results):
    if not any(r.get('selected_guide',{}).get('downloaded_files') and not r.get('download_reviewed') for r in results.values()):return results
    artifact_python=Path(os.getenv('LABOURLAWYER_ARTIFACT_PYTHON',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')))
    if not artifact_python.is_file():raise RuntimeError('Artifact Python unavailable; downloads preserved and not published as templates.')
    save(run/'status.json',{'state':'reviewing','phase':'download_content','completed':len(results),'total':len(results),'requested_provinces':list(results)})
    downloads=sum(len(r.get('selected_guide',{}).get('templates',[]))+len(r.get('selected_guide',{}).get('supporting_documents',[])) for r in results.values())
    subprocess.run([str(artifact_python),str(ROOT/'scripts/review-openclaw-downloads.py'),str(run)],check=True,timeout=60+downloads*300)
    return json.loads((run/'results.json').read_text(encoding='utf8'))

def finish_review(run,merged,status):
    import subprocess
    status['state']='reviewing';save(run/'status.json',status)
    try:subprocess.run([sys.executable,str(ROOT/'scripts/refresh-province-experiences.py'),'--resume',str(merged),'--without-browser-agent'],check=True)
    except Exception as exc:
        status.update(state='failed',error=str(exc));save(run/'status.json',status);raise
    reviewed=json.loads((merged/'status.json').read_text(encoding='utf8'))
    status['state']='review_incomplete' if reviewed['state']=='review_incomplete' else 'complete' if status['acquired']==status['total'] else 'complete_with_gaps'
    status['pending_ai']=reviewed.get('pending_ai',[]);save(run/'status.json',status)
    return status

def _main(args):
    current=load_experiences()
    slugs=args.provinces.split(',') if args.provinces else None
    if args.resume and not slugs:
        old_status=Path(args.resume)/'status.json'
        if old_status.exists():slugs=json.loads(old_status.read_text(encoding='utf8')).get('requested_provinces')
        if not slugs and (Path(args.resume)/'launch.json').exists():slugs=json.loads((Path(args.resume)/'launch.json').read_text(encoding='utf8')).get('provinces')
        if not slugs:slugs=[p.name for p in Path(args.resume).iterdir() if p.is_dir() and p.name in PROVINCE_DOCUMENTS] or None
    if slugs is None:slugs=[s for s,p in current['provinces'].items() if p['state']!='fresh']
    if any(s not in PROVINCE_DOCUMENTS for s in slugs):raise ValueError('Unknown province')
    run=Path(args.resume).resolve() if args.resume else TASK_ROOT/(datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8])
    if not run.resolve().is_relative_to(TASK_ROOT.resolve()):raise ValueError('Task directory must stay in openclaw-tasks')
    run.mkdir(parents=True,exist_ok=True);temp=run/'temp';temp.mkdir(exist_ok=True)
    configure(run)
    emit('probe',message='检查 Ubuntu 模型连接',completed=0,total=len(slugs),output=str(run))
    os.environ.update(TEMP=str(temp),TMP=str(temp),PYTHONUTF8='1')
    old_launch=run/'launch.json'
    if old_launch.exists() and json.loads(old_launch.read_text(encoding='utf8')).get('owner_pid')!=os.getpid():old_launch.rename(run/('launch-previous-'+uuid.uuid4().hex[:6]+'.json'))
    save(old_launch,{'owner_pid':os.getpid(),'started_at':datetime.now().astimezone().isoformat(),'provinces':slugs,'resumed':bool(args.resume)})
    results={};print('OPENCLAW RUN',run,flush=True)
    try:save(run/'model-probe.json',check_model_available())
    except Exception as exc:
        status={'state':'failed','error':str(exc),'requested_provinces':slugs,'completed':0,'total':len(slugs)}
        emit('job','failed',message='Ubuntu 模型探测失败',error=str(exc),output=str(run))
        save(run/'status.json',status);print(json.dumps(status,ensure_ascii=False),flush=True);return
    if args.resume and not args.no_publish and (run/'status.json').exists():
        previous=json.loads((run/'status.json').read_text(encoding='utf8'))
        if previous.get('derived_batch') and previous.get('state') in ('reviewing','review_incomplete','failed','queued'):
            merged=(ROOT/previous['derived_batch']).resolve()
            if not merged.is_relative_to(EXPERIENCE_ROOT.resolve()):raise ValueError('Review batch must stay in province-experiences')
            print(json.dumps(finish_review(run,merged,previous),ensure_ascii=False),flush=True);return
    for slug in slugs:
        start_url=PORTALS[slug]
        official_entry=None
        if getattr(args,'official_entry',None):
            navigation=json.loads((ROOT/'config/province_service_portals.json').read_text(encoding='utf8'))
            candidates=navigation.get('navigation_embedded',{}).get(slug,[]) if args.official_entry in ('embedded','services') else [navigation.get('navigation_windows',{}).get(slug,'')]
            if args.official_entry=='services':candidates=list(reversed(candidates))
            official_entry=next((url for url in candidates if official_url(url)),None)
            if not official_entry:raise ValueError('No observed national navigation entry for '+slug)
        prior=run/slug/'task.json'
        if prior.is_file():
            cached=json.loads(prior.read_text(encoding='utf8'))
            retry_pdf=getattr(args,'retry_portal_fallbacks',False) and cached.get('selected_guide',{}).get('source_kind')=='registered_official_pdf_fallback'
            reinspect=cached.get('selected_guide',{}).get('source_kind')=='openclaw_browser_verified_page' and (getattr(args,'reinspect_captured',False) or not valid_guide(cached['selected_guide']))
            if (cached['state']=='acquired' and not retry_pdf and not reinspect) or (getattr(args,'skip_completed_attempts',False) and cached['state'] not in ('running','interrupted') and not retry_pdf and not reinspect):
                results[slug]=recover_registered_pdf(run,slug,cached)
                emit('browser','cached',kind='region',province=slug,region_state=results[slug]['state'],message='复用已保存采集结果',completed=len(results),total=len(slugs),output=str(run))
                continue
            if cached.get('status',{}).get('site_opened') and official_url(cached.get('final_url','')) and not cached.get('certificate_error'):
                start_url=cached['final_url']
            if reinspect and official_url(cached['selected_guide'].get('guide_url','')):start_url=cached['selected_guide']['guide_url']
            # Preserve failed task evidence instead of overwriting it.
            attempt=run/slug
            if attempt.is_dir():attempt.rename(run/(slug+'-previous-'+uuid.uuid4().hex[:6]))
        if official_entry:start_url=official_entry
        if getattr(args,'restart_portal',False):start_url=PORTALS[slug]
        save(run/'status.json',{'state':'running','current':slug,'completed':len(results),'total':len(slugs),'requested_provinces':slugs,'source_run':current['run_id']})
        def inspect(port,url,folder):return asyncio.run(asyncio.wait_for(inspect_guide(port,url,folder),100))
        result=run_task(slug,start_url,run/slug,POLICY['capitals'][slug],args.steps,args.budget,inspect)
        result=recover_registered_pdf(run,slug,result)
        emit('browser',result['state'],kind='region',province=slug,region_state=result['state'],message='指南取得' if result['status']['guide_found'] else '本次仍有指南缺口',completed=len(results)+1,total=len(slugs),output=str(run),error=result.get('error',''))
        results[slug]=result;save(run/'results.json',results)
        print('OPENCLAW RESULT',slug,result['state'],result.get('error',''),flush=True)
    try:results=review_downloads(run,results)
    except Exception as exc:
        status={'state':'review_incomplete','phase':'download_content','error':str(exc),'requested_provinces':slugs,'completed':len(results),'total':len(slugs)}
        emit('job','review_incomplete',message='下载内容复核未完成',error=str(exc),output=str(run))
        save(run/'status.json',status);print(json.dumps(status,ensure_ascii=False),flush=True);return
    pending={s:r.get('pending_downloads',[]) for s,r in results.items() if r.get('pending_downloads')}
    if pending:
        status={'state':'review_incomplete','phase':'download_content','pending_downloads':pending,'requested_provinces':slugs,'completed':len(results),'total':len(slugs)}
        emit('job','review_incomplete',message='有下载文件尚未确认',output=str(run))
        save(run/'status.json',status);print(json.dumps(status,ensure_ascii=False),flush=True);return
    try:merged=publish(run,results) if not args.no_publish else None
    except Exception as exc:
        status={'state':'failed','phase':'publish','error':str(exc),'requested_provinces':slugs,'completed':len(results),'total':len(slugs)}
        emit('job','failed',message='发布失败；原结果保留',error=str(exc),output=str(run))
        save(run/'status.json',status);print(json.dumps(status,ensure_ascii=False),flush=True);return
    acquired=sum(r['status']['guide_found'] for r in results.values())
    status={'state':'reviewing' if merged else 'complete' if acquired==len(slugs) else 'complete_with_gaps','completed':len(results),'total':len(slugs),'requested_provinces':slugs,'acquired':acquired,'derived_batch':str(merged.relative_to(ROOT)) if merged else None,'source_run':current['run_id']}
    save(run/'status.json',status)
    emit('publish',message='保存采集状态与派生批次',output=str(merged or run))
    if merged:
        # Resume skips unchanged successful captures and historical AI calls.
        status=finish_review(run,merged,status)
    print(json.dumps(status,ensure_ascii=False),flush=True)
    emit('job',status['state'],message='OpenClaw 采集任务结束',completed=len(results),total=len(slugs),counts={'acquired':acquired,'gap':len(slugs)-acquired},output=str(merged or run))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--provinces');p.add_argument('--resume');p.add_argument('--steps',type=int,default=12);p.add_argument('--budget',type=int,default=900);p.add_argument('--no-publish',action='store_true');p.add_argument('--skip-completed-attempts',action='store_true',help='Reuse completed failed attempts as well as successes; do not revisit them during this continuation');p.add_argument('--retry-portal-fallbacks',action='store_true',help='Explicitly retry a repaired provincial browser route while preserving its verified PDF fallback');p.add_argument('--reinspect-captured',action='store_true',help='Explicitly reopen an already observed native guide URL after repairing incomplete tab capture; preserve the prior attempt');p.add_argument('--official-entry',choices=('window','embedded','services'),help='Use an actual province URL observed in the official national navigation; no guessed addresses')
    p.add_argument('--restart-portal',action='store_true',help='For failed attempts, open the registered portal first to initialize its anonymous browser session; preserve previous evidence')
    args=p.parse_args()
    if not 1<=args.steps<=30 or not 60<=args.budget<=1800:p.error('Steps 1..30; province budget 60..1800 seconds')
    main(args)
