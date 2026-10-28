"""Furong's own formally listed Hunan guide, originals and public login boundary."""
import copy,hashlib,re
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from lxml import html
from regional_guides import digest,resolve_channel
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://zwfw-new.hunan.gov.cn/hnywtb/service/guide.html?id=aYcZ8ELbR56Me61a8eSG0A&rightsCode=002014302002&ywCode=01&approve_id=0661f202529745928ad2d4bc532e233a'
APPROVE='0661f202529745928ad2d4bc532e233a'
AUTHORITY='芙蓉区人力资源和社会保障局'
SERVICE='劳动人事争议仲裁申请'
FILES={
 '1624951667887':('1－仲裁申请书（劳动者）.doc','c6bbebf6eed3a11f1cbe5ee14cd6de9937f741c9fcda37165e06d0706e18ea97','blank','zwfw202106'),
 '1624951667935':('2－仲裁申请书（单位）.doc','756b7ee8f3d4a0d5ad23adaec090b5f1722acc7669c869638b0535dcdf9ae279','blank','zwfw202106'),
 '1732694895374':('仲裁申请书（劳动者）.doc','369d38b1bcb1d92e0be6b815d6269967fc7324afbb63cc22a94331bbfcc220cc','sample','zwfw202411'),
 '1732694895330':('仲裁申请书（单位）.doc','00a47b36fa43d89f8c604d66585ac5e191360dd3d546feecc82ea8d6b4307444','sample','zwfw202411'),
}
MATERIALS=[('4891df7773174447bdc418d4b48af0b6','劳动仲裁申请书'),('53d02c276a644f23911413115fe65cac','居民身份证'),('6d7b57ec64704cec9bd818158ade7092','营业执照'),('5c3437efd3b64443a07a4dd8e1bd3537','证据材料')]
def text(e):return re.sub(r'\s+',' ',e.text_content()).strip()
def pairs(e):
    result={}
    for row in e.xpath('.//tr'):
        cells=row.xpath('./td')
        for i in range(0,len(cells)-1,2):result[text(cells[i]).rstrip('：:')]=text(cells[i+1])
    return result
def checked(page):
    if page.get('url')!=SOURCE or page.get('title')!='办事指南':raise ValueError('不是本区自身正式指南')
    dom=html.fromstring(page['html'])
    if [text(e) for e in dom.xpath('//h2[@class="title-name"]')]!=[SERVICE]:raise ValueError('不是仲裁申请事项')
    basic=dom.xpath('//div[@data-lift-target="0"]')
    if len(basic)!=1 or pairs(basic[0]).get('办理部门')!=AUTHORITY:raise ValueError('本区自身办理机关未加载或不匹配')
    return dom
