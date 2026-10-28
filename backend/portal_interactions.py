"""Public guide navigation shared by every province collector."""
import re

GUIDE_LABELS=('查看指南','办事指南','办事指南详情')
MATERIAL_LABELS=('申请材料','申报材料','办事材料','所需材料','材料目录','材料清单','查看材料清单','带什么')

async def select_capital(page,capital):
    """Use public city controls when available, recording actual selections."""
    actions=[]
    for frame in page.frames:
        for label in ('切换区域','切换地区','请选择地区','选择地区','地区选择'):
            loc=frame.get_by_text(label,exact=True)
            for i in range(min(await loc.count(),8)):
                try:
                    node=loc.nth(i)
                    if not await node.is_visible():continue
                    await node.click(timeout=1800);await page.wait_for_timeout(350)
                    actions.append({'action':'open_region_picker','label':label});break
                except Exception:continue
            if actions:break
        for name in (capital,capital.removesuffix('市')):
            loc=frame.get_by_text(name,exact=True)
            for i in range(min(await loc.count(),40)):
                try:
                    node=loc.nth(i)
                    if not await node.is_visible():continue
                    clickable=await node.evaluate("n=>n.matches('a,button,[onclick],[role=button]')||getComputedStyle(n).cursor==='pointer'")
                    if not clickable:continue
                    await node.click(timeout=1800);await page.wait_for_timeout(800)
                    actions.append({'action':'select_capital','name':name});return actions
                except Exception:continue
    return actions

async def confirm_search_region(page):
    actions=[]
    for frame in page.frames:
        dialogs=frame.locator('[role=dialog]:visible,.el-message-box:visible,.el-dialog:visible,.ivu-modal:visible,.modal:visible,.layui-layer:visible,.ui-dialog:visible')
        for index in range(min(await dialogs.count(),12)):
            dialog=dialogs.nth(index)
            try:
                text=await dialog.inner_text(timeout=1500)
                if not re.search(r'是否搜索.{0,30}(所在地|地区)|当前IP所在地',text,re.I):continue
                for label in ('确定','是','确认'):
                    button=dialog.get_by_text(label,exact=True)
                    if await button.count() and await button.first.is_visible():
                        await button.first.click(timeout=3000)
                        city=re.search(r'所在地为\s*([^，,。；;？?\n]{2,30})',text)
                        actions.append(dict(action='confirm_search_region',button=label,scope=city.group(1).strip() if city else '',prompt=text[:220]))
                        await page.wait_for_timeout(700)
                        break
            except Exception:continue
    return actions

async def scan_scroll(page,terms=('劳动','仲裁','调解'),max_steps=18):
    """Trigger lazy results below the fold, then focus an actual small result node."""
    scanned=[]
    for frame in page.frames:
        try:
            if frame!=page.main_frame:
                element=await frame.frame_element();await element.scroll_into_view_if_needed(timeout=1500)
            await frame.evaluate('window.scrollTo(0,0)')
            previous=-1
            for step in range(max_steps):
                position=await frame.evaluate('() => ({y:scrollY,h:innerHeight,total:Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)})')
                if position['y']==previous or position['y']+position['h']>=position['total']-8:break
                previous=position['y']
                await frame.evaluate('window.scrollBy(0,Math.max(500,innerHeight*0.8))')
                await page.wait_for_timeout(250)
            candidates=await frame.locator('a,button,[onclick],span,div').evaluate_all('''(ns,terms)=>ns.filter(n=>{
                const t=(n.innerText||'').trim().replace(/\s/g,'');
                return t.length<100 && terms.some(s=>t.includes(s)) && /劳动.*(仲裁|调解)|申请书|证据清单|证据目录/.test(t) && !/仲裁员|委员会.*备案|查询/.test(t) && n.getBoundingClientRect().width>0;
            }).map(n=>({text:(n.innerText||'').trim(),y:n.getBoundingClientRect().top+scrollY})).sort((a,b)=>a.y-b.y)''',list(terms))
            if candidates:
                target=candidates[0];await frame.evaluate('(y)=>window.scrollTo(0,Math.max(0,y-180))',target['y'])
            else:await frame.evaluate('window.scrollTo(0,0)')
            scanned.append(dict(frame_url=frame.url,steps=step+1,results=len(candidates),focused=candidates[0]['text'] if candidates else ''))
        except Exception as exc:scanned.append(dict(frame_url=frame.url,error=str(exc)[:160]))
    return scanned

