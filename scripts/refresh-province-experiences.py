"""Resume a province UI refresh, reusing discovery and capturing public guides.

No foreground browser, local model, login or application submission. All files
are isolated in this run. Unreachable pages keep explicitly dated old evidence.
"""
import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import uuid
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from province_experience import POLICY, PORTALS, EXPERIENCE_ROOT, choose_guide, plain_guide, portal_source, service_kind, guide_rank, valid_guide
from province_documents import PROVINCE_DOCUMENTS
from portal_audit import write_json, now, sha
from portal_audit_capture import snapshot, settle, search, KEYWORDS
from portal_guide_navigation import body_text, capture_materials
from portal_workflows import PublicResponses, guide_record, capture_flow, parse_public_record, official_region_names
from portal_interactions import select_capital
from terminal_progress import configure, emit


def response_matches(record, guide_url):
    parsed=urlsplit(guide_url)
    query=dict(parse_qsl(parsed.query));query.update(dict(parse_qsl(parsed.fragment.split('?',1)[-1])))
    identifiers=[v for k,v in query.items() if k.lower() in ('id','matterid','itemid','taskcode','localinnercode','ssqdcode','ssqdid','rowguid','sourcekey') and len(v)>=8]
    request=record['url']+' '+(record.get('post_data') or '')
    return bool(identifiers and any(v in request for v in identifiers))


def historical(source, slug):
    path = source / slug / 'workflows.json'
    guides = json.loads(path.read_text(encoding='utf8')).get('guides', []) if path.exists() else []
    # Empty guide titles may still be identifiable in already saved DOM text.
    from portal_workflows import service_title
    for guide in guides:
        text = source / slug / (guide.get('stage', '') + '.txt')
        if not guide.get('service_name') and text.is_file():
            guide['service_name'] = service_title(text.read_text(encoding='utf8'))
    return guides


