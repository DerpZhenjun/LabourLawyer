"""UNREGISTERED own Huian/Quangang API source and private Word review proposal."""
from pathlib import Path,PurePosixPath
from copy import deepcopy
from hashlib import sha256
import json,re
from regional_huian_quangang_request import Application,Evidence
from hq_word_mechanics import _layout_inspect,_layout_fill
BASE='reports/overnight-gap-closure-20261030/localities/fujian-huian-quangang-source-projection'
SOURCE_PINS_SHA256='9a1a18cfb30e0251717fcbf7ca158d3af4ab3400f62cd5cb1b691d276472ca2e'
REGIONS={'350521': {'folder': 'huian-350521', 'source_id': '5a2049b6dd7a240d496c29d7', 'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?infoType=1&unid=A917E510341EA05C46948B616C3BE489', 'service_unid': 'A917E510341EA05C46948B616C3BE489', 'service_code': '11350521003825518W400201430200Y01', 'authority': '惠安县人力资源和社会保障局', 'district': '惠安县', 'official_version': '1', 'source_manifest_sha256': '4a9697f5ea943d6dc02b5a9361da7bf6639a50cd6c76f357aa01d68686d4178b'}, '350505': {'folder': 'quangang-350505', 'source_id': '4f9f8144ec2ae19a7f2e70cf', 'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?infoType=1&unid=746DE402C70F4CCCDFFDB52EA51A431A', 'service_unid': '746DE402C70F4CCCDFFDB52EA51A431A', 'service_code': '11350505726453922H400201430200Y01', 'authority': '泉州市泉港区人力资源和社会保障局', 'district': '泉港区', 'official_version': '1', 'source_manifest_sha256': 'c3d3dc26535ed2df27d53d4ad4f3fb723e1bfb740fa2ee6926c4a550783a6267'}}
ADAPTER='fujian_huian_quangang_own_api_nov1_v1'
WORD_SHA256='113e12ddec99ef1c528f65618c2b2bbf32b1c642e424c540e525af29b539246f'
STAGE_SHA256='49d9dee2b760157c9bb3f09ec0dd4a13198ae440878483fa53f44059d1f39625'
PUBLICATION_SHA256='6bd4bcaa2eee4b1d9414fafc6b6441aaaae8256908c65292a47d579c35ab802e'

def require(ok,message='Own API-bound proposal context differs'):
 if not ok:raise ValueError(message)
def exact(a,b):
 if type(a) is not type(b):return False
 if isinstance(b,dict):return a.keys()==b.keys() and all(exact(a[k],v) for k,v in b.items())
 if isinstance(b,list):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
 return a==b
def _raw(root,name):
 require(isinstance(root,(str,Path)) and str(root).strip());base=Path(root).resolve();rel=PurePosixPath(name)
 require(type(name) is str and not rel.is_absolute() and '\\' not in name and ':' not in name and '..' not in rel.parts and all(not p.startswith('.') for p in rel.parts))
 require(name.startswith(BASE+'/') and rel.suffix in {'.json','.docx'})
 p=base/name;require(p.is_file() and p.resolve()==p and all(not q.is_symlink() for q in [p,*p.parents]));return p.read_bytes()
