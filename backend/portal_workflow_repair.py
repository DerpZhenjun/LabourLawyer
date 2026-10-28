"""Normalize saved jurisdiction data and finish previously hidden process tabs."""
import asyncio,json,os,re,hashlib
from urllib.parse import urlsplit
# A long continuation may have imported these helpers before a resumed repair
# was updated. Refresh pure helpers only after acquisition has closed its pages.
import importlib,portal_interactions,portal_workflows,portal_guide_navigation,portal_audit_report
for module in (portal_interactions,portal_workflows,portal_guide_navigation,portal_audit_report):importlib.reload(module)
from portal_workflows import guide_record,official_region_names,service_title,arbitration_service,capture_flow,FLOW_LABELS
from portal_audit_capture import settle

async def repair_workflows(folder,items,progress):
    from playwright.async_api import async_playwright
    from portal_audit import write_json
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True,env=os.environ.copy())
        sem=asyncio.Semaphore(4);done=0
        async def one(index,item):
            nonlocal done
            directory=folder/item['slug'];path=directory/'workflows.json'
            if not path.is_file():return
            catalog=json.loads(path.read_text(encoding='utf8'));responses=directory/'public-guide-responses.json'
            names=official_region_names(json.loads(responses.read_text(encoding='utf8'))) if responses.is_file() else {}
            originals=list(catalog['guides']);valid=[];excluded=list(catalog.get('excluded_guides',[]))
            async with sem:
                ctx=await browser.new_context(locale='zh-CN',viewport={'width':1440,'height':1000});ctx.set_default_timeout(4000)
                try:
                    for position,record in enumerate(originals):
                        versions=[o for o in item['observations'] if o['stage']==record.get('stage')]
                        observation=next((o for o in reversed(versions) if o.get('screenshot_sha256')==record.get('evidence_sha256')),versions[-1] if versions else None)
                        if not observation:valid.append(record);continue
                        picture=directory/record.get('screenshot','missing')
                        if not picture.is_file() or hashlib.sha256(picture.read_bytes()).hexdigest()!=record.get('evidence_sha256'):
                            # Prior numeric filenames could collide after resume.
                            # Only the invalid proof is recaptured, at a unique path.
                            from portal_guide_navigation import capture_materials
                            page=await ctx.new_page()
                            try:
                                await page.goto(record['guide_url'],timeout=30000,wait_until='domcontentloaded');await settle(page)
                                stage='district-'+record['id']+'-integrity-templates'
                                replacement=await capture_materials(page,directory,stage,item['scope'],download=False)
                                if replacement.get('page_problem') or (replacement.get('http_status') or 200)>=400:raise RuntimeError('补拍页面访问异常')
                                replacement['report_include']=observation.get('report_include',False)
                                if observation.get('final_url')==record['guide_url']:observation['superseded_by']=stage
                                item['observations'].append(replacement)
                                record.update(stage=stage,screenshot=replacement['screenshot'],evidence_sha256=replacement['screenshot_sha256'])
                                observation=replacement
                                print('INTEGRITY-REPAIR',item['slug'],record['id'],flush=True)
                            except Exception as exc:
                                record.update(state='evidence_invalid',evidence_error=str(exc)[:180]);valid.append(record)
                                if observation.get('final_url')==record['guide_url']:observation.update(evidence_error='截图与原校验和不符，不能作为当前指南证据',page_problem='evidence_invalid')
                                continue
                            finally:await page.close()
                        text_path=directory/observation.get('text_file','missing');text=text_path.read_text(encoding='utf8') if text_path.is_file() else ''
                        normalized=guide_record(item,observation,text)
                        title=normalized['service_name'] or record.get('service_name','')
                        if title and not arbitration_service(title):
                            record.update(state='unrelated_service_excluded',exclusion_reason='该指南不是劳动仲裁或调解申请')
                            if not any(r.get('id')==record.get('id') for r in excluded):excluded.append(record)
                            for other in item['observations']:
                                if other.get('final_url')==record.get('guide_url'):other['non_target_service']=title
                            continue
                        region=normalized['region_name'] or record.get('region_name','')
                        if len(region)>30 or re.search('无法选中|不支持办理|确认|重置|请选择|取消',region):region=''
                        record.update(service_name=title,region_name=region,region_code=record.get('region_code') or normalized['region_code'],authority=record.get('authority') if record.get('source_response_url') else normalized['authority'])
                        if record['region_code'] in names:record.update(region_name=names[record['region_code']],jurisdiction_status='official_directory')
                        if not record.get('workflow_text') and not record.get('steps') and not record.get('flow_review_note') and any(label in text for label in FLOW_LABELS):
                            page=await ctx.new_page()
                            try:
                                await page.goto(record['guide_url'],timeout=25000,wait_until='domcontentloaded');await settle(page)
                                flow_text,flow=await asyncio.wait_for(capture_flow(page,directory,record['stage']+'-continued'),timeout=90)
                                repaired=guide_record(item,observation,text,flow_text)
                                if repaired.get('workflow_text') or flow.get('structured_steps'):
                                    record.update(workflow_text=repaired['workflow_text'],steps=flow.get('structured_steps',[]),state='captured',flow_screenshot=flow.get('screenshot'))
                                    item['observations'].append(flow)
                                    print('FLOW-REPAIR',item['slug'],title,flush=True)
                                else:record['flow_review_note']='已打开流程标签，页面未提供可提取的流程文字；原截图保留'
                            except Exception as exc:record['flow_review_note']='流程续查未完成：'+str(exc)[:160]
                            finally:await page.close()
                        valid.append(record)
                        catalog.update(guides=valid+originals[position+1:],excluded_guides=excluded);write_json(path,catalog)
                        write_json(directory/'observations.json',item)
                finally:await ctx.close()
            catalog.update(guides=valid,excluded_guides=excluded)
            catalog['coverage'].update(captured_guides=len(valid),workflow_guides=sum(bool(r.get('workflow_text') or r.get('steps')) for r in valid),excluded_guides=len(excluded))
            for o in item['observations']:
                if o['stage'].startswith('district-') and o['stage'].endswith('-templates'):o['report_include']=False
            chosen=set()
            for record in sorted(valid,key=lambda r:(not bool(r.get('templates')),not bool(r.get('workflow_text') or r.get('steps')))):
                if record.get('state')=='evidence_invalid' or record['guide_url'] in chosen:continue
                observation=next((o for o in item['observations'] if o['stage']==record.get('stage') and not o.get('superseded_by') and not o.get('non_target_service')),None)
                if observation:
                    observation['report_include']=True;chosen.add(record['guide_url'])
                    if len(chosen)==3:break
            item['workflow_coverage']=catalog['coverage'];write_json(path,catalog);write_json(directory/'observations.json',item);done+=1;progress(done,'流程复核 '+item['name'])
        await asyncio.gather(*(one(i,x) for i,x in enumerate(items,1)));await browser.close()
    write_json(folder/'results.json',items);return items
