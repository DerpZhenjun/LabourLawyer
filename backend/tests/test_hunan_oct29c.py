"""C own-source binding and deterministic worker-form safeguards."""
import json,tempfile,unittest,shutil
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import regional_hunan_oct29c as hn

class HunanOct29cTests(unittest.TestCase):
 def pair(self,name='yuhua'):
  g=hn.with_capabilities(hn.parse_capture(name));return g,next(t for t in g['templates'] if t['can_generate'])
 def test_own_source_and_auth_boundary(self):
  for name,s in hn.SPECS.items():
   g,t=self.pair(name)
   self.assertEqual(g['region_code'],s['code']);self.assertEqual(len(g['materials']),4)
   self.assertEqual(len(g['templates']),4);self.assertEqual(sum(t['can_generate'] for t in g['templates']),1)
   self.assertEqual(g['channel']['online_status'],'auth_required');self.assertFalse(g['channel']['submitted'])
   self.assertEqual(g['evidence_template_status'],'not_found_in_checked_sources')
 def test_cross_district_same_bytes_rejected(self):
  a,ta=self.pair();b,tb=self.pair('wangcheng')
  self.assertEqual(ta['sha256'],tb['sha256']);self.assertIsNone(hn.blank_binding(a,tb))
  for t in a['templates']:
   if t['id']!=ta['id']:self.assertIsNone(hn.blank_binding(a,t))
 def test_official_facts_tamper_rejected_lifecycle_ignored(self):
  g,t=self.pair()
  for key in ['authority','source_url','region_code','service_code']:
   c=deepcopy(g);c[key]='wrong';self.assertIsNone(hn.blank_binding(c,t),key)
  for key in ['fields','materials','evidence','sections']:
   c=deepcopy(g);c.pop(key);self.assertIsNone(hn.blank_binding(c,t),key)
  c=deepcopy(g);c.update(published=True,version=999,publication_status='published',candidate_web_qa='PASS',warnings=['lifecycle'])
  self.assertEqual(hn.blank_binding(c,t),'application')
 def test_clean_root_and_no_fallback(self):
  g,t=self.pair()
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises((ValueError,OSError)):hn.parse_capture('yuhua',Path(tmp))
   with patch.object(hn,'ROOT',Path(tmp)):self.assertIsNone(hn.blank_binding(g,t))
 def test_missing_or_altered_derived_closes_capability(self):
  g,t=self.pair()
  with patch.object(hn,'_derived',side_effect=ValueError('changed')):self.assertIsNone(hn.blank_binding(g,t))
 def test_public_only_root_loads_and_tampered_source_fails(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);public=json.loads((hn.ROOT/hn.REPORT/'PUBLIC-WHITELIST.json').read_text('utf8'))['files']
   paths=list(public)+[hn.REPORT+'/PUBLIC-WHITELIST.json',hn.ADAPTATION+'/DERIVED-MANIFEST.json']
   paths += [x['file'] for x in json.loads((hn.ROOT/hn.ADAPTATION/'DERIVED-MANIFEST.json').read_text('utf8'))['files']]
   for rel in paths:
    dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(hn.ROOT/rel,dest)
   with patch.object(hn,'ROOT',root):
    g,t=self.pair();self.assertEqual(hn.blank_binding(g,t),'application')
    p=root/hn.REPORT/'yuhua/guide/page.json';p.write_bytes(p.read_bytes()+b' ')
    self.assertIsNone(hn.blank_binding(g,t))
 def test_exact_contract_rejects_unrepresented_fields(self):
  g,t=self.pair()
  for data in [{'idNumber':'123'},{'submitterName':'forbidden'},{'address':'old alias'}, {'factsReason':'测'*1801}, {'requests':['x']*9}, {'evidenceList':[{}]*11}, {'evidenceList':[{'unknown':'x'}]}, {'applicantName':'x'*161}, {'requests':[12]}, {'applicantName':'\x00'}]:
   with self.assertRaises(ValueError,msg=str(data)[:60]):hn.fill_document(g,t,'application',hn.ROOT/t['file'],data)
 def test_preserved_package_fill_and_original_unchanged(self):
  for name in hn.SPECS:
   g,t=self.pair(name);source=hn.ROOT/t['file'];before=source.read_bytes()
   data={'applicantName':'林虚构','respondentName':'虚构星禾公司','requests':['请求虚构工资100元。'],'factsReason':'软件测试虚构事实。','evidenceList':[{'name':'虚构合同','source':'虚构保存','purpose':'虚构证明'}]}
   with tempfile.TemporaryDirectory() as tmp:
    output=Path(tmp)/'filled.docx';hn.fill_document(g,t,'application',source,data).save(output)
    _,derived=hn._derived(name)
    with ZipFile(derived) as a,ZipFile(output) as b:
     self.assertEqual(set(a.namelist()),set(b.namelist()))
     self.assertEqual([n for n in a.namelist() if a.read(n)!=b.read(n)],['word/document.xml'])
     xml=b.read('word/document.xml').decode();self.assertIn('林虚构',xml);self.assertIn('虚构证明',xml)
   self.assertEqual(before,source.read_bytes())
 def test_wrong_path_and_evidence_kind_rejected(self):
  g,t=self.pair()
  with self.assertRaises(ValueError):hn.fill_document(g,t,'application',hn.ROOT/'wrong.doc',{})
  with self.assertRaises(ValueError):hn.fill_document(g,t,'evidence',hn.ROOT/t['file'],{})

if __name__=='__main__':unittest.main()
