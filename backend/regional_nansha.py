"""Own Nansha material notice: pinned image transcription, no online inference."""
import hashlib
import copy
import re
from pathlib import Path
from lxml import html
from regional_guides import digest,resolve_channel
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://www.gzns.gov.cn/gzjg/gzsnsq/qzfgzbm/qrlzyhshbzj/ldrszyzc/content/post_5801798.html'
TITLE='【置顶】仲裁告知事项及申请材料下载'
IMAGE_SHA={'880829':'bbaf11d46ed7f45b42fa6960cefa434b051a07b81076bb53e0796b9dd21550c5',
           '98877':'3da2c60f3f8e8471f76b8d9a279ac1b1d1cce17023f7a81f258a18e97bf0d2d2'}
DOCUMENT_IDS='78883 78885 78886 7448532 7974339 78993 80422 7643694 6746747 8038769 8038770 78941 120820 120822 7977172 120825 120826 7976858 120828 120829 120830 7974340 78960'.split()
INSTRUCTIONS=set('78883 78885 78886 7448532 78993 80422 7643694 6746747 78941'.split())
# Classification is valid only for these individually reviewed original bytes.
CLASSIFIED_SHA={
    '78883':'1a2322876e6f4444769a886f8d9481bb39dc21e8a48f93fe3d60a358122bb5d9',
    '78885':'66d82094dc33f9af78b58ae9f4d4cf8a7c36ed4ca6a42b3819f861b74c488dc7',
    '78886':'4391ba81f9a8b299fe2495f9d67d8b71d61ba06528afa2436cac401a1bd3bb14',
    '7448532':'b7961468f046cefaea9df5e4c021398b2498cd6cb22de57b5c31927589961624',
    '7974339':'827ee76fb2ac943f6c411e01ee7b6b199cb3830234317e518e36b6166549796d',
    '78993':'3947d00bf306d623a1ea1284a97ca0f3a2a8ef2cb255e215e142ef3a6a8f50df',
    '80422':'cec407e2203fbc58c32f95305a63d360f103e2550df7329150800f429fa7e957',
    '7643694':'20afd8d88d24885387413b18b18181dc638ba37bb29295d5da39377a2cf5e7c8',
    '6746747':'440300c00c1f77dc41dc96ee0f9658dfc047717e8e157be39ffdf909a1ac2752',
    '8038769':'b3e474c82349993f1c105b692a11e0c99db7109ba4718ec80f59641119fca430',
    '8038770':'c8dca0defb5245f8814b40bce67ebf15279073006f591481630cd8793ca1bd35',
    '78941':'78b6f3d3e386bf84e10671f7293725730ffc770d868f22dcf338e06e09283907',
    '120820':'cb861ae97c5aaaf141db6e2b9584e7e1592eab100ebd8a59a77bef176fad6df1',
    '120822':'5672d4a80723be81b33db5cd5d060d07f2bd8a900be97ff93d9c66838a6d1441',
    '7977172':'d7e213f1f272dd9a3d5dbb974095c579d0395e419b3f6bbe3ca10d117e6fe5b9',
    '120825':'6af2e5a0e1459fbddb1a4ac2f38a3f939188905c549a5d47320465460debab11',
    '120826':'f6e766270f55daa8283561e38ea57111d9a088f733c8e7e28a925c550a2cc0bf',
    '7976858':'17cb06f956c606e1e7a0677816c9dd7b253bac79088b1a9b3621f694d2edc10d',
    '120828':'6d7686f05317235f453b4d42de000bcfd703b97f5cd92981690fc37b365d0d07',
    '120829':'ac29d68b3853719383ed31366541e4c533b98bb6a1c47e1551e9c3b6637490fd',
    '120830':'52d0c99fba6dc078d742a05c976c4bd1a96e34bd99a5c768a8e143e2a152a3d9',
    '7974340':'0c63b09cfc670912dbedfa20aa2c99e0f8ed6d5ec986a57e73748f89c8ed410d',
    '78960':'f764424866831171eddf16925e661eecff141afed4a237f67bda68b51b349ffe',
}
COPIES='正本1份，根据被申请人（及第三人）数量提交相应数量的副本（按对方当事人数量增加）'
# These nine row groups were read from the exact pinned image, not another district.
ROWS=[
 ('申请人身份证复印件','必须','1份','原件1份核对后退回，复印件1份',None),
 ('被申请人工商信息材料','必须','1份','被申请人最新（1个月内）工商信息材料（复印件1份；国家企业信用信息网查询：http://www.gsxt.gov.cn/）',None),
 ('证据材料','必须',COPIES,'证据材料：按以下顺序排列提交（若有）。1.证明劳动关系证据，如劳动合同、社保缴费明细、工牌等材料；2.入职方面的证据，如入职登记表、聘用书等；3.工作内容方面的证据，如岗位调整通知、任命通知、借调函、岗位说明书、员工绩效考核表等；4.关于约定工资、工时证据，如劳动合同、员工手册等规章制度；5.工资发放的证据，如工资条、银行转账流水等；6.具体工作时间的证据，如考勤表、考勤记录等；7.离职方面的证据，如离职交接表、辞退书、辞职申请等；8.其他证据，如微信、QQ聊天记录、录音、录像证据等。注：证据材料只收复印件，所有的书面证据都需要编排页码；视频、录音等电子证据要用光盘提交并提供对应的文字版；工伤案件要提供工伤认定决定书，若有劳动能力鉴定书、伤残等级认定书等证明一并提供；单位诉个人必须提交证明劳动关系证据。',None),
 ('劳动争议仲裁申请书、证据清单','必须',COPIES,'劳动争议仲裁申请书、证据清单（不按模板填写需提交送达地址确认书；即未按照本区提供模板填写时另附确认书）',None),
 ('授权委托材料','按情形提交','1份','授权委托材料：律师代理的提交律师公函、授权委托书、律师证复印件（需核对原件）；法定代理的需提交授权委托书、代理人身份证复印件，相关的户籍证明核对原件并提供复印件；基层法律服务工作者代理的，当事人户籍地需位于基层法律服务工作者执业辖区内；单位员工代理的需提供授权委托书及劳动关系证明材料，如劳动合同、工牌等。注：授权权限需要明确是一般授权还是特别授权。','有授权委托的'),
 ('加班工资明细表','按情形提交','1份','加班工资明细表','请求涉及加班费的'),
 ('员工推举代表书','按情形提交','1份（图片原文；附表另写两份，须确认）','员工推举代表书（推举3个或5个员工代表，所有员工签名按手印）','集体劳动争议的（十人或以上，且有共同被申请人、共同请求）'),
 ('法定代表人身份证明书及单位主体材料','按情形提交','1份','法定代表人身份证明书1份，单位提供营业执照核对原件并提交1份副本及被申请人居民身份证复印件1份','用人单位诉劳动者'),
 ('医疗费审核清单及材料','按情形提交','1份','医疗费审核清单1份，提供医疗费材料：病历资料、费用明细清单、医疗票据三项复印件','涉及医疗费（工伤或患病）的'),
]

