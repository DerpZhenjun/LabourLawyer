"""Resume from saved searches, expanding public guide and district evidence."""
import asyncio,json,os,re,time,hashlib
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,unquote
from pathlib import Path
from lxml import html
from portal_audit_capture import official,settle,snapshot,search_outcome,search
from portal_guide_navigation import follow_public_guide,clicked_page,capture_materials,body_text
from portal_interactions import confirm_search_region,scan_scroll,GUIDE_LABELS
from portal_workflows import PublicResponses,capture_flow,guide_record,parse_public_record,save_catalog,official_region_names,service_title,arbitration_service

def pending_urls(entries):
    """Keep a failed guide URL resumable even when its error follows the URL."""
    return list(dict.fromkeys(e.split(' ',1)[0] for e in entries if official(e.split(' ',1)[0])))

def guide_stage(url):
    return 'district-'+hashlib.sha256(url.encode()).hexdigest()[:12]

def saved_urls(folder,item):
    urls=[]
    for obs in item['observations']:
        if obs.get('final_url') and not obs.get('superseded_by') and ('guide' in obs['stage'] or obs['stage'].endswith('-templates')) and official(obs['final_url']):
            if '#material' not in obs['final_url']:urls.append(obs['final_url'])
        source=folder/obs.get('html_file','missing')
        if not source.is_file():continue
        try:tree=html.fromstring(source.read_text(encoding='utf8'))
        except ValueError:continue
        for a in tree.xpath('//a[@href]|//*[@data-url]'):
            label=''.join(a.itertext()).strip();href=a.get('href') or a.get('data-url');context=label+' '+a.get('data-title','')
            if official(href) and ('劳动' in context and re.search('仲裁|调解',context) or label in GUIDE_LABELS and '劳动' in a.get('data-title','')):urls.append(href)
    return list(dict.fromkeys(urls))

async def discover_guides(page,folder,stage,recorder):
    """Walk visible results and public guide buttons, including picker pagination."""
    found=[];actions=[];seen=set();incomplete=[]
    original=page.url;deadline=time.monotonic()+90
    for number in range(1,51):
        await confirm_search_region(page);await scan_scroll(page)
        text=await body_text(page);signature=re.sub(r'\s+','',text)
        if signature in seen:break
        seen.add(signature)
        for frame in page.frames:
            anchors=await frame.locator('a[href],[data-url]').evaluate_all(r'''ns=>ns.map(n=>({url:n.href||n.getAttribute('data-url'),text:(n.innerText||'')+' '+(n.getAttribute('data-title')||'')}))''')
            for a in anchors:
                if official(a['url']) and re.search('劳动.*(仲裁|调解)',a['text']) and not re.search('法规|新闻|通知|条例|办法|查询',a['text']):found.append(a['url'])
            for label in GUIDE_LABELS:
                targets=frame.get_by_text(label,exact=True)
                for index in range(min(await targets.count(),200)):
                    if time.monotonic()>deadline:incomplete.append('指南发现达到单页时间上限，需续查');break
                    if 'zwfw.tj.gov.cn' in page.url and '区/县' in text and index>0:break
                    target=targets.nth(index)
                    try:
                        if not await target.is_visible():continue
                        context=await target.evaluate(r'''n=>{let p=n;for(let i=0;p&&i<8;i++,p=p.parentElement){const t=p.innerText||'';if(/劳动.*(仲裁|调解)/.test(t)&&t.length<2500)return t;}return n.parentElement?.innerText||'';}''')
                        # District modal rows need not repeat the service name.
                        picker='区/县' in text and '劳动' in text and '仲裁' in text
                        if not picker and not re.search('劳动.*(仲裁|调解)',context):continue
                        href=await target.evaluate('n=>n.href||n.getAttribute("data-url")||n.getAttribute("href")')
                        if href and official(href):found.append(href);continue
                        before=set(page.context.pages);guide=await clicked_page(page,target)
                        if guide.url!=original and official(guide.url):found.append(guide.url)
                        actions.append(dict(button=label,row=context[:180],url=guide.url))
                        if guide!=page:await guide.close()
                        elif page.url!=original:
                            await page.goto(original,timeout=30000,wait_until='domcontentloaded');await settle(page)
                            # A same-tab navigation resets result pagination.
                            incomplete.append('同标签页导航后结果分页需续查');break
                    except Exception as exc:incomplete.append(str(exc)[:160])
        next_button=None
        for frame in page.frames:
            for selector in ('button.btn-next:not([disabled]):visible','button:has-text("下一页"):not([disabled]):visible','a:has-text("下一页"):visible','li.ant-pagination-next:not(.ant-pagination-disabled):visible','.el-pagination .number:visible'):
                loc=frame.locator(selector)
                for i in range(min(await loc.count(),60)):
                    node=loc.nth(i)
                    if '.number' in selector and (await node.inner_text()).strip()!=str(number+1):continue
                    if re.search('disabled',await node.get_attribute('class') or ''):continue
                    next_button=node;break
                if next_button:break
            if next_button:break
        if 'zwfw.tj.gov.cn' in page.url and '区/县' in text:break
        if not next_button or time.monotonic()>deadline:break
        try:await next_button.click(timeout=3000);await settle(page)
        except Exception as exc:incomplete.append('分页未完成：'+str(exc)[:120]);break
    if number==50:incomplete.append('结果页超过50页，需续查')
    return list(dict.fromkeys(found)),actions,list(dict.fromkeys(incomplete))

