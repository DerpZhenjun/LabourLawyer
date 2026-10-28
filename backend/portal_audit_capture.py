"""Three independent searches per region; failures are not negative results."""
import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit,quote
from province_documents import PROVINCE_DOCUMENTS
from terminal_progress import emit
from portal_interactions import confirm_search_region,scan_scroll,material_controls,visible_material_names,activate_section,GUIDE_LABELS,MATERIAL_LABELS

KEYWORDS=('劳动仲裁','劳动人事争议仲裁','劳动人事争议调解')
TERMS=(*KEYWORDS,'劳动争议仲裁','劳动争议调解','劳动关系仲裁')

def official(url):
    p=urlsplit(url)
    return p.scheme in ('http','https') and (p.hostname or '').endswith('.gov.cn')

def jurisdiction_choices(scope):
    # Split each administrative level. A greedy match would swallow
    # "江苏省无锡市锡山区" and lose the city needed by the public picker.
    return re.findall(r'[\u4e00-\u9fff]{2,8}?(?:自治区|自治州|自治县|省|市|区|县)',scope)

async def settle(page):
    for event,timeout in [('domcontentloaded',10000),('networkidle',2500)]:
        try: await page.wait_for_load_state(event,timeout=timeout)
        except Exception: pass
    try:
        await page.evaluate('() => Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,2000))])')
        await page.wait_for_timeout(1800)
        for frame in page.frames:
            loading=frame.get_by_text(re.compile(r'^(搜索中|检索中|加载中|正在加载)(\.\.\.|…)?$'))
            if await loading.count() and await loading.first.is_visible():
                try:await loading.first.wait_for(state='hidden',timeout=20000)
                except Exception:pass
    except Exception: pass

