"""Prioritize official portal guides and turn sourced facts into short UI cards."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'config/province_experience_policy.json').read_text(encoding='utf8'))
PORTAL_CONFIG = json.loads((ROOT / 'config/province_service_portals.json').read_text(encoding='utf8'))
PORTALS = PORTAL_CONFIG['portals']
EXPERIENCE_ROOT = ROOT / 'templates/_reports/province-experiences'


def portal_source(url, slug):
    host = (urlsplit(url).hostname or '').lower()
    if not host.endswith('.gov.cn'):
        return False
    expected = (urlsplit(PORTALS[slug]).hostname or '').removeprefix('www.')
    aliases = {'beijing': ('banshi.beijing.gov.cn',), 'shanghai': ('zwdt.sh.gov.cn',), 'tianjin': ('zwfw.tj.gov.cn',), 'shanxi': ('sxzwfw.gov.cn','zwfw.shanxi.gov.cn'), 'hebei': ('hbzwfw.gov.cn','zwfw.hebei.gov.cn'), 'chongqing': ('zwykb.cq.gov.cn',), 'jiangsu': ('jszwfw.gov.cn',), 'zhejiang': ('zjzwfw.gov.cn',), 'guangdong': ('gdzwfw.gov.cn',), 'jiangxi': ('jxzwfww.gov.cn',), 'liaoning': ('lnzwfw.gov.cn',), 'yunnan': ('zwfw.yn.gov.cn',), 'xizang': ('xzzwfw.gov.cn',)}
    window=(urlsplit(PORTAL_CONFIG.get('navigation_windows',{}).get(slug,'')).hostname or '')
    domains = tuple(domain for domain in (expected, *aliases.get(slug, ()),window) if domain)
    return any(host == domain or host.endswith('.' + domain) for domain in domains)


def service_kind(title):
    title = re.sub(r'\s+', '', title or '')
    if re.search(r'仲裁员|仲裁机构查询|劳动保障监察|欠薪保障金|委员会.*(?:备案|登记|设立)', title):
        return 'other'
    if '劳动' in title and '仲裁' in title and not re.search('委员会.*(?:备案|登记|设立)', title):
        return 'arbitration'
    if '劳动' in title and '调解' in title:
        return 'mediation'
    return 'unknown'


def guide_rank(guide, slug, position=0):
    text = ' '.join(str(guide.get(k, '')) for k in ('region_name', 'authority', 'guide_url'))
    capital = POLICY['capitals'][slug]
    url=urlsplit(guide.get('guide_url',''));query=dict(parse_qsl(url.query));query.update(dict(parse_qsl(url.fragment.split('?',1)[-1])))
    codes=[str(guide.get('region_code',''))]+[v for k,v in query.items() if k.lower() in ('areacode','regioncode','locationcode','sitecode')]
    in_capital = capital.removesuffix('市') in text or any(code.startswith(POLICY['capital_codes'][slug]) for code in codes)
    return (not portal_source(guide.get('guide_url', ''), slug), not in_capital, position)


def choose_guide(guides, slug):
    from portal_audit_capture import official
    eligible = [(i, g) for i, g in enumerate(guides) if is_guide_url(g.get('guide_url', '')) and official(g.get('guide_url', '')) and (service_kind(g.get('service_name')) in ('arbitration', 'mediation') or (service_kind(g.get('service_name')) == 'unknown' and any(re.search('仲裁申请书|证据清单|证据目录', str(m)) for m in g.get('materials', []) + g.get('templates', []))))]
    return min(eligible, key=lambda pair: guide_rank(pair[1], slug, pair[0]))[1] if eligible else None


def is_guide_url(url):
    return bool(url) and not re.search(r'/search(?:/|\?|$)|search-results|searchValue=|intellsearch|api-gateway/.*/search', url, re.I)


def valid_guide(guide):
    if not guide:return False
    flow=re.sub(r'\s+','',guide.get('workflow_text') or '')
    navigation_only=bool(re.fullmatch(r'(?:中介服务|常见问题|基本信息|办事评价|受理条件|申请材料|办理流程|收费标准|设定依据)+',flow))
    return bool(is_guide_url(guide.get('guide_url', '')) and service_kind(guide.get('service_name')) in ('arbitration', 'mediation') and (guide.get('steps') or (flow and not navigation_only) or guide.get('materials') or guide.get('templates')))

def pending_openclaw_reviews(profiles):
    """Keep unreviewed native browser evidence out of the client snapshot."""
    return [slug for slug,p in profiles.items() if p.get('openclaw_task') and (p.get('ai_review',{}).get('state')!='reviewed' or p.get('ai_review',{}).get('parse_state')!='valid')]

def guide_belongs_to_province(guide,slug):
    """Verify ownership before accepting an agent's navigation result."""
    url=guide.get('guide_url','')
    if any(other!=slug and portal_source(url,other) for other in PORTALS):return False
    code=str(guide.get('region_code',''))
    prefix=POLICY['capital_codes'][slug][:2]
    if re.fullmatch(r'\d{6,12}',code) and not code.startswith(prefix):return False
    if portal_source(url,slug) or (re.fullmatch(r'\d{6,12}',code) and code.startswith(prefix)):return True
    scope=' '.join(str(guide.get(k,'')) for k in ('region_name','authority'))
    from province_documents import PROVINCE_DOCUMENTS
    return PROVINCE_DOCUMENTS[slug]['name'] in scope or POLICY['capitals'][slug] in scope


