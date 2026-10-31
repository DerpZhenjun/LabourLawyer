"""Versioned technical field contracts for exact, already bound local documents.

This describes editable slots and platform capacity, never arbitration rules.
No store, model inference, template mutation, or province fallback occurs here.
"""
from copy import deepcopy
from datetime import date
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

from regional_adapters import checked_reference_adapter
from regional_public_provenance import public_evidence
from regional_fujian_oct31h import ADAPTER as FJH, form_fields as fujian_h_fields, defaults as fujian_h_defaults
from regional_fujian_oct31i import ADAPTER as FJI, schema_descriptor as fujian_i_schema
from regional_fujian_oct31j import ADAPTER as FJJ, schema_descriptor as fujian_j_schema
from regional_fujian_oct31k import ADAPTER as FJK, schema_descriptor as fujian_k_schema

ROOT=Path(__file__).resolve().parents[1]
EJS='jiangsu_own_blank_oct29e_v1'
FJS='jiangsu_own_blank_oct30f_v1'
GJS='jiangsu_kunshan_own_blank_oct31g_v1'
EXACT_JS={EJS,FJS,GJS}
ZJ_OWN={'zhejiang_own_worker_oct29d_v1','zhejiang_own_worker_oct29e_v1','zhejiang_chunan_own_worker_oct30_v1'}
HN={'hunan_own_legacy_worker_oct29b_v1','hunan_own_legacy_worker_oct29c_v1'}
JS_BLANK={'jiangsu_xishan_blank_v1','jiangsu_own_blank_oct29_v1',
          'jiangsu_own_blank_oct29c_v1','jiangsu_own_blank_oct29d_v1'}
REFERENCE={'sichuan_combined_reference_v1','tianfu_reference_v1'}
NINGBO='zhejiang_ningbo_own_blank_oct29_v1'
FEIDONG='anhui-feidong-official-application-20261029'
SUPPORTED_ADAPTERS=frozenset(EXACT_JS|{NINGBO,FEIDONG,FJH,FJI,FJJ,FJK}|ZJ_OWN|HN|JS_BLANK|REFERENCE)
PUBLIC_PROOF_ADAPTERS=frozenset(EXACT_JS|{NINGBO,FEIDONG,FJH,FJI,FJJ,FJK,'jiangsu_own_blank_oct29c_v1','jiangsu_own_blank_oct29d_v1'}|ZJ_OWN|HN)

JS_APP=('applicantName birthDate gender idNumber idAddress otherDocumentType otherDocumentNumber '
        'applicantMailingAddress phone acceptMediation legalAid respondentName respondentType '
        'registeredAddress socialCreditCode legalRepName legalRepPosition departmentHead departmentHeadPosition '
        'mailingAddress companyContact companyContactPhone committeeName applicationDate copyCount evidenceCopyCount '
        'requests factsReason').split()
ZJ_APP=('applicantName birthDate gender nationality idNumber phone householdType idAddress respondentName '
        'socialCreditCode registeredAddress mailingAddress workAddress legalRepName legalRepPhone legalRepPosition '
        'companyContact companyContactPhone committeeName applicationDate copyCount requests factsReason').split()
HN_APP=('applicantName gender birthDate occupation nationality idAddress postalCode phone workUnit '
        'workUnitPostalCode workUnitPhone respondentName registeredAddress respondentPostalCode legalRepName '
        'legalRepPosition legalRepPhone hrContactName hrContactPosition hrContactPhone thirdParty committeeName '
        'applicationDate copyCount requests factsReason evidenceList').split()
SAMPLE_APP=('applicantName gender nationality birthDate idNumber idAddress currentAddress phone '
            'applicantMailingAddress applicantPostalCode respondentName legalRepName legalRepPosition '
            'registeredAddress companyContactPhone factsReason requests committeeName').split()
