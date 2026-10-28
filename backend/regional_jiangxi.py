"""Rongjiang's own public notice and blank DOC; no province or county fallback."""
import hashlib,re
from pathlib import Path
from urllib.parse import urljoin
from lxml import html
from regional_guides import digest,resolve_channel
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://rjxq.ganzhou.gov.cn/rjxq/tzgg/202606/f931ffb78c85406cbf9636a3489296b5.shtml'
TITLE='赣州蓉江新区劳动人事争议仲裁申请书、证据目录及模板'
PROFILE='https://rjxq.ganzhou.gov.cn/rjxq/zjyd/zjyd.shtml'
ANNEX='853097ba8d9f4036b61e806e44314c21'
DOWNLOAD=SOURCE.removesuffix('.shtml')+'/files/'+ANNEX+'.doc'
FILE='templates/_docx/_regional/function-jiangxi-ganzhou-rongjiang/'+ANNEX+'.doc'
SHA='3729dc3af6b0289db06a29ee3628f6f1bd7bdb3cdab6813103310d48511260c4'
HEADERS=['序号','证据名称','证据来源','证明目的','页数']


def compact(value):return re.sub(r'\s+','',value)


def parse_rongjiang_capture(page,original,identity,slots):
    if page['url']!=SOURCE:raise ValueError('不是蓉江新区自己的文书公告')
    dom=html.fromstring(page['html']);titles=dom.xpath('//div[@class="contit"]');blocks=dom.xpath('//div[@id="zoom"]')
    if len(titles)!=1 or titles[0].text_content().strip()!=TITLE or len(blocks)!=1:raise ValueError('自身公告标题或正文已改变')
    r=identity.get('directory_record',{})
    if (r.get('provider'),r.get('province'),r.get('city'),r.get('district'),r.get('code'),r.get('parent_code'))!=('national','jiangxi','赣州市','蓉江新区','360798','360700'):
        raise ValueError('服务目录身份不是蓉江新区，不可映射邻区或全市')
    if r.get('raw_record',{}).get('regionName')!='蓉江新区' or identity.get('own_profile_url')!=PROFILE:
        raise ValueError('自身功能区身份未核验')
    block=blocks[0];links={urljoin(SOURCE,a.get('href')) for a in block.xpath('.//a[@href]')}
    if (original.get('source_url')!=SOURCE or original.get('download_url')!=DOWNLOAD or DOWNLOAD not in links
        or original.get('file')!=FILE or original.get('sha256')!=SHA or original.get('http_status')!=200
        or original.get('download_status')!='downloaded' or not (ROOT/FILE).is_file()
        or hashlib.sha256((ROOT/FILE).read_bytes()).hexdigest()!=SHA):raise ValueError('自身原件来源或字节校验失败')
    if (slots.get('source')!=FILE or slots.get('sha256')!=SHA or slots.get('pages')!=2
        or len(slots.get('tables',[]))!=1 or slots['tables'][0].get('columns')!=5 or slots['tables'][0].get('rows')!=11
        or '示例' in slots.get('text','') or '赣州蓉江新区劳动人事争议仲裁委员会' not in slots.get('text','')):
        raise ValueError('原件类型和版式未经独立只读核验')
    if [c['text'] for c in slots['tables'][0]['cells'][:5]]!=HEADERS:raise ValueError('原件证据表列已改变')
    tables=[]
    for table in block.xpath('.//table'):
        tables.append([[re.sub(r'\s+',' ',cell.text_content()).strip() for cell in row.xpath('./td|./th')] for row in table.xpath('.//tr')])
    if len(tables)!=2 or any(len(t)!=11 or t[0]!=HEADERS or any(len(row)!=5 for row in t) for t in tables):raise ValueError('网页空白表/样例表结构改变')
    if any(any(row[1:]) for row in tables[0][1:]):raise ValueError('网页第一张表已不是空白表')
    text=block.text_content();clean=compact(text)
    copies='被申请人（第三人）人数+1份'
    if '注：1-2项为必须提供的证据材料，3-10项证据材料根据实际情况提供。' not in clean or copies not in clean:
        raise ValueError('自身证据适用条件或份数原文未识别')
    address=re.search(r'2\.办公地址：([^。]+)',clean)
    phone=re.search(r'3\.咨询电话：(0797-\d{7})',clean)
    if not address or not phone:raise ValueError('自身办公地点或咨询电话未识别，不能借用网站页脚电话')
    provenance={'source_url':SOURCE,'region_code':'360798','collected_at':page['captured_at'],'verified_at':page['captured_at']}
    fields={k:{**provenance,'raw_value':'','normalized_value':None,'verification_status':'missing'} for k in
        ['办理形式','办理时间','服务对象','法定办结时限','承诺办结时限','是否收费','到办事现场次数','必须到现场原因']}
    for key,value,label in [('办理地点',address[1],'办公地址'),('咨询方式',phone[1],'咨询电话')]:
        fields[key]={**provenance,'raw_value':value,'normalized_value':value,'original_label':label,'verification_status':'verified',
            'scope_note':'来自本区文书公告，不据此推断仅限窗口或仲裁管辖'}
    materials=[{**provenance,'id':digest([SOURCE,'application'])[:20],'name':'劳动人事争议仲裁申请书',
        'required':'需要提交','copies':copies,'raw_copies':'仲裁申请书一式两份，按照'+copies+'提交，用A4纸打印。',
        'format':'A4纸打印','original_copy':None,'purpose':None,'applicable_conditions':'按被申请人（第三人）人数准备',
        'details':{'官方材料原文':'仲裁申请书一式两份，按照'+copies+'提交，用A4纸打印。'},'verification_status':'verified'}]
    for n,row in enumerate(tables[1][1:],1):
        if row[0]!=str(n):raise ValueError('证据样例顺序变化')
        _,name,source,purpose,pages=row
        materials.append({**provenance,'id':digest([SOURCE,'evidence',n])[:20],'name':name,
            'required':'必须提供' if n<=2 else '根据实际情况提供','copies':copies,'raw_copies':'证据目录和证据材料，按照'+copies+'提交。',
            'format':None,'original_copy':'复印件' if '复印件' in name else None,'purpose':purpose,
            'applicable_conditions':'工伤案件，根据实际情况提供' if name.startswith('（工伤案件）') else '根据实际情况提供' if n>2 else None,
            'details':{'官方证据目录示例行':' | '.join(row),'官方份数原文':'证据目录和证据材料，按照'+copies+'提交。',
                '示例页码（不是要求）':pages,'证据来源示例':source,'范围说明':'证据名称和页码来自本区示例，按真实材料替换；未将十行全部设为必需'},'verification_status':'verified'})
    template={**provenance,'id':ANNEX,'annex_id':ANNEX,'original_name':'劳动仲裁申请书及证据目录.doc',
        'original_server_filename':ANNEX+'.doc','official_kind':'blank','file':FILE,'sha256':SHA,
        'download_url':DOWNLOAD,'download_status':'downloaded','downloaded_at':original['downloaded_at'],
        'file_type':'doc','original_pages':2,'evidence_columns':HEADERS,'contained_document_types':['application','evidence'],
        'can_generate':False,'document_types':[],'classification_note':'下载原件两页均为空白；网页另含填写示例，二者已独立核对。原DOC尚未完成填写适配。'}
    return {'province':'jiangxi','province_name':'江西省','city':'赣州市','district':'蓉江新区','region_code':'360798',
        'official_region_code':None,'official_service_region_code':'360798',
        'region_code_kind':'official_service_directory_code_not_administrative_division',
        'service_name':'劳动人事争议仲裁申请','service_code':None,'source_type':'official_document_notice',
        'source_url':SOURCE,'source_title':page['title'],'authority':'赣州蓉江新区劳动人事争议仲裁委员会',
        'verification_status':'partial','collected_at':page['captured_at'],'verified_at':page['captured_at'],
        'fields':fields,'materials':materials,'templates':[template],'channel':resolve_channel({},''),
        'sections':{'申请材料':'\n'.join(m['name']+'：'+m['required']+'；'+m['copies'] for m in materials),
                    '官方文书正文及填写示例':text.strip()},
        'warnings':['仅适用赣州蓉江新区自身公告，不代表赣州市或南康区；服务目录编码不直接证明行政区划或仲裁管辖。',
            '本来源是官方文书和材料示例公告，不是完整办事指南；网上办理、办理时间、收费及到场次数尚待核验。',
            '网页填写示例与下载空白原件已区分；十种证据不是全部必需，示例页码不是规定页数。',
            '尚未完成原DOC本地填写适配，目前只保留自己的官方原件，不用其他区县模板代替。']}
