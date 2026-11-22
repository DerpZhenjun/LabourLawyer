"""Gulou own-source blanks. Offline review, isolated stage and publication are
separate authorities. No other locality's facts, forms or field sets are used.
"""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Annotated, Literal
from zipfile import ZipFile
from lxml import etree as E
from pydantic import BaseModel, ConfigDict, Field, field_validator
from regional_guides import digest, region_key

ROOT=Path(__file__).resolve().parents[1]
ADAPTER='fujian_gulou_own_blank_oct31h_v1'
SUPPORTED=frozenset({'350102'})
FOLDER='reports/overnight-gap-closure-20261030/localities/fujian-own-discovery/gulou-350102'
SOURCE_FREEZE=FOLDER+'/SOURCE-DISCOVERY-FREEZE.json'
FREEZE_SHA='6aa0a44017bf60eb39e07f441e31676bf88716b5f69722188c9258ff5e2efc15'
SOURCE_ID='3e2246aa2a534d2b37f6c6c5'
SERVICE='113501020036093803400201430200201'
OFFLINE_REVIEW=FOLDER+'/ROOT-OFFLINE-WORD-REVIEW.json'
OFFLINE_REVIEW_SHA='33f301242bba00761cc5aba26c35643f39844fab7b2c21719029b8de4b17f4c3'
QA_REPORT='reports/overnight-gap-closure-20261030/localities/fujian-h'
WORD_MANIFEST=QA_REPORT+'/WORD-MANIFEST.json'
WORD_SHA='612fda853f9ad18f6b88271ad0c6af19045463468ab8e5bb756cdf1cb9baa895'
STAGE_PROPOSAL=QA_REPORT+'/STAGE-PROPOSAL.json'
STAGE_RECEIPT=QA_REPORT+'/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT=QA_REPORT+'/FINAL-BROWSER-QA.json'
STAGE_SHA256='76b891e7c44261b8a77dc7fbfa190ce06d0b377ad2934b7654181d3de4c9fb34'
PUBLICATION_SHA256='f2dd9dbb759288f4fbbedcb311ea00fc13c69814374982ba43aa3cce03fa22d1'
SPECS={
 'application':dict(id='F4048D8C91E2FF882AC6C62CC0EC4D86',file='application-own-blank-public-retrieval.docx',sha256='093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365'),
 'evidence':dict(id='CC300F5D9DD5DC404D65C68116D50C55',file='evidence-list-own-blank.docx',sha256='d70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815'),
 'reference':dict(id='7C3DBFA82D340B3C50F4DD45E14FE785',file='evidence-material-own-format-reference.docx',sha256='31b98bc4a0ac254e1d819aed66f9d1d211c1aca3b3feea8c258c79a88b2a926e')}
ANNEX={kind:SPECS[kind]['id'] for kind in ('application','evidence')}
APPLICATION_FIELDS=('applicantName','agentName','respondentName','requests','factsReason')
EVIDENCE_FIELDS=('evidenceList',)
ITEM_FIELDS=('name','pageCount','originalType','purpose','pageRange')
_METADATA=frozenset({'version','region_id','content_hash'})
_FAILURES=(ValueError,OSError,KeyError,TypeError,StopIteration,AttributeError)
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
N={'w':W}


def require(condition,message):
    if not condition:raise ValueError(message)


