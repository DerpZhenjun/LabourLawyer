"""Unregistered K own-source candidates. Offline filling grants no public phase."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile
from lxml import etree as E
from regional_guides import digest,region_key

ADAPTER='fujian_three_own_blank_oct31k_v1'
SOURCE_BASE='reports/overnight-gap-closure-20261030/localities/fujian-k-source-projection'
REGIONS={'350111': {'province': 'fujian',
            'city': '福州市',
            'district': '晋安区',
            'region_code': '350111',
            'source_id': '09dcedf106cd2fd411a09546',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=2AE4D76F39D556A71053EF3E78D83397&infoType=1',
            'service_code': '11350111768596390D400201430200201',
            'authority': '福州市晋安区人力资源和社会保障局',
            'folder': 'jinan-350111',
            'allowed_kinds': ['application', 'evidence'],
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': '743F21F90A88857531C1B7321E35AD5B',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-k-source-projection/jinan-350111/application-own-format-public-retrieval.docx'},
                          'evidence': {'file_id': 'CC300F5D9DD5DC404D65C68116D50C55',
                                       'material_id': 'CCD67DD595A67E389AC2EBFAB5409943',
                                       'official_label': '证据清单（空白）.docx',
                                       'sha256': 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815',
                                       'bytes': 18887,
                                       'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-k-source-projection/jinan-350111/evidence-list-own-format-public-retrieval.docx'}},
            'manifest_sha256': '454a4eab5d67f9f0e297ac37ae83a052e9e997a86771e6354f3031ae0ff72569'},
 '350121': {'province': 'fujian',
            'city': '福州市',
            'district': '闽侯县',
            'region_code': '350121',
            'source_id': '70d8f78ba93e94e9afecf7f3',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=91F7E51AA93120174C111809DD6CB410&infoType=1',
            'service_code': '11350121003640951K400201430200201',
            'authority': '闽侯县人力资源和社会保障局',
            'folder': 'minhou-350121',
            'allowed_kinds': ['application'],
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': 'E995DF176916B9D20080AE72C5CE7708',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-k-source-projection/minhou-350121/application-own-format-public-retrieval.docx'}},
            'manifest_sha256': '942bbb67e20627e02fcb30d72b8fef9c8e022ae9b0bf640383ef04b5704dc440'},
 '350105': {'province': 'fujian',
            'city': '福州市',
            'district': '马尾区',
            'region_code': '350105',
            'source_id': '0aa50441bacd05b2245fb5f1',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=1719B4B2674EECE065CC22222ACD8A54&infoType=1',
            'service_code': '11350105003628311J400201430200201',
            'authority': '福州经济技术开发区人力资源和社会保障局',
            'folder': 'mawei-350105',
            'allowed_kinds': ['application'],
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': '0B1E30097A841DB55BF139918A072106',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-k-source-projection/mawei-350105/application-own-format-public-retrieval.docx'}},
            'manifest_sha256': 'ea79a1e90cc56fc9c8914752933f70c3fff37df518da2dfe327bbc8eb8297caa'}}
QA_REPORT='reports/overnight-gap-closure-20261030/localities/fujian-k/integration-qa-v1'
WORD_MANIFEST=QA_REPORT+'/WORD-MANIFEST.json'
WORD_SHA='52097115c840d8edb04e47cd2fc5c6f2ff87a8b5456ca2d242277935412d8b85'
STAGE_RECEIPT=QA_REPORT+'/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT=QA_REPORT+'/FINAL-BROWSER-QA.json'
STAGE_SHA256='d23c44632e61878f597e74528c949603a868ca471f5c83245be579deb7bc8b19'
PUBLICATION_SHA256=None
APP_FIELDS=('applicantName','agentName','respondentName','requests','factsReason')
ITEM_FIELDS=('name','pageCount','originalType','purpose','pageRange')
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';N={'w':W}
_METADATA={'version','region_id','content_hash'}
_FAILURES=(ValueError,OSError,KeyError,TypeError,StopIteration,AttributeError)

def require(ok,message):
    if not ok:raise ValueError(message)
def exact(a,b):
    if type(a) is not type(b):return False
    if isinstance(b,dict):return a.keys()==b.keys() and all(exact(a[k],v) for k,v in b.items())
    if isinstance(b,list):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b
def path_at(root,relative):
    require(root is not None and str(root).strip(),'Explicit K own-source root required')
    root=Path(root).resolve();rel=Path(relative)
    require(not rel.is_absolute() and not rel.drive and '..' not in rel.parts,'Own relative path required')
    path=(root/rel).resolve();require(path.is_relative_to(root) and path.relative_to(root).as_posix()==rel.as_posix(),'Own path escaped or linked');return path
def _bytes(root,relative):
    try:return path_at(root,relative).read_bytes()
    except OSError as exc:raise ValueError('Own K proof unavailable in explicit root') from exc
def _read(root,relative):return json.loads(_bytes(root,relative))
def _meta(code):
    require(type(code) is str and code in REGIONS,'Only own K locality identities supported');return REGIONS[code]
def _kind(code,kind):
    meta=_meta(code);require(type(kind) is str and kind in meta['allowed_kinds'],'Own evidence/sample/reference kind not adapted');return meta

def _sources(root,code):
    meta=_meta(code);folder=SOURCE_BASE+'/'+meta['folder'];raw=_bytes(root,folder+'/SOURCE-PROJECTION-MANIFEST.json')
    require(sha256(raw).hexdigest()==meta['manifest_sha256'],'Own K projection version changed');manifest=json.loads(raw)
    require(all(k in manifest and exact(manifest[k],v) for k,v in meta.items() if k!='manifest_sha256')
        and digest(meta['source_url'])[:24]==meta['source_id'],'Own canonical source frame changed')
    require(manifest['schema_version']==1 and type(manifest['schema_version']) is int
        and manifest['derived_sanitized_projection'] is True and manifest['raw_parent_is_runtime_dependency'] is False
        and manifest['committee_full_name'] is None and manifest['can_generate'] is False and manifest['published'] is False,'Own source-only qualification changed')
    expected={'NORMALIZED-OWN-SOURCE.json','own-guide-native-dom.json','own-official-bindings.json','SOURCE-QUALIFICATIONS.json'}
    expected.update(Path(t['source_file']).name for t in meta['templates'].values())
    require(type(manifest['files']) is dict and set(manifest['files'])==expected,'Own projection leaf set changed')
    for name,pin in manifest['files'].items():
        body=_bytes(root,folder+'/'+name)
        require(type(pin['bytes']) is int and len(body)==pin['bytes'] and sha256(body).hexdigest()==pin['sha256'],'Own source leaf bytes changed')
    normalized=_read(root,folder+'/NORMALIZED-OWN-SOURCE.json');binding=_read(root,folder+'/own-official-bindings.json');q=_read(root,folder+'/SOURCE-QUALIFICATIONS.json')
    require(all(exact(normalized['region'].get(k),meta[k]) for k in ['province','city','district','region_code','source_id','source_url'])
        and normalized['service_code_literal']==meta['service_code'] and normalized['raw_fields']['实施主体']['raw_value'].strip()==meta['authority'],'Own native identity differs')
    require(all(exact(binding.get(k),meta[k]) for k in ['region_code','source_id','source_url','service_code','authority'])
        and binding['byte_identity_grants_other_region_authority'] is False and binding['can_generate'] is False and binding['published'] is False,'Own attachment frame differs')
    require(q['canonical_source_id']==meta['source_id'] and exact(q['eligible_kinds'],meta['allowed_kinds'])
        and q['committee_full_name'] is None and q['committee_autofill_allowed'] is False and q['can_generate'] is False
        and q['root_stage_receipt'] is None and q['root_final_receipt'] is None,'Own qualification differs')
    require(len(normalized['materials'])==3 and len(binding['attachments'])==6,'Own three materials/six binding scope differs')
    for panel in normalized['materials']:
        for row in panel['attachments']:
            matches=[t for t in binding['attachments'] if t['file_id']==row['file_id'] and t['material_id']==panel['material_id']]
            require(len(matches)==1 and matches[0]['official_type_raw']==row['official_type_raw'] and matches[0]['official_label']==row['label'],'Own native material/file/type differs')
    for kind,t in meta['templates'].items():
        row=next(t2 for t2 in binding['attachments'] if t2['file_id']==t['file_id'])
        require(row['source_url']==meta['source_url'] and row['material_id']==t['material_id'] and row['official_type_raw']=='1'
            and row['eligible_kind']==kind and row['content_role']=='fillable_own_blank' and row['sha256']==t['sha256']
            and folder+'/'+row['file']==t['source_file'],'Own eligible blank binding differs')
        blank_layout(_bytes(root,t['source_file']),kind)
    return manifest

def source_files(root,code=None):
    result=[]
    for c in [code] if code is not None else REGIONS:
        manifest=_sources(root,c);folder=SOURCE_BASE+'/'+REGIONS[c]['folder']
        result.extend([folder+'/SOURCE-PROJECTION-MANIFEST.json',*[folder+'/'+p for p in manifest['files']]])
    return result

def parse_capture(code,*,root):
    meta=_meta(code);manifest=_sources(root,code);folder=SOURCE_BASE+'/'+meta['folder']
    n=_read(root,folder+'/NORMALIZED-OWN-SOURCE.json');dom=_read(root,folder+'/own-guide-native-dom.json');binding=_read(root,folder+'/own-official-bindings.json');q=_read(root,folder+'/SOURCE-QUALIFICATIONS.json')
    capture=folder+'/own-guide-native-dom.json';capture_sha=manifest['files']['own-guide-native-dom.json']['sha256'];fields={}
    province_name=n['official_title'].split('网上办事大厅',1)[0]
    require(province_name=='福建省','Own province display title differs')
    for key,item in n['raw_fields'].items():
        require(type(item['raw_value']) is str and item['source_url']==meta['source_url'],'Own public field frame differs')
        fields[key]={**deepcopy(item),'source_label':item.get('raw_label',key),'capture_file':capture,'capture_sha256':capture_sha,'region_code':code,'collected_at':n['observed_at'],'verified_at':n['observed_at'],'verification_status':'verified'}
    if code=='350121':
        # Retain this actual own-source conflict without endorsing it as an
        # arbitration requirement, basis, or a default fact in any document.
        require(fields['权责清单']['raw_value'].strip()=='企业年金方案报备','Own Minhou conflicting source row changed')
        fields['权责清单'].update(normalized_value=None,verification_status='unverified',normalization='Not normalized: own official row conflicts with this service')
    # Existing display keys are aliases of this source's own records; retain
    # the original keys, raw values, pointers, and verification metadata.
    for display,source in {'承诺办结时限':'承诺时限','法定办结时限':'法定时限','咨询方式':'联系电话','必须到现场原因':'必须现场办理原因','服务对象':'申报对象'}.items():
        require(source in fields,'Own source field unavailable: '+source)
        fields[display]=deepcopy(fields[source])
    for label in ['办理时间','办理地点','交通指引']:
        match=re.search(r'(?:^|\n)'+label+'：([^\n]+)',dom['raw_public_text'])
        require(match is not None,'Own window field unavailable: '+label)
        value=match.group(1)
        fields[label]={'raw_value':value,'normalized_value':value.strip(),'source_url':meta['source_url'],'source_label':label,
            'source_pointer':f'text/{label}@{match.start(1)}:{match.end(1)}','capture_file':capture,'capture_sha256':capture_sha,
            'region_code':code,'collected_at':n['observed_at'],'verified_at':n['observed_at'],'verification_status':'verified'}
    sections={'本区公开办事指南原文':dom['raw_public_text'],'办理流程与窗口办理':n['source_workflow_and_window_literal']}
    conditions=re.search(r'受理条件\n(1[、.].+?)\n申报材料',dom['raw_public_text'],re.S)
    require(conditions is not None,'Own reception conditions unavailable');sections['受理条件']=conditions.group(1)
    materials=[]
    for index,panel in enumerate(n['materials']):
        raw=panel['raw_public_text'];labels=list(re.finditer(r'(?:^|\n)([^\n\t]{1,40})\t[ \t]*',raw));details={}
        for i,label in enumerate(labels):details[label.group(1).rstrip('：:').strip()]=raw[label.end():labels[i+1].start() if i+1<len(labels) else len(raw)].strip()
        match=re.search(r'(\d+)份',panel['copies_literal']);require(match is not None,'Own copies literal unavailable')
        original=re.search(r'材料类型：([^\n]+)',details.get('材料要求',''))
        require(original is not None,'Own original/copy material type unavailable')
        materials.append({'id':panel['material_id'],'name':panel['header'].splitlines()[-1],'required':details.get('材料必要性',''),
            'format':details.get('材料形式',''),'copies':int(match.group(1)),'paper_copies':int(match.group(1)),
            'copies_source_literal':panel['copies_literal'],'copies_are_source_metadata':True,'original_copy':original.group(1).strip(),'instructions':details.get('填报须知',''),
            'details':details,'raw_source_text':raw,'source_url':meta['source_url'],'capture_file':capture,'capture_sha256':capture_sha,
            'generation_status':'UNKNOWN_NOT_ADAPTED' if index==1 and code!='350111' else 'own_blank_available' if index<2 else 'reference_only'})
    templates=[]
    for row in binding['attachments']:
        eligible=row['eligible_kind'];templates.append({'id':row['file_id'],'annex_id':row['file_id'],'region_code':code,'material_id':row['material_id'],
            'official_kind':'blank' if eligible else 'sample' if row['official_type_raw']=='2' else 'reference','official_reported_type':row['official_type_raw'],
            'original_name':row['official_label'],'file_type':'docx','source_url':meta['source_url'],'download_url':row['public_download_url'],
            'file':folder+'/'+row['file'] if row['file'] else None,'sha256':row['sha256'],'bytes':row['bytes'],'download_status':'downloaded' if eligible else 'metadata_only',
            'can_generate':False,'document_types':[],'content_role':row['content_role'],'eligible_own_kind':eligible,'sample_contents_verified':False})
    return {**{k:meta[k] for k in ['province','city','district','region_code','source_id','source_url','service_code','authority']},
        'province_name':province_name,'service_name':'劳动人事争议仲裁申请','source_version':meta['manifest_sha256'],'official_version':None,'verification_status':'partial','guide_status':'partial',
        'collected_at':n['observed_at'],'verified_at':n['observed_at'],'fields':fields,'materials':materials,'templates':templates,
        'sections':sections,'committee_full_name':None,'committee_autofill_allowed':False,
        'appointment_organization_literal':q['appointment_organization_literal'],'can_generate':False,'published':False,'publication_status':'source_only',
        'channel':{'raw_value':fields.get('办理形式',{}).get('raw_value',''),'online_status':'unverified','entry_url':None,'entry_check':{'status':'unverified','scope':n.get('online_channel_scope')},'submission_verified':False},
        'evidence':{'capture_file':capture,'capture_sha256':capture_sha,'source_projection':folder+'/SOURCE-PROJECTION-MANIFEST.json','source_projection_sha256':meta['manifest_sha256']},
        'warnings':['自身partial来源；官方版本未知；预约组织标签不是委员会自动填写授权。','显示份数与按人数副本备注均保留，不自动推断法律提交份数。','非适配证据状态UNKNOWN，不声称官网不提供；示范或扫描说明不生成。']+(['官网部分说明与此事项不一致，需向办理机构核对'] if code=='350121' else [])}

def prepare_candidate(code,*,root):
    g=parse_capture(code,root=root);meta=_meta(code);g.update(can_generate=True,offline_candidate=True,generation_adapter=ADAPTER,publication_status='unregistered_offline_candidate')
    for kind,spec in meta['templates'].items():
        t=next(t for t in g['templates'] if t['id']==spec['file_id']);t.update(can_generate=True,document_types=[kind],adapter=ADAPTER,generation_mode='blank')
    return g

def _word_manifest(root):
    require(type(WORD_SHA) is str and re.fullmatch('[a-f0-9]{64}',WORD_SHA),'K Word QA not sealed')
    raw=_bytes(root,WORD_MANIFEST);require(sha256(raw).hexdigest()==WORD_SHA,'K Word manifest differs');m=json.loads(raw)
    require(m['eligible_originals']==4 and m['fictional_fixtures']==8 and m['word_documents']==12 and m['original_pages']==7 and m['generated_pages']==37
        and m['stage_approved'] is False and m['can_publish'] is False,'Own Word scope differs')
    require(exact(m['source_versions'],{c:r['manifest_sha256'] for c,r in REGIONS.items()}),'Own Word source versions differ')
    require(type(m['files']) is list and m['files'] and len({r['path'] for r in m['files']})==len(m['files']),'Own Word leaves invalid')
    for row in m['files']:
        require(row['path'].startswith(QA_REPORT+'/'),'Own Word path differs');body=_bytes(root,row['path'])
        require(type(row['bytes']) is int and len(body)==row['bytes'] and sha256(body).hexdigest()==row['sha256'],'Own Word leaf changed')
    return m
def approval_requirements(*,stage=True):
    result={'identities':[{k:m[k] for k in ['region_code','source_id','manifest_sha256','service_code']} for m in REGIONS.values()],
        'word_manifest_sha256':WORD_SHA,'eligible_originals':4,'approved_by':'independent_root','visual_review':'PASS','source_projection_review':'PASS','can_publish':not stage,'model_calls':0}
    if not stage:result.update(stage_receipt_sha256=STAGE_SHA256,native_confirmation_download_own_forms=True)
    return result
def _receipt(root,stage=True):
    pin=STAGE_SHA256 if stage else PUBLICATION_SHA256;require(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin),'K independent phase not approved')
    for c in REGIONS:_sources(root,c)
    word=_word_manifest(root);raw=_bytes(root,STAGE_RECEIPT if stage else PUBLICATION_RECEIPT);require(sha256(raw).hexdigest()==pin,'Own K approval bytes differ');r=json.loads(raw)
    require(all(k in r and exact(r[k],v) for k,v in approval_requirements(stage=stage).items()),'Own K approval scope differs')
    require(type(r.get('files')) is list and r['files'] and len({x['path'] for x in r['files']})==len(r['files']),'Own phase leaves invalid')
    if stage:require(exact(r['files'],word['files']),'Own complete offline Word proof not stage-approved')
    for leaf in r['files']:
        require(leaf['path'].startswith(QA_REPORT+'/'),'Own phase leaf path differs');body=_bytes(root,leaf['path'])
        require(type(leaf['bytes']) is int and len(body)==leaf['bytes'] and sha256(body).hexdigest()==leaf['sha256'],'Own phase leaf bytes differ')
    return {'receipt':STAGE_RECEIPT if stage else PUBLICATION_RECEIPT,'sha256':pin}
def staged_candidate(code,*,root):
    g=prepare_candidate(code,root=root);g['candidate_adapter_evidence']=_receipt(root);g.update(offline_candidate=False,publication_status='staged_own_word_qa');return g
def _published(code,root):
    g=staged_candidate(code,root=root);g['publication_adapter_evidence']=_receipt(root,False);g.update(published=True,publication_status='published');return g
def _matches(g,c):
    if type(g) is not dict or set(g)-set(c)-_METADATA:return False
    if 'version' in g and (type(g['version']) is not int or g['version']<1):return False
    if 'region_id' in g and g['region_id']!=region_key('fujian',c['city'],c['district']):return False
    if 'content_hash' in g and (type(g['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}',g['content_hash'])):return False
    return all(k in g and exact(g[k],v) for k,v in c.items())
def _bound(g,root,allow_source=False):
    require(type(g) is dict,'Own K guide required');code=g.get('region_code');raw=parse_capture(code,root=root)
    if allow_source and _matches(g,raw):return raw
    canonical=_published(code,root) if g.get('published') is True or 'publication_adapter_evidence' in g else staged_candidate(code,root=root)
    require(_matches(g,canonical),'Own K canonical source/phase binding differs');return canonical
def with_capabilities(g,*,root):_bound(g,root,True);return deepcopy(g)
def with_publication_evidence(g,*,root):
    require(type(g) is dict and _matches(g,staged_candidate(g.get('region_code'),root=root)),'Own K stage required');result=_published(g['region_code'],root)
    for key in _METADATA&set(g):result[key]=deepcopy(g[key])
    return result
def checked_adapter(g,t,kind,*,root):
    c=_bound(g,root);meta=_kind(g['region_code'],kind);expected=next(x for x in c['templates'] if x['id']==meta['templates'][kind]['file_id'])
    require(exact(t,expected) and expected['can_generate'] is True and expected['official_kind']=='blank','Own K approved blank differs');return ADAPTER
def public_evidence(g,root):
    try:return deepcopy(_bound(g,root,True)['evidence'])
    except _FAILURES:return None
def approved_report_attachment(g,t,root):
    try:return any(exact(row,t) and row['download_status']=='downloaded' for row in _bound(g,root,True)['templates'])
    except _FAILURES:return False

def defaults(code,kind):
    _kind(code,kind);return {'applicantName':'','agentName':'','respondentName':'','requests':[''],'factsReason':''} if kind=='application' else {'evidenceList':[{k:'' for k in ITEM_FIELDS}]}
def form_fields(code,kind):
    _kind(code,kind)
    def slot(key,label,n,**extra):return {'key':key,'label':label,'type':'text','nullable':False,'maxLength':n,**extra}
    if kind=='application':return [slot('applicantName','申请人信息',180),slot('agentName','委托代理人信息',180),slot('respondentName','被申请人信息',180),{'key':'requests','label':'仲裁请求','type':'text_list','nullable':False,'maxItems':3,'maxLength':360},slot('factsReason','事实与理由',2400)]
    return [{'key':'evidenceList','label':'证据内容','type':'object_list','nullable':False,'maxItems':9,'fields':[slot('name','证据名称',60),slot('pageCount','页数',4),slot('originalType','原件或复印件',4,choices=['原件','复印件']),slot('purpose','证明对象',80),slot('pageRange','页码',32)]}]
def schema_descriptor(code,kind):
    m=_kind(code,kind);return {'schema_id':f'fujian-k-{code}-{kind}-v1','schema_version':1,'region_code':code,'source_id':m['source_id'],'source_version':m['manifest_sha256'],'fields':form_fields(code,kind),'defaults':defaults(code,kind),'policy':{'unknown_fields':'reject','invalid_xml':'reject','text_controls':'newline_only','trim_text':True,'capacity_is_official_requirement':False}}
def template_path(code,kind,*,root):
    m=_kind(code,kind);_sources(root,code);return path_at(root,m['templates'][kind]['source_file'])
def envelope(code,kind,data,*,root):
    m=_kind(code,kind);_sources(root,code);t=m['templates'][kind]
    return {**{k:m[k] for k in ['province','city','district','region_code','source_id','source_url']},'source_version':m['manifest_sha256'],
        'material_id':t['material_id'],'template_id':t['file_id'],'template_file':t['source_file'],'template_sha256':t['sha256'],'template_version':'sha256:'+t['sha256'],
        'schema_id':f'fujian-k-{code}-{kind}-v1','schema_version':1,'kind':kind,'mode':'blank','data':deepcopy(data)}
def text(value,capacity):
    require(type(value) is str and len(value)<=capacity and all(c=='\n' or 0x20<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff for c in value),'Invalid own text type/XML/technical capacity');return value.strip()
def validate_request(payload,*,root):
    require(type(payload) is dict,'Own K request object required');m=_kind(payload.get('region_code'),payload.get('kind'));kind=payload['kind'];expected=envelope(m['region_code'],kind,{},root=root)
    require(payload.keys()==expected.keys() and all(exact(payload[k],v) for k,v in expected.items() if k!='data'),'Own K request identity/schema differs')
    data=payload['data'];require(type(data) is dict,'Own form data must be object')
    if kind=='application':
        require(not set(data)-set(APP_FIELDS),'Unknown own application slot');values={k:'' for k in APP_FIELDS if k!='requests'};values['requests']=[]
        for key,value in data.items():
            if key=='requests':require(type(value) is list and len(value)<=3,'Own request slot capacity exceeded');values[key]=[text(x,360) for x in value]
            else:values[key]=text(value,2400 if key=='factsReason' else 180)
    else:
        require(not set(data)-{'evidenceList'},'Unknown own evidence slot');rows=data.get('evidenceList',[]);require(type(rows) is list and len(rows)<=9,'Own evidence capacity exceeded');values={'evidenceList':[]}
        for row in rows:
            require(type(row) is dict and not set(row)-set(ITEM_FIELDS),'Invalid own evidence item');item={k:'' for k in ITEM_FIELDS}
            for key,value in row.items():item[key]=text(value,{'name':60,'pageCount':4,'originalType':4,'purpose':80,'pageRange':32}[key])
            require(item['originalType'] in ('','原件','复印件') and (not item['pageCount'] or re.fullmatch('[1-9][0-9]{0,3}',item['pageCount'])),'Invalid own pages or original/copy value');values['evidenceList'].append(item)
    return m,kind,values

def blank_layout(raw,kind):
    with ZipFile(BytesIO(raw)) as z:
        require(z.testzip() is None,'Own DOCX CRC invalid');r=E.fromstring(z.read('word/document.xml'));ps=r.findall('w:body/w:p',N)
        require(len(r.findall('w:body/w:sectPr',N))==1,'Own section changed')
        if kind=='application':
            require(len(ps)==22 and not r.findall('.//w:tbl',N),'Own application positions changed')
            for i,label in [(0,'仲裁申请书'),(2,'申请人：'),(3,'委托代理人：'),(4,'被申请人：'),(19,'申请人：')]:require(''.join(ps[i].itertext()).strip()==label,'Own blank application label changed')
            require(all(not ''.join(p.itertext()).strip() for p in ps[11:15]),'Filled facts are not a blank')
            for i,p in enumerate(ps[7:10]):require(''.join(p.itertext()).strip()==f'{i+1}、','Filled request is not a blank')
        else:
            ts=r.findall('.//w:tbl',N);require(len(ps)==2 and len(ts)==1,'Own evidence positions changed');rows=ts[0].findall('w:tr',N)
            require(len(rows)==11 and [''.join(c.itertext()) for c in rows[0].findall('w:tc',N)]==['序号','证据名称','页数','原件/复印件','证明对象','页码'],'Own evidence columns changed')
            require(all(len(row.findall('w:tc',N))==6 and all(not ''.join(c.itertext()).strip() for c in row.findall('w:tc',N)) for row in rows[1:-1]),'Filled evidence is not a blank')
            require(rows[-1].find('w:tc/w:tcPr/w:gridSpan',N).get('{'+W+'}val')=='6','Own totals merge changed')
        return r
def replace_text(p,value):
    runs=p.findall('w:r',N)
    if runs:
        run=runs[0]
        for child in list(run):
            if child.tag!='{'+W+'}rPr':run.remove(child)
        for extra in runs[1:]:p.remove(extra)
    else:
        run=E.SubElement(p,'{'+W+'}r');pr=p.find('w:pPr/w:rPr',N)
        if pr is not None:run.append(deepcopy(pr))
    node=E.SubElement(run,'{'+W+'}t');node.set('{http://www.w3.org/XML/1998/namespace}space','preserve');node.text=value
def candidate_fill(payload,*,root):
    m,kind,v=validate_request(payload,root=root);raw=_bytes(root,m['templates'][kind]['source_file'])
    active=(any(v[k] for k in APP_FIELDS if k!='requests') or any(v['requests'])) if kind=='application' else any(any(row.values()) for row in v['evidenceList'])
    if not active:return raw
    doc=blank_layout(raw,kind);ps=doc.findall('w:body/w:p',N)
    if kind=='application':
        for index,key,label in [(2,'applicantName','申请人：'),(3,'agentName','委托代理人：'),(4,'respondentName','被申请人：')]:
            if v[key]:replace_text(ps[index],label+v[key])
        for i,p in enumerate(ps[7:10]):
            if i<len(v['requests']) and v['requests'][i]:p.findall('.//w:t',N)[1].text=v['requests'][i]
        if v['factsReason']:replace_text(ps[11],v['factsReason'])
        # No committee/signature/date value is supplied or inferred.
        for p in ps[15:20]:
            pr=p.find('w:pPr',N)
            if pr is None:pr=E.Element('{'+W+'}pPr');p.insert(0,pr)
            keep=pr.find('w:keepNext',N)
            if keep is None:keep=E.SubElement(pr,'{'+W+'}keepNext')
            keep.set('{'+W+'}val','1')
    else:
        table=doc.find('.//w:tbl',N);rows=table.findall('w:tr',N);items=[row for row in v['evidenceList'] if any(row.values())]
        E.SubElement(rows[0].find('w:trPr',N),'{'+W+'}tblHeader')
        for unused in rows[1+len(items):-1]:table.remove(unused)
        rows=table.findall('w:tr',N)
        for i,row in enumerate(rows[1:-1]):
            E.SubElement(row.find('w:trPr',N),'{'+W+'}cantSplit');item=items[i]
            for cell,value in zip(row.findall('w:tc',N),[str(i+1),item['name'],item['pageCount'],item['originalType'],item['purpose'],item['pageRange']]):replace_text(cell.find('w:p',N),value)
        pages=str(sum(int(row['pageCount']) for row in items)) if all(row['pageCount'] for row in items) else '____'
        replace_text(rows[-1].find('w:tc/w:p',N),f'以上证据材料合计 {len(items)}份（组） {pages}页')
    xml=E.tostring(doc,encoding='UTF-8',xml_declaration=True,standalone=True);out=BytesIO()
    with ZipFile(BytesIO(raw)) as src,ZipFile(out,'w') as result:
        for member in src.infolist():result.writestr(member,xml if member.filename=='word/document.xml' else src.read(member.filename))
    return out.getvalue()

class _PatchedDocument:
    def __init__(self,body,root):self.body=body;self.root=Path(root).resolve()
    def save(self,destination):
        if hasattr(destination,'write'):destination.write(self.body);return
        path=Path(destination).resolve();require(not path.is_relative_to(self.root/'reports'),'Do not overwrite own source/proof');path.write_bytes(self.body)
def fill_document(g,t,kind,path,data,*,root):
    checked_adapter(g,t,kind,root=root);require(Path(path).resolve()==template_path(g['region_code'],kind,root=root),'Own K original differs')
    return _PatchedDocument(candidate_fill(envelope(g['region_code'],kind,data,root=root),root=root),root)

def example_data(code,kind,stress=False,*,root):
    """Read only this locality/kind's already sealed fictional fixture."""
    _kind(code,kind);_word_manifest(root)
    fixture=_read(root,QA_REPORT+f'/fixtures/{code}-'+('stress' if stress else 'normal')+f'-{kind}.json')
    require(fixture['fictional_only'] is True and fixture['real_case_data'] is False
        and exact(fixture['request'],envelope(code,kind,fixture['data'],root=root)),'Own fictional fixture context differs')
    return deepcopy(fixture['data'])