async def snapshot(page,folder,stage,url=None,action=''):
    from portal_audit import now,sha
    emit('capture',province=folder.name,message=action or stage,url=url or page.url,output=str(folder))
    obs=dict(stage=stage,started_at=now(),requested_url=url,action=action,errors=[])
    failures=[]
    def failed(req): failures.append(dict(url=req.url.split('?')[0],failure=req.failure))
    def failed_response(resp):
        if resp.status>=400:failures.append(dict(url=resp.url.split('?')[0],http_status=resp.status))
    page.on('requestfailed',failed)
    page.on('response',failed_response)
    try:
        if url:
            main_response=await page.goto(url,wait_until='domcontentloaded',timeout=30000)
            obs['http_status']=main_response.status if main_response else None
    except Exception as exc: obs['errors'].append(str(exc)[:800])
    if url:await settle(page)
    else:await page.wait_for_timeout(350)
    try:
        obs.update(final_url=page.url,title=await page.title(),content_type=await page.evaluate('document.contentType'),frame_urls=[f.url for f in page.frames])
        texts=[];links=[];downloads=[];material_names=[]
        for frame in page.frames:
            try:
                texts.append(await frame.locator('body').inner_text(timeout=2000))
                found=await frame.locator('a:visible,button:visible,[role=button]:visible,[onclick]:visible,[data-bind*=click]:visible,[data-url]:visible,span:visible,div:visible').evaluate_all('''ns=>ns.filter(n=>{
                    const t=(n.innerText||'').trim();return t.length<180 && /劳动.*(仲裁|调解)|申请书|证据清单|证据目录|空白表格/.test(t.replace(/\\s/g,'')) &&
                    (n.tagName==='A'||n.tagName==='BUTTON'||n.hasAttribute('onclick')||n.getAttribute('role')==='button'||n.hasAttribute('data-url')||(n.getAttribute('data-bind')||'').includes('click')||getComputedStyle(n).cursor==='pointer');
                }).map(n=>({text:(n.innerText||'').trim(),url:n.href||'',href:n.getAttribute('href')||'',click:!n.href||n.href.startsWith('javascript:')}))''')
                for entry in found:entry['frame_url']=frame.url
                links.extend(found)
                controls=await material_controls(frame)
                for entry in controls:entry['frame_url']=frame.url
                downloads.extend(controls)
                material_names.extend(await visible_material_names(frame))
            except Exception: pass
        text='\n'.join(texts)
        (folder/f'{stage}.txt').write_text(text,encoding='utf8')
        (folder/f'{stage}.html').write_text(await page.content(),encoding='utf8')
        obs.update(text_file=f'{stage}.txt',html_file=f'{stage}.html',visible_excerpt=text[:1600])
        obs['candidate_links']=[x for x in links if (official(x['url']) or x['click'] and official(x['frame_url'])) and (any(t in re.sub(r'\s','',x['text']) for t in TERMS) or re.search('劳动.{0,18}(仲裁|调解)',re.sub(r'\s','',x['text']))) and len(x['text'])<180 and not re.search('仲裁法|调解法|条例|办法|通知|公告|政策|新闻|怎么办|如何|哪些|是否|查询|仲裁员',x['text'])][:25]
        obs['template_links']=downloads[:50]
        obs['material_names']=list(dict.fromkeys(material_names)) if material_names else list(dict.fromkeys(line.strip() for line in text.splitlines() if 2<len(line.strip())<75 and any(t in line for t in ('申请书','证据清单','证据目录')) and not re.search('应当|申请人|填写|提交|例如|必须',line)))[:12]
        obs['materials_source']='visible_official_table' if material_names else 'visible_document_names'
        diagnostic=text+' '.join(obs['errors'])
        obs['page_problem']=('certificate' if re.search('ERR_CERT_|连接不是私密',diagnostic) else
            'network' if re.search('ERR_CONNECTION|ERR_NAME_|ERR_TIMED_OUT|无法访问此网站|网络异常，请稍后',diagnostic) else
            'blocked' if re.search('验证码|人机验证|Access Denied|403 Forbidden|405.{0,8}Method Not Allowed|412 Precondition|429 Too Many|安全防护.{0,8}拦截',text[:2000],re.I) else
            'render_error' if obs.get('content_type') not in ('text/html','application/xhtml+xml') or text.lstrip().startswith(('<!DOCTYPE','<html')) or re.search(r'(?m)^\s*(搜索中|检索中|加载中|正在加载)(\.\.\.|…)?\s*$',text) else
            'blank' if len(text.strip())<15 else None)
        image=folder/f'{stage}.png'
        # Late scripts and smooth scrolling can move the page after metadata
        # extraction. Confirm the download control again immediately before QA.
        if stage.endswith('-templates') and (downloads or obs['material_names']):
            from portal_interactions import focus_material_download
            obs['capture_material_focus']=await focus_material_download(page)
        try:await page.screenshot(path=str(image),timeout=15000,animations='disabled')
        except Exception:
            # Font-loading timeouts must not discard a rendered public page.
            import base64
            session=await page.context.new_cdp_session(page)
            try:
                captured=await session.send('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
                image.write_bytes(base64.b64decode(captured['data']))
            finally:await session.detach()
        obs.update(screenshot=image.name,screenshot_sha256=sha(image))
    except Exception as exc:obs['errors'].append('capture: '+str(exc)[:400])
    page.remove_listener('requestfailed',failed)
    page.remove_listener('response',failed_response)
    obs.update(finished_at=now(),network_failures=failures[:30])
    emit('capture','warning' if obs.get('page_problem') else 'completed',province=folder.name,
         message=stage+' / '+str(obs.get('page_problem') or '截图已保存'),url=obs.get('final_url',''),output=str(folder))
    return obs

async def find_search(page):
    async def fields():
        for frame in page.frames:
            loc=frame.locator('input:visible:not([readonly]):not([disabled]):not([type=password]):not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]):not([type=file])')
            for i in range(min(await loc.count(),25)):
                c=loc.nth(i);attrs=' '.join([(await c.get_attribute(a) or '') for a in ('placeholder','aria-label','id','name','class','type')])
                attrs+=' '+await c.evaluate('n=>{const p=n.closest("form,[class*=search],[id*=search]");return p?(p.className+" "+p.id):""}')
                if re.search('搜索|检索|关键词|关键字|search|keyword|事项|办理|服务',attrs,re.I):return c
        return None
    field=await fields()
    if field is not None:return field
    for frame in page.frames:
        for selector in ('[aria-label*=搜索]:visible','[title*=搜索]:visible','.search-icon:visible','a:has-text("统一搜索"):visible'):
            loc=frame.locator(selector)
            if await loc.count():
                try:
                    await loc.first.click(timeout=2500);await page.wait_for_timeout(800)
                    field=await fields()
                    if field is not None:return field
                except Exception:pass
    return None

async def search(page,folder,keyword,number,stage=None,interactive=False):
    action=dict(keyword=keyword,enter_submitted=False,attempts=[])
    chosen=await find_search(page);result=page;changed=False
    if chosen is not None:
        action['search_field']={a:await chosen.get_attribute(a) for a in ('id','name','placeholder','type')}
        before_url=page.url;before=await page.locator('body').inner_text(timeout=4000);old=set(page.context.pages)
        try:
            if interactive:
                await chosen.scroll_into_view_if_needed(timeout=3000)
                await chosen.click(timeout=3000);await chosen.fill('',timeout=3000)
                await chosen.press_sequentially(keyword,delay=90,timeout=5000)
                action['input_method']='click_and_type'
            else:await chosen.fill(keyword,timeout=5000)
            await chosen.press('Enter',timeout=5000)
            action['enter_submitted']=True;await page.wait_for_timeout(4000)
            new=[p for p in page.context.pages if p not in old];result=new[-1] if new else page
            await settle(result)
            action['public_confirmations']=await confirm_search_region(result)
            text=await result.locator('body').inner_text(timeout=4000)
            changed=result!=page or result.url!=before_url or (text!=before and keyword in text and bool(re.search('检索结果|搜索结果|找到|搜索到|相关结果|没有找到|无相关',text)))
            if not changed:
                for frame in page.frames:
                    buttons=frame.get_by_text(re.compile(r'^(搜索|检索)$'))
                    for i in range(min(await buttons.count(),10)):
                        if await buttons.nth(i).is_visible():
                            await buttons.nth(i).click(timeout=3500);await page.wait_for_timeout(4000)
                            action['attempts'].append('回车后未形成结果页，补充点击搜索按钮')
                            new=[p for p in page.context.pages if p not in old];result=new[-1] if new else page
                            await settle(result)
                            text=await result.locator('body').inner_text(timeout=4000)
                            changed=result!=page or result.url!=before_url or (text!=before and keyword in text and bool(re.search('检索结果|搜索结果|找到|搜索到|相关结果|没有找到|无相关',text)))
                            break
                    if changed:break
            if not changed:
                # Icon buttons and input[type=button] have no inner text.
                for frame in page.frames:
                    loc=frame.locator('input[type=submit][value*=搜]:visible,input[type=button][value*=搜]:visible,.search-btn:visible,.search-button:visible,.search-icon:visible,button[id*=search]:visible,a:has-text("更多结果"):visible,[aria-label*=搜索]:visible,[title*=搜索]:visible')
                    for i in range(min(await loc.count(),8)):
                        try:
                            await loc.nth(i).click(timeout=3000);await page.wait_for_timeout(3000)
                            new=[p for p in page.context.pages if p not in old];result=new[-1] if new else page
                            await settle(result);text=await result.locator('body').inner_text(timeout=4000)
                            changed=result!=page or result.url!=before_url or (text!=before and keyword in text and bool(re.search('检索结果|搜索结果|找到|搜索到|相关结果|没有找到|无相关',text)))
                            action['attempts'].append('回车后未形成结果页，补充点击可见搜索图标/按钮')
                            if changed:break
                        except Exception:pass
                    if changed:break
        except Exception as exc:action['attempts'].append(str(exc)[:400])
    if changed:
        # Search portals often default to laws/news; observe their service tab.
        for label in ('政务事项','政务服务','办事服务','服务事项'):
            clicked=False
            for frame in result.frames:
                loc=frame.get_by_text(label,exact=True)
                for i in range(min(await loc.count(),8)):
                    c=loc.nth(i)
                    try:
                        href=await c.get_attribute('href')
                        if await c.is_visible() and (not href or href.startswith(('javascript:','#'))):
                            await c.click(timeout=3500);await settle(result)
                            action['attempts'].append('查看搜索结果的“'+label+'”分类');clicked=True;break
                    except Exception:pass
                if clicked:break
            if clicked:break
    confirmations=await confirm_search_region(result)
    action.setdefault('public_confirmations',[]).extend(confirmations)
    action['scroll_scan']=await scan_scroll(result)
    obs=await snapshot(result,folder,stage or f'search-{number:02d}',action=action)
    obs['search_scope']='；'.join(c.get('scope','') for c in action['public_confirmations'] if c.get('scope')) or '页面默认检索范围'
    obs.update(keyword=keyword,enter_submitted=action['enter_submitted'],result_page_confirmed=changed)
    if not action['enter_submitted']:obs['candidate_links']=[]
    obs['candidate_links'].sort(key=lambda c:('申请' not in c['text'],keyword not in c['text'].replace(' ',''),'指南' not in c['text']))
    obs['outcome']=search_outcome(obs)
    return result,obs

def search_outcome(obs):
    if obs.get('page_problem') or (obs.get('http_status') or 200)>=400:return '访问异常，未完成检索'
    if not obs.get('enter_submitted'):return '未找到可操作的搜索框，未完成检索'
    if not obs.get('result_page_confirmed'):
        return '已按回车，画面可见相关入口候选；未确认正式结果页' if obs.get('candidate_links') else '已按回车，但未确认形成搜索结果页'
    if obs.get('candidate_links'):return '搜索结果中可见相关入口候选'
    return '本次搜索结果未定位到相关入口'

async def templates(page,folder,stage,scope='',keyword=''):
    # A public guide may require choosing a jurisdiction before materials appear.
    selected=[]
    resolution=None
    # Zhejiang publishes a guide base URL in its own script and the item code
    # on the result control. Preserve both as evidence instead of inventing URLs.
    if urlsplit(page.url).hostname=='search.zj.gov.cn':
        controls=await page.locator('a[data-service-action-kind="catalog-guide"][data-local-inner-code]').evaluate_all('''ns=>ns.map(n=>{
            let p=n;for(let i=0;p&&i<6;i++,p=p.parentElement){if((p.innerText||'').includes('劳动'))break;}
            return {code:n.getAttribute('data-local-inner-code'),text:p?p.innerText:''};
        })''')
        controls=[c for c in controls if re.search('劳动.*(仲裁|调解)',c['text'])]
        controls.sort(key=lambda c:keyword not in re.sub(r'\s','',c['text']))
        scripts=await page.locator('script[src]').evaluate_all('ns=>ns.map(n=>n.src)')
        script=next((u for u in scripts if official(u) and '/zwfwbszn/zwfw_bszn.js' in u),None)
        if controls and script:
            try:
                response=await page.context.request.get(script,timeout=20000)
                body=await response.text()
                match=re.search(r'const BASE_URL\s*=\s*"([^"]+localInnerCode=)"',body)
                code=controls[0]['code']
                if response.ok and match and official(match[1]) and re.fullmatch(r'[A-Fa-f0-9-]{32,36}',code):
                    (folder/'public-guide-script.js').write_text(body,encoding='utf8')
                    url=match[1]+quote(code,safe='');page=await page.context.new_page()
                    await snapshot(page,folder,stage+'-resolved',url,'按结果编码及官网公开脚本进入办事指南')
                    resolution=dict(script_url=script,item_code=code,guide_url=url)
            except Exception:pass
    from portal_guide_navigation import capture_materials
    return await capture_materials(page,folder,stage,scope,keyword,resolution)

async def capture_region(browser,slug,url,folder,semaphore):
    from portal_audit import write_json
    async with semaphore:
        folder.mkdir(parents=True,exist_ok=True);meta=PROVINCE_DOCUMENTS[slug]
        item=dict(slug=slug,name=meta['name'],portal_url=url,source_url=meta['source_url'],authority=meta['authority'],scope=meta['scope'],documents=meta['documents'],observations=[],searches=[],schema_version=3)
        context=await browser.new_context(locale='zh-CN',viewport={'width':1440,'height':900},accept_downloads=True)
        context.set_default_timeout(5000)
        try:
            for number,keyword in enumerate(KEYWORDS,1):
                page=await context.new_page()
                home=await snapshot(page,folder,f'portal-{number:02d}',url,'准备搜索 '+keyword);item['observations'].append(home)
                if home.get('page_problem') in ('blank','network'):
                    home=await snapshot(page,folder,f'portal-{number:02d}-retry',url,'重新加载门户');item['observations'].append(home)
                if slug=='shanxi' and not home.get('page_problem'):
                    anchors=await page.locator('a[href]').evaluate_all('ns=>ns.map(n=>({text:n.innerText||n.title||"",url:n.href}))')
                    platform=next((a for a in anchors if official(a['url']) and 'zwfw' in a['url'] and urlsplit(a['url']).hostname!=urlsplit(url).hostname),None)
                    if platform:
                        item['service_platform_url']=platform['url'];item['observations'].append(await snapshot(page,folder,f'platform-{number:02d}',platform['url'],'由省政府栏目进入其官方链接的平台'))
                if home.get('page_problem') in ('certificate','blocked','network','render_error'):
                    result=page;obs=await snapshot(page,folder,f'search-{number:02d}',action='门户访问异常，无法提交 '+keyword)
                    obs.update(keyword=keyword,enter_submitted=False,result_page_confirmed=False,candidate_links=[],page_problem=home['page_problem'],http_status=home.get('http_status'))
                    obs['outcome']=search_outcome(obs)
                else:result,obs=await search(page,folder,keyword,number)
                if not obs.get('enter_submitted') and (home.get('http_status') or 200)>=400:
                    obs['http_status']=home['http_status'];obs['page_problem']=home.get('page_problem') or 'blocked'
                    obs['outcome']=search_outcome(obs)
                item['observations'].append(obs);item['searches'].append(obs)
                seen=set()
                for index,link in enumerate(obs.get('candidate_links',[])[:1],1):
                    key=link.get('href') or link['url'] or link['text']
                    if key in seen:continue
                    seen.add(key);stage=f'guide-{number:02d}-{index:02d}'
                    if link.get('click'):
                        old=set(context.pages);before=result.url
                        frame=next((f for f in result.frames if f.url==link.get('frame_url')),result.main_frame)
                        target=frame.get_by_text(link['text'],exact=True)
                        try:
                            # Prefer the guide in the same result row to a title
                            # that merely expands a definition or changes a filter.
                            has_guide=await target.first.evaluate('''n=>{
                                let p=n;for(let i=0;p&&i<7;i++,p=p.parentElement){
                                    if((p.innerText||'').length>1400)break;
                                    for(const c of p.querySelectorAll('a,button,span,div')){
                                        if((c.innerText||'').trim()==='办事指南' && c.getBoundingClientRect().width>0){
                                            c.setAttribute('data-portal-guide-click','selected');return true;
                                        }
                                    }
                                }return false;
                            }''')
                            if has_guide:target=frame.locator('[data-portal-guide-click=selected]')
                            await target.first.click(timeout=5000);await result.wait_for_timeout(3000)
                            fresh=[p for p in context.pages if p not in old];guide=fresh[-1] if fresh else result
                            captured=await snapshot(guide,folder,stage,action='点击搜索结果入口：'+link['text'])
                            captured['entrance_opened']=bool(fresh) or guide.url!=before
                        except Exception as exc:
                            captured=await snapshot(result,folder,stage,action='入口点击未完成');captured['errors'].append(str(exc)[:300]);captured['entrance_opened']=False;guide=result
                    else:
                        guide=await context.new_page();captured=await snapshot(guide,folder,stage,link['url'],'打开结果入口：'+link['text']);captured['entrance_opened']=not captured.get('page_problem')
                    captured['keyword']=keyword;item['observations'].append(captured)
                    captured=await templates(guide,folder,stage+'-templates',meta['scope'],keyword);captured['keyword']=keyword;item['observations'].append(captured)
                    if guide!=result:await guide.close()
                    if link.get('click') and guide==result:break
                for p in list(context.pages):await p.close()
                write_json(folder/'observations.json',item)
            if official(meta['source_url']):
                page=await context.new_page();item['observations'].append(await snapshot(page,folder,'official-source',meta['source_url'],'已有官方来源，独立于门户搜索结果'))
                item['observations'].append(await templates(page,folder,'official-source-templates'))
            if any(s.get('candidate_links') for s in item['searches']):item.update(result_code='service_candidate_visible',result='检索画面中可见相关入口候选')
            elif all(s.get('result_page_confirmed') and not s.get('page_problem') for s in item['searches']):item.update(result_code='not_located_in_limited_search',result='三个关键词的本次结果均未定位到入口')
            else:item.update(result_code='access_failed',result='部分检索未完成，不能判断入口有无')
        except Exception as exc:item.update(result_code='audit_error',result='采集异常，需重跑',error=str(exc))
        finally:await context.close()
        write_json(folder/'observations.json',item);return item

async def collect(folder,slugs,progress,resume=False):
    from playwright.async_api import async_playwright
    from portal_audit import CONFIG,write_json
    config=json.loads(CONFIG.read_text(encoding='utf8'));temp=folder/'temp';temp.mkdir(parents=True,exist_ok=True)
    os.environ.update(TEMP=str(temp.resolve()),TMP=str(temp.resolve()))
    chrome=next((p for p in [Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe')] if p.exists()),None)
    if chrome is None:raise FileNotFoundError('未找到已安装Chrome')
    results=[];pending=[]
    for slug in slugs:
        saved=folder/slug/'observations.json';x=json.loads(saved.read_text(encoding='utf8')) if resume and saved.is_file() else None
        if x and x.get('schema_version')==3 and len(x.get('searches',[]))==3 and x.get('result_code')!='audit_error':results.append(x)
        else:pending.append(slug)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=str(chrome),headless=True,chromium_sandbox=True,env=os.environ.copy())
        semaphore=asyncio.Semaphore(3)
        tasks=[asyncio.create_task(capture_region(browser,s,config['portals'][s],folder/s,semaphore)) for s in pending]
        for task in asyncio.as_completed(tasks):
            item=await task
            item['access_note']=config.get('access_notes',{}).get(item['slug'])
            item['url_provenance']=config.get('url_provenance',{}).get(item['slug'])
            results.append(item);write_json(folder/item['slug']/'observations.json',item);write_json(folder/'results.json',sorted(results,key=lambda x:slugs.index(x['slug'])))
            progress(len(results),item['name']);print(f'CAPTURE {len(results)}/{len(slugs)} {item["slug"]}: {item["result"]}',flush=True)
        await browser.close()
    return sorted(results,key=lambda x:slugs.index(x['slug']))