async def visible_material_names(frame):
    """Read all names in the visible official material table, including ID."""
    return await frame.locator('table:visible').evaluate_all(r'''tables=>{
        const names=[];
        for(const table of tables){
            const rows=Array.from(table.querySelectorAll('tr')).filter(r=>r.closest('table')===table);
            const header=rows.find(r=>Array.from(r.cells).some(c=>(c.innerText||'').replace(/\s/g,'')==='材料名称'));
            if(!header){
                // Some official guides use one vertical table per material.
                const title=table.querySelector('th .lcmc');
                if(title&&title.getClientRects().length&&rows.some(r=>(r.cells?.[0]?.innerText||'').trim()==='材料分类')){
                    const name=(title.innerText||'').trim();if(name&&name.length<100)names.push(name);
                }
                continue;
            }
            const index=Array.from(header.cells).findIndex(c=>(c.innerText||'').replace(/\s/g,'')==='材料名称');
            for(const row of rows.slice(rows.indexOf(header)+1)){
                const cell=row.cells[index];if(!cell||!row.getClientRects().length)continue;
                const clone=cell.cloneNode(true);clone.querySelectorAll('button,.el-tag,.ant-tag,.badge').forEach(n=>n.remove());
                const name=(clone.textContent||'').replace(/已关联电子证照/g,'').replace(/\s+/g,' ').trim();
                if(name&&name.length<100&&!/申请材料总要求|信息真实|材料齐全|材料名称/.test(name))names.push(name);
            }
        }
        return [...new Set(names)];
    }''')

