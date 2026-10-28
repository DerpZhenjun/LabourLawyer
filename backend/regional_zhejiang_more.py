"""Independent next Zhejiang captures; no inherited Yuhang/Xihu jurisdiction rules.

parse_binjiang_capture/parse_shangcheng_capture take the next Zhejiang capture
directory and its SOURCE-MANIFEST.json path or decoded mapping. The actual raw
inventory is pinned; new caller checksums cannot authorize replacement evidence.
No database, network, generation, publication or layout-render operations occur.
"""
from datetime import datetime
import hashlib,json,re,io,zipfile
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from lxml import html,etree
from regional_guides import digest

ROOT=Path(__file__).resolve().parents[1]
REPORT='reports/nationwide-localization-20261028-next/zhejiang'
MANIFEST_DIGEST='c553d5ba00dd3abb5ce3a841739ba8e42499051f39f040cc1bae00e5ecaa5558'
SERVICE='劳动人事争议仲裁申请'
STANDARD='fc266994-f669-4861-acdc-799f3ea2decc'
CATEGORY='8d0494f2-74c9-11e9-b64f-6c92bf669f92'
SPECS={
    'binjiang':{'district':'滨江区','code':'330108','local':'a3163f38-bd62-4d18-8374-a79177c440fb',
        'agency_raw':'区人力社保局（区党委编办）','phone':'0571-89520795',
        'window':'杭州市滨江区住房和城市建设局（杭州市滨江区西兴街道江南大道87号）杭州市滨江区江南大道87号国土大楼1楼社会治理中心14号窗口','materials':[]},
    'shangcheng':{'district':'上城区','code':'330102','local':'01a9e0fa-ab7e-4232-99e1-014d3ad99b45',
        'agency_raw':'区人力社保局','phone':'0571-87818803',
        'window':'上城区社会矛盾纠纷调处化解中心（杭州市上城区望江街道望江东路6-1号一楼综合窗口）25号窗口',
        'materials':['用人单位登记注册材料','《劳动人事争议仲裁申请书》','《证据清单》','存在劳动关系的证据和可证实申请人主张的证据']}}
BLANKS={
    '21B24C52D2AC3EB007AA7F55CE0AAD79':('application.docx','劳动人事争议仲裁申请书','0eab0f0a2ee98e8ca1e4d2fa5469fcb5738d0c0f24671345bebc8394099ae41f',1),
    '872DFF90A8578907CB947197A784AA48':('evidence-list.docx','证据清单','4965bf3d2bf76404ab190d1e47d2fa250c8cb8bd93762949df94be38b2d4ca8c',2)}

def parse_binjiang_capture(capture_root,manifest):return _parse(capture_root,manifest,'binjiang')
def parse_shangcheng_capture(capture_root,manifest):return _parse(capture_root,manifest,'shangcheng')
def _text(node):return re.sub(r'\s+',' ',node.text_content()).strip()
def _class(node,name):return node.xpath('.//*[contains(concat(" ",normalize-space(@class)," "),$class)]',**{'class':' '+name+' '})

class _Evidence:
    def __init__(self,root,manifest):
        self.root=Path(root).resolve();self.used={}
        try:
            m=json.loads(Path(manifest).read_text(encoding='utf8')) if isinstance(manifest,(str,Path)) else manifest
            if digest(m)!=MANIFEST_DIGEST:raise ValueError('不是本轮独立采集的固定来源清单')
            self.files=m['files']
        except (TypeError,KeyError,OSError,json.JSONDecodeError) as exc:raise ValueError('缺少本轮固定来源清单') from exc
    def read(self,relative):
        path=(self.root/relative).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():raise ValueError('原始证据缺失或越界')
        body=path.read_bytes();entry=self.files.get(relative)
        checksum=hashlib.sha256(body).hexdigest()
        if not entry or entry!={'sha256':checksum,'bytes':len(body)}:raise ValueError('原始证据SHA或长度改变：'+relative)
        self.used[relative]={'sha256':checksum,'bytes':len(body)}
        return body
    def load(self,relative):return json.loads(self.read(relative).decode('utf8'))