async def capture_region(browser, slug, folder, source, semaphore):
    meta = PROVINCE_DOCUMENTS[slug]
    folder.mkdir(parents=True, exist_ok=True)
    guides = historical(source, slug)
    chosen = choose_guide(guides, slug)
    observations, attempts = [], []
    def add(obs):
        observations.append(obs);write_json(folder/'observations.json',observations)
    historical_guide = chosen
    async with semaphore:
        context = await browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='zh-CN', timezone_id='Asia/Shanghai', accept_downloads=True)
        responses = PublicResponses(context)
        try:
            for layer in (1, 2, 3):
                page = await context.new_page()
                try:
                    if layer == 3:
                        if not historical_guide or portal_source(historical_guide['guide_url'],slug):continue
                        opening=await snapshot(page,folder,'department-fallback',historical_guide['guide_url'],'门户未取得有效指南后才查询已有官方部门来源')
                        add(opening)
                        if opening.get('page_problem'):continue
                    elif layer == 2:
                        # Warm the real portal and submit through its public UI;
                        # no injected API, fingerprint spoofing or TLS bypass.
                        warm = await snapshot(page, folder, 'layer2-home', PORTALS[slug], '第二层：正常打开门户、点击输入并滚动')
                        add(warm)
                        if warm.get('page_problem'):continue
                        attempts.extend(await select_capital(page,POLICY['capitals'][slug]))
                        result = await search(page, folder, '劳动人事争议仲裁', 1, stage='layer2-search', interactive=True)
                        page, obs = result
                        add(obs)
                        links = [r for r in obs.get('candidate_links', []) if portal_source(r.get('url', ''), slug)]
                        if links:
                            await page.goto(links[0]['url'], wait_until='domcontentloaded', timeout=30000)
                            await settle(page)
                        elif not chosen:
                            # Related mediation is also a valid public route.
                            page, obs = await search(page, folder, '劳动人事争议调解', 2, stage='layer2-mediation', interactive=True)
                            add(obs)
                    elif chosen and portal_source(chosen['guide_url'],slug) and not guide_rank(chosen,slug)[1]:
                        opening = await snapshot(page, folder, 'primary-open', chosen['guide_url'], '复用已发现的官方指南网址')
                        add(opening)
                        if opening.get('page_problem'):continue
                    else:
                        opening = await snapshot(page, folder, 'primary-home', PORTALS[slug], '打开本省官方门户')
                        add(opening)
                        if opening.get('page_problem'):continue
                        attempts.extend(await select_capital(page,POLICY['capitals'][slug]))
                        page, obs = await search(page, folder, '劳动人事争议仲裁', 1, stage='primary-search')
                        add(obs)
                        links = [r for r in obs.get('candidate_links', []) if portal_source(r.get('url', ''), slug)]
                        if links:
                            await page.goto(links[0]['url'], wait_until='domcontentloaded', timeout=30000)
                            await settle(page)
                    material = await capture_materials(page, folder, f'layer{layer}-templates', POLICY['capitals'][slug])
                    add(material)
                    # capture_materials can open a guide in another tab.
                    if material.get('final_url') != page.url:
                        page = next((p for p in context.pages if p.url == material.get('final_url')), page)
                    text = await body_text(page)
                    flow_text, flow = await capture_flow(page, folder, f'layer{layer}')
                    add(flow)
                    guide = guide_record({'slug': slug, 'name': meta['name']}, material, text, flow_text)
                    guide['flow_screenshot'] = flow.get('screenshot')
                    guide['steps'] = flow.get('structured_steps', [])
                    await responses.flush(folder)
                    for record in responses.records:
                        parsed = parse_public_record(record)
                        if parsed and parsed.get('steps') and response_matches(record,page.url):
                            # Only accept the response for this loaded guide,
                            # not an earlier search/city's asynchronous response.
                            guide.update(parsed)
                    names = official_region_names(responses.records)
                    guide['region_name'] = guide.get('region_name') or names.get(str(guide.get('region_code', '')), '')
                    valid = not material.get('page_problem') and valid_guide(guide)
                    attempts.append({'layer': layer, 'valid_guide': valid, 'url': page.url, 'page_problem': material.get('page_problem')})
                    if valid:
                        chosen = guide
                        break
                except Exception as exc:
                    attempts.append({'layer': layer, 'error': str(exc)[:500]})
                finally:
                    for p in list(context.pages):await p.close()
            await responses.flush(folder)
        finally:
            await context.close()
    fresh = chosen is not historical_guide and chosen is not None
    state = 'fresh' if fresh else 'historical' if chosen else 'not_detected'
    profile = plain_guide(chosen or {}, slug, meta.get('scope', ''))
    profile.update(slug=slug, name=meta['name'], state=state, portal_url=PORTALS[slug], source_run=None if fresh else source.name,
                   selected_guide=chosen, source_policy='portal_first_capital_first_first_visible_district',
                   capital_confirmed=bool(chosen and not guide_rank(chosen, slug)[1]),
                   templates=(chosen or {}).get('templates', []), template_status='downloads_detected' if (chosen or {}).get('templates') else '本次没有检测到文书模板',
                   checked_at=now(), attempts=attempts)
    if not profile['steps']:
        profile['steps'] = [{'title': '先打开官方入口', 'text': '搜索劳动仲裁，选择实际办理地区，再打开办事指南。', 'source_text': '', 'official_name': ''}]
        profile['notes'].insert(0, '这里还没有取得可确认的办理步骤，请先查看官方页面。')
    if not profile['capital_confirmed']:
        profile['notes'].append('优先查询' + POLICY['capitals'][slug] + '；目前记录的入口未确认是该市的指南。')
    write_json(folder / 'observations.json', observations)
    write_json(folder / 'experience.json', profile)
    print('CAPTURE', slug, state, profile['service_kind'], flush=True)
    return profile