async def tianjin_catalog(context,recorder):
    """Page an observed anonymous official directory, never the application API."""
    seeds=[r for r in list(recorder.records) if '/task/list-task-dept2?' in r['url']]
    found=[]
    for seed in seeds:
        parts=urlsplit(seed['url']);query=dict(parse_qsl(parts.query))
        for number in range(1,51):
            query.update(current=str(number),size='10')
            url=urlunsplit(parts._replace(query=urlencode(query)))
            response=await context.request.get(url,timeout=20000)
            if not response.ok:break
            body=await response.text();data=json.loads(body)
            recorder.records.append(dict(url=url,method='GET',post_data=None,status=response.status,body=body,sha256=__import__('hashlib').sha256(body.encode()).hexdigest()))
            rows=(data.get('result') or {}).get('taskList') or []
            for row in rows:
                if row.get('itemId'):
                    # Route and taskCode mapping are demonstrated by the clicked
                    # guide and official task directory saved in this same batch.
                    found.append(dict(url='https://zwfw.tj.gov.cn/#/operatingInstruction?taskCode='+row['itemId'],region_name=row.get('areaName',''),region_code=row.get('areaCode',''),authority=row.get('deptName',''),service_name=row.get('zixiang','')))
            if len(rows)<10:break
    return {r['url']:r for r in found}