def parse_nansha_capture(page,files):
    if page.get('url')!=SOURCE:raise ValueError('不是南沙区自身来源')
    dom=html.fromstring(page['html']);titles=dom.xpath('//meta[@name="ArticleTitle"]/@content');blocks=dom.xpath('//div[@id="zoomcon"]')
    if titles!=[TITLE] or len(blocks)!=1 or '广州市南沙区劳动人事争议仲裁院' not in dom.text_content():
        raise ValueError('自身材料事项或实施机关结构变化')
    block=blocks[0];links=block.xpath('.//a[contains(concat(" ",normalize-space(@class)," ")," nfw-cms-attachment ")]')
    images=block.xpath('.//img[contains(concat(" ",normalize-space(@class)," ")," nfw-cms-img ")]')
    observed={a.get('attachment-id'):(a.get('href'),a.text_content().strip()) for a in links}
    image_urls={a.get('img-id'):a.get('src') for a in images}
    if len(links)!=23 or set(observed)!=set(DOCUMENT_IDS) or set(image_urls)!=set(IMAGE_SHA):
        raise ValueError('自身附件或材料图片变化，不能套用旧转录')
    if len(files)!=25 or {f.get('id') for f in files}!=set(DOCUMENT_IDS)|set(IMAGE_SHA):
        raise ValueError('自身25原始文件缺失、重复或被其他区替代')
    checked={}
    for f in files:
        identity=f['id'];image=identity in IMAGE_SHA;ext='png' if image else 'docx' if identity=='7974339' else 'doc'
        expected=f'templates/_docx/_regional/440115/{identity}.{ext}';path=ROOT/expected
        url=image_urls[identity] if image else observed[identity][0]
        if (f.get('source_url')!=SOURCE or f.get('download_url')!=url or f.get('final_download_url')!=url
            or f.get('file')!=expected or f.get('file_type')!=ext or f.get('download_status')!='downloaded'
            or f.get('http_status')!=200 or not path.is_file()):raise ValueError('南沙自身原件来源、路径或下载身份不匹配')
        data=path.read_bytes();checksum=hashlib.sha256(data).hexdigest()
        signature=b'\x89PNG\r\n\x1a\n' if image else b'PK' if ext=='docx' else bytes.fromhex('D0CF11E0A1B11AE1')
        if checksum!=f.get('sha256') or not data.startswith(signature):raise ValueError('自身原始文件SHA或格式不匹配')
        if image and checksum!=IMAGE_SHA[identity]:raise ValueError('官方材料图片已变化，人工转录失效')
        if not image and checksum!=CLASSIFIED_SHA[identity]:raise ValueError('官方原件字节已改变，必须重新核验空白、样例和说明分类')
        checked[identity]=f
    provenance={'source_url':SOURCE,'region_code':'440115','collected_at':page['captured_at'],'verified_at':page['captured_at']}
    materials=[]
    for i,(name,required,copies,raw,condition) in enumerate(ROWS,1):
        materials.append({**provenance,'id':digest([SOURCE,'image-row',i])[:20],'name':name,'required':required,'copies':copies,
            'raw_copies':raw,'original_copy':'复印件（查验原件见原文）' if i in {1,2,3} else None,
            'format':None,'purpose':None,'applicable_conditions':condition,'verification_status':'verified',
            'details':{'图片原文':raw,'source_image_url':image_urls['880829'],'source_image_sha256':IMAGE_SHA['880829'],
                       'extraction_method':'人工对照本区官方图片转录；不是HTML正文，也不代表现行性已全部核验'}})
    templates=[]
    for identity in DOCUMENT_IDS:
        f=checked[identity];kind='instruction' if identity in INSTRUCTIONS else 'blank'
        templates.append({**provenance,**{k:f[k] for k in ['download_url','final_download_url','file','sha256','file_type','download_status']},
            'id':'nansha-5801798-'+identity,'official_annex_id':identity,'original_name':observed[identity][1],
            'official_download_name':f.get('official_download_name'),'downloaded_at':f['collected_at'],
            'official_kind':kind,'classification_note':'本区原告知或说明文件' if kind=='instruction' else '本区未填写表格；未适配生成，原件及生成版式尚有独立门禁',
            'can_generate':False,'document_types':[]})
    fields={k:{**provenance,'raw_value':'','normalized_value':None,'verification_status':'missing'} for k in
            ['办理形式','办理地点','办理时间','咨询方式','服务对象','法定办结时限','承诺办结时限','是否收费','到办事现场次数','必须到现场原因']}
    return {'province':'guangdong','province_name':'广东省','city':'广州市','district':'南沙区','region_code':'440115',
        'service_name':'劳动人事争议仲裁申请','service_code':None,'authority':'广州市南沙区劳动人事争议仲裁院',
        'source_url':SOURCE,'source_title':page['title'],'source_type':'official_material_notice','verification_status':'partial',
        'collected_at':page['captured_at'],'verified_at':page['captured_at'],'fields':fields,'materials':materials,'templates':templates,
        'channel':resolve_channel({},''),'sections':{'申请材料':'\n'.join(m['name']+'：'+m['details']['图片原文'] for m in materials),
            '官方正文及附件索引':block.text_content().strip(),'来源与现行性':'官网发布日期2020-04-23；附件仍可公开下载；含2017/2018管辖通知，现行有效性未全部核验，不自动判断管辖。',
            '材料清单与流程图':'官方图片URL及SHA见材料details和证据manifest；不以纸质表或流程图推断网办能力。'},
        'warnings':['仅适用南沙自己的材料公告，不覆盖广州其他区或整个自贸区。',
            '南沙e受达是文书送达选项，不是已核验的网上立案入口；办理形式、网办、时限、收费和现场次数待核实。',
            '个案申请书原件本机只读渲染第一页注意事项与公司信息重叠；原因未明，不能批准生成或声称原政府文件错误。',
            '材料图片推举书写1份，附表备注写一式两份；原文均保留，请向机构确认，不静默选择。',
            '附录地址、2017/2018管辖条款和2020版本现行性待机构核实，不把旧资料自动作为现行受理判断。',
            '原申请书DOC/四列证据清单独立文件，尚未适配，不借用白云四列或江苏六列表。']}

