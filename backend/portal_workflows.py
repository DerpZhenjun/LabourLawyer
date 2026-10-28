"""Evidence-backed district guides; missing coverage stays explicit for the UI."""
import asyncio
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from portal_interactions import activate_section, scan_scroll

FLOW_LABELS=('办理流程','办理程序','流程说明','办理环节','办事流程','查看办理流程','怎么办')

def service_title(text):
    parts=[p.strip() for p in re.split(r'[\n\t]',text) if p.strip()]
    for i,value in enumerate(parts[:-1]):
        if value in ('事项名称','办事事项名称','服务事项名称','业务名称'):
            child=parts[i+1]
            if child in ('劳动者申请立案','用人单位申请立案') and re.search('实施清单名称[：:]劳动人事争议仲裁申请',text):return '劳动人事争议仲裁申请（'+child+'）'
            return child
        # Many guide pages put the actual title directly after their breadcrumb.
        # This also identifies non-labour arbitration services for exclusion.
        if value.startswith('当前位置') and len(parts[i+1])<90 and value.endswith(parts[i+1]):return parts[i+1]
        labelled=re.fullmatch(r'(?:事项名称|办事事项名称|服务事项名称|业务名称)\s*[:：]\s*(.{2,90})',value)
        if labelled:return labelled.group(1)
    for value in parts:
        if len(value)<80 and re.fullmatch(r'(?:工会)?劳动.{0,45}(?:仲裁|调解)(?:.{0,15}(?:申请|受理|服务|指南))?',value):return value
    return ''

def arbitration_service(title):
    return bool(re.search(r'劳动.{0,35}(仲裁|调解)',title) and not re.search(r'仲裁员|仲裁机构查询|劳动保障监察|欠薪保障金',title))

def clean(value):
    from lxml import html
    if value is None:return ''
    value=str(value)
    if '<' in value:
        try:value=html.fromstring(value).text_content()
        except (ValueError,TypeError):pass
    return re.sub(r'\s+',' ',value).strip()

def section_text(text,labels,next_labels):
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    chunks=[]
    for i,line in enumerate(lines):
        if line not in labels:continue
        segment=[]
        for following in lines[i+1:]:
            if following in next_labels:break
            segment.append(following)
            if sum(map(len,segment))>12000:break
        if segment:chunks.append('\n'.join(segment))
    return max(chunks,key=len,default='')

def guide_record(item,observation,text,flow_text=''):
    from portal_audit import now
    flow=section_text(flow_text or text,FLOW_LABELS,('办理结果','收费标准','收费项目信息','常见问题','申请材料','基本信息','结果名称及样本','设定依据','咨询电话','中介服务','办事评价','受理条件','带什么','详版指南','服务承诺','相关站点','国家政务服务平台','切换简洁版'))
    authority=re.search(r'(?m)^\s*(?:办理部门(?:[（(]实施主体[）)])?|实施主体|实施机构|实施单位|办理机构|受理机构)\s*[:：]?\s*\n?([^\n\t]{2,100})',text)
    region=re.search(r'(?m)^\s*(?:所属地区|办理地区|行政区划)\s*[:：]?\s*\n?([^\n\t]{2,30})$',text)
    parsed=urlsplit(observation.get('final_url',''));query=dict(parse_qsl(parsed.query))
    query.update(dict(parse_qsl(parsed.fragment.split('?',1)[-1])))
    code=query.get('locationCode') or query.get('areaCode') or query.get('regionCode') or ''
    if not re.fullmatch(r'\d{6,12}',code):
        path_code=re.search(r'/pubtask/task/\d/(\d{12})/',parsed.path)
        code=path_code.group(1) if path_code else ''
    return dict(id=hashlib.sha256(observation.get('final_url','').encode()).hexdigest()[:20],province=item['slug'],province_name=item['name'],
        guide_url=observation.get('final_url'),service_name=service_title(text),
        region_name=region.group(1).strip() if region else '',region_code=code,authority=authority.group(1).strip() if authority else '',
        jurisdiction_status='page_explicit' if region else 'not_explicit',workflow_text=flow,steps=[],
        materials=observation.get('material_names',[]),templates=observation.get('template_links',[]),
        screenshot=observation.get('screenshot'),flow_screenshot=observation.get('flow_screenshot'),stage=observation['stage'],
        captured_at=now(),state='captured' if flow else 'workflow_not_detected',source_kind='official_page',
        evidence_sha256=observation.get('screenshot_sha256'),scope_note='仅适用于该指南所载地区；未标明地区时不作省级通用推断')