def review(profile, run):
    from template_acquisition.openclaw_bridge import describe_image
    slug = profile['slug']
    folder = run / slug
    if (folder / 'ai.json').is_file():
        cached=json.loads((folder / 'ai.json').read_text(encoding='utf8'))
        if cached.get('state')=='reviewed' and cached.get('parse_state') in (None,'valid') and cached.get('inputs') and all((folder/i['filename']).is_file() and sha(folder/i['filename'])==i['sha256'] for i in cached['inputs']):
            emit('vision','cached',province=slug,message='复用校验值一致的 AI 结果')
            return cached
        (folder/'ai.json').rename(folder/('ai-previous-'+uuid.uuid4().hex[:6]+'.json'))
        if (folder/'openclaw-raw.json').exists():(folder/'openclaw-raw.json').rename(folder/('openclaw-raw-previous-'+uuid.uuid4().hex[:6]+'.json'))
    obs = json.loads((folder / 'observations.json').read_text(encoding='utf8'))
    selected = [o for o in obs if o.get('screenshot') and (o['stage'].endswith('-templates') or o['stage'].endswith('-flow'))][-2:]
    if not selected:selected = [o for o in obs if o.get('screenshot')][-1:]
    images = [folder / o['screenshot'] for o in selected]
    result = {'state': 'no_images', 'base_url': 'http://10.66.66.1:11434', 'model': 'qwen3.8:27b'}
    if images:
        prompt = '只复核这些实际截图，不猜隐藏内容。逐图输出 JSON 数组，字段 stage、visible_service、has_template_download、notes。只有申请书或证据清单旁的文书下载按钮才算模板下载；办事指南下载、APP下载、结果样本不算。调解不能说成仲裁；空白或网络错误要指出。截图顺序：' + json.dumps([{'stage': o['stage'], 'url': o.get('final_url')} for o in selected], ensure_ascii=False)
        try:
            raw = describe_image(images, folder / 'openclaw-raw.json', run / 'openclaw' / slug, timeout_seconds=300, prompt=prompt, base_url='http://10.66.66.1:11434')
            data = json.loads(raw.read_text(encoding='utf8'))
            if data.get('base_url') != result['base_url'] or data.get('result', {}).get('model') != result['model']:raise ValueError('模型来源不符合要求')
            result.update(state='reviewed', output=data['result'].get('outputs'), inputs=[{'filename': p.name, 'sha256': sha(p)} for p in images], role='辅助视觉意见，不自动覆盖采集事实')
        except Exception as exc:result.update(state='failed', error=str(exc)[:500])
    write_json(folder / 'ai.json', result)
    print('OPENCLAW', slug, result['state'], flush=True)
    return result