def _parse(root,manifest,name):
    e=_Evidence(root,manifest);spec=SPECS[name]
    source='https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode='+spec['local']
    authority='杭州市'+spec['district']+'人力资源和社会保障局'
    pages={};doms={}
    for section in ['conditions','materials','flow','window','faq','basic','law']:
        folder=name+'-'+section;page=e.load(folder+'/dom.json')
        if page['url']!=source or SERVICE not in page['title'] or SERVICE not in page['text']:
            raise ValueError('不是本区自身实际指南来源或栏目')
        datetime.fromisoformat(page['captured_at'].replace('Z','+00:00'))
        pages[section]=page;doms[section]=html.fromstring(page['html']);e.read(folder+'/page.png')
    basic=pages['basic'];dom=doms['basic']
    search=e.load(name+'-search/dom.json');u=urlsplit(search['url'])
    if (u.scheme!='https' or u.hostname!='search.zj.gov.cn'
        or parse_qs(u.query).get('websiteid')!=[spec['code']+'000000']
        or ('当前搜索范围为： '+spec['district']) not in search['text']):raise ValueError('目录地区、城市或来源不匹配')
    directory=html.fromstring(search['html']).xpath('//a[@title=$title and @data-local-inner-code]',title=SERVICE)
    if len(directory)!=1 or directory[0].get('data-stdcateguid')!=STANDARD or directory[0].get('categorysourcereferno')!=CATEGORY:
        raise ValueError('目录真实事项标识不匹配')
    if spec['window'] not in pages['window']['text'] or spec['phone'] not in basic['text']:
        raise ValueError('实际窗口的完整市区或本区咨询电话不匹配')
    if name=='binjiang':
        identity=e.load('binjiang-agency/dom.json');iu=urlsplit(identity['url'])
        if iu.scheme!='https' or iu.hostname!='www.hhtz.gov.cn' or authority not in identity['text']:
            raise ValueError('滨江本区实施主体全称旁证缺失')
        identity_source=identity['url'];identity_file='binjiang-agency/dom.json'
    else:
        provenance=e.load('shangcheng/agency-provenance.json')
        identity_source=provenance['source_url'];identity_file='shangcheng/agency-identity.pdf'
        pdf=e.read(identity_file)
        txt=e.read('shangcheng/agency-identity.txt').decode('utf8')
        if not pdf.startswith(b'%PDF') or authority not in re.sub(r'\s+','',txt):raise ValueError('上城完整机关身份旁证缺失')
    raw={}
    for row in _class(dom,'subtit'):
        cells=row.xpath('./span')
        if len(cells)==2:raw[_text(cells[0]).rstrip('：:')]=_text(cells[1])
    if raw.get('实施主体')!=spec['agency_raw'] or raw.get('法定办结时限')!='60天':raise ValueError('本区实施机关或法定时限改变')
    header={}
    for row in _class(dom,'summary-item'):
        val=_text(row)
        for label in ['到现场次数','承诺办结时限']:
            if val.startswith(label):header[label]=val.removeprefix(label).replace(' ','')
    if header!={'到现场次数':'0次','承诺办结时限':'44工作日'}:raise ValueError('已观察的原始时限或跑动次数改变')
    own={'source_url':source,'region_code':spec['code'],'collected_at':basic['captured_at'],'verified_at':basic['captured_at']}
    def field(value,normalized=None,**extra):return {**own,'raw_value':value,'normalized_value':normalized if normalized is not None else value,'verification_status':'verified' if value else 'missing',**extra}
    fields={k:field(v) for k,v in {**raw,**header}.items() if k!='设定依据'}
    fields['实施主体']=field(spec['agency_raw'],authority,normalization_note='完整市区和机构名称由自身窗口/目录及单独机构旁证核验；原括注仍保留')
    flow_nodes=_class(doms['flow'],'flow-rich-text-body');conditions=_class(doms['conditions'],'condition')
    if len(flow_nodes)!=1 or len(conditions)!=1 or '管辖范围' not in _text(conditions[0]):raise ValueError('真实展开条件或流程不完整')
    flow=flow_nodes[0].text_content().strip()
    if '在5个工作日内作出是否受理的决定' not in flow or '现场或邮寄提交申请材料' not in flow:raise ValueError('实际申请/受理阶段改变')
    fields['受理决定时限']=field('5个工作日',scope='acceptance_decision_only',official_context=flow)
    window=pages['window']['text'].split('基本信息\n')[-1].split('好差评\n')[0].strip()
    hours=window.split('工作时间\n')[1].split('联系电话\n')[0].strip()
    fields['办理地点']=field(spec['window']);fields['办理时间']=field(hours);fields['咨询电话']=field(spec['phone'])
    material_dom=doms['materials'];nodes=_class(material_dom,'material-name-row')
    if [_text(n) for n in nodes]!=spec['materials']:raise ValueError('自身实际材料行改变')
    materials=[]
    for i,node in enumerate(nodes):
        item=node.getparent().getparent();modules=[_text(x) for x in _class(item,'small-module')]
        if modules!=['纸质材料 2份，A4','原件']:raise ValueError('本区材料份数/规格/原件要求改变')
        labels=[_text(x) for x in _class(item,'download')+_class(item,'exampleOne')]
        if labels!=(['下载'] if i in {1,2} else []):raise ValueError('本区空白/示例控件身份改变')
        materials.append({**own,'id':digest([source,spec['materials'][i]])[:20],'name':spec['materials'][i],
            'required':None,'copies':'2','raw_copies':modules[0],'format':'纸质材料，A4','original_copy':modules[1],
            'applicable_conditions':None,'purpose':None,'details':{'原始材料行':_text(item),'必要性':'当前界面未分别标注必要/可选'},'verification_status':'verified'})
    if name=='binjiang':
        if '当前情形下，无需递交材料' not in pages['materials']['text'] or _class(material_dom,'download'):
            raise ValueError('滨江观察到的材料缺口状态改变，需重新核验')
        fields['材料栏原文']=field('当前情形下，无需递交材料',scope='portal_display_only_not_legal_exemption')
    online=e.load(name+'-online/dom.json');lu=urlsplit(online['url']);ld=html.fromstring(online['html'])
    gap=(datetime.fromisoformat(online['captured_at'].replace('Z','+00:00'))-datetime.fromisoformat(basic['captured_at'].replace('Z','+00:00'))).total_seconds()
    if (lu.scheme!='https' or lu.hostname!='user.zjzwfw.gov.cn' or lu.path!='/pc/login'
        or '个人用户登录' not in online['text'] or not ld.xpath('//input[@type="password"]') or not 0<=gap<=600):
        raise ValueError('未取得自身实际在线按钮对应的登录边界')
    e.read(name+'-online/page.png');e.read('browser-actions.jsonl')
    check={**own,'url':online['url'],'checked_at':online['captured_at'],'official_link':True,'status':'auth_required','post_login_flow':'unknown','submitted':False}
    templates=[];copy_note=''
    if name=='shangcheng':
        originals=e.load('shangcheng/originals.json');network=e.load('shangcheng-attachment-network-settled.json')
        if len(originals)!=2 or {f['annex_id'] for f in originals}!=set(BLANKS):raise ValueError('上城自身两份空白原件缺失')
        for f in originals:
            annex=f['annex_id'];filename,label,checksum,index=BLANKS[annex]
            relative='shangcheng/originals/'+filename
            download='https://portal.zjzwfw.gov.cn/media/oss/FILE/META_DATA/'+annex+'.docx'
            canonical='templates/_docx/_regional/330102/'+annex+'-'+label+'.docx'
            if any(f.get(k)!=v for k,v in {'file':relative,'canonical_file':canonical,'source_url':download,'final_url':download,'http_status':200,'sha256':checksum,'kind':'blank','original_name':label}.items()):raise ValueError('上城附件来源/名称/路径/SHA改变')
            body=e.read(relative);canonical_path=ROOT/canonical
            if hashlib.sha256(body).hexdigest()!=checksum or not canonical_path.is_file() or canonical_path.read_bytes()!=body:raise ValueError('上城原始下载或canonical副本字节不匹配')
            if not any(n['url']==download and n['status']==200 and n['method']=='GET' for n in network):raise ValueError('缺少上城自己实际材料控件网络200证据')
            with zipfile.ZipFile(io.BytesIO(body)) as archive:xml=etree.fromstring(archive.read('word/document.xml'))
            content=''.join(xml.itertext())
            if label not in content:raise ValueError('自身空白文书正文身份不匹配')
            if filename=='application.docx':
                copy_note='申请书副本份数，应按对方当事人人数提交。'
                if copy_note not in content:raise ValueError('申请书副本说明缺失')
            templates.append({**own,'id':digest([source,annex,'blank'])[:24],'annex_id':annex,'official_annex_id':annex,
                'material_id':materials[index]['id'],'original_name':spec['materials'][index],'source_filename':annex+'.docx',
                'official_kind':'blank','file_type':'docx','file':canonical,'retained_download_file':REPORT+'/'+relative,
                'sha256':checksum,'bytes':len(body),'download_url':download,'final_download_url':download,'http_status':200,
                'download_status':'downloaded','download_acquisition':f['acquisition'],'downloaded_at':f['acquired_at'],
                'can_generate':False,'document_types':[]})
    sections={'基本信息':'\n'.join(k+'：'+v for k,v in raw.items()),'受理条件':_text(conditions[0]),'办理流程':flow,
        '申请材料':('\n'.join(m['details']['原始材料行'] for m in materials) if materials else '当前情形下，无需递交材料'),
        '窗口办理':window,'常见问题':pages['faq']['text'].split('基本信息\n')[-1].split('好差评\n')[0].strip(),
        '设定依据':pages['law']['text'].split('设定依据\n')[-1]}
    warnings=['仅限杭州市该区自身已实际采集事项；不使用余杭、西湖或省级模板补齐要求。',
        '60天、44工作日保留原始单位；5个工作日仅为是否受理的决定阶段。','在线仅核验至实际登录表单，登录后流程未知，未提交。']
    if name=='binjiang':warnings.append('门户材料栏显示“当前情形下，无需递交材料”，但自身流程明确要求提交申请材料；这是公开信息冲突，不能解释为无需材料，未继承任何其他区附件。')
    else:warnings.extend(['窗口下午时间原文14:00-5:30疑有歧义，保留原文，须向机关确认。','公开材料行仅四项且未列身份证，不据此断言无需身份材料；材料表2份原件与申请书按被申请人数交副本均保留。'])
    return {'province':'zhejiang','province_name':'浙江省','city':'杭州市','district':spec['district'],'region_code':spec['code'],
        'service_name':SERVICE,'service_code':spec['local'],'service_code_type':'observed_localInnerCode_not_national_implementation_code',
        'service_ids':{'localInnerCode':spec['local'],'stdcateguid':STANDARD,'categorysourcereferno':CATEGORY},
        'directory_service_ids':{k:directory[0].get(k) for k in ['data-local-inner-code','data-stdcateguid','categorysourcereferno']},
        'directory_navigation_note':'实际按本区选择器/指南控件到达独立URL，目录catalogue标识与最终localInnerCode分别保留；最终窗口/实施主体另行核验。',
        'authority':authority,'source_id':digest(source)[:24],'source_url':source,'source_title':basic['title'],'source_type':'official_service_guide',
        'collected_at':basic['captured_at'],'verified_at':basic['captured_at'],'verification_status':'conflict' if name=='binjiang' else 'partial',
        'materials_status':'portal_material_flow_conflict' if name=='binjiang' else 'four_rows_captured',
        'fields':fields,'materials':materials,'templates':templates,'sections':sections,
        'authority_evidence':{'source_url':identity_source,'file':REPORT+'/'+identity_file,'scope':'机构全称旁证；不替代自己的仲裁指南或窗口'},
        'copy_conflict':{'status':'retained_unresolved' if copy_note else 'not_applicable_no_annex','attachment_note':copy_note},
        'channel':{'raw_value':flow,'form':'window_and_online','online_status':'auth_required','entry_url':source,'mentioned_urls':[],'entry_check':check},
        'evidence':{'manifest_digest':MANIFEST_DIGEST,'capture_file':REPORT+'/'+name+'-basic/dom.json',
            'capture_sha256':e.used[name+'-basic/dom.json']['sha256'],'source_files':e.used},'warnings':warnings}
