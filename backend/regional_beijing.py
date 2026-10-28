"""Two independently captured exact Beijing guides; no province-wide fallback."""
import copy,hashlib,json,re
from pathlib import Path
from urllib.parse import urldefrag,urlsplit,parse_qs,urljoin
from lxml import html
from regional_guides import digest,resolve_channel

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110112000000/c692cfd3-1a9d-4734-8f16-86b3a0dbafee.html?locationCode=110112000000&serverType=1002'
AUTHORITY='北京市通州区人力资源和社会保障局'
SERVICE='11110112000082974B300201430200200'
CHAOYANG_SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110105000000/75d01c1c-dc66-49fe-93a1-7003eaaedd8a.html'
CHAOYANG_AUTHORITY='北京市朝阳区人力资源和社会保障局'
CHAOYANG_SERVICE='11110105000052732A300201430200200'
DONGCHENG_SOURCE='https://banshi.beijing.gov.cn/pubtask/task/1/110101000000/63fb2f78-f61a-434e-a834-ac398cd29417.html?locationCode=110101000000'
DONGCHENG_AUTHORITY='北京市东城区人力资源和社会保障局'
DONGCHENG_SERVICE='11110101067308122H300201430200200'
SAMPLES={
    '705e848d-4775-4fda-8f07-2b8d90003426':('授权委托书(样表).docx','b399473613078d7f1045ade4f1d10f70d1a2a48182d1e77c02e2db01bab5ffdf'),
    'cd9f9b5c-6fcb-4040-b116-cdf752a4e7ef':('仲裁申请书(样表).docx','ba10414a8d5e8dddaf8fd5c3a9477200c308a44a606a15ef0363e829978aa06d'),
    'f08a123f-4bb8-4d4a-a819-a80d1da16644':('身份证件(样表).docx','ce430936de3c25292538980bc1b6bb53f91dd030298954cedf1e63a6e12e2800'),
}
SECTION_IDS=['basic-main','apply-main','path-main','sample-main','setting-main','charge-main','question-main']
SECTION_NAMES=['基本信息','申请材料','办理流程','结果名称及样本','设定依据','收费依据及标准','常见问题']
def text(e):
    return re.sub(r'【展开】|【收起】|查看详情|来源说明>','',e.text_content()).strip()
def rows(block):
    result={}
    for row in block.xpath('.//tr'):
        cells=row.xpath('./td')
        for i in range(0,len(cells)-1,2):result[text(cells[i])]=text(cells[i+1])
    return result
def _checked_page(page,source,authority,service,district):
    if urldefrag(page.get('url',''))[0]!=source or page.get('title')!='劳动人事争议仲裁申请':
        raise ValueError('不是'+district+'自身仲裁申请指南')
    dom=html.fromstring(page['html'])
    heading=[text(e) for e in dom.xpath('//p[@class="bszn-city"]/span')]
    if (authority not in dom.text_content() or service not in dom.text_content() or heading!=[district]
        or (district=='通州区' and not any('副中心（通州区）' in e.text_content() for e in dom.xpath('//span[@class="dangq"]')))):
        raise ValueError('自身机关、地区或业务办理编码不匹配')
    return dom
def checked_page(page):return _checked_page(page,SOURCE,AUTHORITY,SERVICE,'通州区')
def _chaoyang_page(page):return _checked_page(page,CHAOYANG_SOURCE,CHAOYANG_AUTHORITY,CHAOYANG_SERVICE,'朝阳区')

def _dongcheng_page(page):return _checked_page(page,DONGCHENG_SOURCE,DONGCHENG_AUTHORITY,DONGCHENG_SERVICE,'东城区')

def parse_tongzhou_capture(captures,downloads):
    return _parse_capture(captures,downloads,SOURCE,AUTHORITY,SERVICE,'110112','通州区')

def parse_chaoyang_capture(captures,downloads):
    return _parse_capture(captures,downloads,CHAOYANG_SOURCE,CHAOYANG_AUTHORITY,CHAOYANG_SERVICE,'110105','朝阳区')

def parse_dongcheng_capture(captures,downloads):
    return _parse_capture(captures,downloads,DONGCHENG_SOURCE,DONGCHENG_AUTHORITY,DONGCHENG_SERVICE,'110101','东城区')