def short_step(step):
    name = step.get('name', '')
    official_name=name
    aliases={'收件':'接收材料','审核':'审查','审核申请':'审查','办结':'结案处理','制证':'发证','制证/文':'发证'}
    name=aliases.get(name,name)
    pairs = [('申请', '先交材料', '按下面的材料清单准备，交到官方指南指定的办理入口。'), ('受理', '留意受理通知', '提交后留意通知；需要补材料时，按通知补齐。'), ('审查', '配合材料检查', '工作人员核对材料时，按要求说明或补充。'), ('决定', '查看办理结果', '查看官方发给你的办理结果，有疑问就向办理机构询问。'), ('送达', '收好结果文书', '按通知收取文书，仔细看文书里的后续事项。'), ('发证', '按通知领取结果', '按官方通知领取并保存结果。'), ('调解', '按通知参加调解', '按通知参加调解，看清协议内容再决定是否签字。'), ('开庭', '按通知参加开庭', '看清通知上的时间和地点，提前准备要带的材料。'), ('接待', '先登记你的问题', '在官方指定的接待渠道说明你的问题，按要求登记。'), ('立案', '留意立案通知', '留意是否立案的通知，按通知补充材料。'), ('排庭', '留意开庭安排', '收到开庭通知后，看清时间、地点和要带的材料。'), ('审理', '按通知参加审理', '按通知参加审理，准备好要说明的事情和相关证据。'), ('结案', '查看案件结果', '保存结果文书，仔细看后续事项。')]
    if name=='接收材料':matched=('留意材料接收','提交后留意材料是否已接收，需要补材料时按通知补齐。')
    elif '开庭' in name and '调解' in name:matched=('留意开庭、调解通知','按通知参加开庭或调解，看清时间、地点和要带的材料。')
    else:matched = next(((plain,text) for word,plain,text in pairs if word in name), None)
    title = matched[0] if matched else name or '按官方通知办理'
    description = re.sub(r'\s+', ' ', step.get('description', '')).strip()
    sentence = re.split(r'(?<=[。；])', description)[0].strip()
    return {'title': title, 'text': matched[1] if matched else sentence[:140] or '具体怎么做，请看官方指南。', 'official_name': official_name, 'source_text': description}


