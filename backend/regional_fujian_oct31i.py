"""Unregistered I provider: independent safe public projections, offline != stage.

No raw signed response or private candidate directory is a runtime dependency.
"""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile
from lxml import etree as E
from regional_guides import digest,region_key

ROOT=Path(__file__).resolve().parents[1]
ADAPTER='fujian_taijiang_cangshan_own_blank_oct31i_v1'
SOURCE_BASE='reports/overnight-gap-closure-20261030/localities/fujian-i-source-projection'
REGIONS={
 '350103':dict(folder='taijiang-350103',district='台江区',source_id='dcf9b71dee1c1cb61a3af637',copies=2,
    manifest_sha256='c607b8c474e722911789ed7c80a0ed6b3e1e1c8dc0aa6fdd1ad78e09cd157368',
    service='11350103003616417P400201430200201',authority='福州市台江区人力资源和社会保障局',
    source_url='https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=442BD04C55F500427A01682CD4325DC4&infoType=1',
    material_ids={'application':'1D19C0BB7B7D32E5FD97087F41BF8997','evidence':'95BFC814AC83608699C37332D64064B1'}),
 '350104':dict(folder='cangshan-350104',district='仓山区',source_id='9ab36db8d0ff985d9617a944',copies=1,
    manifest_sha256='3894d8243227389134ac0fbff5524deeee37c30f03295685cc1897eb3bf5f2e2',
    service='113501040584075247400201430200201',authority='福州市仓山区人力资源和社会保障局',
    source_url='https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=C305CB8E72A47E753A26686C733D3559&infoType=1',
    material_ids={'application':'DB3A5171F298FBC28D4A42816C7655B2','evidence':'819E2B1CD8F2F6F2189AA531692FE3F1'})}
SUPPORTED=frozenset(REGIONS)
KINDS=('application','evidence')
SPECS={'application':dict(id='F4048D8C91E2FF882AC6C62CC0EC4D86',file='application-own-format-public-retrieval.docx',sha256='093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365'),
       'evidence':dict(id='CC300F5D9DD5DC404D65C68116D50C55',file='evidence-list-own-format-public-retrieval.docx',sha256='d70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815')}
QA_REPORT='reports/overnight-gap-closure-20261030/localities/fujian-i/integration-qa-v1'
WORD_MANIFEST=QA_REPORT+'/WORD-MANIFEST.json'
WORD_SHA='7228ec3f5d170021ff4df69edc9a883a284ec42109633413278b02bf4c47eaf9'
STAGE_RECEIPT=QA_REPORT+'/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT=QA_REPORT+'/FINAL-BROWSER-QA.json'
STAGE_SHA256='d51d75f69935039d605a5627794b2ae280df1c8bc61bf54b449874d56dc16c6e'
PUBLICATION_SHA256='60d0a9ec2b141a7704c5b72c9127fbbbdb2ca5f4c0f667dca50f4cee96690319'
APP_FIELDS=('applicantName','agentName','respondentName','requests','factsReason')
ITEM_FIELDS=('name','pageCount','originalType','purpose','pageRange')
_METADATA=frozenset({'version','region_id','content_hash'})
_FAILURES=(ValueError,OSError,KeyError,TypeError,StopIteration,AttributeError)
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
N={'w':W}


def require(ok,message):
    if not ok:raise ValueError(message)


def exact(a,b):
    if type(a) is not type(b):return False
    if isinstance(b,dict):return a.keys()==b.keys() and all(exact(a[k],v) for k,v in b.items())
    if isinstance(b,list):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b


def path_at(root,relative):
    require(root is not None and str(root).strip(),'必须明确I自身公开证据根目录')
    root=Path(root).resolve();rel=Path(relative)
    require(not rel.is_absolute() and not rel.drive and '..' not in rel.parts,'自身公开相对路径无效')
    path=(root/rel).resolve();require(path.is_relative_to(root) and path.relative_to(root).as_posix()==rel.as_posix(),'公开证据路径越界或链接替换')
    return path


def _bytes(root,relative):
    try:return path_at(root,relative).read_bytes()
    except OSError as exc:raise ValueError('明确公开根目录缺少I自身证据') from exc