FD_PARTIES=['applicant_lines','agent_lines','respondent_lines','representative_lines']
JS_ITEM=['name','source','purpose','originalType','pageCount']
ZJ_ITEM=['name','pageCount','source','purpose']
SAMPLE_ITEM=['name','itemCount','pageCount','originalType','purpose','notes']
HOUSEHOLD_CHOICES=['本省非农业户口','本省农业户口','港澳台人员','外籍人员']
LABELS=dict(applicantName='申请人姓名',birthDate='出生日期',gender='性别',nationality='民族',idNumber='身份证明号码',
    idAddress='申请人住所',otherDocumentType='其他证件类型',otherDocumentNumber='其他证件号码',
    applicantMailingAddress='申请人通讯地址',phone='联系电话',acceptMediation='是否接受调解',legalAid='是否法律援助',
    respondentName='被申请人名称',respondentType='被申请人性质',registeredAddress='被申请人住所',
    socialCreditCode='统一社会信用代码',legalRepName='法定代表人或主要负责人',legalRepPosition='负责人职务',
    departmentHead='劳动者所在部门负责人',departmentHeadPosition='部门负责人职务',mailingAddress='被申请人通讯地址',
    companyContact='单位联系人',companyContactPhone='单位联系人电话',committeeName='提交的仲裁委员会',
    applicationDate='申请日期',copyCount='副本份数',evidenceCopyCount='申请书所附证据副本份数',requests='请求事项',
    factsReason='事实与理由',householdType='户口类型',workAddress='实际工作地址',legalRepPhone='负责人联系电话',
    occupation='职业',postalCode='住所邮编',workUnit='工作单位',workUnitPostalCode='工作单位邮编',
    workUnitPhone='工作单位电话',respondentPostalCode='被申请人邮编',hrContactName='人力资源管理部门负责人',
    hrContactPosition='人力资源负责人职务',hrContactPhone='人力资源负责人电话',thirdParty='第三人',
    currentAddress='现住址',applicantPostalCode='申请人邮编',applicant_lines='申请人分行信息',agent_lines='委托代理人分行信息',
    respondent_lines='被申请人分行信息',representative_lines='法定代表人分行信息',facts='事实和理由',
    caseNumber='案号',submitDate='提交日期',evidenceList='证据内容',name='证据名称',source='证据来源',purpose='证明内容',
    originalType='原件或复印件',pageCount='页数',itemCount='材料件数',notes='备注')


def _root(root):
    if isinstance(root,str) and not root.strip():raise ValueError('必须明确有效的契约根目录')
    value=Path(ROOT if root is None else root).resolve()
    if not value.is_dir():raise ValueError('契约根目录不存在')
    return value


def _own_original(guide,template,adapter,root):
    """Older checked adapters have historical implicit roots; never borrow them."""
    filename=template.get('file');checksum=template.get('sha256')
    if not isinstance(filename,str) or not filename or not isinstance(checksum,str):raise ValueError('缺少本区原件校验信息')
    relative=Path(filename);path=(root/relative).resolve()
    if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(root):raise ValueError('本区原件路径超出指定根目录')
    try:actual=hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:raise ValueError('指定根目录缺少本区原件') from exc
    if actual!=checksum:raise ValueError('指定根目录的本区原件字节已变化')
    if adapter in PUBLIC_PROOF_ADAPTERS and public_evidence(guide,root) is None:raise ValueError('指定根目录缺少本区完整公开来源证明')


def _resolve(schema,value):
    if '$ref' in value:
        return schema['$defs'][value['$ref'].rsplit('/',1)[-1]]
    return value


def _limit(prop,name):
    values=[prop[name]] if name in prop else []
    values += [v[name] for v in prop.get('anyOf',[]) if name in v]
    return min(values) if values else None