def official_region_names(records):
    mapping={}
    def walk(node):
        if isinstance(node,list):
            for child in node:walk(child)
        elif isinstance(node,dict):
            name=node.get('locationName') or node.get('areaName') or node.get('area_name') or node.get('REGNNM')
            code=node.get('id') or node.get('areaCode') or node.get('area_code') or node.get('REGNCODE')
            if name and code and re.fullmatch(r'\d{6,12}',str(code)):mapping[str(code)]=name
            for value in node.values():
                if isinstance(value,(dict,list)):walk(value)
    for record in records:
        if not re.search('serviceArea|list-region|fsx03001',record['url']):continue
        try:
            data=json.loads(record['body'])
            if isinstance(data.get('C-Response-Body'),str):data=json.loads(data['C-Response-Body'])
            walk(data)
        except (ValueError,TypeError):continue
    return mapping

class PublicResponses:
    def __init__(self,context):
        self.context=context;self.records=[];self.tasks=set()
        context.on('response',self.schedule)
    def schedule(self,response):
        if not (urlsplit(response.url).hostname or '').endswith('.gov.cn'):return
        if re.search('login|userinfo|token|sso|passport|analytics',response.url,re.I):return
        if not re.search('json|text/plain',' '.join([response.headers.get('content-type','')])):return
        task=asyncio.create_task(self.capture(response));self.tasks.add(task);task.add_done_callback(self.tasks.discard)
    async def capture(self,response):
        try:
            body=await asyncio.wait_for(response.text(),10)
            if len(body)>2000000:return
            json.loads(body)
            self.records.append(dict(url=response.url,method=response.request.method,post_data=response.request.post_data,status=response.status,body=body,sha256=hashlib.sha256(body.encode()).hexdigest()))
        except Exception:pass
    async def flush(self,folder):
        if self.tasks:await asyncio.gather(*list(self.tasks),return_exceptions=True)
        from portal_audit import write_json
        write_json(folder/'public-guide-responses.json',self.records)

def parse_public_record(record):
    """Normalize only known official schema fields, retaining response provenance."""
    payload=json.loads(record['body']);url=record['url']
    if urlsplit(url).hostname=='wssp.hainan.gov.cn' and urlsplit(url).path=='/wssp3/bszn/exempt/allInfo':
        data=payload.get('data') or {};basic=data.get('sxImplBasic') or {}
        if not basic.get('rowguid') or not arbitration_service(basic.get('taskname','')):return None
        phases=sorted(data.get('flowHjs') or [],key=lambda s:float(s.get('hjNum') or 0))
        steps=[dict(order=i+1,name=clean(s.get('hjTbcxname') if s.get('hjType')==2 else s.get('hjName')),description=clean(s.get('hjSm')),duration=clean(s.get('hjLimittime')),special=s.get('hjType')==2) for i,s in enumerate(phases)]
        materials=[dict(name=clean(m.get('materialname')),quantity=clean(m.get('pagenum')),requirement=clean(m.get('isneed'))) for m in data.get('materials') or []]
        return dict(region_code=clean(basic.get('xzqhcodeing')),region_name=clean(basic.get('xzqhcodename')),authority=clean(basic.get('deptname')),service_name=clean(basic.get('taskname')),steps=steps,workflow_text='\n'.join(s['name']+' '+s['description'] for s in steps),materials=materials,materials_complete=True,jurisdiction_status='matched_official_public_response',source_response_url=url,source_response_sha256=record['sha256'])
    if '/implement/queryImplementInfo.do' in url:
        data=payload.get('data') or {}
        if not isinstance(data,dict):return None
        steps=[dict(order=i+1,name=clean(s.get('ywhjName')),description=clean(s.get('postResponse')),duration=clean(s.get('handleTimeLimit'))) for i,s in enumerate(sorted(data.get('blhjJson') or [],key=lambda s:int(s.get('sort') or 0)))]
        materials=[dict(name=clean(m.get('materialName')),materialName=clean(m.get('materialName')),quantity=clean((m.get('json') or {}).get('ggfs')),requirement=clean(m.get('materialNeedName'))) for m in data.get('clJson') or []]
        return dict(region_code=clean(data.get('ssqdZoneCode')),region_name=clean(data.get('ssqdZoneName')),authority=clean(data.get('implementOrgName') or data.get('ssqdDeptName')),service_name=clean(data.get('ssqdName')),steps=steps,workflow_text=clean(data.get('hanleProc')),materials=materials,materials_complete=True,durations={'legal':data.get('legalTime'),'promise':data.get('promiseTime')},source_response_url=url,source_response_sha256=record['sha256'])
    if '/get-regulation-info' in url:
        data=payload.get('result') or {}
        if not isinstance(data,dict):return None
        steps=[dict(order=i+1,name=clean(s.get('nodename') or s.get('stepname')),description=clean(s.get('spbz')),result=clean(s.get('spresult')),duration=clean(s.get('blsx'))) for i,s in enumerate(data.get('taskNodeList') or [])]
        return dict(steps=steps,workflow_text='\n'.join(s['name']+' '+s['description'] for s in steps),materials=data.get('materialInformationList',[]),authority=clean(data.get('departName')),region_code=clean(data.get('areaId')),contacts=data.get('ListInfoAboutAddressAndPhone',[]),jurisdiction=data.get('matterSpecial'),source_response_url=url,source_response_sha256=record['sha256'])
    if '/gml/web10002' in url:
        data=payload.get('C-Response-Body') or {}
        if isinstance(data,str):data=json.loads(data)
        # Some versions wrap the actual guide in a body/data property.
        if isinstance(data,dict) and isinstance(data.get('data'),dict):data=data['data']
        if not isinstance(data,dict):return None
        steps=[dict(order=i+1,name=name,description=clean(data.get(field)),duration=clean(data.get(field+'Day'))) for i,(name,field) in enumerate([('申请','apply'),('受理','accept'),('审查','checkup'),('决定','decide'),('送达','arrival')]) if data.get(field)]
        return dict(region_code=data.get('regncode',''),authority=data.get('orgName',''),service_name=data.get('name',''),steps=steps,workflow_text='\n'.join(s['name']+' '+s['description'] for s in steps),materials=data.get('matterFileList',[]),jurisdiction=data.get('countyPerRange'),contacts=[data.get('sceneAdvice'),data.get('adviceWay')],durations={'legal':data.get('legalDay'),'promise':data.get('promiseDay')},source_response_url=url,source_response_sha256=record['sha256'])
    return None

