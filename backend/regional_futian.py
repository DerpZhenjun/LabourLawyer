"""Futian-only supplementary sources; old FAQs and a failed auth hop are not a current guide."""
import re
from lxml import html
from regional_guides import digest,resolve_channel

SOURCES={
    'materials':('https://www.szft.gov.cn/msfw/jyefw/cjwt/content/post_3288213.html','申请劳动人事争议仲裁须提交什么材料？','福田区政府在线'),
    'jurisdiction':('https://www.szft.gov.cn/msfw/jyefw/ldzc/bszn/content/post_12840398.html','深圳市、区劳动人事仲裁委员会的管辖范围如何划分？','福田区人力资源局'),
    'query':('https://www.szft.gov.cn/msfw/jyefw/ldzc/bszn/content/post_12840380.html','劳动人事争议仲裁信息可以网上查询吗？','福田区人力资源局'),
    'channel':('https://hrss.sz.gov.cn/zmhd/cjwt/cjwt/ldgx/content/post_12717688.html','深圳市劳动争议调援裁诉一站式服务平台的查询登录渠道是？平台的具体作用是？深圳哪些区的劳动争议调解仲裁可以在平台上申请？','深圳市人力资源和社会保障局'),
}
ENTRY='https://hrsspub.sz.gov.cn/szldzc/login'

def _article(key,page):
    url,title,authority=SOURCES[key]
    if page.get('url')!=url:raise ValueError('不是福田自身已核实的补充来源')
    dom=html.fromstring(page['html'])
    if dom.xpath('//meta[@name="ArticleTitle"]/@content')!=[title] or dom.xpath('//meta[@name="ContentSource"]/@content')!=[authority]:
        raise ValueError('自身事项标题或发布机关变化')
    blocks=dom.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," news_cont_d_wrap ")]')
    dates=dom.xpath('//meta[@name="PubDate"]/@content')
    if len(blocks)!=1 or len(dates)!=1 or not re.fullmatch(r'\d{4}-\d\d-\d\d \d\d:\d\d',dates[0]):raise ValueError('正式文章或发布日期结构缺失')
    lines=[re.sub(r'\s+',' ',p.text_content()).strip() for p in blocks[0].xpath('.//p')]
    lines=[p for p in lines if p]
    if not lines:raise ValueError('正文为空，不取页脚或全站搜索内容')
    return {'lines':lines,'text':'\n'.join(lines),'publication_date':dates[0][:10],
        'source_url':url,'source_id':digest(url)[:24],'region_code':'440304',
        'collected_at':page['captured_at'],'verified_at':page['captured_at']}