def _fields(adapter,kind,schema):
    if adapter==FJH:return fujian_h_fields(kind)
    if adapter==FEIDONG:
        if kind!='application':raise ValueError('肥东没有已核验独立证据填写槽')
        keys=FD_PARTIES+['requests','facts'];item_keys=[]
    elif adapter in HN:
        if kind!='application':raise ValueError('湖南附随证据属于劳动者申请书，不是独立证据清单')
        keys=HN_APP;item_keys=['name','source','purpose']
    elif kind=='application':
        keys=JS_APP if adapter in JS_BLANK|EXACT_JS else ZJ_APP if adapter in ZJ_OWN|{NINGBO} else SAMPLE_APP
        item_keys=[]
    elif adapter in REFERENCE:
        keys=['evidenceList'];item_keys=SAMPLE_ITEM
    else:
        keys=['committeeName','caseNumber','submitDate','evidenceList']
        if adapter in ZJ_OWN:keys.insert(2,'copyCount')
        item_keys=ZJ_ITEM if adapter in ZJ_OWN|{NINGBO} else JS_ITEM
    properties=schema['properties'];result=[]
    for key in keys:
        if key not in properties:raise ValueError('已绑定填写槽不在当前请求模型中：'+key)
        prop=_resolve(schema,properties[key]);field={'key':key,'label':LABELS[key],'type':'text','nullable':False}
        if key=='copyCount':field['label']='申请书副本份数' if kind=='application' else '证据清单份数'
        if key=='idAddress':
            field['label']='户籍所在地' if adapter in REFERENCE else '申请人居住地址' if adapter in JS_BLANK|EXACT_JS else '住所' if adapter in HN else '身份证住址'
        if key=='idNumber' and adapter in JS_BLANK|EXACT_JS:field['label']='公民身份号码'
        if key=='evidenceList' and adapter in HN:field['label']='申请书附随证据'
        if key=='evidenceList':
            item=_resolve(schema,prop['items']);children=[]
            for child in item_keys:
                node=_resolve(schema,item['properties'][child]);entry={'key':child,'label':LABELS[child],'type':'text','nullable':False}
                maximum=_limit(node,'maxLength')
                if maximum is not None:entry['maxLength']=maximum
                if adapter in REFERENCE|{GJS} and child=='originalType':entry['choices']=['原件','复印件']
                children.append(entry)
            field.update(type='object_list',maxItems=prop['maxItems'],fields=children)
        elif key=='requests' or key in FD_PARTIES:
            field.update(type='text_list',maxItems=prop['maxItems'])
            maximum=_limit(prop.get('items',{}),'maxLength')
            if maximum is None and key=='requests' and adapter not in HN:maximum=1200
            if key in FD_PARTIES:maximum=50
            if maximum is not None:field['maxLength']=maximum
        elif key in {'copyCount','evidenceCopyCount'}:
            field.update(type='copies',integer=adapter not in HN,nullable=adapter not in HN)
            if adapter in HN:field['maxLength']=160
            else:field.update(min=1,max=30,allow_leading_zero=adapter in ZJ_OWN)
        else:
            maximum=_limit(prop,'maxLength')
            # Existing generic date slots and UI input elements have no model
            # bound; publish a conservative editable text capacity, not a rule.
            field['maxLength']=maximum if maximum is not None else 300
            if adapter in EXACT_JS and key in {'birthDate','applicationDate','submitDate'}:field['format']='iso-date'
            if adapter==GJS and key in {'acceptMediation','legalAid'}:field['choices']=['是','否']
            if adapter in ZJ_OWN and key=='householdType':field['choices']=list(HOUSEHOLD_CHOICES)
            if adapter in JS_BLANK and key in {'acceptMediation','legalAid'}:field['choices']=['是','否']
        result.append(field)
    return result


def _empty(field):
    if field['type']=='object_list':return [{f['key']:_empty(f) for f in field['fields']}]
    if field['type']=='text_list':return ['']
    return ''


def _contract_id(value):
    body={key:value[key] for key in ['schema_version','context','fields','defaults','policy']}
    return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')).hexdigest()


@lru_cache(maxsize=1)
def _wide_ranges():
    """The same runtime Unicode W/F table used by the existing layout filler."""
    ranges=[];start=None
    for point in range(0x110000):
        wide=unicodedata.east_asian_width(chr(point)) in ('W','F')
        if wide and start is None:start=point
        elif not wide and start is not None:ranges.append((start,point-1));start=None
    if start is not None:ranges.append((start,0x10ffff))
    return tuple(ranges)