def _read(root,relative):return json.loads(_bytes(root,relative))


def _meta(code):
    require(type(code) is str and code in REGIONS,'仅支持I两区自身地区编码');return REGIONS[code]


def _sources(root,code):
    meta=_meta(code);folder=SOURCE_BASE+'/'+meta['folder'];raw=_bytes(root,folder+'/SOURCE-PROJECTION-MANIFEST.json')
    require(sha256(raw).hexdigest()==meta['manifest_sha256'],'I自身公开投影版本变化');m=json.loads(raw)
    expected={'province':'fujian','city':'福州市','district':meta['district'],'region_code':code,'source_id':meta['source_id'],
        'source_url':meta['source_url'],'derived_sanitized_projection':True,'raw_api_response_included':False,
        'parent_raw_response_is_public_artifact':False,'guide_status':'partial','committee_full_name':None,'can_generate':False,
        'published':False,'stage_approval':False,'publication_approval':False,
        'copy_literals':[f'原件份数{meta["copies"]}份',f'原件份数{meta["copies"]}份',f'复印件份数{meta["copies"]}份']}
    require(all(k in m and exact(m[k],v) for k,v in expected.items()) and digest(meta['source_url'])[:24]==meta['source_id'],'I自身来源身份或边界变化')
    require(type(m['files']) is dict and len(m['files'])==13,'I公开投影文件数变化')
    for name,pin in m['files'].items():
        data=_bytes(root,folder+'/'+name)
        require(type(pin['bytes']) is int and len(data)==pin['bytes'] and sha256(data).hexdigest()==pin['sha256'],'I自身公开投影文件变化')
    bindings=_read(root,folder+'/own-official-bindings.json');rows=_read(root,folder+'/api-own-attachment-metadata.json')['attachments']
    require(bindings['service_code']==meta['service'] and bindings['authority']==meta['authority'] and bindings['source_url']==meta['source_url'],'I自身机构、事项或指南变化')
    for kind,spec in SPECS.items():
        own=next(r for r in bindings['attachments'] if r['file']==spec['file'])
        row=next(r for r in rows if r['file_id']==spec['id'])
        require(own['file_id']==spec['id'] and own['material_id']==meta['material_ids'][kind] and own['sha256']==spec['sha256']
            and own['official_type']=='format' and own['source_url']==meta['source_url'] and row['type']=='1'
            and row['material_id']==meta['material_ids'][kind] and '示例' not in row['name'],'I自身空白与材料绑定变化')
        require(m['files'][spec['file']]['sha256']==spec['sha256'],'I自身原件字节变化')
    return m


def source_files(root,code=None):
    codes=[code] if code is not None else list(REGIONS);files=[]
    for c in codes:
        m=_sources(root,c);folder=SOURCE_BASE+'/'+REGIONS[c]['folder']
        files.extend([folder+'/SOURCE-PROJECTION-MANIFEST.json',*[folder+'/'+n for n in m['files']]])
    if code is None:
        raw=_bytes(root,SOURCE_BASE+'/BATCH-PROJECTION-INDEX.json')
        require(sha256(raw).hexdigest()=='dfa8c8039addf7953313fb49bdfe32af6e381d4710020e90ca068fe971eceb90','I公开批次投影变化')
        files.append(SOURCE_BASE+'/BATCH-PROJECTION-INDEX.json')
    return files