def parse_futian_capture(pages):
    articles={key:_article(key,pages[key]) for key in SOURCES}
    materials=articles['materials'];lines=materials['lines']
    starts=[i for i,p in enumerate(lines) if '（一）申请人是劳动者的，请提交' in p]
    ends=[i for i,p in enumerate(lines) if '（二）申请人是用人单位的，请提交' in p]
    if len(starts)!=1 or len(ends)!=1 or starts[0]>=ends[0]:raise ValueError('劳动者与用人单位情形无法区分')
    worker=lines[starts[0]+1:ends[0]]
    rows=[re.fullmatch(r'([1-6])、(.+)',p) for p in worker if re.match(r'^\d+、',p)]
    if len(rows)!=6 or any(r is None for r in rows) or [int(r[1]) for r in rows]!=list(range(1,7)):
        raise ValueError('本区六项劳动者材料行缺失、重复或顺序变化')
    names=['仲裁登记表','劳动人事争议仲裁申请书','申请人身份证明复印件','授权委托书及代理人身份证明','被申请人注册信息资料复印件','劳动或人事关系证明材料复印件']
    checks=['仲裁登记表','劳动人事争议仲裁申请书','申请人身份证明复印件','需委托代理','被申请人注册信息资料复印件','存在劳动或人事关系的证明材料复印件']
    provenance={k:materials[k] for k in ['source_url','source_id','region_code','collected_at','verified_at','publication_date']}
    result=[]
    for i,row in enumerate(rows):
        raw=row[2]
        if checks[i] not in raw:raise ValueError('本区材料用途或申请情形变化，需重新核验')
        result.append({**provenance,'id':digest([materials['source_url'],'worker',i+1])[:20],'name':names[i],
            'required':'按情形提交' if i==3 else '必须（2018年原文，现行要求待确认）',
            'copies':'按被申请人人数提供副本' if i==1 else None,'raw_copies':raw,
            'original_copy':'复印件；原件供核对（见原文）' if i in {2,4,5} else None,
            'format':None,'purpose':None,'applicable_conditions':'需委托代理的' if i==3 else None,
            'verification_status':'partial','details':{'官方原文':raw,'现行性':'2018-02-08官方FAQ；不代表现行材料要求已核验'}})
    collective=[p for p in worker if p.startswith('集体争议除以上材料外')]
    if len(collective)!=1 or not all(t in collective[0] for t in ['3至5名','《员工推举代表书》','《申请人仲裁请求明细表》']):
        raise ValueError('集体争议材料情形变化')
    for name in ['员工推举代表书','申请人仲裁请求明细表']:
        result.append({**provenance,'id':digest([materials['source_url'],'collective',name])[:20],'name':name,
            'required':'按情形提交','copies':None,'raw_copies':collective[0],'original_copy':None,'format':None,'purpose':None,
            'applicable_conditions':'集体争议；原文推荐3至5名员工代表','verification_status':'partial',
            'details':{'官方原文':collective[0],'现行性':'2018-02-08官方FAQ；现行要求待机构确认'}})
    jurisdiction=articles['jurisdiction'];query=articles['query'];channel=articles['channel']
    if not all(t in jurisdiction['text'] for t in ['福田区、罗湖区、南山区、盐田区','认缴注册资本','1000万元','市仲裁委管辖范围以外']):
        raise ValueError('福田自身管辖说明不完整，不能按户籍或区名直接决定受理机构')
    if not all(t in query['text'] for t in ['我的案件','进行查询']):raise ValueError('本区案件查询说明变更')
    scoped=[p for p in channel['lines'] if '的劳动争议仲裁可以在平台上申请' in p]
    if len(scoped)!=1 or not re.search(r'(?:^|[。 ])福田区、罗湖区、',scoped[0]) or ENTRY not in channel['text']:
        raise ValueError('市级公告没有在申请能力的适用名单中明确列出福田，不得按全市默认继承')
    entry,attempt=pages['entry'],pages['apply']
    if entry.get('url')!=ENTRY or entry.get('title')!='深圳市劳动争议调援裁诉一站式服务平台' or not all(t in entry.get('text','') for t in ['我要仲裁','请使用个人登录方式']):
        raise ValueError('未核实公告所指公开入口或入口被其他网站替代')
    if attempt.get('url')!='chrome-error://chromewebdata/' or not all(t in attempt.get('text','') for t in ['tyrz.gd.gov.cn','ERR_EMPTY_RESPONSE']):
        raise ValueError('本次申请入口结果变化，需要重新核验，不沿用旧失败结论')
    fields={k:{**provenance,'raw_value':'','normalized_value':None,'verification_status':'missing'} for k in
        ['办理形式','办理地点','办理时间','咨询方式','服务对象','法定办结时限','承诺办结时限','是否收费','到办事现场次数','必须到现场原因']}
    source_evidence=[{k:a[k] for k in ['source_url','source_id','region_code','collected_at','verified_at','publication_date']} for a in articles.values()]
    return {'province':'guangdong','province_name':'广东省','city':'深圳市','district':'福田区','region_code':'440304',
        'service_name':'劳动人事争议仲裁申请','service_code':None,'authority':None,
        'source_url':materials['source_url'],'source_title':SOURCES['materials'][1],
        'source_type':'official_faq_supplementary_sources','verification_status':'partial',
        'collected_at':materials['collected_at'],'verified_at':max(a['verified_at'] for a in articles.values()),
        'source_evidence':source_evidence,'fields':fields,'materials':result,'templates':[],
        'channel':resolve_channel({},''),
        'online_evidence':{'official_claim_includes_futian':True,'claim_source_url':channel['source_url'],'claim_raw':scoped[0],
            'declared_entry':ENTRY,'public_entry_observation':{'url':ENTRY,'collected_at':entry['captured_at']},
            'actual_apply_result':'ERR_EMPTY_RESPONSE','apply_observation':{'collected_at':attempt['captured_at']},
            'authentication_completed':False,'submission_tested':False},
        'sections':{'官方材料原文（含单位申请情形）':materials['text'],
            '本区管辖原文（需结合单位情况确认）':jurisdiction['text'],
            '本区案件查询说明（不是申请功能证明）':query['text'],
            '网上办理来源与本次访问结果':channel['text']+'\n本次实际打开公开平台→我要仲裁→申请仲裁后，认证站tyrz.gd.gov.cn返回ERR_EMPTY_RESPONSE。未登录、未提交，网办实际可用状态待核实。',
            '来源与现行性':'材料FAQ2018-02-08；福田管辖FAQ2025-06-27；本区查询说明2026-04-20；明确列出福田的市级渠道说明2026-04-07。各自来源与捕获时钟见source_evidence。'},
        'warnings':['仅福田自己的补充资料候选，不是完整正式办事指南，不覆盖深圳其他区或全省。',
            '2018年材料FAQ的现行性待确认；未提供份数不自行填1份；用人单位申请情形仅保留原文，不混入劳动者材料。',
            '没有本区已核实的原文书附件；不借用广东省、广州或其他区模板生成。',
            '查询案件不等于可申请；市级公告明确列出福田可申请，但本次实际认证跳转返回空响应，网办保持待核实且不显示已验证申请入口。',
            '页脚福民路123号1409室是网站主办联系地址，不是已核实的仲裁窗口；不自动判断案件管辖。']}