def build_form_contract(guide,template,kind,root=None):
    """Describe only this supplied current guide/template after the own check."""
    root=_root(root)
    if not isinstance(guide,dict) or not isinstance(template,dict) or kind not in {'application','evidence'}:raise ValueError('地区或文书类型无效')
    identity=['province','city','district','region_code','source_id']
    if any(not isinstance(guide.get(k),str) or not guide[k].strip() for k in identity):raise ValueError('地区来源尚未核验')
    if type(guide.get('version')) is not int or guide['version']<1:raise ValueError('缺少当前来源版本')
    if guide.get('verification_status') not in {'verified','partial','conflict'}:raise ValueError('地区指南尚未核验')
    originals=[t for t in guide.get('templates',[]) if isinstance(t,dict) and t.get('id')==template.get('id')]
    if len(originals)!=1 or originals[0]!=template or template.get('can_generate') is not True or kind not in template.get('document_types',[]):raise ValueError('本区没有已核验的可生成附件')
    if template.get('official_kind') not in {'blank','sample'}:raise ValueError('附件没有已核验填写类别')
    adapter=template.get('adapter')
    if adapter not in SUPPORTED_ADAPTERS:raise ValueError('适配器尚无已核验字段契约')
    _own_original(guide,template,adapter,root)
    if checked_reference_adapter(guide,template,kind,root=root)!=adapter:raise ValueError('本区适配器身份不匹配')
    from routes.regional_guides import generation_request_model
    schema=generation_request_model(adapter,kind).model_json_schema()
    own_schema=(fujian_k_schema(guide['region_code'],kind) if adapter==FJK else
                fujian_j_schema(guide['region_code'],kind) if adapter==FJJ else
                fujian_i_schema(guide['region_code'],kind) if adapter==FJI else None)
    fields=deepcopy(own_schema['fields']) if own_schema else _fields(adapter,kind,schema)
    context={k:guide[k] for k in identity};context.update(version=guide['version'],template_id=template['id'],kind=kind,
        mode='blank' if template['official_kind']=='blank' else 'reference_adaptation',adapter=adapter)
    policy={'unknown_fields':'reject','invalid_xml':'reject','capacity_is_official_requirement':False,'text_controls':'xml',
            'trim_text':adapter not in HN|ZJ_OWN|EXACT_JS}
    if adapter==GJS:policy['trim_text']=True
    if adapter==FJH:policy.update(text_controls='newline_only',trim_text=True)
    if adapter in JS_BLANK|REFERENCE|{NINGBO} and kind=='application':policy['text_list_total_max_length']={'requests':1200}
    if adapter==FEIDONG:
        policy['text_controls']='newline_only'
        policy['layout_limits']={'unicode_version':unicodedata.unidata_version,'wide_ranges':[list(x) for x in _wide_ranges()],
            'fields':{**{key:{'line_widths':[40,50],'no_newlines':True,'max_lines':2,'trim':True} for key in FD_PARTIES},
                      'requests':{'first_width':44,'later_width':56,'max_lines':9,'join':'\n','trim':True},
                      'facts':{'first_width':56,'later_width':56,'max_lines':10,'trim':True}}}
    result={'schema_version':1,'context':context,'fields':fields,'defaults':{f['key']:_empty(f) for f in fields},'policy':policy}
    if adapter==FJH:result['defaults']=fujian_h_defaults(kind)
    if own_schema:
        context.update(schema_id=own_schema['schema_id'],schema_version=own_schema['schema_version'],
            source_version=own_schema['source_version'],template_sha256=template['sha256'],template_version='sha256:'+template['sha256'])
        result.update(defaults=deepcopy(own_schema['defaults']),policy=deepcopy(own_schema['policy']))
    result['contract_id']=_contract_id(result)
    return result