def _word_manifest(root,code=None):
    raw=_bytes(root,WORD_MANIFEST);require(sha256(raw).hexdigest()==WORD_SHA,'I公开Word证据清单变化');m=json.loads(raw)
    require(m['generated_pages']==22 and m['original_pages']==6 and m['word_documents']==8 and m['fictional_fixtures']==8
        and m['stage_approved'] is False and m['can_publish'] is False and m['browser_qa']=='NOT_RUN','I Word证据阶段变化')
    require(type(m['files']) is list and len(m['files'])==45 and len({r['path'] for r in m['files']})==45,'I公开Word证据不完整')
    require(m['new_safe_envelope_parity']=='AUTHOR_VERIFIED_COMPLETE_BYTES_AND_ZIP_MEMBERS_EQUAL'
        and m['safe_source_word_parity_sha256']=='5a91c9e65de99be657b43dca1997725f00b1acebde4f2bf21c8577dd2cebdcb5','I新公开来源Word字节一致性证据变化')
    expected=[{'region_code':c,'source_id':v['source_id'],'source_projection_sha256':v['manifest_sha256'],'service_code':v['service']} for c,v in REGIONS.items()]
    require(exact(m['identities'],expected),'I Word证据自身投影身份变化')
    for row in m['files']:
        codes=[row['region_code']] if 'region_code' in row else row.get('region_codes')
        require(type(codes) is list and codes and all(c in REGIONS for c in codes) and row['path'].startswith(QA_REPORT+'/'),'I Word证据范围变化')
        if code is None or code in codes:
            data=_bytes(root,row['path']);require(type(row['bytes']) is int and len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256'],'I自身Word证据文件变化')
    return m


def parse_capture(code,*,root):
    meta=_meta(code);m=_sources(root,code);folder=SOURCE_BASE+'/'+meta['folder'];capture=folder+'/own-guide-native-dom.json';dom=_read(root,capture)
    require(dom['url']==meta['source_url'],'I自身原生指南变化');fields={}
    def field(label,value,pointer,source_label=None):
        captured=value;value=value.strip()
        return {'raw_value':value,'normalized_value':value,'captured_value':captured,'source_label':source_label or label,'source_url':meta['source_url'],
            'capture_file':capture,'capture_sha256':m['files']['own-guide-native-dom.json']['sha256'],'captured_at':dom['captured_at'],
            'source_pointer':pointer,'region_code':code,'collected_at':dom['captured_at'],'verified_at':dom['captured_at'],'verification_status':'verified'}
    for row in dom['tables'][1]:
        if len(row)==2 and all(type(v) is str for v in row):fields[row[0].rstrip('：:').strip()]=field(row[0],row[1],'tables[1]',row[0])
    for display,source in {'咨询方式':'联系电话','服务对象':'申报对象','必须到现场原因':'必须现场办理原因','承诺办结时限':'承诺时限','法定办结时限':'法定时限'}.items():
        if source in fields:fields[display]=deepcopy(fields[source])
    for label,pattern,pointer in [('到办事现场次数',r'服务承诺到现场次数\n([^\n]+)','text/service_commitment_visits'),
        ('是否收费',r'\n收费情况\n是否收费：[\t ]*([^\n]+)','text/fee_section')]:
        found=re.search(pattern,dom['text'])
        if found:fields[label]=field(label,found.group(1),pointer)
    window=re.search(r'窗口办理\n办理时间：([^\n]+)\n办理地点：([^\n]+)\n',dom['text'])
    if window:
        for label,value in zip(('办理时间','办理地点'),window.groups()):fields[label]=field(label,value,'text/window_service_block',label+'：')
    require(fields['实施主体']['raw_value']==meta['authority'] and fields['业务办理项编码']['raw_value']==meta['service'],'I自身正文身份变化')
    require(not re.search(r'(?:福州市)?'+re.escape(meta['district'])+r'劳动(?:人事)?争议仲裁委员会',dom['text']),'I无完整委员会来源，须独立重审')
    bindings=_read(root,folder+'/own-official-bindings.json');materials=[]
    for i,item in enumerate(dom['materials']):
        details={r[0]:r[1] for r in dom['tables'][2+i] if len(r)==2};name=item['header'].splitlines()[-1]
        records=[r for r in bindings['attachments'] if r['file'].startswith(('application-','evidence-list-','evidence-material-')[i])]
        material_id=records[0]['material_id'];copies=re.findall(r'(?:原件|复印件)份数(\d+)份',item['text'])
        require(copies==[str(meta['copies'])],'I自身材料份数原文变化')
        original_type=re.search(r'材料类型：([^\n]+)',details['材料要求']).group(1).strip()
        materials.append({'id':material_id,'name':name,'required':details.get('材料必要性',''),'format':details.get('材料形式',''),'copies':meta['copies'],
            'paper_copies':meta['copies'],'copies_source_literal':m['copy_literals'][i],'copies_are_source_metadata':True,
            'original_copy':original_type,'material_type':original_type,'official_badges':[],
            'attachment_labels':['格式文本','示范文本'],'purpose':'','details':details,'instructions':details.get('填报须知',''),
            'source_url':meta['source_url'],'capture_file':capture,'capture_sha256':m['files']['own-guide-native-dom.json']['sha256']})
    templates=[]
    for row in bindings['attachments']:
        kind=next((k for k,v in SPECS.items() if row['file']==v['file']),None)
        reference=row['content_role']=='scanning_instructions_only';sample=row['official_type']=='sample'
        templates.append({'id':row['file_id'],'annex_id':row['file_id'],'region_code':code,'material_id':row['material_id'],
            'official_kind':'sample' if sample else 'reference' if reference else 'blank','original_name':row['official_label'],
            'file_type':'docx','source_url':meta['source_url'],'download_url':row['public_download_url'],'download_status':'downloaded',
            'document_types':[],'can_generate':False,'file':folder+'/'+row['file'],'sha256':row['sha256'],'bytes':row['bytes'],
            'content_role':'scanning_instructions_only' if reference else 'official_sample_contents_not_visually_reviewed' if sample else 'fillable_own_blank',
            'public_release_status':'source_only_no_generation_approval','sample_contents_verified':False})
    boundary=_read(root,folder+'/online-boundary.json')
    require(boundary['boundary']=='Minzhengtong_APP_scan_login_required' and all(boundary[k] is False for k in ['login_attempted','qr_scanned','application_submitted']),'I原生登录边界变化')
    return {'province':'fujian','province_name':'福建省','city':'福州市','district':meta['district'],'region_code':code,
        'source_id':meta['source_id'],'source_url':meta['source_url'],'service_code':meta['service'],'service_name':'劳动人事争议仲裁申请',
        'authority':meta['authority'],'source_title':'劳动人事争议仲裁申请','source_type':'own_official_guide_derived_safe_projection',
        'source_version':meta['manifest_sha256'],'official_version':'','verification_status':'partial','guide_status':'partial',
        'collected_at':dom['captured_at'],'verified_at':dom['captured_at'],'fields':fields,'sections':{'本区公开办事指南原文':dom['text']},
        'materials':materials,'templates':templates,'committee_full_name':None,'committee_autofill_allowed':False,
        'can_generate':False,'published':False,'publication_status':'source_only','sample_contents_verified':False,
        'attachment_counts':{'observed':6,'format_bytes_retrieved':3,'sample_contents_retrieved':3},
        'native_format_download_completion':'not_asserted_public_bytes_retrieved_independently',
        'channel':{'raw_value':fields.get('办理形式',{}).get('raw_value',''),'online_status':'auth_required','entry_url':None,
            'entry_check':{'status':'auth_required'},'online_boundary_file':folder+'/online-boundary.json','submission_verified':False},
        'evidence':{'capture_file':capture,'capture_sha256':m['files']['own-guide-native-dom.json']['sha256'],
            'source_projection':folder+'/SOURCE-PROJECTION-MANIFEST.json','source_projection_sha256':meta['manifest_sha256']},
        'warnings':['指南仍为部分核实；无来源字段显示待核实。','官网受理后5个工作日是自身受理审查原文，不是仲裁实体裁决期限。',
            '自身材料份数只作来源信息保留，副本及具体提交要求须本人核对；不会自动填写法律份数。',
            '官方示范文件内容虽已取得，尚未独立视觉审核，不用于填写事实或作为空白生成。',
            '证据材料参考文件为扫描上传说明，不可填写生成。','没有明确自身完整委员会名称，委员会前缀、签名、日期均留空。',
            '网上入口到闽政通APP扫码登录止，未登录、未扫码、未提交。']}


def _binding(g,t,kind):
    return {'adapter':ADAPTER,'kind':kind,'annex_id':t['id'],'source_file':t['file'],'source_sha256':t['sha256'],
        'source_url':t['source_url'],'region_code':g['region_code'],'source_id':g['source_id'],'source_version':g['source_version']}


def prepare_candidate(code,*,root):
    """Offline only. Public checked entry points deliberately do not accept this."""
    g=parse_capture(code,root=root);_word_manifest(root,code)
    g.update(can_generate=True,generation_adapter=ADAPTER,publication_status='unregistered_offline_candidate',offline_candidate=True)
    for kind,spec in SPECS.items():
        t=next(t for t in g['templates'] if t['id']==spec['id'] and t['official_kind']=='blank')
        t.update(can_generate=True,document_types=[kind],adapter=ADAPTER,generation_adapter=ADAPTER,
            strict_binding=_binding(g,t,kind),generation_mode='blank',content_kind='filled_official_blank',
            generation_label='依据'+g['district']+'自身官方空白表格填写',render_status='offline_byte_parity_review_only')
    return g


def approval_requirements(*,stage=True):
    result={'identities':[{'region_code':c,'source_id':v['source_id'],'source_projection_sha256':v['manifest_sha256'],'service_code':v['service']} for c,v in REGIONS.items()],
        'word_manifest_sha256':WORD_SHA,'approved_by':'independent_root','visual_review':'PASS','source_projection_review':'PASS','can_publish':not stage,'model_calls':0}
    if not stage:result.update(stage_receipt_sha256=STAGE_SHA256,native_confirmation_download_four_forms=True)
    return result


def _receipt(root,stage=True):
    pin=STAGE_SHA256 if stage else PUBLICATION_SHA256
    require(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin),'I自身独立阶段收据未批准固定')
    for code in REGIONS:_sources(root,code)
    word=_word_manifest(root);relative=STAGE_RECEIPT if stage else PUBLICATION_RECEIPT;raw=_bytes(root,relative)
    require(sha256(raw).hexdigest()==pin,'I独立阶段收据变化');receipt=json.loads(raw)
    require(all(k in receipt and exact(receipt[k],v) for k,v in approval_requirements(stage=stage).items()),'I审批身份或阶段范围变化')
    files=receipt.get('files');require(type(files) is list and files and all(type(r) is dict and type(r.get('path')) is str for r in files),'I阶段证据清单无效')
    require(len({r['path'] for r in files})==len(files),'I阶段证据清单重复')
    if stage:require(exact(files,word['files']),'I Word证据未完整进入独立stage审批')
    for row in files:
        require(type(row) is dict and type(row.get('path')) is str and row['path'].startswith(QA_REPORT+'/')
            and type(row.get('bytes')) is int and type(row.get('sha256')) is str and re.fullmatch('[a-f0-9]{64}',row['sha256']),'I审批证据路径无效')
        body=_bytes(root,row['path']);require(len(body)==row['bytes'] and sha256(body).hexdigest()==row['sha256'],'I审批证据文件变化')
    return {'receipt':relative,'sha256':pin}