WINDOW_SOURCE='https://www.gzns.gov.cn/gzjg/gzsnsq/qzfgzbm/qrlzyhshbzj/ldrszyzc/content/post_3868389.html'
WINDOW_TITLE='广州市南沙区劳动人事争议仲裁机构设置和收件窗口'

def parse_nansha_windows(page):
    """Separate the page's receiving windows from office and dispatched courts."""
    if page.get('url')!=WINDOW_SOURCE:raise ValueError('不是南沙自身窗口来源')
    dom=html.fromstring(page['html']);blocks=dom.xpath('//div[@id="zoomcon"]')
    if dom.xpath('//meta[@name="ArticleTitle"]/@content')!=[WINDOW_TITLE] or len(blocks)!=1:
        raise ValueError('自身窗口标题或正文结构改变')
    block=blocks[0]
    if '广州市南沙区劳动人事争议仲裁院' not in block.text_content():raise ValueError('自身窗口机关未核实')
    lines={};active=None
    for node in block:
        if not isinstance(node.tag,str):continue
        value=re.sub(r'\s+',' ',node.text_content()).strip()
        if node.tag=='h3':
            active=value;lines[active]=[]
        elif active and value:lines[active].append(value)
    expected=['一、机构简介','二、办公地址及联系电话','三、劳动争议收件窗口','四、人事争议收件窗口','五、劳动人事争议仲裁派出庭','六、涉港澳涉外收件窗口及派出庭']
    if list(lines)!=expected:raise ValueError('自身窗口栏目结构改变，不能混用窗口类型')
    tables=block.xpath('.//table')
    if len(tables)!=1:raise ValueError('自己的收件窗口表缺失或出现歧义')
    rows=[[re.sub(r'\s+','',c.text_content()) for c in row.xpath('./td|./th')] for row in tables[0].xpath('.//tr')]
    if (len(rows)!=11 or rows[0]!=['序号','所属镇街','经办机构','收件窗口地址','联系电话']
        or any(len(r)!=5 for r in rows) or [r[0] for r in rows[1:]]!=[str(i) for i in range(1,11)]):
        raise ValueError('自己的十个收件窗口或字段改变，需要重新核验')
    if len({r[1] for r in rows[1:]})!=10:raise ValueError('收件镇街重复，不能静默合并')
    date_text=' '.join(dom.xpath('//p[contains(concat(" ",normalize-space(@class)," ")," ly ")]//text()'))
    published=re.search(r'发布日期[：:]\s*(\d{4}-\d{2}-\d{2})',date_text)
    if not published:raise ValueError('自身窗口发布日期缺失')
    provenance={'source_url':WINDOW_SOURCE,'source_id':digest(WINDOW_SOURCE)[:24],'region_code':'440115',
                'collected_at':page['captured_at'],'verified_at':page['captured_at'],'verification_status':'verified'}
    windows=[]
    for number,town,agency,address,phone in rows[1:]:
        if not town or not agency or '南沙区' not in address or not re.fullmatch(r'\d{8}',phone):
            raise ValueError('自身窗口地点或联系电话缺失，不能用页脚值补齐')
        windows.append({**provenance,'id':digest([WINDOW_SOURCE,town])[:20],'window_type':'labour_receiving',
                        'number':number,'town':town,'agency_raw':agency,'address_raw':address,'phone_raw':phone})
    office=next((p for p in lines[expected[1]] if p.startswith('南沙区') and '号' in p),None)
    contacts=next((p for p in lines[expected[1]] if p.startswith('联系电话：')),None)
    if not office or not contacts or not re.search(r'020-\d{8}',contacts):raise ValueError('区院办公或联系电话缺失，不从其他区补齐')
    hours=next((p.removeprefix('工作时间：').strip() for p in lines[expected[2]] if p.startswith('工作时间：')),None)
    special_receiving=next((p for p in lines[expected[5]] if '收件窗口' in p),None)
    special_court=next((p for p in lines[expected[5]] if '仲裁庭' in p),None)
    if not special_receiving or not special_court:raise ValueError('特殊收件窗口与仲裁庭未分别核验')
    return {**provenance,'source_title':page['title'],'publication_date':published[1],
            'labour_receiving_windows':windows,'agency_office_raw':office,'agency_contact_raw':contacts,
            'working_hours_raw':hours,'working_hours_scope':'labour_receiving_windows',
            'personnel_receiving_raw':'\n'.join(lines[expected[3]]),'dispatch_courts_raw':'\n'.join(lines[expected[4]]),
            'special_receiving_raw':special_receiving,'special_court_raw':special_court,
            'sections':{k:'\n'.join(v) for k,v in lines.items()}}