def _parse_capture(captures,downloads,SOURCE,AUTHORITY,SERVICE,region_code,district):
    if not set([str(i) for i in range(7)]+['basic','materials','flow'])<=set(captures):
        raise ValueError('缺少实际栏目或展开后的采集证据')
    docs={key:_checked_page(value,SOURCE,AUTHORITY,SERVICE,district) for key,value in captures.items()}
    basic=docs['basic'].get_element_by_id('basic-main');rawfields=rows(basic)
    if rawfields.get('实施机构')!=AUTHORITY or rawfields.get('业务办理项编码')!=SERVICE:
        raise ValueError('基本信息中的机关或事项编码不一致')
    own={'source_url':SOURCE,'region_code':region_code,'collected_at':captures['materials']['captured_at'],
        'verified_at':captures['materials']['captured_at']}
    def field(raw,normalized=None):
        return {**own,'raw_value':raw or '', 'normalized_value':normalized if normalized is not None else raw or None,
            'verification_status':'verified' if raw else 'missing'}
    fields={k:field(v) for k,v in rawfields.items()}
    location=rawfields.get('办理时间和地点','')
    fields['办理地点']=field(next((s.strip() for s in reversed(location.splitlines()) if s.strip().startswith('北京市'+district)),''))
    fields['办理时间']=field(next((s.strip() for s in location.splitlines() if '法定工作日' in s),''))
    charge=rows(docs['5'].get_element_by_id('charge-main'))
    fields['是否收费']=field(charge.get('是否收费',''))
    # Retain the header's original labels and values AND its explicit stage note.
    # The five-day acceptance clock must not become a case-award promise.
    header={}
    for li in docs['basic'].xpath('//ul[contains(@class,"evaluateUl")]/li'):
        labels=li.xpath('./p[@class="orName"]');values=li.xpath('./p[@class="evaluateCon"]')
        if labels and values:header[text(labels[0])]=re.sub(r'\s+','',text(values[0]))
    for key in ['办件类型','法定办结时限','承诺办结时限']:
        fields[key]=field(header.get(key,''))
    fields['到办事现场次数']=field(header.get('到现场次数',''))
    fields['认证等级需求']=field('')
    promises=docs['basic'].xpath('//span[@class="Promise-text"]')
    promise=text(promises[0]) if promises else ''
    if '审查与决定' not in promise:raise ValueError('官方时限说明缺失或改变，需重新核验')
    fields['承诺时限办结说明']=field(promise)
    for key in ['法定办结时限','承诺办结时限']:
        fields[key]['scope']='acceptance_review_decision_not_case_award'
        fields[key]['normalized_value']={'value':header.get(key),'scope':'acceptance_review_decision_not_case_award','official_scope_note':promise}
    flow=docs['flow'].get_element_by_id('path-main')
    if '审查与决定' not in text(flow) or '5个工作日' not in text(flow):
        raise ValueError('审查决定环节或时限已变化，需重新核验')
    fields['审查与决定时限']=field('5个工作日')
    fields['必须到现场原因']=field(rawfields.get('必须现场办理原因说明',''))
    materials=[];materialrows=docs['materials'].xpath('//table[@id="apply-table"]//tr[td]')
    materialrows=[r for r in materialrows if len(r.xpath('./td'))==9]
    if len(materialrows)!=3:raise ValueError('材料结构或数量改变')
    for i,(row,name) in enumerate(zip(materialrows,['仲裁申请书','授权委托书','身份证件'])):
        cells=row.xpath('./td');values=[text(e) for e in cells]
        if values[1]!=name or not values[4]:raise ValueError('材料名称或数量要求改变')
        materials.append({**own,'id':digest([SOURCE,i])[:20],'name':name,'required':values[3],
            'copies':values[4],'raw_copies':values[4],'format':values[5],
            'original_copy':'原件，仅供查验' if i==2 else '原件',
            'purpose':None,'applicable_conditions':'官方标注必要；委托他人参加仲裁时使用，是否免交请向机构确认。' if i==1 else None,
            'details':{'材料来源':values[2],'受理标准':values[7],'提供材料依据':values[8]},
            'verification_status':'verified'})
    controls=docs['materials'].xpath('//table[@id="apply-table"]//a[@doc_id]')
    observed={a.get('doc_id'):(a.get('doc_name'),text(a)) for a in controls}
    if set(observed)!=set(SAMPLES):raise ValueError('自身样例附件身份缺失或改变')
    supplied=[f for f in downloads if f.get('file_type')=='docx']
    if len(supplied)!=3 or {f.get('id') for f in supplied}!=set(SAMPLES):raise ValueError('自身样例原件缺失或重复')
    templates=[]
    for f in supplied:
        identity=f['id'];name,checksum=SAMPLES[identity]
        relative='templates/_docx/_regional/'+region_code+'/'+identity+'.docx';url='https://banshi.beijing.gov.cn/pubtask/download/'+identity+'.docx'
        path=ROOT/relative
        if (observed[identity]!=(name,'样例下载') or f.get('original_name')!=name or urldefrag(f.get('source_url',''))[0]!=SOURCE
            or f.get('file')!=relative or f.get('download_url')!=url or f.get('final_download_url')!=url
            or f.get('sha256')!=checksum or f.get('http_status')!=200 or f.get('download_status')!='downloaded'
            or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum):
            raise ValueError(district+'附件来源、名称、路径或SHA不匹配')
        templates.append({**copy.deepcopy(f),**own,'official_annex_id':identity,'official_kind':'sample',
            'classification_note':'官方样表，含示例信息；不是空白表格，尚未适配填写生成。',
            'can_generate':False,'document_types':[]})
    sections={name:text(docs[str(i)].get_element_by_id(identity)) for i,(identity,name) in enumerate(zip(SECTION_IDS,SECTION_NAMES))}
    sections['基本信息']=text(basic);sections['申请材料']=text(docs['materials'].get_element_by_id('apply-main'));sections['办理流程']=text(flow)
    return {'province':'beijing','province_name':'北京市','city':'北京市','district':district,'region_code':region_code,
        'service_name':'劳动人事争议仲裁申请','service_code':SERVICE,'authority':AUTHORITY,
        'source_url':SOURCE,'source_title':'劳动人事争议仲裁申请','source_type':'official_service_guide',
        'collected_at':own['collected_at'],'verified_at':own['verified_at'],'verification_status':'partial',
        'fields':fields,'materials':materials,'templates':templates,'sections':sections,
        'channel':resolve_channel(rawfields,sections['办理流程']),
        'warnings':['仅适用于该'+district+'事项，不代表北京市其他区县；户籍所在地不直接决定仲裁管辖。',
            '5个工作日是本指南“审查与决定”环节的时限，不是仲裁案件整体结案时限。',
            '公开指南只列三个材料条目，证据材料及委托情形仍须结合受理条件和机构要求核对，不表示只交三种材料即可受理。',
            '官方仅提供三个样表，含旧日期、示例姓名及证照图片；不能当作空白模板，本区暂未开放填写生成。',
            '指南同时列窗口和网上办理，但仍要求按规定提交书面申请；登录后是否需到场请向办理机构核实。']}