async def capture_flow(page,folder,stage):
    from portal_audit_capture import snapshot
    from portal_guide_navigation import body_text
    await activate_section(page,FLOW_LABELS)
    await scan_scroll(page,('流程','受理','审查'))
    # Focus the actual process heading, rather than the materials or page banner.
    for frame in page.frames:
        for label in FLOW_LABELS:
            nodes=frame.get_by_text(label,exact=True)
            for index in reversed(range(min(await nodes.count(),12))):
                try:
                    node=nodes.nth(index)
                    if not await node.is_visible():continue
                    await node.scroll_into_view_if_needed(timeout=1200)
                    break
                except Exception:pass
    text=await body_text(page);steps=[]
    for frame in page.frames:
        flow=frame.locator('#path-table:visible,#flowChart:visible,#workflow:visible,.workflow-content:visible')
        if await flow.count():
            text='办理流程\n'+await flow.first.inner_text()+'\n办理结果'
            await flow.first.scroll_into_view_if_needed(timeout=2500)
            phases=flow.first.locator('li')
            for i in range(min(await phases.count(),30)):
                phase=phases.nth(i);name=phase.locator('.STD_NAME')
                name=await name.first.inner_text() if await name.count() else ''
                rows=await phase.locator('table tbody tr').evaluate_all("ns=>ns.map(n=>Array.from(n.querySelectorAll('td')).map(c=>c.innerText.trim()))")
                if name or rows:steps.append(dict(order=i+1,name=name,rows=rows,description=await phase.inner_text()))
            break
    # Image-only flowcharts need their own viewport evidence.
    for frame in page.frames:
        heading=frame.get_by_text('办理流程图',exact=True)
        if await heading.count() and await heading.first.is_visible():
            await heading.first.evaluate("n=>window.scrollTo({top:scrollY+n.getBoundingClientRect().top-80,behavior:'instant'})")
            await page.wait_for_timeout(300)
            break
    obs=await snapshot(page,folder,stage+'-flow',action='记录本地区公开办理流程');obs['structured_steps']=steps
    return text,obs

def save_catalog(folder,item,records,discovered,pending):
    from portal_audit import now,write_json
    by_url={r['guide_url']:r for r in records if r.get('guide_url')}
    records=list(by_url.values())
    coverage=dict(discovered_urls=list(dict.fromkeys(discovered)),discovered_candidates=len(set(discovered)),discovered_guides=len(set(discovered)),captured_guides=len(records),workflow_guides=sum(bool(r.get('workflow_text') or r.get('steps')) for r in records),
        pending_guides=list(dict.fromkeys(pending)),state='public_discovery_complete' if not pending else 'partial',
        exhaustive_administrative_coverage=False,note='已采集公开检索和地区选择中发现的指南；不能据此推断未发现地区没有服务。')
    result=dict(schema_version=1,province=item['slug'],province_name=item['name'],updated_at=now(),coverage=coverage,guides=records)
    write_json(folder/'workflows.json',result);item['workflow_coverage']=coverage
    return result