def staged_candidate(code,*,root):
    g=prepare_candidate(code,root=root);g['candidate_adapter_evidence']=_receipt(root)
    g.update(publication_status='staged_own_word_qa',offline_candidate=False);return g


def _published(code,root):
    g=staged_candidate(code,root=root);g['publication_adapter_evidence']=_receipt(root,False)
    g.update(published=True,publication_status='published',candidate_web_qa='PASS');return g


def _matches(g,canonical):
    if type(g) is not dict or set(g)-set(canonical)-_METADATA:return False
    if 'version' in g and (type(g['version']) is not int or g['version']<1):return False
    if 'region_id' in g and g['region_id']!=region_key('fujian','福州市',canonical['district']):return False
    if 'content_hash' in g and (type(g['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}',g['content_hash'])):return False
    return all(k in g and exact(g[k],v) for k,v in canonical.items())


def _bound(g,root,allow_source=False):
    require(type(g) is dict,'I指南对象无效');code=g.get('region_code');source=parse_capture(code,root=root)
    if allow_source and _matches(g,source):return source
    canonical=_published(code,root) if 'publication_adapter_evidence' in g or g.get('published') is True else staged_candidate(code,root=root)
    require(_matches(g,canonical),'I自身来源、版本、模板或阶段绑定变化');return canonical


def with_capabilities(guide,*,root):_bound(guide,root,True);return deepcopy(guide)


def with_publication_evidence(guide,*,root):
    require(type(guide) is dict and _matches(guide,staged_candidate(guide.get('region_code'),root=root)),'I最终发布必须来自独立stage')
    g=_published(guide['region_code'],root)
    for k in _METADATA&set(guide):g[k]=deepcopy(guide[k])
    return g


def checked_adapter(guide,template,kind,*,root):
    require(kind in KINDS,'I样例或说明不得生成');g=_bound(guide,root);spec=SPECS[kind]
    t=next(t for t in g['templates'] if t['id']==spec['id'] and t['official_kind']=='blank')
    require(exact(template,t) and t['can_generate'] is True,'I自身空白原件绑定变化');return ADAPTER


def public_evidence(guide,root):
    try:return deepcopy(_bound(guide,root,True)['evidence'])
    except _FAILURES:return None


def approved_report_attachment(guide,template,root):
    try:
        g=_bound(guide,root,True);return any(exact(t,template) and t['download_status']=='downloaded' for t in g['templates'])
    except _FAILURES:return False


def defaults(code,kind):
    _meta(code);require(kind in KINDS,'I自身schema文书类型无效')
    return {'applicantName':'','agentName':'','respondentName':'','requests':[''],'factsReason':''} if kind=='application' else {'evidenceList':[{k:'' for k in ITEM_FIELDS}]}


def form_fields(code,kind):
    _meta(code);require(kind in KINDS,'I自身schema文书类型无效')
    def text(key,label,length,**extra):return {'key':key,'label':label,'type':'text','nullable':False,'maxLength':length,**extra}
    if kind=='application':return [text('applicantName','申请人信息',180),text('agentName','委托代理人信息',180),text('respondentName','被申请人信息',180),
        {'key':'requests','label':'仲裁请求','type':'text_list','nullable':False,'maxItems':3,'maxLength':360},text('factsReason','事实与理由',2400)]
    return [{'key':'evidenceList','label':'证据内容','type':'object_list','nullable':False,'maxItems':15,'fields':[
        text('name','证据名称',60),text('pageCount','页数',4),text('originalType','原件或复印件',4,choices=['原件','复印件']),text('purpose','证明对象',80),text('pageRange','页码',32)]}]


def schema_descriptor(code,kind):
    meta=_meta(code);return {'schema_id':f'fujian-i-{code}-{kind}-v1','schema_version':1,'region_code':code,'source_id':meta['source_id'],
        'source_version':meta['manifest_sha256'],'fields':form_fields(code,kind),'defaults':defaults(code,kind),
        'policy':{'unknown_fields':'reject','invalid_xml':'reject','text_controls':'newline_only','trim_text':True,'capacity_is_official_requirement':False}}


def template_path(code,kind,*,root):
    meta=_meta(code);require(kind in KINDS,'I自身文书类型无效');_sources(root,code)
    return path_at(root,SOURCE_BASE+'/'+meta['folder']+'/'+SPECS[kind]['file'])


def envelope(code,kind,data,*,root):
    g=parse_capture(code,root=root);require(kind in KINDS,'I样例或说明不得生成');t=SPECS[kind]
    return {'province':'fujian','city':'福州市','district':g['district'],'region_code':code,'source_id':g['source_id'],'source_url':g['source_url'],
        'source_version':g['source_version'],'template_id':t['id'],'template_sha256':t['sha256'],'template_version':'sha256:'+t['sha256'],
        'schema_id':f'fujian-i-{code}-{kind}-v1','schema_version':1,'kind':kind,'mode':'blank','data':deepcopy(data)}


def _text(value,capacity):
    require(type(value) is str and len(value)<=capacity and all(c=='\n' or 0x20<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff for c in value),'I文字类型、XML字符或技术容量无效')
    return value.strip()


def validate_request(payload,*,root):
    require(type(payload) is dict,'I请求必须为对象');code=payload.get('region_code');kind=payload.get('kind')
    require(type(kind) is str and kind in KINDS,'I样例或说明不得生成');expected=envelope(code,kind,{},root=root)
    require(payload.keys()==expected.keys() and all(exact(payload[k],v) for k,v in expected.items() if k!='data'),'I自身地区、来源、版本、原件、schema或blank绑定变化')
    data=payload['data'];require(type(data) is dict,'I填写数据必须为对象')
    if kind=='application':
        require(not set(data)-set(APP_FIELDS),'I申请书不支持额外字段');values={k:'' for k in APP_FIELDS if k!='requests'};values['requests']=[]
        for key,value in data.items():
            if key=='requests':
                require(type(value) is list and len(value)<=3,'I请求超出技术容量');values[key]=[_text(x,360) for x in value]
            else:values[key]=_text(value,2400 if key=='factsReason' else 180)
    else:
        require(not set(data)-{'evidenceList'},'I证据清单不支持额外字段');rows=data.get('evidenceList',[])
        require(type(rows) is list and len(rows)<=15,'I证据项数超出技术容量');values={'evidenceList':[]}
        for row in rows:
            require(type(row) is dict and not set(row)-set(ITEM_FIELDS),'I证据项不支持额外字段');item={k:'' for k in ITEM_FIELDS}
            for k,v in row.items():item[k]=_text(v,{'name':60,'pageCount':4,'originalType':4,'purpose':80,'pageRange':32}[k])
            require(item['originalType'] in ('','原件','复印件') and (not item['pageCount'] or re.fullmatch('[1-9][0-9]{0,3}',item['pageCount'])),'I证据页数或原件类型无效')
            values['evidenceList'].append(item)
    return code,kind,values


def fixture(code,kind,scenario,*,root):
    _meta(code);require(kind in KINDS and scenario in {'normal','stress'},'I虚构fixture类型无效');_word_manifest(root,code)
    f=_read(root,QA_REPORT+f'/fixtures/{code}-{scenario}-{kind}.json')
    require(f['region_code']==code and f['kind']==kind and f['scenario']==scenario and f['public_generation_approved'] is False
        and exact(f['request'],envelope(code,kind,f['data'],root=root)),'I虚构fixture绑定变化');validate_request(f['request'],root=root)
    return f


def example_data(code,kind,stress=False,*,root):return deepcopy(fixture(code,kind,'stress' if stress else 'normal',root=root)['data'])


def blank_layout(raw,kind):
    with ZipFile(BytesIO(raw)) as z:
        require(z.testzip() is None,'Own DOCX package invalid')
        r=E.fromstring(z.read('word/document.xml'));ps=r.findall('w:body/w:p',N)
        require(len(r.findall('w:body/w:sectPr',N))==1,'Own section layout changed')
        if kind=='application':
            require(len(ps)==22 and not r.findall('.//w:tbl',N),'Own application layout changed')
            text=lambda p:''.join(p.itertext())
            require(text(ps[0])=='仲裁申请书' and text(ps[2]).strip()=='申请人：' and text(ps[3]).strip()=='委托代理人：'
                and text(ps[4]).strip()=='被申请人：' and text(ps[19])=='申请人：','Own application is not the inspected blank')
            require(all(not text(p).strip() for p in ps[11:15]),'Filled facts cannot be a blank')
            for i,p in enumerate(ps[7:10]):require(text(p).strip()==f'{i+1}、','Filled requests cannot be a blank')
        else:
            ts=r.findall('.//w:tbl',N);require(len(ps)==2 and len(ts)==1,'Own evidence layout changed')
            rows=ts[0].findall('w:tr',N)
            require(len(rows)==11 and [''.join(c.itertext()) for c in rows[0].findall('w:tc',N)]==['序号','证据名称','页数','原件/复印件','证明对象','页码'],'Own evidence columns changed')
            require(all(not ''.join(c.itertext()).strip() for row in rows[1:-1] for c in row.findall('w:tc',N)),'A filled sample is not a blank evidence list')
        return r


def replace_text(p,value):
    """Locality-free paragraph/run mutation; preserve paragraph and run properties."""
    runs=p.findall('w:r',N)
    if runs:
        r=runs[0]
        for child in list(r):
            if child.tag!='{'+W+'}rPr':r.remove(child)
        for extra in runs[1:]:p.remove(extra)
    else:
        r=E.SubElement(p,'{'+W+'}r');pr=p.find('w:pPr/w:rPr',N)
        if pr is not None:r.append(deepcopy(pr))
    t=E.SubElement(r,'{'+W+'}t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=value


def candidate_fill(payload,*,root):
    code,kind,values=validate_request(payload,root=root);_word_manifest(root,code)
    raw=template_path(code,kind,root=root).read_bytes()
    active=any(values[k] for k in APP_FIELDS if k!='requests') or any(values['requests']) if kind=='application' else any(any(row.values()) for row in values['evidenceList'])
    if not active:return raw
    document=blank_layout(raw,kind);ps=document.findall('w:body/w:p',N)
    if kind=='application':
        for index,key,label in [(2,'applicantName','申请人：'),(3,'agentName','委托代理人：'),(4,'respondentName','被申请人：')]:
            if values[key]:replace_text(ps[index],label+values[key])
        for i,p in enumerate(ps[7:10]):
            if i<len(values['requests']) and values['requests'][i]:p.findall('.//w:t',N)[1].text=values['requests'][i]
        if values['factsReason']:replace_text(ps[11],values['factsReason'])
        # Committee text and every signature/date run stay unchanged.
        for p in ps[15:20]:
            pr=p.find('w:pPr',N)
            if pr is None:pr=E.Element('{'+W+'}pPr');p.insert(0,pr)
            keep=pr.find('w:keepNext',N)
            if keep is None:keep=E.SubElement(pr,'{'+W+'}keepNext')
            keep.set('{'+W+'}val','1')
    else:
        table=document.find('.//w:tbl',N);rows=table.findall('w:tr',N);items=[row for row in values['evidenceList'] if any(row.values())]
        E.SubElement(rows[0].find('w:trPr',N),'{'+W+'}tblHeader')
        for unused in rows[1+len(items):-1]:table.remove(unused)
        rows=table.findall('w:tr',N)
        while len(rows)-2<len(items):
            node=deepcopy(rows[1]);table.insert(list(table).index(rows[-1]),node);rows=table.findall('w:tr',N)
        for i,row in enumerate(rows[1:-1]):
            E.SubElement(row.find('w:trPr',N),'{'+W+'}cantSplit');item=items[i]
            fields=[str(i+1),item['name'],item['pageCount'],item['originalType'],item['purpose'],item['pageRange']]
            for cell,value in zip(row.findall('w:tc',N),fields):replace_text(cell.find('w:p',N),value)
        pages=str(sum(int(row['pageCount']) for row in items)) if all(row['pageCount'] for row in items) else '____'
        replace_text(rows[-1].find('w:tc/w:p',N),f'以上证据材料合计 {len(items)}份（组） {pages}页')
    xml=E.tostring(document,encoding='UTF-8',xml_declaration=True,standalone=True);out=BytesIO()
    with ZipFile(BytesIO(raw)) as src,ZipFile(out,'w') as result:
        for member in src.infolist():result.writestr(member,xml if member.filename=='word/document.xml' else src.read(member.filename))
    return out.getvalue()


class _PatchedDocument:
    def __init__(self,body,root):self.body=body;self.root=Path(root).resolve()
    def save(self,destination):
        if hasattr(destination,'write'):destination.write(self.body);return
        target=Path(destination).resolve()
        require(not target.is_relative_to(self.root/'reports'),'不得覆盖I公开来源或冻结证据')
        target.write_bytes(self.body)


def fill_document(guide,template,kind,path,data,*,root):
    checked_adapter(guide,template,kind,root=root)
    require(Path(path).resolve()==path_at(root,template['file']),'I原件路径不是自身模板')
    return _PatchedDocument(candidate_fill(envelope(guide['region_code'],kind,data,root=root),root=root),root)
