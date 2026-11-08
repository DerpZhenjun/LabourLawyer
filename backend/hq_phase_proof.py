"""Portable own HQ Word proof validation. No Office, network, implicit root or approval writes."""
from pathlib import Path,PurePosixPath
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from lxml import etree
import json,re,stat
from copy import deepcopy
QA='reports/overnight-gap-closure-20261030/localities/fujian-huian-quangang/word-qa-nov1-v1'
CODES=('350521','350505')
KINDS=('application','evidence')

def need(ok):
 if not ok:raise ValueError('Own HQ Word/phase proof differs')
def read(root,name):
 need(isinstance(root,(str,Path)) and str(root).strip() and type(name) is str);r=Path(root).resolve();p=PurePosixPath(name);need(name.startswith(QA+'/') and not p.is_absolute() and p.as_posix()==name and '..' not in p.parts and all(not x.startswith('.') for x in p.parts) and '\\' not in name and ':' not in name and p.suffix in {'.json','.docx','.png'});target=r/name
 need(target.is_file() and target.resolve()==target)
 for q in [target,*target.parents]:need(not q.is_symlink() and not getattr(q.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0))
 return target.read_bytes()
def strict_json(raw):
 def pairs(rows):
  d={}
  for k,v in rows:need(k not in d);d[k]=v
  return d
 def invalid(value):raise ValueError('Nonfinite proof JSON')
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
def parts(raw):
 with ZipFile(BytesIO(raw)) as z:
  need(z.testzip() is None and len(z.namelist())==len(set(z.namelist())));out={}
  for name in z.namelist():
   p=PurePosixPath(name);need(not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name and not name.lower().startswith('word/embeddings/') and 'vbaproject' not in name.lower());b=z.read(name);out[name]=sha256(b).hexdigest()
   if name.endswith(('.xml','.rels')):
    node=etree.fromstring(b,etree.XMLParser(resolve_entities=False,no_network=True));need(not node.getroottree().docinfo.doctype)
    for e in node.iter():need(e.get('TargetMode','').lower()!='external')
  return out

