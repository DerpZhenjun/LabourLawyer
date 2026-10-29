"""Public source and individual-page QA finalization for the two Hunan captures."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_hunan_oct29b import parse_capture,with_capabilities,SPECS,MANIFEST_SHA256,DERIVED_MANIFEST_SHA256,ADAPTER
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def finalize():
 now=datetime.now(timezone.utc).isoformat();manifest=json.loads((OUT/'SOURCE-MANIFEST.json').read_text(encoding='utf8'))
 assert sha(OUT/'SOURCE-MANIFEST.json')==MANIFEST_SHA256
 for relative,expected in manifest['files'].items():
  p=OUT/relative;assert expected=={'sha256':sha(p),'bytes':p.stat().st_size}
 assert sha(OUT/'DERIVED-MANIFEST.json')==DERIVED_MANIFEST_SHA256
 conversion=json.loads((OUT/'DERIVED-MANIFEST.json').read_text(encoding='utf8'));derived=[]
 for x in conversion['files']:
  assert sha(OUT/x['source'])==x['source_sha256'] and sha(OUT/x['file'])==x['sha256']
  derived.append({k:v for k,v in x.items() if k not in {'paragraphs','tables'}})
 guides=[];originals=[]
 for name,s in SPECS.items():
  g=with_capabilities(parse_capture(name));save(name+'/guide.json',g)
  guides.append({'district':g['district'],'region_code':g['region_code'],'portal_area_label':s['portal_label'],'authority':g['authority'],'source_url':g['source_url'],
   'official_approve_id':s['approve'],'implementation_code':s['implementation'],'guide_file':str((OUT/name/'guide.json').relative_to(ROOT)).replace('\\','/'),
   'status':'own_official_guide_and_originals_collected_worker_conversion_adapter_verified','published':False,'materials':4,'blank_originals':2,'sample_originals':2,
   'offline_generation':['worker_application_from_platform_conversion'],'web_acceptance':'NOT_RUN_EXISTING_STARTUP_REJECTION_NOT_RETRIED'})
  for r in json.loads((OUT/name/'originals.json').read_text(encoding='utf8')):
   p=OUT/r['file'];assert sha(p)==r['sha256'];originals.append({**r,'file':str(p.relative_to(ROOT)).replace('\\','/'),'public_reason':'Own official template/sample control public original; sample facts never reused'})
 pages=[];results={}
 for result_name,role in [('original-render-result.json','official_original'),('filled-render-result.json','fictional_filled_conversion')]:
  result=json.loads((OUT/result_name).read_text(encoding='utf8'))
  for task in result['tasks']:
   for image in task['pages']:
    pages.append({'file':image,'sha256':sha(OUT/image),'district':task['district'],'role':role,'status':'PASS_PRESERVED_OFFICIAL_SOURCE' if role=='official_original' else 'PASS',
      'inspection':'individual view_image; text, field wrapping, page breaks, notes, dates, signatures and copy-count blanks reviewed'})
  result.update(visual_review='PASS_ALL_CURRENT_PAGES_INDIVIDUALLY_VIEWED',visual_checked_at=now)
  if role=='official_original':result['notes']=['Official blank DOC has inherited mostly empty fourth page; retained without altering source.',
    'Official worker sample contains Kaifu addresses and invalid birth date 1997.10.32; examples stay separate and are not used as default facts.']
  else:result['notes']=['Natural field wrapping preserves source flow; unused blank fill rows removed. Final two pages per worker application.',
    'Destination is explicitly fictional in QA payload; no committee identity is inferred from a department name.',
    'Only word/document.xml changes against each own platform-converted DOCX; official DOC originals remain byte-identical.',
    'First layout revision remains under attempts/first-layout and is excluded from accepted output whitelist.']
  save(result_name,result);results[role]={'files':len(result['tasks']),'pages':sum(t['page_count'] for t in result['tasks'])}
 assert len(pages)==32
 save('PAGE-QA.json',{'checked_at':now,'status':'PASS','pages':pages,'page_count':32})
 contract={'adapter':ADAPTER,'supported_document':'worker application only; embedded evidence section is part of that application, not an independent evidence-list form',
  'source_format':'official downloaded .doc','generation_format':'docx from bound platform conversion','limits':{'requests':8,'factsReason_characters':1800,'embedded_evidence_items':10,'ordinary_field_characters':160},
  'fields':{'applicantName':0,'gender':1,'birthDate':1,'occupation':1,'nationality':1,'idAddress':2,'address':'alias for idAddress','postalCode':2,'phone':2,
    'workUnit':3,'workUnitPostalCode':3,'workUnitPhone':3,'respondentName':4,'registeredAddress':5,'respondentAddress':'alias for registeredAddress','respondentPostalCode':5,
    'legalRepName':6,'legalRepPosition':6,'legalRepPhone':6,'hrContactName':7,'hrContactPosition':7,'hrContactPhone':7,'thirdParty':8,'requests':'11–18','factsReason':20,
    'committeeName':'destination placeholder in row33, explicit user input only','applicationDate':'date in row33','copyCount':'copy count in row33; defaults blank','evidenceList':'35–56: name/source/purpose'},
  'signature':'always blank; submitterName is not inserted','unsupported':['employer application','independent evidence list','idNumber (no source slot)'],'shared_route_integrated_by_this_task':False}
 save('FORM-CONTRACT.json',contract)
 save('RESULTS.json',{'checked_at':now,'guides':guides,'public_originals':originals,'derived_conversion_copies':derived,'layout':results,'total_current_pages_viewed':32,
   'tests':{'passed':7,'failed':0,'command':'.venv/Scripts/python.exe -m unittest backend.tests.test_hunan_oct29b -v','log':'tests.log'},
   'source_manifest_sha256':MANIFEST_SHA256,'derived_manifest_sha256':DERIVED_MANIFEST_SHA256,'publication':'not_published','shared_route_integrated_by_this_task':False,
   'models_invoked':False,'private_case_databases_accessed':False,'git_used':False,'browser_session':'hn-oct29b (closed)',
   'scope_mapping':'430104 official homepage label 湖南湘江新区 and selector label 岳麓区 resolve to this exact own approve_id and own implementing authority only; no general inheritance',
   'limitations':['两地均为未发布候选；候选站未启动，不绕过旧策略拒绝，候选网页验收NOT_RUN。','两地在线办理只核验至个人/法人登录页，未输入凭据、登录或提交。',
      '四DOCX为平台转换副本，不是官方DOCX原件；仅劳动者申请书已适配。','独立证据清单空白在已核验来源未找到，状态not_found_in_checked_sources，不称官方未提供。','抬头/正文时限、基本信息/FAQ到场要求及材料份数存在不同口径，原文分别保留。'],
   'issues':[{'type':'GENERIC_NATIVE_CARD_TARGET','status':'resolved_by_own_approve_id','evidence':['tianxin/native-guide-target','xiangjiang/native-guide-target'],'resolution':'generic ministry guide was not accepted as district evidence; explicit navigation selection exposed own catalogue ID, region and authority; exact own formal guide opened'},
      {'type':'THEME_SEARCH_NO_RESULT','status':'resolved_by_all_topics','resolution':'cleared narrow topic through native All choice while keeping same-district search; no negative service inference'},
      {'type':'LEGACY_DOC_CONVERSION','status':'completed_and_bound','resolution':'read-only original PDF export followed by separate blank-only DOCX SaveAs2, own original SHA unchanged'},
      {'type':'FIRST_LAYOUT_EXTRA_PAGE','status':'resolved','evidence':'attempts/first-layout','resolution':'removed forced field newlines, retained natural source wrapping; final two pages each'}]})
 files={}
 for p in sorted(OUT.rglob('*')):
  if not p.is_file() or any(x in {'attempts','__pycache__'} for x in p.relative_to(OUT).parts) or p.name=='PUBLIC-WHITELIST.json':continue
  files[str(p.relative_to(ROOT)).replace('\\','/')]={'sha256':sha(p),'bytes':p.stat().st_size}
 for relative in ['backend/regional_hunan_oct29b.py','backend/tests/test_hunan_oct29b.py','scripts/collect-hunan-oct29b.py']:
  p=ROOT/relative;files[relative]={'sha256':sha(p),'bytes':p.stat().st_size}
 save('PUBLIC-WHITELIST.json',{'checked_at':now,'scope':'Explicit public rendered sources, filtered public own-catalogue response bodies, official blank/sample originals, identified platform conversions and fictional accepted QA; no cookies/HAR/SSO queries/login DOM/private cases.',
  'guides':guides,'public_originals':originals,'derived_conversion_copies':derived,'files':files,'excluded':['attempts/** (first layout revision retained locally)','**/__pycache__/**','browser auth/session state, raw request/response headers, HAR, SSO query and private case data (not retained in report)']})
 print(json.dumps({'guides':len(guides),'originals':len(originals),'derived_copies':len(derived),'public_files':len(files),'source_files':len(manifest['files']),'pages_viewed':len(pages)}))
if __name__=='__main__':finalize()