async def main(args):
    source_root = ROOT / 'templates/_reports/portal-audits'
    source = source_root / json.loads((source_root / 'latest.json').read_text(encoding='utf8'))['id']
    run = Path(args.resume).resolve() if args.resume else EXPERIENCE_ROOT / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
    if not run.is_relative_to(EXPERIENCE_ROOT.resolve()):raise ValueError('Run must remain in province-experiences')
    run.mkdir(parents=True, exist_ok=True)
    configure(run)
    emit('capture',message='启动指南采集',completed=0,total=len(PROVINCE_DOCUMENTS),output=str(run))
    saved_manifest=json.loads((run/'experiences.json').read_text(encoding='utf8')) if (run/'experiences.json').exists() else {}
    metadata={key:saved_manifest[key] for key in ('parent_run','openclaw_run') if key in saved_manifest}
    temp = run / 'temp';temp.mkdir(exist_ok=True);os.environ.update(TEMP=str(temp), TMP=str(temp))
    write_json(run / 'status.json', {'state': 'running', 'source_run': source.name, 'owner_pid': os.getpid(), 'updated_at': now()})
    print('RUN', run, flush=True)
    slugs = list(PROVINCE_DOCUMENTS)
    profiles = {}
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        from browser_identity import normal_user_agent
        identity=normal_user_agent()
        browser = await pw.chromium.launch(args=['--user-agent='+identity] if identity else [], executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True, chromium_sandbox=True)
        semaphore = asyncio.Semaphore(3)
        async def one(slug):
            cached = run / slug / 'experience.json'
            if cached.is_file():
                saved=json.loads(cached.read_text(encoding='utf8'))
                if saved.get('state')!='fresh' or valid_guide(saved.get('selected_guide')):return saved
                write_json(run/slug/'experience-invalid-result-page.json',saved)
            try:return await asyncio.wait_for(capture_region(browser, slug, run / slug, source, semaphore), 240)
            except Exception as exc:
                # Durable recovery record; keep the historic time and source.
                meta = PROVINCE_DOCUMENTS[slug];guide = choose_guide(historical(source, slug), slug)
                p = plain_guide(guide or {}, slug, meta.get('scope', ''))
                p.update(slug=slug, name=meta['name'], state='historical' if guide else 'not_detected', selected_guide=guide, templates=(guide or {}).get('templates', []), source_run=source.name, portal_url=PORTALS[slug], checked_at=now(), error=str(exc)[:500], capital_confirmed=bool(guide and not guide_rank(guide,slug)[1]))
                if not (run / slug / 'observations.json').exists():write_json(run / slug / 'observations.json', [])
                write_json(cached,p);print('RECOVER',slug,p['state'],flush=True);return p
        # Acquire the semaphore before starting a per-region timeout so queued
        # provinces do not expire before any browser work has started.
        gate = asyncio.Semaphore(3)
        async def gated(slug):
            async with gate:return await one(slug)
        for task in asyncio.as_completed([asyncio.create_task(gated(s)) for s in slugs]):
            p = await task;profiles[p['slug']] = p
            emit('capture',kind='region',province=p['slug'],region_state=p['state'],message='本省采集结果：'+p['state'],completed=len(profiles),total=len(slugs),output=str(run))
            write_json(run / 'experiences.json', {**metadata,'version': 1, 'run_id': run.name, 'source_run': source.name, 'provinces': profiles})
        await browser.close()
    # New acquisitions use OpenClaw as the final public-browser recovery layer.
    # Resuming completed captures/reviews must not repeat successful work.
    if not args.without_browser_agent and (not args.resume or args.with_browser_agent):
        import importlib.util
        spec=importlib.util.spec_from_file_location('openclaw_acquire',ROOT/'scripts/openclaw-acquire-guides.py')
        agent=importlib.util.module_from_spec(spec);spec.loader.exec_module(agent)
        missing=[s for s,p in profiles.items() if p['state']!='fresh' and not p.get('openclaw_attempt')]
        if missing:
            write_json(run/'status.json',{'state':'running','phase':'openclaw_browser','regions':31,'pending':missing,'updated_at':now()})
            await asyncio.to_thread(agent.supplement,profiles,run,missing)
    # Sequential model calls avoid competing for Ubuntu GPU memory.
    for number,slug in enumerate(slugs,1):
        emit('vision',province=slug,message='检查本省截图',completed=number-1,total=len(slugs),output=str(run))
        profiles[slug]['ai_review'] = await asyncio.to_thread(review, profiles[slug], run)
        write_json(run / 'experiences.json', {**metadata,'version': 1, 'run_id': run.name, 'source_run': source.name, 'provinces': profiles})
    states = {s: sum(p['state'] == s for p in profiles.values()) for s in ('fresh', 'historical', 'not_detected')}
    reviewed = sum(p['ai_review']['state'] == 'reviewed' for p in profiles.values())
    status = {'state': 'complete_with_gaps' if states['not_detected'] or reviewed < 31 else 'complete', 'counts': states, 'ai_reviewed': reviewed, 'regions': 31, 'updated_at': now(), 'source_run': source.name}
    write_json(run / 'status.json', status)
    import subprocess
    subprocess.run([sys.executable,str(ROOT/'scripts/finalize-province-experiences.py'),str(run),'--no-publish'],check=True)
    normalized=json.loads((run/'experiences.json').read_text(encoding='utf8'))
    status=json.loads((run/'status.json').read_text(encoding='utf8'))
    from province_experience import pending_openclaw_reviews
    pending=pending_openclaw_reviews(normalized['provinces'])
    if pending:
        status.update(state='review_incomplete',pending_ai=pending)
        write_json(run/'status.json',status)
    else:
        write_json(EXPERIENCE_ROOT / 'latest.json', {'id': run.name, **status})
        subprocess.run([sys.executable,str(ROOT/'scripts/sync-province-experiences.py')],check=True)
    artifact_python=Path(os.getenv('LABOURLAWYER_ARTIFACT_PYTHON',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')))
    if artifact_python.is_file():
        emit('report',message='生成并渲染两份 Word 报告',completed=len(slugs),total=len(slugs),output=str(run))
        subprocess.run([str(artifact_python),str(ROOT/'scripts/build-province-experience-reports.py'),str(run)],check=True,timeout=60)
        subprocess.run([str(artifact_python),str(ROOT/'scripts/render_portal_reports.py'),str(run)],check=True,timeout=300)
    else:
        write_json(run/'report-error.json',{'error':'Bundled artifact Python unavailable; JSON evidence and client snapshots preserved.'})
    print('DONE', json.dumps(status, ensure_ascii=False), flush=True)
    emit('job',status['state'],message='指南更新结束',counts=states,completed=len(profiles),total=len(slugs),output=str(run))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume');parser.add_argument('--without-browser-agent',action='store_true');parser.add_argument('--with-browser-agent',action='store_true');asyncio.run(main(parser.parse_args()))
