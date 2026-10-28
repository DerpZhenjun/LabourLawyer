"""OpenClaw reviews every required screenshot, with resumable raw records."""
import json
from pathlib import Path
import re
from portal_audit import MODEL,MODEL_BASE_URL,sha,write_json

def required_images(item):
    return [o for o in item['observations'] if not o.get('superseded_by') and not o.get('evidence_error') and (o['stage'].startswith('search-') or o['stage'].endswith('-templates') and (not o['stage'].startswith('district-') or o.get('report_include')))]

def parse_answer(payload,stages):
    answer='\n'.join(o.get('text','') for o in payload['result']['outputs'])
    answer=re.sub(r'^```(?:json)?\s*|\s*```$','',answer.strip())
    decoded=json.loads(answer[answer.index('{'):answer.rindex('}')+1])
    reviews=decoded.get('images',[])
    # Numeric image labels keep a 27B CPU/GPU response short. Expand them
    # deterministically; retain the unmodified model answer in the raw record.
    for v in reviews:
        if type(v.get('stage')) is int and 1<=v['stage']<=len(stages):
            v['stage']=stages[v['stage']-1]
            v['page_kind']=v.pop('kind','其他')
            v['entrance_visible']=v.pop('entry',None)
            v['template_names']=v.pop('names',None)
            v['warning']=v.pop('note','')
    if {v.get('stage') for v in reviews}!=set(stages) or len(reviews)!=len(stages):raise ValueError('AI没有逐一覆盖全部输入截图')
    for v in reviews:
        if not isinstance(v.get('entrance_visible'),bool) or not isinstance(v.get('template_names'),list):raise ValueError('AI验证字段不完整')
    return reviews

def cached_images(directory):
    verified={}
    for record in directory.glob('openclaw-*.json'):
        try:cached=json.loads(record.read_text(encoding='utf8'))
        except (OSError,ValueError):continue
        actual=cached.get('result',{})
        if cached.get('timed_out') or actual.get('ok') is not True or actual.get('provider')!='ollama' or actual.get('model')!=MODEL.removeprefix('ollama/'):continue
        for v in cached.get('verified_json',[]):
            if v.get('state')=='complete' and v.get('model')==MODEL and v.get('screenshot_sha256') in cached.get('input_sha256',[]):
                candidate=dict(v,source_record=record.name,model_server=cached.get('base_url') or '历史记录未注明服务器')
                previous=verified.get(v['screenshot_sha256'],{})
                def rank(entry):
                    server=entry.get('model_server')
                    return 2 if server==MODEL_BASE_URL else 1 if server=='http://192.168.110.89:11434' else 0
                if rank(candidate)>=rank(previous):verified[v['screenshot_sha256']]=candidate
    return verified

def completed_review_matches(directory,existing,required,cache):
    images={v['stage']:v for v in existing.get('images',[])}
    if existing.get('state')!='complete' or existing.get('model')!=MODEL or set(images)!={o['stage'] for o in required}:return False
    for o in required:
        picture=directory/o.get('screenshot','absent.png');v=images[o['stage']]
        if not picture.is_file() or v.get('state')!='complete' or v.get('model')!=MODEL:return False
        digest=sha(picture)
        if v.get('screenshot_sha256')!=digest or digest not in cache:return False
    return True