def parse_furong_capture(captures,downloads):
    listing=captures['list'];u=urlsplit(listing.get('url',''));q=parse_qs(u.query)
    if u.hostname!='zwfw-new.hunan.gov.cn' or q.get('areacode')!=['430102999000'] or q.get('orgId')!=['b64b25bb2e0a449fb82212e04984cee8']:raise ValueError('没有本区自身目录来源')
    rows=html.fromstring(listing['html']).xpath('//tr[td/a[@title="劳动人事争议仲裁申请"]]')
    if len(rows)!=1 or AUTHORITY not in text(rows[0]) or not rows[0].xpath('.//a[@onclick="checkGuide(\''+APPROVE+'\',\'Y\',\'\');"]'):
        raise ValueError('自身仲裁目录行未明确指向本指南；不能混用调解事项')
    docs={k:checked(v) for k,v in captures.items() if k not in {'list','online'}}
    dom=docs['basic'];raw=pairs(dom.xpath('//div[@data-lift-target="0"]')[0])
    if not raw.get('办理地点','').startswith('湖南省长沙市芙蓉区人民东路189号'):raise ValueError('本区窗口地址改变，需重新核验')
    own={'source_url':SOURCE,'region_code':'430102','collected_at':captures['basic']['captured_at'],'verified_at':captures['basic']['captured_at']}
    def field(value):return {**own,'raw_value':value or '', 'normalized_value':value or None,'verification_status':'verified' if value else 'missing'}
    fields={k:field(v) for k,v in raw.items()}
    for e in dom.xpath('//div[contains(@class,"msg")][p/span[@class="count"]]'):
        labels=e.xpath('./span[@class="desc"]');values=e.xpath('./p')
        if labels and values:fields['到办事现场次数' if text(labels[0])=='到现场次数' else text(labels[0])]=field(re.sub(r'\s+','',text(values[0])))
    for k in ['认证等级需求','计划生效日期','计划取消日期','预约方式','物流寄送','结果领取方式']:
        fields[k]=field('')
    fields['咨询方式']=field(raw.get('咨询服务',''));fields['必须到现场原因']=field(raw.get('必需现场办理原因',''))
    for k in ['法定办结时限','承诺办结时限','必须到现场原因','到办事现场次数']:fields[k]['verification_status']='conflict'
    materials=[];blocks=dom.xpath('//dl[@data-material-id]')
    if len(blocks)!=4:raise ValueError('自身四项材料结构变化')
    for block,(identity,name) in zip(blocks,MATERIALS):
        if block.get('data-material-id')!=identity or [text(e) for e in block.xpath('./dt//h2')]!=[name]:raise ValueError('本区材料身份或顺序变化')
        detail=pairs(block);required=block.xpath('./dt//div[@class="materialsName"]/span')
        if not required or text(required[0])!='必要':raise ValueError('材料必要性改变，需核验')
        exemptions=block.xpath('.//div[@role="tooltip"]')
        if exemptions:
            exemption=text(exemptions[0])
            if exemption!='该材料已关联电子证照，如您已有共享数据，则可免提交':raise ValueError('免交条件变化')
            detail['免提交条件']=exemption
        form=detail.get('材料形式','');notice=detail.get('填报须知','')
        if not all(detail.get(k) for k in ['来源渠道','材料类型','材料形式','提交方式','受理标准','填报须知']):raise ValueError('本区材料详情缺失')
        materials.append({**own,'id':digest([SOURCE,identity])[:20],'official_material_id':identity,'name':name,
            'required':'必要（符合共享条件可免提交）' if exemptions else '必要',
            'copies':notice if '份数' in notice else ('1份' if '(1份)' in form else None),
            'raw_copies':form+'；'+notice,'format':form,'original_copy':detail['材料类型'],'purpose':None,
            'applicable_conditions':'个性化单位登记地和层级尚未选择；只展示公开材料，不代判断管辖。',
            'details':detail,'verification_status':'partial' if '份数' in notice else 'verified'})
    supplied=[f for f in downloads if f.get('file_type')=='doc']
    if len(supplied)!=4 or {f.get('id') for f in supplied}!=set(FILES):raise ValueError('本区四份原件不完整')
    templates=[]
    for f in supplied:
        identity=f['id'];name,checksum,kind,bucket=FILES[identity];path='templates/_docx/_regional/430102/'+identity+'.doc'
        url=urlsplit(f.get('download_url',''));query=parse_qs(url.query)
        expected_role='blank_control_unclassified' if kind=='blank' else 'sample_control_unclassified'
        if (f.get('source_url')!=SOURCE or f.get('region_code')!='430102' or f.get('file')!=path or f.get('original_name')!=name
            or f.get('official_kind')!=expected_role or f.get('sha256')!=checksum or f.get('http_status')!=200 or f.get('download_status')!='downloaded'
            or f.get('final_download_url')!=f.get('download_url') or url.scheme!='https' or url.hostname!='zwfw-new.hunan.gov.cn'
            or url.path!='/picPathMapping' or query.get('bucketName')!=[bucket] or not query.get('picPath',[''])[0].endswith('/'+identity+'$$'+name)
            or not (ROOT/path).is_file() or hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=checksum):raise ValueError('本区附件来源、控件角色、地区、路径或SHA不匹配')
        templates.append({**copy.deepcopy(f),**own,'official_kind':kind,'official_annex_id':identity,'can_generate':False,'document_types':[],
            'classification_note':'官网模板控件原件；空白表跨页版式待适配验收。' if kind=='blank' else '官网示例控件原件；含示例信息，不能当作空白模板或默认事实。'})
    sections={}
    for e in dom.xpath('//div[@data-lift-target]'):
        headings=e.xpath('./div/h2')
        if headings:sections[text(headings[0])]=text(e)
    for name in ['权利与义务','结果样本','常见问题','法律依据']:
        more=docs[name].xpath('//div[@data-lift-target="8"]')
        if len(more)!=1:raise ValueError('实际更多信息栏目缺失')
        sections[name]=text(more[0])
    after=captures['online'];target=urlsplit(after.get('url',''));query=parse_qs(target.query)
    if (target.scheme!='https' or target.hostname!='auth.zwfw.hunan.gov.cn' or target.path!='/oauth2/govLogin.html'
        or query.get('response_type')!=['gov'] or query.get('redirect_uri')!=['https://zwfw-new.hunan.gov.cn:443/oauth2-login?backUrl=https://zwfw-new.hunan.gov.cn/hnywtb/service/guide.html?id=aYcZ8ELbR56Me61a8eSG0A']
        or not all(s in after.get('text','') for s in ['个人登录','法人登录','手机号/身份证号码'])):raise ValueError('不是自身入口实际到达的公开认证边界')
    check={'official_link':True,'status':'auth_required','url':SOURCE,'verified_at':after['captured_at'],
        'post_login_submission_verified':False,'scope_notice':'在自身指南点击在线办理后到达个人/法人登录页；未登录，未核验登录后提交。'}
    return {'province':'hunan','province_name':'湖南省','city':'长沙市','district':'芙蓉区','region_code':'430102',
        'service_name':SERVICE,'service_code':'002014302002','official_approve_id':APPROVE,'authority':AUTHORITY,
        'source_url':SOURCE,'source_title':SERVICE,'source_type':'official_service_guide','verification_status':'conflict',
        'collected_at':own['collected_at'],'verified_at':max(p['captured_at'] for p in captures.values()),
        'fields':fields,'materials':materials,'templates':templates,'sections':sections,
        'channel':resolve_channel(raw,sections.get('流程说明',''),check),
        'online_evidence':{'source_url':SOURCE,'observed_auth_host':target.hostname,'authentication_completed':False,'submission_tested':False,
            'raw_method':raw.get('办理形式'),'scope_notice':check['scope_notice']},
        'warnings':['仅芙蓉区本事项；不代表长沙其他区县或湖南省全省，单位登记地和层级未选择，不按户籍自动判断管辖。',
            '官网抬头60工作日，正文45日及最多延长15日，环节表受理3工作日、办结41工作日；口径不一致，不能合并或保证结案日期。',
            '基本信息0次且无需到现场，常见问题却答需要现场办理；到场要求有冲突，应联系本区窗口确认。',
            '申请书和证据材料表内2份，填报说明按当事人数量+1，原模板另说明副本按被申请人数提交；保留各自原文，向窗口确认总份数。',
            '身份证、营业执照只在已有关联共享数据条件下可免提交，不是普遍免交；个性化要求仍待确认。',
            '官网两份空白DOC与两份示例分别保留；原空白表跨页留白，示例有非法日期，不复制示例事实，不宣称已完成填写适配。',
            '本指南未找到独立证据清单空白附件；结果样本为裁决等结果文书，不是申请模板，不借用其他地区文书。',
            '权利与义务栏目含通用行政表述，按官网原文留存，不将其直接作为仲裁救济程序承诺。']}
