"""Revisit reached guides when their screenshot still shows a result list."""
import asyncio
import json
import os
import re
from pathlib import Path
from lxml import html
from playwright.async_api import async_playwright
from portal_audit_capture import official,snapshot,templates,search_outcome

async def refine_materials(folder,items,progress):
    from portal_audit import write_json
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True,env=os.environ.copy())
        semaphore=asyncio.Semaphore(3)
        done=0
        async def one(index,x):
            nonlocal done
            async with semaphore:
                context=await browser.new_context(locale='zh-CN',viewport={'width':1440,'height':900},accept_downloads=False);context.set_default_timeout(5000)
                try:
                    for search in x.get('searches',[]):
                        captured=next(o for o in x['observations'] if o['stage']==search['stage'])
                        text_file=folder/x['slug']/search.get('text_file','absent.txt')
                        visible=text_file.read_text(encoding='utf8') if text_file.is_file() else ''
                        if re.search('403 Forbidden|405.{0,8}Method Not Allowed|429 Too Many|安全防护.{0,8}拦截',visible[:2000],re.I):
                            search.update(page_problem='blocked',result_page_confirmed=False,candidate_links=[])
                            search['outcome']=search_outcome(search);captured.update(search)
                        number=search['stage'].removeprefix('search-')
                        home=next((o for o in reversed(x['observations']) if o['stage'] in ('portal-'+number,'portal-'+number+'-retry')), {})
                        if not search.get('enter_submitted') and (home.get('http_status') or 200)>=400:
                            search.update(http_status=home['http_status'],page_problem=home.get('page_problem') or 'blocked')
                            search['outcome']=search_outcome(search)
                            captured=next(o for o in x['observations'] if o['stage']==search['stage']);captured.update(search)
                        if not search.get('enter_submitted'):
                            text_file=folder/x['slug']/search.get('text_file','absent.txt')
                            if text_file.is_file() and '429 Too Many' in text_file.read_text(encoding='utf8'):
                                search.update(page_problem='blocked',access_detail='页面显示 429 Too Many Requests（请求频率限制）')
                                search['outcome']=search_outcome(search)
                                next(o for o in x['observations'] if o['stage']==search['stage']).update(search)
                    if any(s.get('candidate_links') for s in x['searches']):x.update(result_code='service_candidate_visible',result='检索画面中可见相关入口候选')
                    elif all(s.get('result_page_confirmed') and not s.get('page_problem') for s in x['searches']):x.update(result_code='not_located_in_limited_search',result='三个关键词的本次结果均未定位到入口')
                    else:x.update(result_code='access_failed',result='部分检索未完成，不能判断入口有无')
                    search_urls={o.get('final_url') for o in x.get('searches',[])}
                    originals=[]
                    for o in x['observations']:
                        if not o['stage'].endswith('-templates') or o.get('superseded_by'):continue
                        evidence=folder/x['slug']/o.get('text_file','absent.txt')
                        text=evidence.read_text(encoding='utf8') if evidence.is_file() else ''
                        version=o.get('material_capture_version')
                        picker_pending=version==3 and not o.get('template_area_visible') and re.search('选择办理区域|选择办理地点|请选择.{0,8}(地区|区域)|选择实施清单',text)
                        if version not in (2,3,4,5) or o.get('final_url') in search_urls and version not in (3,4,5) or picker_pending:originals.append(o)
                    for old in originals:
                        text=(folder/x['slug']/old.get('text_file','absent.txt')).read_text(encoding='utf8') if old.get('text_file') else ''
                        if old.get('page_problem') in ('certificate','blocked','network'):continue
                        if not official(old.get('final_url','')):continue
                        page=await context.new_page();url=old['final_url']
                        # A reached jurisdiction picker can expose the concrete
                        # public guide URL. Use that recorded anchor, never a guessed URL.
                        source=folder/x['slug']/old.get('html_file','absent.html')
                        if source.is_file():
                            tree=html.fromstring(source.read_text(encoding='utf8'))
                            for anchor in tree.xpath('//a[@href]'):
                                name=''.join(anchor.itertext()).strip();href=anchor.get('href','')
                                if name=='办事指南' and official(href) and '劳动' in anchor.get('data-title',''):
                                    url=href;break
                        stage=old['stage'].removesuffix('-templates')+'-verified'
                        reached=await snapshot(page,folder/x['slug'],stage,url,'复核已到达入口的公开办事指南');reached['keyword']=old.get('keyword')
                        capture=await templates(page,folder/x['slug'],stage+'-templates',x['scope'],old.get('keyword') or '');capture['keyword']=old.get('keyword')
                        capture['refined_from']=old['stage'];old['superseded_by']=capture['stage']
                        x['observations'].extend([reached,capture]);x.pop('ai_review',None)
                        for pg in list(context.pages):await pg.close()
                    write_json(folder/x['slug']/'observations.json',x)
                    done+=1;progress(done,x['name']);print('MATERIALS',x['slug'],'saved',flush=True)
                finally:await context.close()
        await asyncio.gather(*(one(i,x) for i,x in enumerate(items,1)))
        await browser.close()
    write_json(folder/'results.json',items);return items