def workflow_steps(raw):
    """Use actual phase labels and chains; never turn tabs/FAQ into steps."""
    phases=('申请','收件','接收申请','审核申请','受理','审查','审理','调解','决定','裁决','制证','送达','颁发和送达','办结','结案处理','接待登记','立案登记','案件组庭排庭','案件审理','出具结案文书')
    lines=[s.strip() for s in raw.splitlines() if s.strip()]
    headers=[i for i,s in enumerate(lines) if s in ('办理流程','办事流程','办理程序')]
    if headers:lines=lines[headers[-1]+1:]
    boundary=next((i for i,s in enumerate(lines) if s in ('审批结果','办件公示','收费情况','办理地点/时间','办理方式','更多信息','线下办理','常见问题','特别程序')),len(lines))
    lines=lines[:boundary]
    for text in lines:
        chain=[s.strip() for s in re.split(r'[-—－→]+',text)]
        if len(chain)>1 and all(s in phases for s in chain):return [short_step({'name':s,'description':text}) for s in chain]
    labels=[]
    for text in lines:
        name=re.sub(r'^\d+\s*(?=[\u4e00-\u9fff])','',text.split('\t')[0].strip())
        if name in phases and name not in labels:labels.append(name)
    if labels:return [short_step({'name':name,'description':'\n'.join(lines)}) for name in labels]
    # A single explicit online instruction, such as Shanghai's union route.
    sentences=[s for s in lines if 3<len(s)<240 and re.search('登录|提交|申请|受理|审理|调解',s) and not re.search('申请书|更多信息|承诺办结|到现场|特别程序|名称|法定',s)]
    return [{'title':'打开官方申请入口' if s.startswith('登录') else '按官方流程办理','text':s[:140],'source_text':s,'official_name':''} for s in sentences[:3]]


def plain_guide(guide, slug, template_scope='', observed_scope=''):
    kind = service_kind(guide.get('service_name'))
    steps = [short_step(s) for s in guide.get('steps', []) if s.get('name') or s.get('description')]
    raw = guide.get('workflow_text', '')
    if not steps and raw:
        steps=workflow_steps(raw)
    notes = ['先确认在哪里办理，再填材料。', '签名请本人手写。材料带几份，请看官方指南。']
    if guide.get('materials_complete') is False:notes.append('材料清单请以官方 PDF 为准。')
    if kind == 'mediation':
        notes.insert(0, '这里办理调解。需要申请仲裁，请另找“仲裁申请”入口。')
    from province_documents import PROVINCE_DOCUMENTS
    if template_scope and PROVINCE_DOCUMENTS[slug].get('documents'):
        notes.append('这份在线表格用于“' + template_scope + '”。在其他地区办理，请先问当地窗口能否使用。')
    if observed_scope and observed_scope != POLICY['capitals'][slug]:
        notes.append('这次查的是“' + observed_scope + '”。其他地区请查看当地指南。')
    materials = []
    for item in guide.get('materials', []) or [t.get('material_name','') for t in guide.get('templates',[])]:
        if isinstance(item, dict):
            value = item.get('materialName') or item.get('name') or item.get('clmc') or ''
        else:
            value = str(item)
        value = re.sub(r'^\d+[\s、.\t]+', '', value).strip()
        # Some portals append footer requirements or download labels to rows.
        # These are not documents the applicant needs to bring.
        if re.search(r'信息真实|材料齐全|填报完整|法规规定要求|申请材料总要求', value):
            continue
        if re.search(r'示范文本下载|格式文本下载', value) and ' ' in value:
            value=value.split(' ',1)[0]
        if value and len(value) < 100 and not re.search(r'如何|哪些|常见问题', value):
            materials.append(value)
    return {'service_kind': kind, 'service_name': guide.get('service_name', ''), 'scope': guide.get('region_name') or observed_scope or '官方页面未标明地区',
            'steps': steps, 'materials': list(dict.fromkeys(materials)), 'notes': notes, 'source_url': guide.get('guide_url'), 'captured_at': guide.get('captured_at'),
            'workflow_detected': bool(steps), 'preferred_city': POLICY['capitals'][slug]}


def load_experiences():
    latest = EXPERIENCE_ROOT / 'latest.json'
    if not latest.is_file():
        return None
    index = json.loads(latest.read_text(encoding='utf8'))
    run_id = index.get('id', '')
    if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[a-z0-9]{8}', run_id):
        raise ValueError('Invalid province experience run')
    return json.loads((EXPERIENCE_ROOT / run_id / 'experiences.json').read_text(encoding='utf8'))