def _text(value,field):
    if not isinstance(value,str):raise ValueError(field['label']+'须填写文字')
    if any(not (c in '\t\n\r' or 0x20<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff) for c in value):raise ValueError(field['label']+'含无效XML字符')
    if field.get('maxLength') is not None and len(value)>field['maxLength']:raise ValueError(field['label']+'超出技术容量')
    if value and field.get('choices') is not None and value not in field['choices']:raise ValueError(field['label']+'不是本表可填写选项')
    if value and field.get('format')=='iso-date':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):raise ValueError(field['label']+'须为有效YYYY-MM-DD日期')
        try:date.fromisoformat(value)
        except ValueError as exc:raise ValueError(field['label']+'不是有效日历日期') from exc
    return value


def _value(value,field,adapter):
    kind=field['type']
    if value is None:
        if field.get('nullable'):return None
        raise ValueError(field['label']+'不能为null')
    if kind=='text':return _text(value,field)
    if kind=='copies':
        if field.get('integer') is False:
            if isinstance(value,str):return _text(value,field)
            if type(value) is int and len(str(value))<=field.get('maxLength',160):return value
            if type(value) is float and math.isfinite(value) and len(str(value))<=field.get('maxLength',160):return value
            raise ValueError(field['label']+'须为文字或有限数值')
        if value=='':return '' if adapter in ZJ_OWN else None
        if type(value) is int:number=value
        elif isinstance(value,str) and re.fullmatch(r'[0-9]+',value):
            if not field.get('allow_leading_zero') and len(value)>1 and value.startswith('0'):raise ValueError('副本份数不接受前导零')
            significant=value.lstrip('0') or '0'
            if len(significant)>2:raise ValueError('副本份数超出技术容量')
            number=int(significant)
        else:raise ValueError('副本份数须留空或填写整数')
        if not field['min']<=number<=field['max']:raise ValueError('副本份数超出技术容量')
        return value if adapter in ZJ_OWN else number
    if kind in {'text_list','object_list'}:
        if not isinstance(value,list) or len(value)>field['maxItems']:raise ValueError(field['label']+'列表类型或项数无效')
        if kind=='text_list':return [_text(v,field) for v in value]
        return [_object(v,field['fields'],adapter) for v in value]
    raise ValueError('未知字段类型')


def _object(value,fields,adapter):
    allowed={f['key']:f for f in fields}
    if not isinstance(value,dict) or any(not isinstance(k,str) or k not in allowed for k in value):raise ValueError('填写数据含本表没有槽位的字段')
    return {k:_value(v,allowed[k],adapter) for k,v in value.items()}


def validate_contract_data(contract,data):
    """Reject unsupported data before model defaults/coercion can discard it.

Only the declared copy normalization occurs here; legacy generation retains its
own documented trimming after this validator. Input objects are never mutated.
"""
    try:valid=isinstance(contract,dict) and type(contract.get('schema_version')) is int and contract['schema_version']==1 and contract.get('contract_id')==_contract_id(contract)
    except (KeyError,TypeError,ValueError):valid=False
    if not valid:raise ValueError('填写契约已改变或无效')
    adapter=contract['context']['adapter'];result=_object(data,contract['fields'],adapter)
    for key,limit in contract['policy'].get('text_list_total_max_length',{}).items():
        if len('\n'.join(result.get(key,[])))>limit:raise ValueError('请求事项总文本超出既有编辑容量')
    if adapter==FEIDONG:
        from regional_anhui_oct29 import _width,_clean,_wrap
        for key in FD_PARTIES:
            for index,value in enumerate(result.get(key,[])):
                if '\n' in value or _width(_clean(value))>(40 if index==0 else 50):raise ValueError('当事人分行信息超出本表显示宽度')
        if len(_wrap('\n'.join(result.get('requests',[])),44,56))>9 or len(_wrap(result.get('facts','')))>10:raise ValueError('本表请求或事实超过既有行数容量')
    return deepcopy(result)
