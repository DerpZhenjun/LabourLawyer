"""Kunshan own-source worker blanks. Source, isolated stage and final publication
are distinct projections; both approval pins remain unset until independent root review.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Annotated,ClassVar
from pydantic import BaseModel,ConfigDict,Field,create_model,model_validator
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import _Row
from regional_documents import PreservedPackageDocument
from regional_guides import digest,region_key
from WenShu.template_fill import fill_label_slots,replace_span,set_cell_text
from WenShu.exact_template_fill import keep_body,fill_sections,remove_empty_edges

ROOT=Path(__file__).resolve().parents[1]
ADAPTER='jiangsu_kunshan_own_blank_oct31g_v1'
SUPPORTED=frozenset({'320583'})
FOLDER='reports/overnight-gap-closure-20261030/localities/kunshan/source-discovery/continuation-20261031-native'
SOURCE_FREEZE=FOLDER+'/SOURCE-FREEZE.json'
FREEZE_SHA='daa6ecda9f78f398c196ba579a4d870591e02a328aca3d5665ae9177151f2c6d'
SERVICE='1132058301418949XF400201430200201'
SOURCE_ID='d39444ab7f4bcaea2ea91473'
QA_REPORT=Path('reports/overnight-gap-closure-20261030/localities/kunshan/integration-qa-v1')
WORD_MANIFEST=(QA_REPORT/'WORD-MANIFEST.json').as_posix()
WORD_SHA='edddb2840686b10c64fc164a4c5a63f9744e42c8f3fc9a2763b116d9d3eabf8f'
STAGE_PROPOSAL=(QA_REPORT/'STAGE-PROPOSAL.json').as_posix()
STAGE_RECEIPT=(QA_REPORT/'STAGE-APPROVAL.json').as_posix()
PUBLICATION_RECEIPT=(QA_REPORT/'FINAL-BROWSER-QA.json').as_posix()
STAGE_SHA256='f794e50d5ba7fcc01d520625efeaa60a851fd2c01d5428b1305fd5634e32bc32'
PUBLICATION_SHA256='c55b2c697c5a2668b6752ce6ea6bdfcea4670a4be41be11c55f4d23e131d8894'
ANNEX={'application':'3c17b2ea-434e-4b29-8fe4-40e88ad11c57','evidence':'de3a0ee9-0827-4f44-b9ad-ba05010a03d9'}
APPLICATION_FIELDS=frozenset('committeeName applicantName gender birthDate idNumber idAddress otherDocumentType otherDocumentNumber applicantMailingAddress phone acceptMediation legalAid respondentName respondentType registeredAddress socialCreditCode legalRepName legalRepPosition departmentHead departmentHeadPosition mailingAddress companyContact companyContactPhone requests factsReason applicationDate copyCount evidenceCopyCount'.split())
EVIDENCE_FIELDS=frozenset({'committeeName','caseNumber','submitDate','evidenceList'})
ITEM_FIELDS=frozenset({'name','source','purpose','originalType','pageCount'})
_METADATA=frozenset({'version','content_hash','region_id'})
_FAILURES=(ValueError,OSError,KeyError,TypeError,StopIteration,AttributeError)


def require(condition,message):
    if not condition:raise ValueError(message)


def exact(actual,expected):
    if type(actual) is not type(expected):return False
    if isinstance(expected,dict):return actual.keys()==expected.keys() and all(exact(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):return len(actual)==len(expected) and all(exact(a,b) for a,b in zip(actual,expected))
    return actual==expected


def path_at(root,relative):
    require(root is not None and str(root).strip(),'必须明确本区公开根目录')
    root=Path(root).resolve();relative=Path(relative)
    require(not relative.is_absolute() and not relative.drive and '..' not in relative.parts,'本区来源路径无效')
    p=(root/relative).resolve()
    require(p.is_relative_to(root) and p.relative_to(root).as_posix()==relative.as_posix(),'本区来源路径越界')
    return p


def read_json(root,relative):return json.loads(path_at(root,relative).read_text('utf-8-sig'))


def source_files(root):
    raw=path_at(root,SOURCE_FREEZE).read_bytes();require(sha256(raw).hexdigest()==FREEZE_SHA,'本区来源冻结清单变化')
    return list(json.loads(raw)['files'])


def _word_manifest(root):
    raw=path_at(root,WORD_MANIFEST).read_bytes();require(sha256(raw).hexdigest()==WORD_SHA,'本区独立Word证据清单变化')
    manifest=json.loads(raw)
    require(manifest.get('source_freeze_sha256')==FREEZE_SHA and manifest.get('region_code')=='320583'
            and manifest.get('source_id')==SOURCE_ID and manifest.get('generated_pages')==11,'本区Word证据身份变化')
    for row in manifest['files']:
        require(row['path'].startswith(QA_REPORT.as_posix()+'/'),'本区Word证据路径不匹配')
        body=path_at(root,row['path']).read_bytes()
        require(len(body)==row['bytes'] and sha256(body).hexdigest()==row['sha256'],'本区Word证据文件变化')
    return manifest


def parse_capture(code='320583',*,root=None):
    require(str(code)=='320583','不是本区自身指南')
    root=ROOT if root is None else root
    _word_manifest(root);result=_source_guide(root)
    freeze=read_json(root,SOURCE_FREEZE)
    result.update(verification_status='verified',publication_status='source_only',source_type='own_official_guide',
                  source_title='劳动人事争议仲裁申请',collected_at=freeze['frozen_at'],verified_at=freeze['frozen_at'])
    # Project this own frozen capture into the existing public wire shape.
    # Never change the capture bytes or borrow another locality's field values.
    provenance={key:result[key] for key in ['source_url','region_code','collected_at','verified_at','verification_status']}
    require(all(type(value) is str for value in result['fields'].values()),'本区原始字段类型变化')
    result['fields']={name:{'raw_value':value,'normalized_value':value.strip(),**provenance}
                      for name,value in result['fields'].items()}
    capture=read_json(root,FOLDER.rsplit('/',1)[0]+'/own-guide.json')
    require(type(capture.get('text')) is str and capture['text'],'本区原文缺失')
    result['sections']={'本区公开办事指南原文':capture['text']}
    for material in result['materials']:
        details=material['details'];copies=details['纸质材料份数']
        require(type(copies) is str and re.fullmatch(r'[0-9]+',copies),'本区材料份数原文变化')
        material.update(copies=int(copies),raw_copies=material['paper_copies'],
            required=details['材料必要性'],original_copy=details['材料类型'],format=details['材料形式'],
            paper_size=details['纸质材料规格'],source_channel=details['来源渠道'],**provenance)
    result.pop('Word_stage',None);result.pop('candidate_adapter',None)
    result['evidence']={'capture_file':FOLDER.rsplit('/',1)[0]+'/own-guide.json',
        'capture_sha256':freeze['files'][FOLDER.rsplit('/',1)[0]+'/own-guide.json']['sha256'],
        'source_freeze':SOURCE_FREEZE,'source_freeze_sha256':FREEZE_SHA,
        'word_manifest':WORD_MANIFEST,'word_manifest_sha256':WORD_SHA,
        'online_boundary':FOLDER+'/online-devtools-login-proof.json'}
    for template,material in zip(result['templates'],result['materials']):
        template.update(original_name=material['name']+'.docx',file_type='docx',download_status='downloaded',
                        document_types=[],public_release_status='own_source_retained')
    return result


def _receipt(root,stage=True):
    pin=STAGE_SHA256 if stage else PUBLICATION_SHA256
    require(type(pin) is str and re.fullmatch(r'[a-f0-9]{64}',pin),'本区独立审批收据尚未固定')
    path=STAGE_RECEIPT if stage else PUBLICATION_RECEIPT
    raw=path_at(root,path).read_bytes();require(sha256(raw).hexdigest()==pin,'本区审批收据变化')
    receipt=json.loads(raw)
    required={'identities':[{'region_code':'320583','source_id':SOURCE_ID,'service_code':SERVICE}],
              'source_freeze_sha256':FREEZE_SHA,'word_manifest_sha256':WORD_SHA,
              'approved_by':'independent_root','visual_review':'PASS','can_publish':not stage,'model_calls':0}
    require(all(k in receipt and exact(receipt[k],v) for k,v in required.items()),'本区审批范围不匹配')
    if not stage:
        require(receipt.get('stage_receipt_sha256')==STAGE_SHA256
                and receipt.get('native_confirmation_download_two_forms') is True,'本区最终网页下载证明缺失')
    files=receipt.get('files')
    require(type(files) is list and files and len({r['path'] for r in files})==len(files),'本区审批证据清单缺失或重复')
    if stage:require(exact(files,_word_manifest(root)['files']),'本区独立Word证据未完整审批')
    for row in files:
        require(row['path'].startswith(QA_REPORT.as_posix()+'/'),'本区审批证据路径不匹配')
        body=path_at(root,row['path']).read_bytes()
        require(type(row['bytes']) is int and len(body)==row['bytes'] and sha256(body).hexdigest()==row['sha256'],'本区审批证据变化')
    return {'receipt':path,'sha256':pin}


def _binding(template,kind):
    return {'adapter':ADAPTER,'kind':kind,'annex_id':template['id'],'source_file':template['file'],
            'source_sha256':template['sha256'],'source_url':template['source_url']}


def prepare_candidate(code='320583',*,root):
    result=parse_capture(code,root=root);result['candidate_adapter_evidence']=_receipt(root)
    result.update(can_generate=True,generation_adapter=ADAPTER,publication_status='staged_own_word_qa')
    for t in result['templates']:
        kind=next((kind for kind,annex in ANNEX.items() if t['id']==annex),None)
        if kind:t.update(can_generate=True,document_types=[kind],generation_adapter=ADAPTER,adapter=ADAPTER,
            strict_binding=_binding(t,kind),generation_mode='blank',content_kind='filled_official_blank',
            applicant_scope='worker' if kind=='application' else 'evidence_list',
            generation_label='依据昆山市自身官方空白表格填写',render_status='PASS')
    return result


def _published(root):
    result=prepare_candidate(root=root);result['publication_adapter_evidence']=_receipt(root,stage=False)
    result.update(published=True,publication_status='published',candidate_web_qa='PASS');return result


def _matches(guide,canonical):
    if type(guide) is not dict or set(guide)-set(canonical)-_METADATA:return False
    if 'version' in guide and (type(guide['version']) is not int or guide['version']<1):return False
    if 'region_id' in guide and guide['region_id']!=region_key('jiangsu','苏州市','昆山市'):return False
    if 'content_hash' in guide and (type(guide['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}',guide['content_hash'])):return False
    return all(k in guide and exact(guide[k],v) for k,v in canonical.items())


def _bound(guide,root,allow_source=False):
    source=parse_capture(root=root)
    if allow_source and _matches(guide,source):return source
    canonical=_published(root) if type(guide) is dict and ('publication_adapter_evidence' in guide or guide.get('published') is True) else prepare_candidate(root=root)
    require(_matches(guide,canonical),'本区来源、材料、能力或审批绑定不匹配');return canonical


def with_capabilities(guide,root=None):
    _bound(guide,ROOT if root is None else root,allow_source=True);return deepcopy(guide)


def with_publication_evidence(guide,*,root):
    require(_matches(guide,prepare_candidate(root=root)),'必须从已审批的本区候选生成发布投影')
    result=_published(root)
    for key in _METADATA&set(guide):result[key]=deepcopy(guide[key])
    return result


def checked_adapter(guide,template,kind,root=None):
    root=ROOT if root is None else root;canonical=_bound(guide,root)
    require(kind in ANNEX,'本区文书类型不匹配')
    own=next(t for t in canonical['templates'] if t['id']==ANNEX[kind])
    require(exact(template,own) and own['official_kind']=='blank' and own['can_generate'] is True,'本区原件与文书绑定不匹配')
    return ADAPTER


def public_evidence(guide,root):
    try:
        require(root is not None,'必须明确公开根目录')
        return deepcopy(_bound(guide,root,allow_source=True)['evidence'])
    except _FAILURES:return None


def approved_report_attachment(guide,template,root):
    try:
        require(root is not None,'必须明确公开根目录')
        canonical=_bound(guide,root,allow_source=True)
        return any(exact(t,template) for t in canonical['templates'])
    except _FAILURES:return False


def _plain(value):
    if isinstance(value,BaseModel):return value.model_dump()
    if isinstance(value,dict):return {k:_plain(v) for k,v in value.items()}
    if isinstance(value,list):return [_plain(v) for v in value]
    return value


def _text(value,maxlen=300):
    require(type(value) is str and len(value)<=maxlen and all(c in '\t\n\r' or 0x20<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff for c in value),'文字类型、XML字符或技术容量无效')
    return value.strip()


def _validate_data(kind,data):
    data=_plain(data);require(type(data) is dict,'本区填写数据须为对象')
    allowed=APPLICATION_FIELDS if kind=='application' else EVIDENCE_FIELDS if kind=='evidence' else ITEM_FIELDS
    require(not set(data)-allowed,'含本区没有槽位的字段');result={}
    for key,value in data.items():
        if key=='requests':
            require(type(value) is list and len(value)<=4,'请求项数超出技术容量');result[key]=[_text(x,1200) for x in value]
        elif key=='evidenceList':
            require(type(value) is list and len(value)<=40,'证据项数超出技术容量');result[key]=[_validate_data('item',x) for x in value]
        elif key in {'copyCount','evidenceCopyCount'}:
            require(value is None or type(value) is int and 1<=value<=30,'副本须为整数或留空');result[key]=value
        else:
            result[key]=_text(value,12000 if key=='factsReason' else 1200 if key=='purpose' else 300)
            if key.endswith('Date') and result[key]:
                require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',result[key]),'日期须为YYYY-MM-DD');date.fromisoformat(result[key])
            if key in {'acceptMediation','legalAid'}:require(result[key] in {'','是','否'},'本区选项不匹配')
            if key=='originalType':require(result[key] in {'','原件','复印件'},'原件或复印件选项不匹配')
    return result


class _OwnSlots(BaseModel):
    model_config=ConfigDict(extra='forbid')
    _slot_kind:ClassVar[str]='application'
    @model_validator(mode='before')
    @classmethod
    def own_slots(cls,value):return _validate_data(cls._slot_kind,value)


Text=Annotated[str,Field(strict=True,max_length=300)]
class EvidenceItem(_OwnSlots):
    _slot_kind='item'
    name:Text='';source:Text='';purpose:Annotated[str,Field(strict=True,max_length=1200)]='';originalType:Text='';pageCount:Text=''


ApplicationRequest=create_model('KunshanApplicationRequest',__base__=_OwnSlots,
    **{key:(Text,'') for key in sorted(APPLICATION_FIELDS-{'requests','factsReason','copyCount','evidenceCopyCount'})},
    requests=(list[Annotated[str,Field(strict=True,max_length=1200)]],Field(default_factory=list,max_length=4)),
    factsReason=(Annotated[str,Field(strict=True,max_length=12000)],''),
    copyCount=(Annotated[int,Field(strict=True,ge=1,le=30)]|None,None),
    evidenceCopyCount=(Annotated[int,Field(strict=True,ge=1,le=30)]|None,None))


class EvidenceRequest(_OwnSlots):
    _slot_kind='evidence'
    committeeName:Text='';caseNumber:Text='';submitDate:Text=''
    evidenceList:list[EvidenceItem]=Field(default_factory=list,max_length=40)


def fill_offline(kind,data,*,root):
    require(kind in ANNEX,'本区文书类型不匹配');source=parse_capture(root=root)
    t=next(t for t in source['templates'] if t['id']==ANNEX[kind]);raw=path_at(root,t['file']).read_bytes()
    doc=Document(BytesIO(raw));values=_validate_data(kind,data)
    if kind=='application':
        values={k:v for k,v in values.items() if v is not None};application_fill(doc,values)
    else:
        values['evidenceList']=[r for r in values.get('evidenceList',[]) if any(r.values())]
        if not values['evidenceList']:values['evidenceList']=[{k:'' for k in ITEM_FIELDS}]
        for row in values['evidenceList']:
            for key in ITEM_FIELDS:row.setdefault(key,'')
        evidence_fill(doc,values)
    return PreservedPackageDocument(doc,raw)


def fill_document(guide,template,kind,path,data,*,root):
    checked_adapter(guide,template,kind,root=root)
    require(Path(path).resolve()==path_at(root,template['file']),'传入原件路径不是昆山市自身附件')
    return fill_offline(kind,data,root=root)


# Own reviewed source reconstruction and Word slot maps, retained verbatim.
OWN_SLOTS={1:[('申请人','applicantName'),('性别','gender'),('出生日期','birthDate')],
 2:[('公民身份号码','idNumber'),('居住地址','idAddress')],
 3:[('其他证件类型','otherDocumentType'),('证件号码','otherDocumentNumber')],
 4:[('通讯地址','applicantMailingAddress'),('移动电话','phone')],
 5:[('是否接受调解','acceptMediation'),('是否法律援助','legalAid')],
 6:[('被申请人','respondentName'),('性质','respondentType')],
 7:[('注册地址（住所）','registeredAddress')],8:[('统一社会信用代码','socialCreditCode')],
 9:[('法定代表人或者主要负责人姓名','legalRepName'),('职务','legalRepPosition')],
 10:[('劳动者所在部门负责人','departmentHead'),('职务','departmentHeadPosition')],
 11:[('通讯地址','mailingAddress')],12:[('联系人','companyContact'),('移动电话','companyContactPhone')]}

def _source_guide(root):
    freeze_raw=path_at(root,FOLDER+'/SOURCE-FREEZE.json').read_bytes()
    require(sha256(freeze_raw).hexdigest()==FREEZE_SHA,'Own source freeze differs')
    freeze=json.loads(freeze_raw)
    require(freeze['region_code']=='320583' and freeze['source_id']==SOURCE_ID
            and freeze['service_code']==SERVICE and freeze['online_status']=='auth_required'
            and freeze['published'] is False,'Own source identity or boundary differs')
    for file,pin in freeze['files'].items():
        body=path_at(root,file).read_bytes()
        require(len(body)==pin['bytes'] and sha256(body).hexdigest()==pin['sha256'],'Frozen own source file differs')
    bindings=read_json(root,FOLDER+'/own-native-bindings.json')
    downloads=read_json(root,FOLDER+'/own-source-downloads.json')
    source_url=bindings['source_url']
    require(sha256(json.dumps(source_url,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]==SOURCE_ID,
            'Own guide source identity differs')
    captured=read_json(root,'reports/overnight-gap-closure-20261030/localities/kunshan/source-discovery/own-guide.json')
    fields={}
    for table in captured['tables']:
        for row in table:
            if len(row) in {2,4}:
                for i in range(0,len(row),2):fields[row[i]]=row[i+1]
    materials=[];templates=[]
    for index,material in enumerate(bindings['materials']):
        controls=material['controls'];blank=next(c for c in controls if c['kind']=='空白表格')
        url=re.search(r"downloadClyb\('([^']+)'",blank['handler']).group(1)
        annex=url.split('attachGuid=')[1]
        own=next(d for d in downloads if d.get('annex_id')==annex)
        require(own['source_url']==source_url and own['url']==url and own['status']==200,'Own blank binding differs')
        details={}
        for row in material['detail_fields']:
            for i in range(0,len(row)-1,2):details[row[i]]=row[i+1]
        materials.append({'id':annex,'name':material['name'],'paper_copies':material['paper_copies'],'details':details})
        templates.append({'id':annex,'region_code':'320583','material_id':annex,'official_kind':'blank',
            'source_url':source_url,'download_url':url,'file':FOLDER+'/'+own['file'],'sha256':own['sha256'],
            'bytes':own['bytes'],'can_generate':False,'candidate_document_types':[k for k,v in ANNEX.items() if v==annex],
            'content_role':'fillable_own_blank' if annex in ANNEX.values() else 'heading_only_copy_placeholder'})
    return {'province':'jiangsu','city':'苏州市','district':'昆山市','region_code':'320583',
        'source_id':SOURCE_ID,'source_url':source_url,'service_code':SERVICE,
        'service_name':'劳动人事争议仲裁申请','authority':'昆山市人力资源和社会保障局',
        'source_version':FREEZE_SHA,'verification_status':'source_verified_candidate_only',
        'fields':fields,'materials':materials,'templates':templates,
        'channel':{'raw_value':fields['办理形式'],'online_status':'auth_required',
            'observed_login_origin':'https://www.jszwfw.gov.cn','submission_verified':False},
        'candidate_adapter':ADAPTER,'can_generate':False,'published':False,
        'publication_status':'private_offline_candidate','Word_stage':'NOT_REVIEWED_BY_ROOT',
        'warnings':['只支持本区自身劳动者申请书单一被申请人及六列证据清单。',
                    '身份与证据复印件原件仅有标题，不提供填写生成。',
                    '网上办理已到官方登录及验证码边界；未登录、未提交申请。',
                    '源指南申请书4份与证据清单2份要求保留；原件副本栏须本人核对。',
                    '签名、提交人与接收人由本人或经办人手写；调解、法律援助不自动选择。']}

def written_date(value):
    if not value:return ''
    d=date.fromisoformat(value);return f'{d.year}年{d.month}月{d.day}日'

def application_fill(doc,data):
    require(len(doc.paragraphs)==118 and doc.paragraphs[0].text=='劳动人事争议仲裁申请书（劳动者申请）'
            and doc.paragraphs[59].text=='劳动人事争议仲裁申请书（用人单位申请）','Own application layout changed')
    # Drop employer form and source-metadata footer based on this original map.
    keep_body(doc,0,57);ps=list(doc.paragraphs)
    for index,slots in OWN_SLOTS.items():
        fill_label_slots(ps[index],[(label,data.get(key,'')) for label,key in slots],pad=False)
    if data.get('committeeName'):replace_span(ps[44],0,len(ps[44].text),data['committeeName'])
    if data.get('applicationDate'):replace_span(ps[48],0,len(ps[48].text),written_date(data['applicationDate']))
    for label,key in [('本申请书副本','copyCount'),('相关证据','evidenceCopyCount')]:
        match=re.search(re.escape(label)+r'(?P<blank>\s+)(?=份)',ps[51].text)
        require(match,'Own footer slot changed')
        if key in data:replace_span(ps[51],match.start('blank'),match.end('blank'),str(data[key]))
    for p in ps[13:20]:p._p.getparent().remove(p._p)
    fill_sections(doc,data)
    # A signature belongs with its date; its name is never filled automatically.
    for p in ps[43:48]:p.paragraph_format.keep_with_next=True
    ps[48].paragraph_format.keep_with_next=False
    for p in ps[43:49]:p.paragraph_format.keep_together=True
    remove_empty_edges(doc)

def evidence_fill(doc,data):
    require(len(doc.paragraphs)==9 and len(doc.tables)==1 and len(doc.tables[0].rows)==13
            and len(doc.tables[0].columns)==6,'Own evidence layout changed')
    table=doc.tables[0];items=data['evidenceList'];rows=list(table.rows)[1:]
    require([c.text for c in table.rows[0].cells]==['序号','证据名称','证据来源','证  明  内  容','原件或复印件','页数'],
            'Own evidence columns changed')
    header_properties=table.rows[0]._tr.get_or_add_trPr()
    if header_properties.find(qn('w:tblHeader')) is None:header_properties.append(OxmlElement('w:tblHeader'))
    while len(rows)<len(items):
        node=deepcopy(rows[-1]._tr);rows[-1]._tr.addnext(node);rows.append(_Row(node,table))
    for i,(row,item) in enumerate(zip(rows,items),1):
        properties=row._tr.get_or_add_trPr()
        if properties.find(qn('w:cantSplit')) is None:properties.append(OxmlElement('w:cantSplit'))
        for height in row._tr.iter(qn('w:trHeight')):
            if height.get(qn('w:hRule'))=='exact':height.set(qn('w:hRule'),'atLeast')
        for cell,value in zip(row.cells,[str(i),item['name'],item['source'],item['purpose'],item['originalType'],item['pageCount']]):set_cell_text(cell,value)
    for row in rows[len(items):]:table._tbl.remove(row._tr)
    if data.get('committeeName'):replace_span(doc.paragraphs[0],0,len(doc.paragraphs[0].text),data['committeeName'])
    if data.get('caseNumber'):replace_span(doc.paragraphs[3],0,len(doc.paragraphs[3].text),data['caseNumber'])
    if data.get('submitDate'):
        p=doc.paragraphs[5];start=p.text.index('提交时间：')+len('提交时间：')
        replace_span(p,start,len(p.text),written_date(data['submitDate']))
    remove_empty_edges(doc)