def verify_tongzhou_online_capture(before,after):
    return _verify_online_capture(before,after,checked_page,SOURCE)

def verify_chaoyang_online_capture(before,after):
    return _verify_online_capture(before,after,_chaoyang_page,CHAOYANG_SOURCE)

def verify_dongcheng_online_capture(before,after):
    return _verify_online_capture(before,after,_dongcheng_page,DONGCHENG_SOURCE)

def _verify_online_capture(before,after,check,source):
    dom=check(before)
    controls=[a for a in dom.xpath('//a[@href]') if text(a)=='网上办理']
    if len(controls)!=1:raise ValueError('缺少自身唯一网上办理入口')
    entry=urljoin(source,controls[0].get('href'));u=urlsplit(entry)
    expected='aHR0cHM6Ly9mdXd1LnJzai5iZWlqaW5nLmdvdi5jbi96aHJzL2FwaTQvYXJiaXRyYXRpb24vaHRtbC9ob21lL2luZGV4'
    if (u.scheme!='https' or u.netloc!='banshi.beijing.gov.cn' or u.path!='/pubservice/proAccept/urlCheck'
        or parse_qs(u.query).get('baseUrl')!=[expected]):
        raise ValueError('自身仲裁网上办理入口已变化；不能用调解入口替代')
    target=urlsplit(after.get('url',''));query=parse_qs(target.query)
    back=query.get('backUrl',[''])[0]
    if (target.scheme!='https' or target.netloc!='banshi.beijing.gov.cn'
        or target.path!='/pubservice/user/commonLoginPage' or not back.startswith('/proAccept/urlCheck?')
        or parse_qs(urlsplit(back).query).get('baseUrl')!=[expected]
        or query.get('serverType')!=parse_qs(u.query).get('serverType')):
        raise ValueError('不是自身入口实际到达的官方登录选择页')
    afterdom=html.fromstring(after['html'])
    if '请选择登录' not in afterdom.text_content() or not any('个人登录' in text(a) for a in afterdom.xpath('//a')):
        raise ValueError('实际登录边界内容缺失，不能宣称入口已核验')
    return {'official_link':True,'status':'auth_required','url':entry,'final_url':after['url'],
        'checked_at':after['captured_at'],'post_login_submission_verified':False,
        'scope_notice':'实际点击仅到达官方个人/法人登录选择页；未登录，未核验登录后的网办范围、到场要求或提交能力。'}
