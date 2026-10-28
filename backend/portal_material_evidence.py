"""Repair reported material screenshots after visual review found wrong scroll."""
import asyncio,os,hashlib
from portal_audit_capture import official,settle,snapshot
from portal_interactions import MATERIAL_LABELS,activate_section,scan_scroll,focus_material_download

def cached_attachment(previous,current):
    """Reuse an attachment only when a saved identity matches the new control."""
    current_urls={u for u in (current.get('url'),current.get('download_url')) if u}
    matches=[]
    for old in previous:
        old_urls={u for u in (old.get('url'),old.get('download_url')) if u}
        same_id=current.get('doc_id') and old.get('doc_id')==current['doc_id']
        # A visible label cannot override conflicting attachment identities.
        # Generic "download" labels recur for distinct files in one guide.
        conflicting_id=current.get('doc_id') and old.get('doc_id') and old['doc_id']!=current['doc_id']
        conflicting_url=current_urls and old_urls and not current_urls.intersection(old_urls)
        same_fields=not conflicting_id and not conflicting_url and current.get('material_name') and current.get('control_text') and current.get('kind') and old.get('material_name')==current['material_name'] and old.get('control_text')==current['control_text'] and old.get('kind')==current['kind']
        if same_id or current_urls.intersection(old_urls) or same_fields:matches.append(old)
    receipts=[old for old in matches if old.get('file')]
    return receipts[0] if len(receipts)==1 else matches[0] if len(matches)==1 else {}

def normalize_observations(directory,item):
    grouped={}
    for o in item['observations']:grouped.setdefault(o['stage'],[]).append(o)
    resolved=[]
    for stage,versions in grouped.items():
        if len(versions)==1:resolved.append(versions[0]);continue
        matching=[]
        for o in versions:
            p=directory/o.get('screenshot','missing')
            if p.is_file() and o.get('screenshot_sha256')==hashlib.sha256(p.read_bytes()).hexdigest():matching.append(o)
        winner=(matching or versions)[-1]
        if not matching:winner['evidence_error']='阶段编号重复且截图校验失败；待补拍'
        winner['report_include']=any(o.get('report_include') for o in versions)
        resolved.append(winner)
        for o in versions:
            if o is not winner:item.setdefault('observation_history',[]).append(dict(o,history_reason='旧阶段编号重复，当前观测采用与原图校验和一致的版本'))
    item['observations']=resolved

async def repair_views(folder,items,progress):
    from playwright.async_api import async_playwright
    from portal_audit import write_json
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True,env=os.environ.copy())
        sem=asyncio.Semaphore(3);done=0
        async def one(index,item):
            nonlocal done
            async with sem:
                ctx=await browser.new_context(locale='zh-CN',viewport={'width':1440,'height':1000});ctx.set_default_timeout(4000)
                directory=folder/item['slug'];seen=set()
                normalize_observations(directory,item)
                from portal_audit_report import current_searches
                latest=current_searches(item);item['searches']=latest
                by_keyword={o['keyword']:o['stage'] for o in latest}
                for old_search in item['observations']:
                    if old_search['stage'].startswith('search-') and old_search.get('keyword') in by_keyword and old_search['stage']!=by_keyword[old_search['keyword']]:
                        old_search['superseded_by']=by_keyword[old_search['keyword']]
                try:
                    for old in list(item['observations']):
                        if not old['stage'].endswith('-templates') or old.get('superseded_by') or old.get('non_target_service') or old.get('evidence_error') or (old.get('material_capture_version') or 0)>=6 or old.get('material_recheck_error'):continue
                        if old['stage'].startswith('district-') and not old.get('report_include'):continue
                        url=old.get('final_url','')
                        if url in seen or not official(url) or not old.get('template_links'):continue
                        seen.add(url);page=await ctx.new_page()
                        try:
                            await page.goto(url,timeout=30000,wait_until='domcontentloaded');await settle(page)
                            await activate_section(page,MATERIAL_LABELS);await scan_scroll(page,('申请书','证据清单'));focused=await focus_material_download(page)
                            if not focused:continue
                            stage=old['stage'].removesuffix('-templates')+'-focused-templates'
                            current=await snapshot(page,directory,stage,action='图像复核发现原图未对准文书行，补拍实际下载控件')
                            if current.get('page_problem'):continue
                            for a in current['template_links']:
                                cached=cached_attachment(old['template_links'],a)
                                for field in ('file','sha256','bytes','download_status','download_url'):
                                    if field in cached:a[field]=cached[field]
                            current.update(material_capture_version=6,material_focus=focused,template_area_visible=True,templates_detected=True,template_status='downloads_detected',keyword=old.get('keyword'),selected_jurisdictions=old.get('selected_jurisdictions',[]),report_include=old.get('report_include',True),refined_from=old['stage'])
                            old['superseded_by']=stage;item['observations'].append(current)
                            # Other copies of the same guide share the new proof.
                            for duplicate in item['observations']:
                                if duplicate['stage']!=stage and duplicate['stage'].endswith('-templates') and duplicate.get('final_url')==url:duplicate['superseded_by']=stage
                            catalog_path=directory/'workflows.json'
                            if catalog_path.is_file():
                                import json
                                catalog=json.loads(catalog_path.read_text(encoding='utf8'))
                                for guide in catalog.get('guides',[]):
                                    if guide.get('guide_url')==url or guide.get('stage')==old['stage']:
                                        guide.update(stage=stage,screenshot=current.get('screenshot'),evidence_sha256=current.get('screenshot_sha256'),templates=current.get('template_links',[]),materials=current.get('material_names',[]))
                                write_json(catalog_path,catalog)
                            item.pop('ai_review',None);write_json(directory/'observations.json',item)
                            print('MATERIAL-FOCUS',item['slug'],stage,focused['material'],flush=True)
                        except Exception as exc:
                            # A failed supplementary visit cannot invalidate a
                            # verified historical screenshot or stop other regions.
                            old['material_recheck_error']=str(exc)[:250]
                            from portal_audit import now
                            old['material_recheck_attempted_at']=now()
                            write_json(directory/'observations.json',item)
                            print('MATERIAL-RECHECK-PENDING',item['slug'],old['stage'],str(exc)[:90],flush=True)
                        finally:await page.close()
                finally:await ctx.close()
                write_json(directory/'observations.json',item)
                done+=1;progress(done,'材料截图复核 '+item['name'])
        await asyncio.gather(*(one(i,x) for i,x in enumerate(items,1)));await browser.close()
    write_json(folder/'results.json',items);return items