def _json(root,name):return json.loads(_raw(root,name))
def _source(code,root):
 require(type(code) is str and code in REGIONS);pinsraw=_raw(root,BASE+'/OWN-SOURCE-PINS.json');require(sha256(pinsraw).hexdigest()==SOURCE_PINS_SHA256);pins=json.loads(pinsraw);require(pins['WORD'] is pins['STAGE'] is pins['PUBLICATION'] is None)
 pin=pins['regions'][code];require(exact(pin,REGIONS[code]));folder=BASE+'/'+pin['folder'];raw=_raw(root,folder+'/SOURCE-PROJECTION-MANIFEST.json');require(sha256(raw).hexdigest()==pin['source_manifest_sha256']);manifest=json.loads(raw)
 require(manifest['region_code']==code and manifest['source_id']==pin['source_id'] and manifest['source_url']==pin['source_url'] and manifest['official_version']=='1' and manifest['WORD'] is manifest['STAGE'] is manifest['PUBLICATION'] is None)
 require(len(manifest['files'])==12 and set(manifest['files'])=={'safe-'+n for n in ['accept-list.json','flow-nodes.json','legal-basis.json','material-list.json','matter-according.json','matter-basic.json','notice-list.json','table-info.json']}|{'guide.json','PUBLIC-RETRIEVALS.json','application-format-public-retrieval.docx','evidence-format-public-retrieval.docx'})
 for name,p in manifest['files'].items():
  body=_raw(root,folder+'/'+name);require(type(p['bytes']) is int and len(body)==p['bytes'] and sha256(body).hexdigest()==p['sha256'])
  if name.startswith('safe-'):require(b'x-wbsign' not in body.lower())
 service=_json(root,folder+'/safe-matter-basic.json')['data']['apasService'];require(service['areacode']==code and service['unid']==pin['service_unid'] and service['taskHandleItem']==pin['service_code'] and service['deptname']==pin['authority'] and service['serviceVersion']=='1')
 guide=_json(root,folder+'/guide.json');require(all(guide[k]==pin[k] for k in ['source_id','source_url','service_unid','service_code','authority','district','official_version']));require(guide['published'] is False and guide['can_generate'] is False and guide['committee_autofill_allowed'] is False and guide['committee_full_name'] is None)
 materials=_json(root,folder+'/safe-material-list.json')['data'];rows=[m for d in materials['directoryList'] for m in d['material']]+materials['noDirectoryList'];require(len(rows)==3 and all(r['serviceid']==pin['service_unid'] for r in rows));require({m['material_id'] for m in guide['materials']}=={r['unid'] for r in rows})
 tables=_json(root,folder+'/safe-table-info.json')['data']['tableList'];require(len(tables)==6 and len(guide['templates'])==6);require({t['id'] for t in guide['templates']}=={t['unid'] for t in tables})
 receipts=_json(root,folder+'/PUBLIC-RETRIEVALS.json')
 for kind,r in receipts.items():
  t=next(t for t in tables if t['unid']==r['official_attachment_unid']);require(t['punid']==r['official_material_unid'] and t['fileunid']==r['official_public_file_unid'] and t['type']=='1' and r['service_unid']==pin['service_unid'] and r['source_url']==pin['source_url'] and r['region_code']==code and r['TLS_verification']=='DEFAULT_ENABLED' and r['copied_from_other_district'] is False)
  original=_raw(root,folder+'/'+kind+'-format-public-retrieval.docx');require(len(original)==r['bytes'] and sha256(original).hexdigest()==r['sha256']);_layout_inspect(original,kind)
 require(set(receipts)=={'application','evidence'});return deepcopy(guide),pin,folder,manifest
def source_files(root):
 result=[BASE+'/OWN-SOURCE-PINS.json']
 for code in REGIONS:
  _,_,folder,m=_source(code,root);result.extend([folder+'/SOURCE-PROJECTION-MANIFEST.json',*[folder+'/'+n for n in m['files']]])
 return result
def prepare_candidate(code,*,root):
 g,p,_,_=_source(code,root);g['source_version']=p['source_manifest_sha256'];return g
def private_candidate(code,*,root,private_review=False):
 if private_review is not True:raise PermissionError('Explicit private review only; no phase approval')
 g=prepare_candidate(code,root=root);g.update(can_generate=True,generation_adapter=ADAPTER,publication_status='PRIVATE_REVIEW_ONLY_UNBOUND')
 for t in g['templates']:
  if t['eligible_own_kind'] is not None:t.update(can_generate=True,adapter=ADAPTER,document_types=[t['eligible_own_kind']],generation_mode='blank')
 return g
def staged_candidate(code,*,root):return _phase_guide(code,root,False)
def published_guide(code,*,root):return _phase_guide(code,root,True)
def _kind(kind):require(type(kind) is str and kind in {'application','evidence'});return Application if kind=='application' else Evidence
def defaults(kind):return _kind(kind)().model_dump()
def example_data(kind):
 _kind(kind);return {'applicantName':'虚构申请人甲（仅测试）','agentName':'','respondentName':'虚构乙公司（仅测试）','requests':['虚构请求，仅核对本区原件填写。'],'factsReason':'全部内容虚构，不涉及真实案件。'} if kind=='application' else {'evidenceList':[{'name':'虚构证据甲','pageCount':'1','originalType':'复印件','purpose':'虚构测试用途','pageRange':'1'}]}