def verify_word(root,pin,root_review_sha,*,source_files,prepare,original,private_candidate,private_contract,data_model,mechanical_fill):
 need(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin) and type(root_review_sha) is str and re.fullmatch('[a-f0-9]{64}',root_review_sha));raw=read(root,QA+'/WORD-MANIFEST.json');need(sha256(raw).hexdigest()==pin);m=strict_json(raw);need(m['scope']=='HQ_OWN_ACTUAL_ROOT_WORD_APPROVAL_ONLY' and m['root_original_review_sha256']==root_review_sha and m['region_codes']==list(CODES) and m['STAGE'] is m['PUBLICATION'] is None)
 need(len(source_files(root))==27 and type(m['physical_documents']) is int and m['physical_documents']==12 and type(m['native_pages']) is int and m['native_pages']==48 and type(m['Root_unique_pixel_pages_actually_viewed']) is int and m['Root_unique_pixel_pages_actually_viewed']==20)
 need(type(m['files']) is dict and len(m['files'])==70 and len(m['jobs'])==12)
 for name,p in m['files'].items():
  b=read(root,QA+'/'+name);need(type(p['bytes']) is int and len(b)==p['bytes'] and sha256(b).hexdigest()==p['sha256'])
 review=strict_json(read(root,QA+'/ROOT-WORD-VISUAL-REVIEW.json'));index=strict_json(read(root,QA+'/ROOT-RENDER-INDEX.json'))
 need(review['status']=='ROOT_ACTUAL_NATIVE_WORD_AND_VISUAL_REVIEW_PASSED_NOT_STAGED_OR_PUBLISHED' and review['region_codes']==list(CODES) and review['portable_sanitization']['original_sha256']==root_review_sha and review['render_index_sha256']==m['root_original_index_sha256']==index['portable_sanitization']['original_sha256'])
 need(review['physical_native_exports']==12 and review['rendered_pages']==48 and review['unique_pixel_pages_actually_viewed']==20 and review['input_identities']==16 and review['blank_original_byte_aliases']==4 and review['clipped_or_lost_content'] is False and review['unexplained_empty_pages'] is False and review['shared_production_registration'] is review['stage_approval'] is review['publication_approval'] is False)
 need(type(review['models']) is int and review['models']==0 and type(review['browser_screenshots']) is int and review['browser_screenshots']==0 and index['Word_owned_instance_quit'] is True and index['frozen_inputs_unchanged'] is True)
 labels={c+'-'+k+'-'+s for c in CODES for k in KINDS for s in ('original','normal','stress')};need({j['label'] for j in m['jobs']}==labels and len(index['pages'])==48 and len(index['text_checks'])==12)
 referenced={'ROOT-WORD-VISUAL-REVIEW.json','ROOT-RENDER-INDEX.json'};allpages=[]
 guides={c:prepare(c,root=root) for c in CODES};originals={(c,k):original(c,k,root=root) for c in CODES for k in KINDS};private_guides={c:private_candidate(c,root=root,private_review=True) for c in CODES}
 for job in m['jobs']:
  code=job['region_code'];kind=job['kind'];role=job['scenario'];need(code in CODES and kind in KINDS and role in {'original','normal','stress'} and job['label']==code+'-'+kind+'-'+role and job['path']=='word/'+job['label']+'.docx')
  guide=guides[code];template=next(t for t in guide['templates'] if t['eligible_own_kind']==kind)
  need(job['source_id']==guide['source_id'] and job['source_url']==guide['source_url'] and job['source_version']==guide['source_version']==m['source_projection_versions'][code] and job['official_version']==guide['official_version']=='1' and job['material_id']==template['material_id'] and job['attachment_id']==template['id'] and job['public_file_unid']==template['public_file_unid'])
  own=originals[(code,kind)];body=read(root,QA+'/'+job['path']);need(job['sha256']==sha256(body).hexdigest() and job['original_sha256']==sha256(own).hexdigest());referenced.add(job['path']);a,b=parts(own),parts(body);need(a.keys()==b.keys() and all(b[n]==v for n,v in a.items() if n!='word/document.xml'))
  if role=='original':need(body==own)
  else:
   need(job['fixture']=='fixtures/'+job['label']+'.json');p=strict_json(read(root,QA+'/'+job['fixture']));need(p['region_code']==code and p['source_id']==guide['source_id'] and p['kind']==kind and p['source_version']==guide['source_version'] and '虚构' in json.dumps(p['data'],ensure_ascii=False));g=deepcopy(private_guides[code]);g['version']=p['version'];contract=private_contract(g,kind,root=root,private_review=True);expected={**contract['context'],'contract_id':contract['contract_id']};need(set(p)==set(expected)|{'data'} and all(type(p[k]) is type(v) and p[k]==v for k,v in expected.items()) and type(p['data']) is dict);data=data_model(kind).model_validate(p['data'],strict=True).model_dump();need(mechanical_fill(own,kind,data)==body);referenced.add(job['fixture'])
   if kind=='evidence' and role=='stress':
    with ZipFile(BytesIO(body)) as z:need('89991' in z.read('word/document.xml').decode('utf8'))
  pages=9 if role=='stress' else 2 if kind=='application' else 1;need(type(job['native_page_count']) is int and job['native_page_count']==pages and len(job['native_pages'])==pages and job['all_fixture_text_preserved'] is True)
  text=next(x for x in index['text_checks'] if x['label']==job['label']);need(text['pages']==pages and text['all_fixture_text_preserved'] is True and text['original_template_empty_pages']==([2] if kind=='application' and role!='stress' else []))
  need([x['page'] for x in job['native_pages']]==list(range(1,pages+1)))
  for row in job['native_pages']:
   need(row['path'].startswith('pages/'+job['label']+'-') and row['path'].endswith('.png'));png=read(root,QA+'/'+row['path']);need(png.startswith(b'\x89PNG\r\n\x1a\n') and sha256(png).hexdigest()==row['sha256']);referenced.add(row['path']);allpages.append((job['label'],row['page'],row['path'],row['sha256']))
 need(referenced==set(m['files']) and len(allpages)==48 and len({x[3] for x in allpages})==20)
 need(set(allpages)=={(r['label'],r['page'],r['path'],r['sha256']) for r in index['pages']})
 need(len(review['reviewed_representatives'])==20 and {r['sha256'] for r in review['reviewed_representatives']}=={x[3] for x in allpages})
 mapped=[(x['label'],x['page'],x['path'],x['sha256']) for group in review['identical_pixel_pages_mapping'] for x in group['identical_pages']];need(len(mapped)==48 and set(mapped)==set(allpages))
 identities=m['input_identities'];need(len(identities)==16 and len({x['label'] for x in identities})==16 and len(m['blank_aliases'])==4)
 for a in m['blank_aliases']:
  need(a['region_code'] in CODES and a['kind'] in KINDS and a['label']==a['region_code']+'-'+a['kind']+'-blank' and a['alias_of']==a['region_code']+'-'+a['kind']+'-original');job=next(j for j in m['jobs'] if j['label']==a['alias_of']);need(a['sha256']==job['sha256'])
 return m

# Cache only immutable semantic Word verification; authority remains uncached.
from hq_word_semantic_cache import wrap_semantic_word
verify_word = wrap_semantic_word(verify_word)