async def material_controls(frame):
    return await frame.locator('a,button,input[type=button],input[type=submit],span,div,[role=button],[onclick]').evaluate_all(r'''ns=>{
        const visible=n=>n.getBoundingClientRect().width>0&&n.getBoundingClientRect().height>0;
        const compact=s=>(s||'').replace(/\s/g,'').trim();
        const result=[];const seen=new Set();
        for(const n of ns){
            if(!visible(n))continue;
            const clickable=n.matches('a,button,input[type=button],input[type=submit],[role=button],[onclick]')||getComputedStyle(n).cursor==='pointer';
            const text=compact(n.innerText||n.value||n.title||'');
            const leafControl=!n.children.length&&/^(?:下载|下载查看|样例下载|模板下载|空白表格|示例样表|模板|示例|.{1,90}\.(?:docx?|pdf|xlsx?))$/.test(text);
            if(!clickable&&!leafControl)continue;
            if(!text||text.length>150)continue;
            if(Array.from(n.querySelectorAll('a,button,span')).some(c=>visible(c)&&compact(c.innerText)===text))continue;
            const download=/下载|查看附件|查看示例|空白表格|样表|^模板$|^示例$|\.docx?$|\.pdf$|\.xlsx?$/.test(text);
            if(!download||/APP|应用|承诺书|客户端下载/.test(text))continue;
            if(Array.from(n.querySelectorAll('a,button,span,div,p,[role=button],[onclick]')).some(c=>visible(c)&&compact(c.innerText).length<text.length&&/下载|查看附件|^模板$|^示例$|\.docx?$|\.pdf$/.test(compact(c.innerText))))continue;
            let row=n.closest('tr,[role=row],.material-item,.material-row,.item,li');
            const viewer=n.closest('form.materialinfo-detail,[role=dialog],.modal');
            const namedRow=viewer&&Array.from(viewer.querySelectorAll('tr')).find(r=>compact(r.cells?.[0]?.innerText)==='材料名称');
            const verticalTable=n.closest('table');
            const verticalTitle=verticalTable?.querySelector('th .lcmc');
            const verticalName=verticalTitle&&Array.from(verticalTable.rows).some(r=>compact(r.cells?.[0]?.innerText)==='材料分类')?compact(verticalTitle.innerText):'';
            const detailName=compact(namedRow?.cells?.[1]?.innerText)||verticalName;
            const attr=n.getAttribute('doc_name')||n.getAttribute('data-name')||detailName||'';
            // A whole-page "下载" button exports the guide, even when a broad
            // ancestor also contains application/evidence material names.
            let specificRow=n.closest('tr,[role=row],.material-item,.material-row,.item');
            if(specificRow&&!specificRow.matches('tr,[role=row]')&&(compact(specificRow.innerText).length>700||specificRow.querySelectorAll('tr').length>1))specificRow=null;
            if(/^(?:下载|一键下载|全部下载|下载至本地|下载到本地)$/.test(text)&&!specificRow&&!attr&&!/\.docx?(?:[?#]|$)/i.test(n.href||''))continue;
            if(/指南下载|下载(?:办事)?指南/.test(text))continue;
            if(row&&!/申请书|证据清单|证据目录/.test(compact(row.innerText))&&!/申请书|证据清单|证据目录/.test(detailName))continue;if(attr&&!/申请书|证据清单|证据目录/.test(attr))continue;
            if(!row){let p=n.parentElement;for(let i=0;p&&i<5;i++,p=p.parentElement){const t=compact(p.innerText);if(t.length<700&&/申请书|证据清单|证据目录/.test(t)){row=p;break;}}}
            const context=compact(row?row.innerText:text);
            if(!/申请书|证据清单|证据目录|证据材料清单/.test(context+attr))continue;
            if(/收件回执|受理通知书|送达回证|裁决书|不予受理决定/.test(context+attr))continue;
            const cells=row?Array.from(row.querySelectorAll('td,[role=cell]')):[];
            const filename=/申请书|证据清单|证据目录/.test(text)&&/\.docx?$|\.pdf$/.test(text)?text:'';
            const doc=attr||filename||cells.map(c=>compact(c.innerText)).find(t=>t.length<100&&/申请书|证据清单|证据目录/.test(t))||context.match(/(?:劳动人事争议|劳动仲裁|仲裁)?申请书|证据(?:材料)?清单|证据目录/)?.[0]||'申请书或证据清单';
            const href=n.href||n.getAttribute('data-url')||'';
            const kindText=text+(detailName?compact(n.closest('td')?.previousElementSibling?.innerText):'');
            const kind=/样|示例|示范/.test(kindText)?'sample':/空表|空白|格式文本|表格下载|^模板$/.test(kindText)?'blank':'document';
            const key=doc+'|'+text+'|'+href;if(seen.has(key))continue;seen.add(key);n.setAttribute('data-portal-material-index',String(result.length));
            result.push({text:text.includes(doc)?text:doc+'（'+text+'）',control_text:text,material_name:doc,url:href.startsWith('http')?href:'',href:n.getAttribute('href')||'',click:!href.startsWith('http'),kind,selector:'[data-portal-material-index="'+result.length+'"]',doc_id:n.getAttribute('doc_id')||'',context:context.slice(0,1200)});
        }
        return result;
    }''')

async def activate_section(page,labels):
    """Scroll in-page anchors without replacing a SPA hash route/query."""
    for frame in page.frames:
        for label in labels:
            loc=frame.get_by_text(label,exact=True)
            # A sidebar hash link may merely scroll to the tab strip. Prefer
            # the actual tab control so hidden workflow/material content opens.
            ordered=[]
            for index in range(min(await loc.count(),20)):
                node=loc.nth(index)
                href=await node.get_attribute('href') or ''
                semantics=await node.evaluate("n=>({clickable:n.matches('a,button,[role=tab],[role=button],[onclick]')||getComputedStyle(n).cursor==='pointer',child:Array.from(n.querySelectorAll('a,button,[role=tab],[role=button],[onclick]')).some(c=>(c.innerText||'').trim()===(n.innerText||'').trim())})")
                if not semantics['clickable']:continue
                # A list item and its real anchor can have identical text.
                # Clicking the inert parent must not count as activating a tab.
                ordered.append(((2 if semantics['child'] else 0)+(1 if href.startswith('#') and not href.startswith('#/') else 0),index))
            for _,index in sorted(ordered):
                target=loc.nth(index)
                try:
                    if not await target.is_visible():continue
                    href=await target.get_attribute('href') or ''
                    if href.startswith('#') and not href.startswith('#/'):
                        anchor=frame.locator('[id="'+href[1:]+'"]')
                        if await anchor.count():await anchor.first.scroll_into_view_if_needed(timeout=2000)
                        else:await target.scroll_into_view_if_needed(timeout=2000)
                    else:
                        if href and not href.startswith(('javascript:','#')):continue
                        await target.click(timeout=2500)
                    await page.wait_for_timeout(600)
                    return True
                except Exception:continue
    return False

