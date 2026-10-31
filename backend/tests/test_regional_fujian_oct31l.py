"""Pingtan own public-source/provider contracts; no private runtime dependency."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import importlib.util,json,re,shutil,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
try:import regional_fujian_oct31l as own
except ModuleNotFoundError:own=None
REVIEWED={('application',False):'ab6e62f806dfac4f6455a315538980421ee56c72d9deb759a7a7614f6fbf84c1',('application',True):'c663d00422173be9389d77c820d052d7e3f0095bf99f586041ac1ba7ff1970bd',('evidence',False):'41cbe398c9f0fdcd53dc9650af0835a421b091c141747959401a2f1337da31b7',('evidence',True):'5f9b1366ad440118c3dc9b83d8dec83fff1fa46632c305d9daec3293ac40824e'}
class PingtanOwnProviderTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(own,'Own formal L provider not implemented')
 def clone(self):
  t=tempfile.TemporaryDirectory(prefix='l-public-cold-');self.addCleanup(t.cleanup);r=Path(t.name)
  for rel in own.source_files(ROOT):
   dest=r/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
  return r
 def test_own_exact_identity_partial_and_missing_version_committee(self):
  g=own.parse_capture('350128',root=ROOT)
  self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('fujian','平潭综合实验区','平潭综合实验区','350128'))
  self.assertEqual(g['source_id'],'511e7f64c9481b5a0b6ff4a1');self.assertEqual(g['service_code'],'1135012806039606XH300201430200201');self.assertEqual(g['authority'],'平潭综合实验区社会事业局')
  self.assertIsNone(g['official_version']);self.assertIsNone(g['committee_full_name']);self.assertEqual(g['verification_status'],'partial')
 def test_own_seven_source_files_cold_root_no_fallback(self):
  self.assertEqual(len(own.source_files(ROOT)),7);r=self.clone();self.assertEqual(own.parse_capture('350128',root=r)['source_id'],own.SOURCE_ID)
  (r/own.SOURCE_BASE/'own-guide-native-dom.json').unlink()
  with self.assertRaises(ValueError):own.parse_capture('350128',root=r)
  for root in [None,'']:
   with self.assertRaises(ValueError):own.parse_capture('350128',root=root)
 def test_no_public_generation_or_unpinned_approval(self):
  self.assertRegex(own.WORD_SHA,r'^[a-f0-9]{64}$');self.assertRegex(own.STAGE_SHA256,r'^[a-f0-9]{64}$');self.assertIsNone(own.PUBLICATION_SHA256)
  g=own.parse_capture('350128',root=ROOT);self.assertFalse(g['can_generate']);self.assertTrue(all(not t['can_generate'] for t in g['templates']))
  self.assertFalse(own.with_capabilities(g,root=ROOT)['can_generate'])
  stage=own.staged_candidate('350128',root=ROOT);self.assertTrue(stage['can_generate']);self.assertFalse(stage['published'])
  self.assertEqual([t['document_types'] for t in stage['templates'] if t['can_generate']],[['application'],['evidence']])
  with self.assertRaises(ValueError):own._published('350128',root=ROOT)
  with self.assertRaises(ValueError):own.with_publication_evidence(stage,root=ROOT)
  with patch.object(own,'WORD_SHA',None),patch.object(own,'STAGE_SHA256',None):
   with self.assertRaises(ValueError):own.staged_candidate('350128',root=ROOT)
  with self.assertRaises(ValueError):own.with_publication_evidence(g,root=ROOT)
  with self.assertRaises(ValueError):own.checked_adapter(g,g['templates'][0],'application',root=ROOT)
 def test_raw_fields_display_shapes_and_exact_own_aliases(self):
  g=own.parse_capture('350128',root=ROOT)
  for field in g['fields'].values():
   self.assertTrue(set(['raw_value','normalized_value','source_url','region_code','collected_at','verified_at','verification_status'])<=set(field));self.assertEqual(field['region_code'],'350128');self.assertEqual(field['source_url'],g['source_url'])
  self.assertEqual(g['fields']['是否收费']['raw_value'],'不收费');self.assertEqual(g['fields']['到办事现场次数']['normalized_value'],'1 次')
  self.assertEqual(g['fields']['承诺办结时限']['raw_value'].strip(),'受理后5个工作日')
 def test_material_copy_notes_and_six_own_attachments_distinct(self):
  g=own.parse_capture('350128',root=ROOT);self.assertEqual([m['copies'] for m in g['materials']],[2,2,2]);self.assertEqual(len(g['templates']),6)
  self.assertIn('被申请人人数',g['materials'][0]['instructions']);self.assertIn('当事人人数',g['materials'][1]['instructions'])
  self.assertEqual([t['material_id'] for t in g['templates'] if t['eligible_own_kind']],['CAAD35DCD8944729A80E6C5A251CB294','59560ABC219CCB4AF2E8840A20C74607'])
  self.assertTrue(all(t['download_status']=='metadata_only' and t['file'] is None for t in g['templates'] if not t['eligible_own_kind']))
 def test_compatible_visits_no_conflict_or_absence_claim(self):
  g=own.parse_capture('350128',root=ROOT);q=json.loads((ROOT/own.SOURCE_BASE/'SOURCE-QUALIFICATIONS.json').read_bytes())
  self.assertEqual(q['source_conflicts_and_scope_notes'][0]['kind'],'COMPATIBLE_SCOPE_NOTE');self.assertEqual(q['operational_issue_events'],[])
  self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url']);self.assertFalse(g['channel']['submission_verified'])
  self.assertFalse(any('官网不提供' in s or 'OFFICIAL_SOURCE_CONFLICT' in s for s in g['warnings']))
 def test_new_public_envelopes_generate_all_four_reviewed_Word_exact_SHA(self):
  for (kind,stress),pin in REVIEWED.items():
   data=own.example_data('350128',kind,stress,root=ROOT);e=own.envelope('350128',kind,data,root=ROOT)
   self.assertEqual(e['source_version'],own.SOURCE_SHA);self.assertNotIn('.runtime',json.dumps(e));self.assertNotIn('private-v',e['schema_id'])
   self.assertEqual(sha256(own.candidate_fill(e,root=ROOT)).hexdigest(),pin)
 def test_original_blank_and_every_unrelated_ZIP_part_exact(self):
  for kind in ['application','evidence']:
   old=own.original_bytes('350128',kind,root=ROOT)
   self.assertEqual(own.candidate_fill(own.envelope('350128',kind,own.defaults('350128',kind),root=ROOT),root=ROOT),old)
   new=own.candidate_fill(own.envelope('350128',kind,own.example_data('350128',kind,root=ROOT),root=ROOT),root=ROOT)
   with ZipFile(BytesIO(old)) as a,ZipFile(BytesIO(new)) as b:
    self.assertEqual(a.namelist(),b.namelist());self.assertIsNone(b.testzip())
    for n in a.namelist():
     if n!='word/document.xml':self.assertEqual(a.read(n),b.read(n))
 def test_cross_city_region_K_source_material_schema_template_rejected(self):
  good=own.envelope('350128','application',own.example_data('350128','application',root=ROOT),root=ROOT)
  for key,value in [('city','福州市'),('district','平潭县'),('region_code','350111'),('source_id','09dcedf106cd2fd411a09546'),('service_code','1135012806039606XH400201430200201'),('material_id','743F21F90A88857531C1B7321E35AD5B'),('template_id','CC300F5D9DD5DC404D65C68116D50C55'),('source_version','0'*64),('schema_version',True),('schema_id','fujian-l-350128-application-word-private-v3'),('template_version','old')]:
   bad=deepcopy(good);bad[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):own.candidate_fill(bad,root=ROOT)
 def test_unknown_code_and_sample_reference_context_refused(self):
  for code in ['350111','350128 ',350128,None]:
   with self.subTest(code=code),self.assertRaises(ValueError):own.parse_capture(code,root=ROOT)
  for kind in ['sample','reference','evidence_list',None]:
   with self.subTest(kind=kind),self.assertRaises(ValueError):own.envelope('350128',kind,{},root=ROOT)
  e=own.envelope('350128','evidence',{},root=ROOT);e['template_id']='D266D62D3E51B38A3C568B47677C4B09'
  with self.assertRaises(ValueError):own.candidate_fill(e,root=ROOT)
 def test_unknown_signature_date_committee_and_invalid_XML_refused(self):
  for key,value in [('signature','禁止代签'),('committeeName','禁止推定'),('applicationDate','2026-10-31'),('factsReason','虚构'+chr(0))]:
   data=own.example_data('350128','application',root=ROOT);data[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):own.candidate_fill(own.envelope('350128','application',data,root=ROOT),root=ROOT)
 def test_default_one_max9_and_pageCount_strict_text(self):
  self.assertEqual(len(own.defaults('350128','evidence')['evidenceList']),1);s=own.schema_descriptor('350128','evidence');self.assertEqual(s['fields'][0]['maxItems'],9);self.assertFalse(s['policy']['capacity_is_official_requirement'])
  for v in [1,True,'01','0','1.5','10000']:
   data=own.example_data('350128','evidence',root=ROOT);data['evidenceList'][0]['pageCount']=v
   with self.subTest(value=v),self.assertRaises(ValueError):own.candidate_fill(own.envelope('350128','evidence',data,root=ROOT),root=ROOT)
 def test_tampered_source_leaf_original_or_manifest_rejected(self):
  for name in ['own-official-bindings.json','application-own-format.docx','SOURCE-PROJECTION-MANIFEST.json']:
   r=self.clone();f=r/own.SOURCE_BASE/name;f.write_bytes(f.read_bytes()+b' ')
   with self.subTest(name=name),self.assertRaises(ValueError):own.parse_capture('350128',root=r)
 def test_public_source_no_private_paths_tokens_or_runtime_dependency(self):
  for name in own.source_files(ROOT):
   if name.endswith('.json'):
    text=(ROOT/name).read_text(encoding='utf8')
    self.assertIsNone(re.search(r'(?<![A-Za-z])[A-Za-z]:[\\/]|/home/|/Users/|\.runtime|x-wbsign|access_token|password|sessionid|signature=',text,re.I))
  g=own.parse_capture('350128',root=ROOT);self.assertEqual(own.public_evidence(g,ROOT)['source_projection_sha256'],own.SOURCE_SHA)
 def test_wrong_source_or_boolean_store_version_with_capability_refused(self):
  g=own.parse_capture('350128',root=ROOT)
  for key,value in [('version',True),('version',0),('city','福州市'),('source_id','0'*24),('official_version','guessed'),('committee_full_name','禁止推定')]:
   bad=deepcopy(g);bad[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):own.with_capabilities(bad,root=ROOT)
if __name__=='__main__':unittest.main()