def review(folder,items,progress):
    import importlib,portal_material_evidence
    importlib.reload(portal_material_evidence)
    for item in items:
        portal_material_evidence.normalize_observations(folder/item['slug'],item)
        write_json(folder/item['slug']/'observations.json',item)
    write_json(folder/'results.json',items)
    from template_acquisition.openclaw_bridge import describe_image
    from urllib.request import urlopen
    with urlopen(MODEL_BASE_URL+'/api/tags',timeout=30) as response:
        installed=json.load(response)['models']
    model_info=next((m for m in installed if m.get('name')==MODEL.removeprefix('ollama/')),None)
    if model_info is None:raise RuntimeError('Ubuntu Ollama '+MODEL_BASE_URL+' 未提供 '+MODEL)
    previous=folder/'model-info.json'
    if previous.is_file():
        old_base=json.loads(previous.read_text(encoding='utf8')).get('base_url')
        if old_base!=MODEL_BASE_URL:
            old_name='model-info-ubuntu-previous.json' if old_base else 'model-info-windows.json'
            backup=folder/old_name
            if not backup.exists():backup.write_bytes(previous.read_bytes())
    model_info=dict(model_info,base_url=MODEL_BASE_URL)
    write_json(folder/'model-info.json',model_info)
    for number,x in enumerate(items,1):
        required=required_images(x)
        existing=x.get('ai_review',{});cache=cached_images(folder/x['slug'])
        # Verified historical Ubuntu calls can be reused; unrecorded/local
        # provider origins cannot satisfy this remote-only verification run.
        cache={digest:v for digest,v in cache.items() if v['model_server'] in (MODEL_BASE_URL,'http://192.168.110.89:11434')}
        if completed_review_matches(folder/x['slug'],existing,required,cache):
            for v in existing['images']:
                v['model_server']=cache[v['screenshot_sha256']]['model_server']
            write_json(folder/x['slug']/'observations.json',x)
            continue
        progress(number-1,'AI '+x['name'])
        observations=[];by_hash={};aliases={}
        for obs in required:
            path=folder/x['slug']/obs.get('screenshot','absent.png')
            digest=sha(path) if path.is_file() else obs['stage']
            if digest in by_hash:aliases[obs['stage']]=by_hash[digest]
            else:by_hash[digest]=obs['stage'];observations.append(obs)
        verified=[];pending=[]
        for obs in observations:
            path=folder/x['slug']/obs.get('screenshot','absent.png')
            if path.is_file() and sha(path) in cache:
                previous=dict(cache[sha(path)]);previous['stage']=obs['stage'];verified.append(previous)
            else:pending.append(obs)
        # Two images fit the configured 8192 context and reduce repeated CLI
        # initialization. Each output must still match exactly one input image.
        for offset in range(0,len(pending),2):
            chunk=pending[offset:offset+2];stages=[o['stage'] for o in chunk]
            label=f'AI {x["name"]}，截图 {offset+1}-{offset+len(chunk)}/{len(pending)}'
            progress(number-1,label)
            paths=[folder/x['slug']/o.get('screenshot','absent.png') for o in chunk]
            dest=folder/x['slug']/f'openclaw-images-{stages[0]}-{stages[-1]}.json'
            labels=[dict(stage=i,keyword=o.get('keyword','不适用')) for i,o in enumerate(chunk,1)]
            prompt='按输入顺序逐图核对，共'+str(len(chunk))+'张；只依据各图可见内容，不猜隐藏链接。编号和检索词：'+json.dumps(labels,ensure_ascii=False)+'。只输出严格JSON，images必须恰好'+str(len(chunk))+'项，stage逐一为1至'+str(len(chunk))+'：{"images":[{"stage":1,"kind":"搜索结果/办事指南/模板材料/首页/错误页/白屏/其他","entry":false,"names":[],"note":"不超过20字"}]}。entry仅表示可见劳动仲裁或调解办事入口，新闻导航不算。names只列实际可见申请书、证据清单名称；样例下载、样表、示例、模板和docx链接都算文书控件，但不能把样表说成空白模板。无下载控件的材料名称不证明可下载。不得把一张图的内容写到另一张。'
            success=False;error='未取得全部截图'
            if all(p.is_file() for p in paths):
                for attempt in range(2):
                    try:
                        describe_image(paths,dest,folder/'openclaw',timeout_seconds=600,prompt=prompt,role='portal_screenshot_review',model=MODEL,base_url=MODEL_BASE_URL)
                        payload=json.loads(dest.read_text(encoding='utf8'));reviews=parse_answer(payload,stages)
                        for v,o,p in zip(sorted(reviews,key=lambda v:stages.index(v['stage'])),chunk,paths):
                            v.update(state='complete',model=MODEL,model_server=MODEL_BASE_URL,keyword=o.get('keyword'),screenshot_sha256=sha(p))
                            visible=(folder/x['slug']/o['text_file']).read_text(encoding='utf8') if o.get('text_file') else ''
                            conflicts=[]
                            if v.get('entrance_visible') and (o.get('page_problem') or o['stage'].startswith('search-') and not o.get('candidate_links')):conflicts.append('AI认为有入口，但采集记录未确认；待人工复核')
                            absent=[t for t in v['template_names'] if t.replace(' ','') not in re.sub(r'\s','',visible)]
                            if absent:conflicts.append('AI所列名称未在页面文字中找到：'+'、'.join(absent))
                            if not v['template_names'] and o.get('template_links'):conflicts.append('记录有下载控件，但AI未从截图确认；待对照原图复核')
                            v['consistency_warnings']=conflicts
                        for v in reviews:v['source_record']=dest.name
                        payload.update(verified_json=reviews,input_sha256=[sha(p) for p in paths]);write_json(dest,payload)
                        verified.extend(reviews);success=True;break
                    except Exception as exc:error=str(exc)
            if not success:verified.extend(dict(stage=o['stage'],keyword=o.get('keyword'),state='failed',error=error) for o in chunk)
            x['ai_review']=dict(state='running',model=MODEL,images=verified)
            write_json(folder/x['slug']/'observations.json',x);write_json(folder/'results.json',items)
            print(f'AI {number}/{len(items)} {x["slug"]} {stages}: {"complete" if success else error}',flush=True)
        by_stage={v['stage']:v for v in verified};expanded=[]
        for obs in required:
            original=aliases.get(obs['stage'],obs['stage'])
            v=dict(by_stage.get(original,dict(state='failed',error='未取得AI输出')))
            v.update(stage=obs['stage'],keyword=obs.get('keyword'))
            if original!=obs['stage']:v['reused_from_stage']=original
            expanded.append(v)
        x['ai_review']=dict(state='complete' if len(expanded)==len(required) and all(v['state']=='complete' for v in expanded) else 'incomplete',model=MODEL,images=expanded)
        write_json(folder/x['slug']/'observations.json',x);write_json(folder/'results.json',items)