async def focus_material_download(page):
    """Put the actual document row in the screenshot, not its FAQ mention."""
    for frame in page.frames:
        # Public guides also collapse vertical material tables with their own
        # header/caret. Open only the observed application/evidence table.
        for header in await frame.locator('tr.gray_line:has(.lcmc):has(.gray_jt_icon)').all():
            try:
                title=(await header.locator('.lcmc').inner_text()).strip()
                if len(title)>100 or not re.search('申请书|证据清单|证据目录',title):continue
                expanded=await header.evaluate("n=>{const row=Array.from(n.closest('table').rows).find(r=>r!==n);return !!row&&getComputedStyle(row).display!=='none'}")
                if await header.is_visible() and not expanded:
                    await header.click(timeout=2500);await page.wait_for_timeout(500)
            except Exception:continue
        for header in await frame.locator('.el-collapse-item__header').all():
            try:
                title=(await header.inner_text()).strip()
                if len(title)>100 or not re.search('申请书|证据清单|证据目录',title) or re.search('常见|如何|是否|需要',title):continue
                expanded=await header.evaluate("n=>n.classList.contains('is-active')||n.parentElement?.classList.contains('is-active')||n.getAttribute('aria-expanded')==='true'")
                if await header.is_visible() and not expanded:
                    await header.click(timeout=2500);await page.wait_for_timeout(500)
            except Exception:continue
        controls=await material_controls(frame)
        controls.sort(key=lambda c:'一键' in c['control_text'])
        if not controls:
            # Some guides expose public attachment details in a material row.
            # This is a read-only viewer, separate from application submission.
            for viewer in await frame.locator('tr [onclick*="popupwindow"]').all():
                try:
                    label=(await viewer.inner_text()).strip()
                    row=await viewer.evaluate("n=>n.closest('tr')?.innerText||''")
                    if label not in ('查看详情','查看附件') or not re.search('申请书|证据清单|证据目录',row) or re.search('收件回执|受理通知书|裁决书',row):continue
                    await viewer.click(timeout=2500);await page.wait_for_timeout(700)
                    controls=await material_controls(frame)
                    if controls:break
                except Exception:continue
        for control in controls:
            if not control.get('selector'):continue
            try:
                if frame!=page.main_frame:
                    element=await frame.frame_element();await element.scroll_into_view_if_needed(timeout=2000)
                await frame.add_style_tag(content='* { scroll-behavior: auto !important; }')
                node=frame.locator(control['selector'])
                await node.scroll_into_view_if_needed(timeout=2500)
                await node.evaluate("n=>{const table=n.closest('table');const vertical=table?.querySelector('th .lcmc');const row=(vertical?table:null)||n.closest('tr,[role=row],.material-item,.material-row,.item')||n.parentElement;const r=row.getBoundingClientRect();const y=r.height>innerHeight-240?n.getBoundingClientRect().top:r.top;window.scrollTo({top:scrollY+y-180,behavior:'instant'})}")
                await page.wait_for_timeout(400)
                visible=await node.evaluate('n=>{const r=n.getBoundingClientRect();return r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth}')
                if visible:return dict(material=control['material_name'],control=control['control_text'],frame_url=frame.url,control_in_viewport=True)
            except Exception:continue
    # A material row remains useful evidence when the download column is empty.
    for frame in page.frames:
        if frame!=page.main_frame:
            try:
                if not await (await frame.frame_element()).is_visible():continue
            except Exception:continue
        for node in await frame.get_by_text(re.compile('申请书|证据清单|证据目录')).all():
            try:
                text=(await node.inner_text()).strip()
                if len(text)>150 or re.search('常见|如何|是否|哪些|需要|应当|事实与理由',text) or not await node.is_visible():continue
                await node.evaluate("n=>n.scrollIntoView({block:'center',behavior:'instant'})")
                await page.wait_for_timeout(300)
                return dict(material=text,control='',frame_url=frame.url,material_row_in_viewport=True)
            except Exception:continue
    return None