def form_fields(kind):
 _kind(kind)
 def text(key,n):return {'key':key,'type':'text','maxLength':n}
 return [text('applicantName',180),text('agentName',180),text('respondentName',180),{'key':'requests','type':'text_list','maxItems':3,'maxLength':360},text('factsReason',2400)] if kind=='application' else [{'key':'evidenceList','type':'object_list','maxItems':9,'fields':[text('name',60),text('pageCount',4),{**text('originalType',4),'choices':['原件','复印件']},text('purpose',80),text('pageRange',32)]}]
def build_contract(guide,kind,*,root,private_review=False):
 if private_review is not True:raise PermissionError('Explicit private contract review only')
 require(type(guide) is dict);code=guide.get('region_code');canonical=private_candidate(code,root=root,private_review=True);require(not(set(guide)-set(canonical)-{'version','region_id','content_hash'}));require(all(k in guide and exact(guide[k],v) for k,v in canonical.items()));require(type(guide.get('version')) is int and guide['version']>0)
 _kind(kind);t=next(t for t in canonical['templates'] if t['eligible_own_kind']==kind);context={k:guide[k] for k in ['province','city','district','region_code','source_id','version']};context.update(template_id=t['id'],kind=kind,mode='blank',adapter=ADAPTER,schema_id='private-huian-quangang-'+code+'-'+kind+'-v1',schema_version=1,source_version=canonical['source_version'],template_sha256=t['sha256'],template_version='sha256:'+t['sha256'])
 c={'schema_version':1,'context':context,'fields':form_fields(kind),'defaults':defaults(kind),'policy':{'unknown_fields':'reject','invalid_xml':'reject','text_controls':'newline_only','trim_text':True,'capacity_is_official_requirement':False,'capacity_is_legal_requirement':False,'committee_autofill_allowed':False,'signature_date_copies_fields':'not_accepted','approval':'UNBOUND_PRIVATE_ONLY'}};c['contract_id']=sha256(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();return c
def envelope(code,kind,data,*,version,root):
 g=private_candidate(code,root=root,private_review=True);g['version']=version;c=build_contract(g,kind,root=root,private_review=True);return {**c['context'],'contract_id':c['contract_id'],'data':deepcopy(data)}
def validate_request(payload,*,root):
 require(type(payload) is dict);code=payload.get('region_code');kind=payload.get('kind');expected=envelope(code,kind,{},version=payload.get('version'),root=root);require(payload.keys()==expected.keys() and all(exact(payload[k],v) for k,v in expected.items() if k!='data'));require(type(payload['data']) is dict)
 data=_kind(kind).model_validate(payload['data'],strict=True).model_dump();return code,kind,data
def original_bytes(code,kind,*,root):
 _kind(kind);_,_,folder,_=_source(code,root);return _raw(root,folder+'/'+kind+'-format-public-retrieval.docx')
def inspect_blank(code,kind,*,root):return _layout_inspect(original_bytes(code,kind,root=root),kind)
def candidate_fill(payload,*,root,private_review=False):
 if private_review is not True:raise PermissionError('Explicit private Word review only; approvals UNBOUND')
 code,kind,data=validate_request(payload,root=root);return _layout_fill(original_bytes(code,kind,root=root),kind,data)

# Own production DTO and phase boundaries. Immutable source/Word mapping above stays separate.
QA_REPORT='reports/overnight-gap-closure-20261030/localities/fujian-huian-quangang/word-qa-nov1-v1'
WORD_MANIFEST=QA_REPORT+'/WORD-MANIFEST.json'
STAGE_RECEIPT=QA_REPORT+'/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT=QA_REPORT+'/FINAL-BROWSER-QA.json'
ROOT_WORD_REVIEW_SHA256='77dc510573d280f790a2f47944d215c43800100f63dd6fe605d3421d82940b9b'
_FAILURES=(ValueError,OSError,KeyError,TypeError,AttributeError,StopIteration)
_METADATA={'version','region_id','content_hash'}

def path_at(root,relative):
 require(isinstance(root,(str,Path)) and str(root).strip());base=Path(root).resolve();name=str(relative);r=PurePosixPath(name)
 require(name.startswith((BASE+'/',QA_REPORT+'/')) and not r.is_absolute() and '..' not in r.parts and all(not x.startswith('.') for x in r.parts) and '\\' not in name and ':' not in name and r.suffix in {'.json','.docx','.png'})
 p=base/name;require(p.is_file() and p.resolve()==p and all(not q.is_symlink() for q in [p,*p.parents]));return p

def _production_guide(guide,root):
 g=deepcopy(guide);code=g['region_code'];_,_,folder,m=_source(code,root);capture=folder+'/safe-matter-basic.json'
 for f in g['fields'].values():f.update(normalized_value=None,verification_status='observed_unverified',region_code=code,source_version=g['source_version'],collected_at=f['observed_at'],verified_at=None,capture_file=capture,capture_sha256=m['files']['safe-matter-basic.json']['sha256'])
 for old,new in [('现场次数','到办事现场次数'),('现场原因','必须到现场原因'),('受理地址','办理地点')]:g['fields'][new]=deepcopy(g['fields'][old])
 for material in g['materials']:
  raw=material['raw_fields'];medium=raw['medium'];n=raw['pagenum'] if medium=='原件' else raw['pagecopynum'];material.update(official_badges=[],required=None,required_raw=raw['necessityIf'],format=medium,material_type=medium,original_copy=medium,copies=medium+n+'份',purpose='',source_channel=raw['materialsrc'],submission_method='纸质，电子（上传）' if raw['gettypeunids']=='paper,upload' else None,details={'官网原件份数':raw['pagenum'],'官网复印件份数':raw['pagecopynum']})
 for t in g['templates']:t.update(local_original=t['file'],original_name=t['official_label'])
 g['channel']['entry_check']={'status':'native_auth_boundary_observed'};g.update(online_entry=None,raw_verification_status=g['verification_status']);return g

def production_source(code,*,root):return _production_guide(prepare_candidate(code,root=root),root)
parse_capture=production_source

def word_proof(*,root):
 from hq_phase_proof import verify_word
 return verify_word(root,WORD_SHA256,ROOT_WORD_REVIEW_SHA256,source_files=source_files,prepare=prepare_candidate,original=original_bytes,private_candidate=private_candidate,private_contract=build_contract,data_model=_kind,mechanical_fill=_layout_fill)

def word_files(root):
 m=word_proof(root=root);return [WORD_MANIFEST,*[QA_REPORT+'/'+n for n in m['files']]]

def word_candidate(code,*,root):
 word_proof(root=root);g=production_source(code,root=root);g['word_adapter_evidence']={'manifest':WORD_MANIFEST,'sha256':WORD_SHA256,'root_original_review_sha256':ROOT_WORD_REVIEW_SHA256,'scope':'WORD_APPROVED_STAGE_UNBOUND'};return g

def production_schema_descriptor(code,kind):
 require(type(code) is str and code in REGIONS);_kind(kind);fields=deepcopy(form_fields(kind));labels={'applicantName':'申请人','agentName':'委托代理人','respondentName':'被申请人','requests':'仲裁请求','factsReason':'事实和理由','evidenceList':'证据清单','name':'证据名称','pageCount':'页数','originalType':'原件或复印件','purpose':'证明对象','pageRange':'页码'}
 hints={'applicantName':'填写本区原件的申请人空白。','agentName':'没有委托代理人可留空。','respondentName':'填写本区原件的被申请人空白。','requests':'原件有3个请求条目；模板容量不是法定请求数量。','factsReason':'按本区原件填写事实和理由，可换行。','evidenceList':'按本区证据清单已有列逐项填写。','pageCount':'本项证据页数，不是材料副本份数。','pageRange':'本项证据对应的页码。'}
 for f in fields:
  f['label']=labels[f['key']];f['hint']=hints.get(f['key'],'')
  for item in f.get('fields',[]):item['label']=labels[item['key']];item['hint']=hints.get(item['key'],'')
 return {'schema_id':'fujian-huian-quangang-'+code+'-'+kind+'-v1','schema_version':1,'source_version':REGIONS[code]['source_manifest_sha256'],'fields':fields,'defaults':defaults(kind),'policy':{'unknown_fields':'reject','invalid_xml':'reject','text_controls':'newline_only','trim_text':True,'capacity_is_official_requirement':False,'capacity_is_legal_requirement':False,'committee_autofill_allowed':False,'signature_date_copies_fields':'not_accepted'}}

def _matches(guide,canonical):
 if type(guide) is not dict:return False
 if 'evidence' in guide:
  code=canonical.get('region_code');expected={'source_projection':BASE+'/'+REGIONS[code]['folder']+'/SOURCE-PROJECTION-MANIFEST.json','source_projection_sha256':canonical['source_version']}
  if not exact(guide['evidence'],expected):return False
  guide={k:v for k,v in guide.items() if k!='evidence'}
 if set(guide)-set(canonical)-_METADATA:return False
 if 'version' in guide and (type(guide['version']) is not int or guide['version']<1):return False
 if 'region_id' in guide:
  expected=sha256(json.dumps([canonical[k] for k in ['province','city','district']],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
  if guide['region_id']!=expected:return False
 if 'content_hash' in guide and (type(guide['content_hash']) is not str or re.fullmatch('[a-f0-9]{64}',guide['content_hash']) is None):return False
 return all(k in guide and exact(guide[k],v) for k,v in canonical.items())

def production_contract(guide,kind,*,root,private_review=False):
 require(type(guide) is dict);code=guide.get('region_code');_kind(kind)
 canonical=word_candidate(code,root=root) if private_review is True else _bound(guide,root)
 require(_matches(guide,canonical) and type(guide.get('version')) is int and guide['version']>0);t=next(t for t in canonical['templates'] if t['eligible_own_kind']==kind);schema=production_schema_descriptor(code,kind)
 ctx={k:guide[k] for k in ['province','city','district','region_code','source_id','version']};ctx.update(template_id=t['id'],kind=kind,mode='blank',adapter=ADAPTER,schema_id=schema['schema_id'],schema_version=1,source_version=canonical['source_version'],template_sha256=t['sha256'],template_version='sha256:'+t['sha256'])
 c={'schema_version':1,'context':ctx,'fields':schema['fields'],'defaults':schema['defaults'],'policy':schema['policy']};c['contract_id']=sha256(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();return c

def validate_production_request(payload,*,root,guide=None,private_review=False):
 require(type(payload) is dict and type(guide) is dict);kind=payload.get('kind');require(type(payload.get('version')) is int and payload['version']>0 and type(payload.get('schema_version')) is int and payload['schema_version']==1 and type(payload.get('data')) is dict)
 parsed=_kind(kind).model_validate(payload['data'],strict=True).model_dump();c=production_contract(guide,kind,root=root,private_review=private_review);expected={**c['context'],'contract_id':c['contract_id']}
 require(payload.keys()==expected.keys()|{'data'} and all(exact(payload[k],v) for k,v in expected.items()));return guide['region_code'],kind,parsed

def approval_requirements(*,root,stage=True):
 require(type(stage) is bool);word_proof(root=root);identities=[]
 for code in REGIONS:
  g=prepare_candidate(code,root=root);identities.append({k:g[k] for k in ['region_code','source_id','source_url','service_unid','service_code','source_version','official_version']});identities[-1].update(material_ids=[m['material_id'] for m in g['materials']],eligible_attachment_ids=[t['id'] for t in g['templates'] if t['eligible_own_kind'] is not None])
 d={'scope':'HQ_OWN_STAGE_APPROVAL' if stage else 'HQ_OWN_FINAL_PUBLICATION','adapter':ADAPTER,'identities':identities,'word_manifest_sha256':WORD_SHA256,'Root_original_Word_review_sha256':ROOT_WORD_REVIEW_SHA256,'approved_by':'independent_root_stage_review' if stage else 'independent_root_final_native_review','stage_approval':'APPROVED','publication_approval':None if stage else 'APPROVED','can_publish':not stage,'model_calls':0}
 if not stage:d.update(stage_receipt_sha256=STAGE_SHA256,browser_QA='PASS',native_final_QA='PASS')
 return d

def _native_names():return [QA_REPORT+'/native-final/'+n for n in ['BROWSER-RESULT.json','ROOT-NATIVE-REVIEW.json',*[c+'-'+k+'-CONTRACT.json' for c in REGIONS for k in ['application','evidence']]]]

def _phase_receipt(root,stage=True):
 pin=STAGE_SHA256 if stage else PUBLICATION_SHA256
 if pin is None:raise PermissionError('Own HQ '+('STAGE' if stage else 'PUBLICATION')+' approval is UNBOUND')
 require(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin) is not None)
 from hq_phase_proof import read,strict_json
 if not stage:_phase_receipt(root,True)
 filename=STAGE_RECEIPT if stage else PUBLICATION_RECEIPT;raw=read(root,filename);require(sha256(raw).hexdigest()==pin);receipt=strict_json(raw);expected=approval_requirements(root=root,stage=stage);require(set(receipt)==set(expected)|{'files'} and all(exact(receipt[k],v) for k,v in expected.items()))
 names=word_files(root) if stage else [*word_files(root),STAGE_RECEIPT,*_native_names()];rows=receipt['files'];require(type(rows) is list and len(rows)==len(names) and len({x['path'] for x in rows})==len(names) and {x['path'] for x in rows}==set(names))
 for row in rows:
  require(set(row)=={'path','bytes','sha256'} and type(row['bytes']) is int);b=read(root,row['path']);require(len(b)==row['bytes'] and sha256(b).hexdigest()==row['sha256'])
 if not stage:_check_native_final(root)
 return {'receipt':filename,'sha256':pin,'scope':expected['scope']}

def _check_native_final(root):
 from hq_phase_proof import read,strict_json
 names=_native_names();review=strict_json(read(root,names[1]));browser_raw=read(root,names[0]);browser=strict_json(browser_raw)
 require(review['status']=='ROOT_HQ_OWN_NATIVE_BROWSER_PASS' and review['actual_browser_review'] is True and review['publication_approval']=='APPROVED' and type(review['models']) is int and review['models']==0 and type(review['browser_screenshots']) is int and review['browser_screenshots']==0 and review['source_ids']==[REGIONS[c]['source_id'] for c in REGIONS] and type(review['contracts']) is int and review['contracts']==4 and type(review['native_downloads']) is int and review['native_downloads']==8 and review['browser_result_sha256']==sha256(browser_raw).hexdigest())
 require(browser['status']=='PASS' and browser['auth_or_submission'] is False and type(browser['models']) is int and browser['models']==0 and len(browser['contracts'])==4 and len(browser['downloads'])==8)
 contracts=[]
 for code in REGIONS:
  for kind in ['application','evidence']:
   c=strict_json(read(root,QA_REPORT+'/native-final/'+code+'-'+kind+'-CONTRACT.json'));g=word_candidate(code,root=root);g['version']=c['context']['version'];require(exact(c,production_contract(g,kind,root=root,private_review=True)));contracts.append(c)
 require(exact(browser['contracts'],contracts));contract_by_pair={(c['context']['region_code'],c['context']['kind']):c for c in contracts};seen=set()
 for row in browser['downloads']:
  code=row['region_code'];kind=row['kind'];scenario=row['scenario'];require(code in REGIONS and kind in {'application','evidence'} and scenario in {'blank','normal'} and row['native_download'] is True and type(row['status']) is int and row['status']==200);key=(code,kind,scenario);require(key not in seen);seen.add(key);contract=contract_by_pair[(code,kind)];require(row['contract_id']==contract['contract_id'] and type(row['version']) is int and row['version']==contract['context']['version'] and row['template_id']==contract['context']['template_id'])
  body=original_bytes(code,kind,root=root) if scenario=='blank' else read(root,QA_REPORT+'/word/'+code+'-'+kind+'-normal.docx');require(row['sha256']==sha256(body).hexdigest() and row['source_id']==REGIONS[code]['source_id'])
 require(len(seen)==8)

def _phase_guide(code,root,published):
 stage_evidence=_phase_receipt(root,True);g=word_candidate(code,root=root);g.update(candidate_adapter_evidence=stage_evidence,can_generate=True,generation_adapter=ADAPTER,offline_candidate=False,publication_status='staged_own_word_approved')
 for t in g['templates']:
  if t['eligible_own_kind'] is not None:t.update(can_generate=True,adapter=ADAPTER,generation_mode='blank',document_types=[t['eligible_own_kind']])
 if published:g.update(publication_adapter_evidence=_phase_receipt(root,False),published=True,publication_status='published')
 return g

def _bound(guide,root,allow_source=False):
 require(type(guide) is dict);code=guide.get('region_code')
 if allow_source:
  for raw in [prepare_candidate(code,root=root),production_source(code,root=root)]:
   if _matches(guide,raw):return raw
  if 'word_adapter_evidence' in guide:
   raw=word_candidate(code,root=root)
   if _matches(guide,raw):return raw
  if guide.get('can_generate') is not True and guide.get('published') is not True and 'candidate_adapter_evidence' not in guide:raise ValueError('Unknown own source or Word-only projection')
 canonical=published_guide(code,root=root) if guide.get('published') is True or 'publication_adapter_evidence' in guide else staged_candidate(code,root=root);require(_matches(guide,canonical));return canonical

def with_capabilities(guide,*,root):
 _bound(guide,root,allow_source=True);return deepcopy(guide)

def with_publication_evidence(guide,*,root):
 require(_matches(guide,staged_candidate(guide.get('region_code'),root=root)));out=published_guide(guide['region_code'],root=root)
 for k in _METADATA&guide.keys():out[k]=deepcopy(guide[k])
 return out

def checked_adapter(guide,template,kind,*,root):
 canonical=_bound(guide,root);_kind(kind);t=next(t for t in canonical['templates'] if t['eligible_own_kind']==kind);require(exact(template,t) and t['can_generate'] is True and t['id']==t['official_attachment_id'] and t['material_id']==t['official_material_id'] and t['official_kind']=='blank');return ADAPTER

def checked_reference_adapter(guide,template,kind,*,root):return checked_adapter(guide,template,kind,root=root)
def template_path(code,kind,*,root):
 _kind(kind);_,_,folder,_=_source(code,root);return path_at(root,folder+'/'+kind+'-format-public-retrieval.docx')
def public_evidence(guide,root):
 try:
  g=_bound(guide,root,allow_source=True);return {'source_projection':BASE+'/'+REGIONS[g['region_code']]['folder']+'/SOURCE-PROJECTION-MANIFEST.json','source_projection_sha256':g['source_version']}
 except (*_FAILURES,PermissionError):return None

def approved_report_attachment(guide,template,root):
 try:return any(exact(t,template) and t['file'] is not None and t['eligible_own_kind'] is not None for t in _bound(guide,root,allow_source=True)['templates'])
 except (*_FAILURES,PermissionError):return False

class _DocumentBytes:
 def __init__(self,body,root):self.body,self.root=body,Path(root).resolve()
 def save(self,destination):
  if hasattr(destination,'write'):destination.write(self.body);return
  p=Path(destination).resolve();require(not p.is_relative_to(self.root));p.write_bytes(self.body)

def fill_document(guide,template,kind,path,data,*,root):
 checked_adapter(guide,template,kind,root=root);require(Path(path).resolve()==template_path(guide['region_code'],kind,root=root));require(type(data) is dict);parsed=_kind(kind).model_validate(data,strict=True).model_dump();return _DocumentBytes(_layout_fill(original_bytes(guide['region_code'],kind,root=root),kind,parsed),root)
def approval_files(root):
 _phase_receipt(root,True);return [*word_files(root),STAGE_RECEIPT]
def publication_files(root):
 _phase_receipt(root,False);return [*word_files(root),STAGE_RECEIPT,PUBLICATION_RECEIPT,*_native_names()]