def exact(actual,expected):
    if type(actual) is not type(expected):return False
    if isinstance(expected,dict):return actual.keys()==expected.keys() and all(exact(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):return len(actual)==len(expected) and all(exact(a,b) for a,b in zip(actual,expected))
    return actual==expected


def path_at(root,relative):
    require(root is not None and str(root).strip(),'必须明确鼓楼自身证据根目录')
    root=Path(root).resolve();relative=Path(relative)
    require(not relative.is_absolute() and not relative.drive and '..' not in relative.parts,'自身证据路径无效')
    p=(root/relative).resolve()
    require(p.is_relative_to(root) and p.relative_to(root).as_posix()==relative.as_posix(),'自身证据路径越界或被链接替换')
    return p


def _bytes(root,relative):
    try:return path_at(root,relative).read_bytes()
    except OSError as exc:raise ValueError('明确指定根目录缺少鼓楼自身证据') from exc


def _read(root,relative):return json.loads(_bytes(root,relative).decode('utf-8-sig'))


def _sources(root):
    raw=_bytes(root,SOURCE_FREEZE)
    require(sha256(raw).hexdigest()==FREEZE_SHA,'鼓楼来源冻结清单变化')
    f=json.loads(raw)
    expected={'province':'fujian','city':'福州市','district':'鼓楼区','region_code':'350102','source_id':SOURCE_ID,
              'service_code':SERVICE,'authority':'福州市鼓楼区人力资源和社会保障局','online_status':'auth_required',
              'can_generate':False,'published':False,'sample_files_downloaded':0}
    require(all(k in f and exact(f[k],v) for k,v in expected.items()),'鼓楼来源身份或边界变化')
    require(digest(f['source_url'])[:24]==SOURCE_ID and len(f['files'])==24,'鼓楼来源身份或文件数变化')
    for name,pin in f['files'].items():
        raw=_bytes(root,FOLDER+'/'+name)
        require(type(pin['bytes']) is int and len(raw)==pin['bytes'] and sha256(raw).hexdigest()==pin['sha256'],'鼓楼冻结来源文件变化')
    for spec in SPECS.values():require(f['files'][spec['file']]['sha256']==spec['sha256'],'鼓楼原件版本变化')
    return f


def source_files(root):return [FOLDER+'/'+name for name in _sources(root)['files']]


def _offline_review(root):
    raw=_bytes(root,OFFLINE_REVIEW)
    require(sha256(raw).hexdigest()==OFFLINE_REVIEW_SHA,'鼓楼独立线下审核记录变化')
    r=json.loads(raw)
    require(r['region_code']=='350102' and r['source_id']==SOURCE_ID and r['source_freeze_sha256']==FREEZE_SHA
            and r['all_png_pages_independently_viewed']==25 and r['can_generate'] is False and r['published'] is False
            and r['guide_status']=='partial' and r['sample_contents_verified'] is False,'鼓楼线下审核范围变化')
    return r


def _word_manifest(root):
    review=_offline_review(root);raw=_bytes(root,WORD_MANIFEST)
    require(sha256(raw).hexdigest()==WORD_SHA,'鼓楼公开Word证据清单变化')
    manifest=json.loads(raw)
    require(manifest['region_code']=='350102' and manifest['source_id']==SOURCE_ID
        and manifest['source_freeze_sha256']==FREEZE_SHA and manifest['offline_review_sha256']==OFFLINE_REVIEW_SHA
        and manifest['reviewed_candidate_manifest_sha256']==review['candidate_manifest_sha256']
        and manifest['generated_pages']==21 and manifest['stage_approved'] is False
        and manifest['can_publish'] is False and manifest['browser_qa']=='NOT_RUN','鼓楼公开Word证据身份或阶段变化')
    files=manifest['files']
    require(type(files) is list and len(files)==27 and len({r['path'] for r in files})==27,'鼓楼公开Word证据清单不完整')
    for row in files:
        require(row['path'].startswith(QA_REPORT+'/'),'鼓楼Word证据路径不匹配')
        data=_bytes(root,row['path'])
        require(type(row['bytes']) is int and len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256'],'鼓楼公开Word证据文件变化')
    return manifest


def parse_capture(code='350102',*,root=None):
    require(type(code) is str and code=='350102','不是鼓楼自身指南')
    root=ROOT if root is None else root;freeze=_sources(root);_word_manifest(root)
    capture=FOLDER+'/own-guide-native-dom.json';dom=_read(root,capture)
    require(dom['url']==freeze['source_url'],'鼓楼原生指南地址变化')
    fields={}
    for row in dom['tables'][1]:
        if len(row)==2 and all(type(v) is str for v in row):
            key=row[0].rstrip('：:').strip()
            fields[key]={'raw_value':row[1],'source_label':row[0],'source_url':freeze['source_url'],
                         'capture_file':capture,'capture_sha256':freeze['files']['own-guide-native-dom.json']['sha256'],
                         'captured_at':dom['captured_at'],'source_pointer':'tables[1]'}
    # Presentation names alias only exact observed own labels; no foreign facts.
    for display,source in {'咨询方式':'联系电话','服务对象':'申报对象','必须到现场原因':'必须现场办理原因',
                           '承诺办结时限':'承诺时限','法定办结时限':'法定时限'}.items():
        if source in fields:fields[display]=deepcopy(fields[source])
    for label,pattern,pointer in [
        ('到办事现场次数',r'服务承诺到现场次数\n([^\n]+)','text/service_commitment_visits'),
        ('是否收费',r'\n收费情况\n是否收费：[\t ]*([^\n]+)','text/fee_section')]:
        found=re.search(pattern,dom['text'])
        if found:
            fields[label]={'raw_value':found.group(1),'source_label':label,'source_url':freeze['source_url'],
                'capture_file':capture,'capture_sha256':freeze['files']['own-guide-native-dom.json']['sha256'],
                'captured_at':dom['captured_at'],'source_pointer':pointer}
    window=re.search(r'窗口办理\n办理时间：([^\n]+)\n办理地点：([^\n]+)\n',dom['text'])
    if window:
        for label,value in zip(('办理时间','办理地点'),window.groups()):
            fields[label]={'raw_value':value,'source_label':label+'：','source_url':freeze['source_url'],
                'capture_file':capture,'capture_sha256':freeze['files']['own-guide-native-dom.json']['sha256'],
                'captured_at':dom['captured_at'],'source_pointer':'text/window_service_block'}
    for field in fields.values():
        field.update(normalized_value=field['raw_value'],region_code='350102',
                     collected_at=dom['captured_at'],verified_at=freeze['captured_at'],verification_status='verified')
    require(fields['实施主体']['raw_value']==freeze['authority'] and fields['业务办理项编码']['raw_value']==SERVICE,'鼓楼指南正文身份变化')
    formats=_read(root,FOLDER+'/api-public-39.json')['data']['tableList'];materials=[]
    for i,m in enumerate(dom['materials']):
        table=dom['tables'][2+i];details={row[0]:row[1] for row in table if len(row)==2}
        name=m['header'].splitlines()[-1];kind=('application','evidence','reference')[i]
        material_id=next(row['punid'] for row in formats if row['fileunid']==SPECS[kind]['id'])
        materials.append({'id':material_id,'name':name,'required':'必要','format':'纸质，电子（上传）',
            'copies':2,'paper_copies':2,'original_copy':'原件' if i<2 else '复印件','material_type':'原件' if i<2 else '复印件',
            'official_badges':[],'attachment_labels':['格式文本'],'purpose':'','details':details,'instructions':details.get('填报须知',''),
            'source_url':freeze['source_url'],'capture_file':capture,'capture_sha256':freeze['files']['own-guide-native-dom.json']['sha256']})
    templates=[]
    for row in formats:
        spec=next((s for s in SPECS.values() if s['id']==row['fileunid']),None)
        kind=next((k for k,s in SPECS.items() if s is spec),None)
        blank=spec is not None and kind!='reference'
        t={'id':row['fileunid'],'annex_id':row['fileunid'],'region_code':'350102','material_id':row['punid'],
           'official_kind':'blank' if blank else 'reference' if spec else 'sample','original_name':row['name'],
           'file_type':'docx','source_url':freeze['source_url'],
           'download_url':'https://zwfw.fujian.gov.cn:732/cms-business/apasService/file/downloadFileStream?unid='+row['fileunid'],
           'download_status':'downloaded' if spec else 'unverified','document_types':[],'can_generate':False,
           'content_role':'fillable_own_blank' if blank else 'scanning_instructions_only' if spec else 'unverified_sample_contents',
           'public_release_status':'own_source_retained' if spec else 'sample_contents_not_fetched'}
        if spec:t.update(file=FOLDER+'/'+spec['file'],sha256=spec['sha256'],bytes=freeze['files'][spec['file']]['bytes'])
        templates.append(t)
    boundary=_read(root,FOLDER+'/online-native-scan-login-boundary.json')
    require(boundary['boundary']=='Minzhengtong_APP_scan_login_required' and boundary['login_attempted'] is False
            and boundary['qr_scanned'] is False and boundary['application_submitted'] is False,'鼓楼原生登录边界变化')
    return {'province':'fujian','province_name':'福建省','city':'福州市','district':'鼓楼区','region_code':'350102',
        'source_id':SOURCE_ID,'source_url':freeze['source_url'],'service_code':SERVICE,'service_name':'劳动人事争议仲裁申请',
        'authority':freeze['authority'],'source_title':'劳动人事争议仲裁申请','source_type':'own_official_guide',
        'source_version':FREEZE_SHA,'official_version':'','verification_status':'partial','guide_status':'partial',
        'collected_at':freeze['captured_at'],'verified_at':freeze['captured_at'],'fields':fields,
        'sections':{'本区公开办事指南原文':dom['text']},
        'materials':materials,'templates':templates,'can_generate':False,'published':False,'publication_status':'source_only',
        'attachment_counts':{'observed':6,'format_bytes_retrieved':3,'sample_contents_retrieved':0},
        'native_format_download_completion':'not_asserted_public_bytes_retrieved_independently',
        'channel':{'raw_value':fields['办理形式']['raw_value'],'online_status':'auth_required','entry_url':None,
                   'observed_entry_url':boundary['entry_url'],'entry_check':{'status':'auth_required'},
                   'platform_link_policy':'official_guide_fallback_for_linked_non_government_host','submission_verified':False},
        'evidence':{'capture_file':capture,'capture_sha256':freeze['files']['own-guide-native-dom.json']['sha256'],
                    'source_freeze':SOURCE_FREEZE,'source_freeze_sha256':FREEZE_SHA,
                    'word_manifest':WORD_MANIFEST,'word_manifest_sha256':WORD_SHA,
                    'online_boundary':FOLDER+'/online-native-scan-login-boundary.json'},
        'sample_contents_verified':False,'warnings':['指南仍为部分核实；未采集字段显示待核实。',
            '官网受理后5个工作日仅保留为受理审查表述，不作为仲裁实体裁决期限。',
            '三份示范文本仅观察到标签与附件身份，未取得或审核内容；不用于填写生成。',
            '证据材料供参考文件是扫描上传说明，不是可填写空白表。',
            '自身材料原件或复印件2份及按当事人人数提供副本的原文同时保留，具体提交须本人核对。',
            '网上申报到闽政通APP扫码登录边界止，未扫码、未登录、未提交。','签名、日期及提交人始终留空，由本人核对填写。']}


def approval_requirements(*,stage=True):
    result={'identities':[{'region_code':'350102','source_id':SOURCE_ID,'service_code':SERVICE}],
            'source_freeze_sha256':FREEZE_SHA,'offline_review_sha256':OFFLINE_REVIEW_SHA,
            'word_manifest_sha256':WORD_SHA,
            'approved_by':'independent_root','visual_review':'PASS','can_publish':not stage,'model_calls':0}
    if not stage:result.update(stage_receipt_sha256=STAGE_SHA256,native_confirmation_download_two_forms=True)
    return result


def _receipt(root,stage=True):
    pin=STAGE_SHA256 if stage else PUBLICATION_SHA256
    require(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin),'鼓楼独立阶段收据尚未批准固定')
    _offline_review(root)
    path=STAGE_RECEIPT if stage else PUBLICATION_RECEIPT;raw=_bytes(root,path)
    require(sha256(raw).hexdigest()==pin,'鼓楼审批收据变化');receipt=json.loads(raw)
    require(all(k in receipt and exact(receipt[k],v) for k,v in approval_requirements(stage=stage).items()),'鼓楼审批身份或阶段范围不匹配')
    files=receipt.get('files')
    require(type(files) is list and files and all(type(r) is dict and {'path','bytes','sha256'}<=r.keys()
        and type(r['path']) is str and type(r['bytes']) is int and type(r['sha256']) is str
        and re.fullmatch('[a-f0-9]{64}',r['sha256']) for r in files),'鼓楼阶段证据清单无效')
    require(len({r['path'] for r in files})==len(files),'鼓楼阶段证据清单重复')
    if stage:require(exact(files,_word_manifest(root)['files']),'鼓楼公开Word证据未被完整纳入独立stage审批')
    for row in files:
        require(type(row['path']) is str and row['path'].startswith(QA_REPORT+'/'),'鼓楼审批证据路径不匹配')
        data=_bytes(root,row['path'])
        require(type(row['bytes']) is int and len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256'],'鼓楼阶段证据文件变化')
    return {'receipt':path,'sha256':pin}


def _binding(t,kind):return {'adapter':ADAPTER,'kind':kind,'annex_id':t['id'],'source_file':t['file'],'source_sha256':t['sha256'],'source_url':t['source_url']}


def prepare_candidate(code='350102',*,root):
    g=parse_capture(code,root=root);g['candidate_adapter_evidence']=_receipt(root)
    g.update(can_generate=True,generation_adapter=ADAPTER,publication_status='staged_own_word_qa')
    for t in g['templates']:
        kind=next((k for k,v in ANNEX.items() if t['id']==v),None)
        if kind:t.update(can_generate=True,document_types=[kind],adapter=ADAPTER,generation_adapter=ADAPTER,
            strict_binding=_binding(t,kind),generation_mode='blank',content_kind='filled_official_blank',
            generation_label='依据鼓楼区自身官方空白表格填写',applicant_scope='own_application' if kind=='application' else 'evidence_list',render_status='PASS')
    return g


def _published(root):
    g=prepare_candidate(root=root);g['publication_adapter_evidence']=_receipt(root,False)
    g.update(published=True,publication_status='published',candidate_web_qa='PASS');return g


def _matches(g,canonical):
    if type(g) is not dict or set(g)-set(canonical)-_METADATA:return False
    if 'version' in g and (type(g['version']) is not int or g['version']<1):return False
    if 'region_id' in g and g['region_id']!=region_key('fujian','福州市','鼓楼区'):return False
    if 'content_hash' in g and (type(g['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}',g['content_hash'])):return False
    return all(k in g and exact(g[k],v) for k,v in canonical.items())


def _bound(g,root,allow_source=False):
    source=parse_capture(root=root)
    if allow_source and _matches(g,source):return source
    canonical=_published(root) if type(g) is dict and ('publication_adapter_evidence' in g or g.get('published') is True) else prepare_candidate(root=root)
    require(_matches(g,canonical),'鼓楼来源、模板、版本或阶段绑定不匹配');return canonical


def with_capabilities(guide,root=None):
    _bound(guide,ROOT if root is None else root,True);return deepcopy(guide)


def with_publication_evidence(guide,*,root):
    require(_matches(guide,prepare_candidate(root=root)),'必须从鼓楼已批准候选投影最终发布')
    g=_published(root)
    for key in _METADATA&set(guide):g[key]=deepcopy(guide[key])
    return g


def checked_adapter(guide,template,kind,root=None):
    canonical=_bound(guide,ROOT if root is None else root)
    require(kind in ANNEX,'鼓楼文书类型不匹配');t=next(t for t in canonical['templates'] if t['id']==ANNEX[kind])
    require(exact(template,t) and t['official_kind']=='blank' and t['can_generate'] is True,'鼓楼自身空白表绑定不匹配')
    return ADAPTER


def public_evidence(guide,root):
    try:
        require(root is not None,'必须明确公开根目录');return deepcopy(_bound(guide,root,True)['evidence'])
    except _FAILURES:return None


def approved_report_attachment(guide,template,root):
    try:
        require(root is not None,'必须明确公开根目录');g=_bound(guide,root,True)
        return any(exact(t,template) and t['download_status']=='downloaded' and 'file' in t for t in g['templates'])
    except _FAILURES:return False


def _text(v,maxlen):
    require(type(v) is str and len(v)<=maxlen and all(c=='\n' or 0x20<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff for c in v),'文字类型、XML字符或技术容量无效')
    return v.strip()


Text180=Annotated[str,Field(strict=True,max_length=180)]
class ApplicationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    applicantName:Text180='';agentName:Text180='';respondentName:Text180=''
    requests:list[Annotated[str,Field(strict=True,max_length=360)]]=Field(default_factory=list,max_length=3)
    factsReason:Annotated[str,Field(strict=True,max_length=2400)]=''
    @field_validator('applicantName','agentName','respondentName','factsReason',mode='before')
    @classmethod
    def text(cls,v,info):return _text(v,2400 if info.field_name=='factsReason' else 180)
    @field_validator('requests',mode='before')
    @classmethod
    def requests_text(cls,v):
        require(type(v) is list and len(v)<=3,'鼓楼请求项数超出技术容量');return [_text(x,360) for x in v]


class EvidenceItem(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:Annotated[str,Field(strict=True,max_length=100)]=''
    pageCount:Annotated[str,Field(strict=True,max_length=4)]=''
    originalType:Literal['','原件','复印件']=''
    purpose:Annotated[str,Field(strict=True,max_length=240)]=''
    pageRange:Annotated[str,Field(strict=True,max_length=32)]=''
    @field_validator('name','pageCount','originalType','purpose','pageRange',mode='before')
    @classmethod
    def text(cls,v,info):
        s=_text(v,{'name':100,'pageCount':4,'originalType':4,'purpose':240,'pageRange':32}[info.field_name])
        if info.field_name=='pageCount':require(not s or re.fullmatch('[1-9][0-9]{0,3}',s),'证据页数须留空或填写1至9999的整数文字')
        return s


class EvidenceRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    evidenceList:list[EvidenceItem]=Field(default_factory=lambda:[EvidenceItem()],max_length=15)


def defaults(kind):
    require(kind in ANNEX,'鼓楼文书类型不匹配')
    if kind=='application':return {'applicantName':'','agentName':'','respondentName':'','requests':[''],'factsReason':''}
    return {'evidenceList':[{key:'' for key in ITEM_FIELDS}]}


def form_fields(kind):
    require(kind in ANNEX,'鼓楼文书类型不匹配')
    def text(key,label,length,**extra):return {'key':key,'label':label,'type':'text','nullable':False,'maxLength':length,**extra}
    if kind=='application':return [text('applicantName','申请人信息',180),text('agentName','委托代理人信息',180),text('respondentName','被申请人信息',180),
        {'key':'requests','label':'仲裁请求','type':'text_list','nullable':False,'maxItems':3,'maxLength':360},text('factsReason','事实与理由',2400)]
    return [{'key':'evidenceList','label':'证据内容','type':'object_list','nullable':False,'maxItems':15,'fields':[
        text('name','证据名称',100),text('pageCount','页数',4),text('originalType','原件或复印件',4,choices=['原件','复印件']),
        text('purpose','证明对象',240),text('pageRange','页码',32)]}]


class _PatchedDocument:
    def __init__(self,raw,xml=None,source_folder=None):self.raw=raw;self.xml=xml;self.source_folder=source_folder
    def save(self,destination):
        if not hasattr(destination,'write') and self.source_folder is not None:
            require(not Path(destination).resolve().is_relative_to(self.source_folder),'不允许覆盖鼓楼冻结来源目录')
        if self.xml is None:
            if hasattr(destination,'write'):destination.write(self.raw)
            else:Path(destination).write_bytes(self.raw)
            return
        with ZipFile(BytesIO(self.raw)) as source,ZipFile(destination,'w') as out:
            for part in source.infolist():out.writestr(part,self.xml if part.filename=='word/document.xml' else source.read(part.filename))


def _replace(p,text):
    runs=p.findall('w:r',N)
    if runs:
        run=runs[0]
        for child in list(run):
            if child.tag!='{'+W+'}rPr':run.remove(child)
        for extra in runs[1:]:p.remove(extra)
    else:
        run=E.SubElement(p,'{'+W+'}r');pr=p.find('w:pPr/w:rPr',N)
        if pr is not None:run.append(deepcopy(pr))
    t=E.SubElement(run,'{'+W+'}t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=text


def fill_offline(kind,data,*,root):
    require(kind in ANNEX,'鼓楼参考说明或样表不允许填写生成');g=parse_capture(root=root);_offline_review(root)
    model=ApplicationRequest if kind=='application' else EvidenceRequest
    if isinstance(data,BaseModel):data=data.model_dump()
    values=model.model_validate(data).model_dump();spec=SPECS[kind]
    raw=path_at(root,FOLDER+'/'+spec['file']).read_bytes()
    if kind=='application':nonempty=any(values[k] for k in APPLICATION_FIELDS if k!='requests') or any(values['requests'])
    else:nonempty=any(any(row.values()) for row in values['evidenceList'])
    if not nonempty:return _PatchedDocument(raw,source_folder=path_at(root,FOLDER))
    document=E.fromstring(ZipFile(BytesIO(raw)).read('word/document.xml'));ps=document.findall('w:body/w:p',N)
    if kind=='application':
        require(len(ps)==22 and ''.join(ps[0].itertext())=='仲裁申请书' and ''.join(ps[19].itertext())=='申请人：','鼓楼申请书自身布局变化')
        _replace(ps[2],'申请人：'+values['applicantName']);_replace(ps[3],'委托代理人：'+values['agentName']);_replace(ps[4],'被申请人：'+values['respondentName'])
        for i in range(3):ps[7+i].findall('.//w:t',N)[1].text=values['requests'][i] if i<len(values['requests']) else ' '*37
        _replace(ps[11],values['factsReason']);ps[16].findall('.//w:t',N)[1].text='福州市鼓楼区'
        for closing in ps[15:20]:
            pr=closing.find('w:pPr',N)
            if pr is None:pr=E.Element('{'+W+'}pPr');closing.insert(0,pr)
            keep=pr.find('w:keepNext',N)
            if keep is None:keep=E.SubElement(pr,'{'+W+'}keepNext')
            keep.set('{'+W+'}val','1')
    else:
        tbl=document.find('.//w:tbl',N);rows=tbl.findall('w:tr',N)
        require(len(rows)==11 and [''.join(c.itertext()) for c in rows[0].findall('w:tc',N)]==['序号','证据名称','页数','原件/复印件','证明对象','页码'],'鼓楼证据清单自身布局变化')
        items=[r for r in values['evidenceList'] if any(r.values())]
        E.SubElement(rows[0].find('w:trPr',N),'{'+W+'}tblHeader')
        for unused in rows[1+len(items):-1]:tbl.remove(unused)
        rows=tbl.findall('w:tr',N)
        while len(rows)-2<len(items):
            row=deepcopy(rows[1]);tbl.insert(list(tbl).index(rows[-1]),row);rows=tbl.findall('w:tr',N)
        for i,row in enumerate(rows[1:-1]):
            E.SubElement(row.find('w:trPr',N),'{'+W+'}cantSplit');x=items[i]
            for cell,value in zip(row.findall('w:tc',N),[str(i+1),x['name'],x['pageCount'],x['originalType'],x['purpose'],x['pageRange']]):_replace(cell.find('w:p',N),value)
        pages=str(sum(int(x['pageCount']) for x in items)) if all(x['pageCount'] for x in items) else '____'
        _replace(rows[-1].find('w:tc/w:p',N),f'以上证据材料合计 {len(items)}份（组） {pages}页')
    return _PatchedDocument(raw,E.tostring(document,encoding='UTF-8',xml_declaration=True,standalone=True),source_folder=path_at(root,FOLDER))


def fill_document(guide,template,kind,path,data,*,root):
    checked_adapter(guide,template,kind,root=root)
    require(Path(path).resolve()==path_at(root,template['file']),'传入原件路径不是鼓楼自身附件')
    return fill_offline(kind,data,root=root)


def example_data(kind,stress=False):
    require(kind in ANNEX,'鼓楼文书类型不匹配')
    if kind=='application':
        f={'applicantName':'林虚构（软件演示虚构人物，无真实身份资料）','agentName':'','respondentName':'福州虚构示例公司（软件演示虚构单位）',
            'requests':['请求支付虚构演示工资1000元。','请求确认虚构演示期间的劳动关系。','本项仅为第三请求字段排版演示。'],
            'factsReason':'全部内容为虚构，仅验证排版，不对应真实案件。'}
        if stress:
            f['applicantName']+='虚构住址和联系方式字段由使用者自行填写，当前仅验证长文字自动换行。'*2
            f['respondentName']+='（长名称排版测试，不对应任何已登记主体）'*4
            f['requests']=[x+'此为长请求换行测试，数额与事实均为虚构，不能用于真实申请。'*3 for x in f['requests']]
            f['factsReason']+='以下文字仅验证多页排版与签名空白保留，不表示法律意见。虚构演示记录按时间顺序整理，具体内容须由真实使用者核验并自行提供。'*8
        return f
    if stress:return {'evidenceList':[{'name':f'虚构演示记录第{i}组，较长名称换行测试','pageCount':'2','originalType':'复印件',
        'purpose':'仅证明软件测试场景中的虚构记录对应关系，不涉及真实案件或真实人员。长文字用于验证表格扩展、跨页重复表头与整行显示。','pageRange':f'{2*i-1}—{2*i}'} for i in range(1,16)]}
    return {'evidenceList':[{'name':'虚构工资记录（仅软件演示）','pageCount':'2','originalType':'复印件','purpose':'验证证据字段与合计功能，全部事实虚构。','pageRange':'1—2'}]}