async def enrich(folder,items,progress):
    from playwright.async_api import async_playwright
    from portal_audit import write_json
    temp=folder/'temp';temp.mkdir(exist_ok=True);os.environ.update(TEMP=str(temp.resolve()),TMP=str(temp.resolve()))
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True,env=os.environ.copy())
        semaphore=asyncio.Semaphore(3);done=0
        async def one(item):
            nonlocal done
            async with semaphore:
                directory=folder/item['slug'];saved=directory/'workflows.json'
                if item.get('enrichment_version')==2 and saved.is_file():
                    checkpoint=json.loads(saved.read_text(encoding='utf8'))
                    resumable=pending_urls(checkpoint.get('coverage',{}).get('pending_guides',[]))
                    if not resumable:
                        done+=1;progress(done,item['name']);return
                context=await browser.new_context(locale='zh-CN',viewport={'width':1440,'height':1000},accept_downloads=True)
                context.set_default_timeout(4000);recorder=PublicResponses(context);urls=saved_urls(directory,item);records=[];pending=[];regional={}
                if saved.is_file():
                    checkpoint=json.loads(saved.read_text(encoding='utf8'));records=checkpoint.get('guides',[])
                    urls.extend(checkpoint.get('coverage',{}).get('discovered_urls',[]))
                    urls.extend(pending_urls(checkpoint.get('coverage',{}).get('pending_guides',[])))
                public_saved=directory/'public-guide-responses.json'
                if public_saved.is_file():recorder.records=json.loads(public_saved.read_text(encoding='utf8'))
                try:
                    for number,old in enumerate(list(item['searches']) if item.get('enrichment_version')!=2 else [],1):
                        url=old.get('final_url') or old.get('requested_url')
                        if not official(url or '') or not old.get('enter_submitted'):continue
                        page=await context.new_page()
                        try:
                            await page.goto(url,timeout=30000,wait_until='domcontentloaded');await settle(page)
                            confirmations=await confirm_search_region(page);scan=await scan_scroll(page)
                            visible=await body_text(page)
                            # Tianjin stores the query in session state, not its
                            # URL. A URL-only revisit must not become a false
                            # negative search result. Re-submit only these cases.
                            fresh_search=None
                            result_visible=bool(re.search('搜索结果|相关结果|检索结果|为您找到|找到.{0,15}结果|相关服务|暂无.{0,8}(结果|数据)|没有找到',visible))
                            if not result_visible and not re.search('ERR_CERT_|ERR_CONNECTION|Access Denied|Forbidden|验证码',visible):
                                if page.url!=item['portal_url']:
                                    await page.goto(item['portal_url'],timeout=30000,wait_until='domcontentloaded');await settle(page)
                                page,fresh_search=await search(page,directory,old['keyword'],number,stage=f'search-{number:02d}-resubmitted-'+str(time.time_ns()))
                                fresh_search['revisit_reason']='原结果网址未保存检索状态，需要重新提交检索'
                                confirmations.extend(fresh_search.get('action',{}).get('public_confirmations',[]));scan=fresh_search.get('action',{}).get('scroll_scan',scan)
                            current=await snapshot(page,directory,f'search-{number:02d}-continued-'+str(time.time_ns()),action='继续检查既有搜索结果的地区提示及页面下方内容')
                            visible=await body_text(page)
                            confirmed=bool(re.search('搜索结果|相关结果|检索结果|为您找到|相关服务|暂无.{0,8}(结果|数据)|没有找到',visible))
                            confirmed=confirmed or (old['keyword'] in unquote(page.url) and bool(current.get('candidate_links')))
                            current.update(keyword=old['keyword'],enter_submitted=fresh_search['enter_submitted'] if fresh_search else old.get('enter_submitted',False),result_page_confirmed=confirmed and not current.get('page_problem'),search_scope='；'.join(c['scope'] for c in confirmations if c.get('scope')) or old.get('search_scope','页面默认检索范围'),public_confirmations=confirmations,scroll_scan=scan,continued_from=old['stage'])
                            if current.get('page_problem'):
                                pending.append('搜索结果续查访问异常：'+url)
                                item.setdefault('failed_search_revisits',[]).append(current)
                            else:
                                current['outcome']=search_outcome(current);old['superseded_by']=current['stage']
                                for prior in item['observations']:
                                    if prior['stage']==old['stage']:prior['superseded_by']=current['stage']
                                item['searches'][number-1]=current
                                item['observations']=[o for o in item['observations'] if o['stage']!=current['stage']];item['observations'].append(current)
                                new,actions,errors=await discover_guides(page,directory,current['stage'],recorder);urls.extend(new);pending.extend(errors);current['guide_discovery']=actions
                                # Click service titles to expose non-anchor district
                                # modals before enumerating their guide buttons.
                                candidates=current.get('candidate_links',[]);candidate_names=set()
                                for c in candidates:
                                    label=re.sub(r'\s','',c['text'])
                                    if label in candidate_names or len(label)>90:continue
                                    if c.get('click') and not re.search(r'^(?:公共服务)?劳动.{0,45}(?:仲裁|调解).{0,12}(?:申请|受理|调解)$',label):continue
                                    candidate_names.add(label)
                                    if not c.get('click'):
                                        if official(c.get('url','')):urls.append(c['url'])
                                        continue
                                    try:
                                        target=page.get_by_text(c['text'],exact=True).first
                                        reached=await clicked_page(page,target)
                                        new,actions,errors=await discover_guides(reached,directory,current['stage'],recorder);urls.extend(new);pending.extend(errors)
                                        if reached.url!=url and official(reached.url):urls.append(reached.url)
                                        if reached!=page:await reached.close()
                                        else:
                                            await page.goto(url,timeout=30000);await settle(page)
                                    except Exception as exc:pending.append('入口未展开：'+c['text']+' '+str(exc)[:80])
                        except Exception as exc:pending.append('续查异常：'+url+' '+str(exc)[:100])
                        finally:
                            for pg in list(context.pages):await pg.close()
                        write_json(directory/'observations.json',item)
                        print('SEARCH-CONTINUED',item['slug'],number,'guides',len(set(urls)),flush=True)
                    if item['slug']=='tianjin':
                        try:regional=await tianjin_catalog(context,recorder);urls.extend(regional)
                        except Exception as exc:pending.append('地区目录未完成：'+str(exc)[:180])
                    if official(item.get('source_url','')):urls.append(item['source_url'])
                    urls=list(dict.fromkeys(urls));visited={r['guide_url'] for r in records};index=0;deadline=time.monotonic()+1800
                    while index<len(urls) and index<500 and time.monotonic()<deadline:
                        url=urls[index];index+=1
                        if url in visited:continue
                        visited.add(url);page=await context.new_page();stage=guide_stage(url)
                        try:
                            await page.goto(url,timeout=30000,wait_until='domcontentloaded');await settle(page)
                            page,selected,actions=await follow_public_guide(page,item['scope'],directory,stage)
                            if not official(page.url):pending.append(url);continue
                            text=await body_text(page)
                            is_guide=bool(re.search('申请材料|所需材料|办理流程|流程说明|材料目录',text) and re.search('办理部门|实施主体|受理机构|办理机构|基本信息|仲裁申请书',text))
                            title=service_title(text)
                            if is_guide and title and not arbitration_service(title):
                                item.setdefault('excluded_services',[]).append(dict(url=page.url,title=title,reason='非劳动仲裁或调解申请事项'));continue
                            if not is_guide:
                                new,_,errors=await discover_guides(page,directory,stage,recorder)
                                urls.extend(u for u in new if u not in urls);pending.extend(errors);continue
                            flow_text,flow=await capture_flow(page,directory,stage)
                            observation=await capture_materials(page,directory,stage+'-templates',item['scope'])
                            observation.update(flow_screenshot=flow.get('screenshot'),guide_discovery_url=url)
                            # The report shows representative distinct guide pages;
                            # all districts retain evidence and structured data.
                            observation['report_include']=sum(o.get('report_include',False) for o in item['observations'])<3
                            item['observations'].extend([flow,observation])
                            text=(directory/observation['text_file']).read_text(encoding='utf8')
                            record=guide_record(item,observation,text,flow_text)
                            if flow.get('structured_steps'):record.update(steps=flow['structured_steps'],state='captured')
                            region_names=official_region_names(recorder.records)
                            if record['region_code'] in region_names:record.update(region_name=region_names[record['region_code']],jurisdiction_status='official_directory')
                            if url in regional:record.update({k:v for k,v in regional[url].items() if k!='url'})
                            for response in reversed(recorder.records):
                                if '/get-regulation-info' in response['url'] and dict(parse_qsl(urlsplit(response['url']).query)).get('item_id')!=dict(parse_qsl(urlsplit(page.url).fragment.split('?',1)[-1])).get('taskCode'):continue
                                if '/get-regulation-info' not in response['url'] and '/gml/web10002' not in response['url']:continue
                                try:normalized=parse_public_record(response)
                                except (ValueError,TypeError):continue
                                if normalized:
                                    if '/gml/web10002' in response['url']:
                                        data=json.loads(json.loads(response['body'])['C-Response-Body'])
                                        if data.get('id') not in page.url:continue
                                    record.update(normalized);record['state']='captured' if record.get('workflow_text') or record.get('steps') else 'workflow_not_detected';break
                            records.append(record)
                            save_catalog(directory,item,records,urls,pending+urls[index:]);write_json(directory/'observations.json',item)
                            print('DISTRICT',item['slug'],index,'/',len(urls),record.get('region_name'),record['state'],flush=True)
                        except Exception as exc:pending.append(url+' '+str(exc)[:160])
                        finally:
                            for pg in list(context.pages):await pg.close()
                    pending.extend(urls[index:]);item['enrichment_version']=2;item.pop('ai_review',None)
                    # Keep successful historic observations but supersede old
                    # template conclusions when the same guide was recaptured.
                    for old in item['observations']:
                        if not old['stage'].endswith('-templates') or old.get('material_capture_version')==5:continue
                        replacement=next((o for o in item['observations'] if o.get('material_capture_version')==5 and o.get('final_url')==old.get('final_url') and not o.get('page_problem')),None)
                        if replacement:old['superseded_by']=replacement['stage']
                    save_catalog(directory,item,records,urls,pending)
                finally:
                    await recorder.flush(directory);await context.close();done+=1;progress(done,item['name']);write_json(directory/'observations.json',item)
        await asyncio.gather(*(one(x) for x in items));await browser.close()
    write_json(folder/'results.json',items)
    return items