def apply_nansha_windows(guide,page):
    if tuple(guide.get(k) for k in ['province','city','district','region_code','source_url'])!=('guangdong','广州市','南沙区','440115',SOURCE):
        raise ValueError('自身南沙窗口资料不能接到其他地区或来源')
    parsed=parse_nansha_windows(page);result=copy.deepcopy(guide)
    provenance={k:parsed[k] for k in ['source_url','source_id','region_code','collected_at','verified_at']}
    def field(raw,scope):return {**provenance,'raw_value':raw or '', 'normalized_value':raw,
                                'scope':scope,'verification_status':'verified' if raw else 'missing'}
    locations='劳动争议收件窗口（请按所属镇街核对）：\n'+'\n'.join(w['town']+'：'+w['address_raw']+'；电话'+w['phone_raw'] for w in parsed['labour_receiving_windows'])
    result['fields']['办理地点']=field(locations,'labour_receiving_windows_not_agency_office_or_court')
    result['fields']['办理时间']=field('劳动争议收件窗口：'+parsed['working_hours_raw'] if parsed['working_hours_raw'] else None,'labour_receiving_windows')
    result['fields']['咨询方式']=field(parsed['agency_contact_raw']+'；各镇街收件电话见窗口清单。','agency_contacts_and_named_receiving_windows')
    result['office_information']=parsed
    result['sections']['本区窗口来源与范围']='来源：'+WINDOW_SOURCE+'\n官网发布日期：'+parsed['publication_date']+'\n核验：'+parsed['verified_at']+'\n收件窗口、办公地点、派出庭是不同场所，不按户籍推定管辖。'
    result['sections']['劳动争议收件窗口']=locations
    result['sections']['区院办公地点（非全部劳动争议收件窗口）']=parsed['agency_office_raw']+'\n'+parsed['agency_contact_raw']
    result['sections']['人事争议收件窗口']=parsed['personnel_receiving_raw']
    result['sections']['劳动人事争议仲裁派出庭（非收件窗口表）']=parsed['dispatch_courts_raw']
    result['sections']['涉港澳涉外收件窗口与仲裁庭']=parsed['special_receiving_raw']+'\n'+parsed['special_court_raw']
    result['verified_at']=max(result['verified_at'],parsed['verified_at'])
    result['warnings'].append('另已核对本区2026年6月2日公布的十个劳动争议收件窗口及该栏工作时间；人事争议、涉港澳涉外收件与派出庭分别见完整原文。存在窗口不等于只支持线下，网上办理仍待核实。')
    return result
