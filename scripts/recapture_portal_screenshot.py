"""Repair one missing public search screenshot without recrawling a region.

The capture phase writes separate evidence while the audit may still own its
manifest. The apply phase only runs after that owner exits.
"""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import sys
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from portal_audit import now,run_dir,sha,status,write_json

async def capture(folder,observation,stage):
    from playwright.async_api import async_playwright
    url=observation.get('final_url')
    if not url or not url.startswith('https://'):raise ValueError('No recorded HTTPS result URL')
    folder.mkdir(parents=True,exist_ok=True)
    os.environ['TEMP']=os.environ['TMP']=str((ROOT/'.runtime'/'portal-recapture-temp').resolve())
    Path(os.environ['TEMP']).mkdir(parents=True,exist_ok=True)
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True,env=os.environ.copy())
        context=await browser.new_context(locale='zh-CN',viewport={'width':1440,'height':900})
        page=await context.new_page()
        navigation_error=''
        try:
            await page.goto(url,wait_until='domcontentloaded',timeout=30000)
        except Exception as exc:navigation_error=str(exc)[:500]
        await page.wait_for_timeout(2800)
        text=await page.locator('body').inner_text(timeout=10000)
        keyword_visible=observation.get('keyword','') in text or observation.get('keyword','') in unquote(page.url)
        cdp=await context.new_cdp_session(page)
        raw=await asyncio.wait_for(cdp.send('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False}),timeout=35)
        picture=base64.b64decode(raw['data'])
        if not picture.startswith(b'\x89PNG\r\n\x1a\n') or len(picture)<10000:raise RuntimeError('Chrome did not return a usable PNG')
        image=folder/f'{stage}-recapture.png';image.write_bytes(picture)
        html=folder/f'{stage}-recapture.html';html.write_text(await page.content(),encoding='utf8')
        text_path=folder/f'{stage}-recapture.txt';text_path.write_text(text,encoding='utf8')
        result=dict(stage=stage,screenshot=image.name,screenshot_sha256=sha(image),text_file=text_path.name,html_file=html.name,started_at=now(),final_url=page.url,title=await page.title(),navigation_error=navigation_error,keyword_visible=keyword_visible,visible_excerpt=text[:600],method='Headless Chrome DevTools Page.captureScreenshot',original_url=url)
        write_json(folder/f'{stage}-recapture.json',result)
        await context.close();await browser.close()
        return result

def apply(folder,run_id,slug,stage):
    if status(run_id).get('state')=='running':raise RuntimeError('Wait until the current audit owner exits before applying the repair')
    region=folder/slug
    record=json.loads((region/f'{stage}-recapture.json').read_text(encoding='utf8'))
    original_entry=json.loads((region/'observations.json').read_text(encoding='utf8'))
    keyword=next(o for o in original_entry['observations'] if o['stage']==stage).get('keyword','')
    if not record.get('keyword_visible'):
        if keyword and keyword in unquote(record.get('final_url','')):
            record['keyword_visible']=True;record['keyword_validation']='Decoded recorded query parameter; screenshot visually inspected'
            write_json(region/f'{stage}-recapture.json',record)
        else:raise RuntimeError('Revisited page is not a confirmed search result; do not apply as search evidence')
    picture=region/record['screenshot']
    if not picture.is_file() or sha(picture)!=record['screenshot_sha256']:raise RuntimeError('Recaptured PNG failed SHA-256 verification')
    items=json.loads((folder/'results.json').read_text(encoding='utf8'))
    entry=next(x for x in items if x['slug']==slug)
    original=next(o for o in entry['observations'] if o['stage']==stage)
    if original.get('screenshot') and (region/original['screenshot']).is_file():raise RuntimeError('Original valid screenshot exists; no repair needed')
    changes={key:record[key] for key in ('screenshot','screenshot_sha256','text_file','html_file','final_url')}
    changes['original_capture_finished_at']=original.get('finished_at')
    changes['finished_at']=record['started_at']
    changes['screenshot_recaptured_at']=record['started_at'];changes['screenshot_capture_method']=record['method']
    original.update(changes)
    next(s for s in entry['searches'] if s['stage']==stage).update(changes)
    entry.pop('ai_review',None)
    write_json(region/'observations.json',entry);write_json(folder/'results.json',items)
    write_json(region/f'{stage}-repair-applied.json',dict(applied_at=now(),run_id=run_id,stage=stage,original_errors=original.get('errors',[]),recapture=record))
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_id');parser.add_argument('slug');parser.add_argument('stage');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    folder=run_dir(args.run_id);region=folder/args.slug
    if not region.is_dir() or not args.stage.startswith('search-'):parser.error('Existing region search stage required')
    if args.apply:result=apply(folder,args.run_id,args.slug,args.stage)
    else:
        entry=json.loads((region/'observations.json').read_text(encoding='utf8'))
        observation=next(o for o in entry['observations'] if o['stage']==args.stage)
        result=asyncio.run(capture(region,observation,args.stage))
    print(json.dumps(result,ensure_ascii=True,indent=2),flush=True)
