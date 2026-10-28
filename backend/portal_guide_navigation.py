"""Resolve public district pickers before inspecting the guide's materials."""
import re
from portal_interactions import GUIDE_LABELS,MATERIAL_LABELS,activate_section,confirm_search_region,scan_scroll,focus_material_download

async def body_text(page):
    texts=[]
    for frame in page.frames:
        try:texts.append(await frame.locator('body').inner_text(timeout=2000))
        except Exception:pass
    return '\n'.join(texts)

async def clicked_page(page,target):
    from portal_audit_capture import settle
    existing=set(page.context.pages)
    await target.click(timeout=4000);await page.wait_for_timeout(700)
    fresh=[p for p in page.context.pages if p not in existing]
    result=fresh[-1] if fresh else page
    await settle(result)
    return result

async def follow_public_guide(page,scope='',folder=None,stage='guide'):
    from portal_audit_capture import jurisdiction_choices,snapshot
    from province_experience import POLICY
    slug=folder.name if folder else ''
    capital=POLICY['capitals'].get(slug)
    if capital:scope=capital
    selected=[];actions=[]
    for step in range(10):
        actions.extend(await confirm_search_region(page))
        text=await body_text(page)
        if any(w in text for w in MATERIAL_LABELS) and any(w in text for w in ('承诺办结','办理流程','基本信息','法定办结')) and not re.search('区/县|选择办理区域|请选择办理',text):break
        picker=bool(re.search('选择办理区域|选择办理地点|区/县|请选择.{0,8}(地区|区域)|选择实施清单',text))
        if picker and folder and not actions:
            await snapshot(page,folder,stage+'-district-picker',action='事项列出不同地区的公开办理入口')
        names=jurisdiction_choices(scope)
        choices=[]
        for name in names:choices.extend([name,name.removesuffix('省').removesuffix('市')])
        # A district/department list (e.g. Tianjin) is followed through the
        # visible guide button; it is not an online-application submission.
        guide_targets=[]
        for frame in page.frames:
            for label in GUIDE_LABELS:
                loc=frame.get_by_text(label,exact=True)
                for index in range(min(await loc.count(),100)):
                    target=loc.nth(index)
                    try:
                        if not await target.is_visible():continue
                        row=await target.evaluate('n=>{let p=n;for(let i=0;p&&i<6;i++,p=p.parentElement){if(p.tagName==="TR"||p.getAttribute("role")==="row"||(p.innerText||"").includes("在线办理"))return p.innerText;}return n.parentElement?.innerText||""}')
                        rank=0 if any(name in row for name in names) else 1
                        guide_targets.append((rank,index,label,target,row))
                    except Exception:pass
        if guide_targets and (picker or not any(w in text for w in MATERIAL_LABELS) or 'search' in page.url or '/so/' in page.url):
            opened=False
            for _,index,label,target,row in sorted(guide_targets,key=lambda v:(v[0],v[1])):
                try:
                    page=await clicked_page(page,target)
                    selected.append(re.sub(r'\s+',' ',row).strip()[:180]);actions.append(dict(action='open_public_guide',button=label,row=row[:250]))
                    opened=True;break
                except Exception:continue
            if opened:continue
        if picker:
            opened=False
            for frame in page.frames:
                for name in choices:
                    if not name or name in selected:continue
                    loc=frame.get_by_text(name,exact=True)
                    for index in reversed(range(min(await loc.count(),70))):
                        try:
                            target=loc.nth(index)
                            if not await target.is_visible():continue
                            await target.click(timeout=700,trial=True)
                            page=await clicked_page(page,target);selected.append(name);actions.append(dict(action='select_public_region',name=name));opened=True;break
                        except Exception:continue
                    if opened:break
                if opened:break
            if opened:continue
            # When a capital needs a district, choose the first visible public
            # district control in DOM order. Never use an online-apply button.
            if capital:
                for frame in page.frames:
                    loc=frame.locator('button,a,[role=button],li,span')
                    for index in range(min(await loc.count(),500)):
                        target=loc.nth(index)
                        try:
                            name=(await target.inner_text(timeout=500)).strip()
                            if not re.fullmatch(r'[\u4e00-\u9fff]{2,12}(?:区|县|旗)',name) or name in selected or not await target.is_visible():continue
                            clickable=await target.evaluate("n=>n.matches('button,a,[role=button],[onclick]')||getComputedStyle(n).cursor==='pointer'")
                            if not clickable:continue
                            page=await clicked_page(page,target);selected.append(name);actions.append(dict(action='select_first_visible_district',name=name));opened=True;break
                        except Exception:continue
                    if opened:break
                if opened:continue
        if picker or '您选择的是' in text:
            confirmed=False
            for frame in page.frames:
                loc=frame.get_by_text('确定',exact=True)
                for index in reversed(range(min(await loc.count(),30))):
                    try:
                        target=loc.nth(index)
                        if not await target.is_visible() or await target.is_disabled():continue
                        classes=await target.get_attribute('class') or ''
                        if re.search(r'\bdissure\b|\bdisabled\b',classes):continue
                        page=await clicked_page(page,target);actions.append(dict(action='confirm_public_region',button='确定'));confirmed=True;break
                    except Exception:continue
                if confirmed:break
            if confirmed:continue
        break
    return page,selected,actions

async def capture_materials(page,folder,stage,scope='',keyword='',resolution=None,download=True):
    from portal_audit_capture import snapshot,settle
    page,selected,actions=await follow_public_guide(page,scope,folder,stage)
    original_url=page.url
    await activate_section(page,MATERIAL_LABELS)
    if page.url!=original_url and '#/' in original_url and '#/' not in page.url:
        # Protect persisted evidence from a website's broken plain hash anchor.
        await page.goto(original_url,wait_until='domcontentloaded',timeout=30000);await settle(page)
        actions.append(dict(action='restore_spa_route',url=original_url))
    scan=await scan_scroll(page,('申请书','证据清单','证据目录'))
    focused=await focus_material_download(page)
    obs=await snapshot(page,folder,stage,action='进入公开指南并检查文书下载控件及材料表')
    obs.update(keyword=keyword,material_capture_version=6,material_focus=focused,selected_jurisdictions=selected,public_navigation=actions,scroll_scan=scan)
    detected=bool(obs.get('template_links'))
    obs.update(template_area_visible=detected,templates_detected=detected,template_status='downloads_detected' if detected else 'materials_only' if obs.get('material_names') else 'none')
    if obs.get('page_problem'):obs['template_status']='access_failed'
    from portal_attachment_downloads import download_controls
    if download:await download_controls(page,folder,obs.get('template_links',[]))
    if resolution:obs['guide_resolution']=resolution
    return obs
