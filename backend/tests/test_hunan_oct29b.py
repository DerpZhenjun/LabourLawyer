"""Own Hunan source, double-label scope and derived worker-package safeguards."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from zipfile import ZipFile
from regional_hunan_oct29b import ROOT,REPORT,SPECS,Evidence,parse_capture,with_capabilities,blank_binding,fill_document

class HunanOct29bTests(unittest.TestCase):
 def test_own_materials_originals_and_boundary(self):
  for name,s in SPECS.items():
   g=with_capabilities(parse_capture(name))
   self.assertEqual(len(g['materials']),4);self.assertEqual(len(g['templates']),4)
   self.assertEqual(sum(t['can_generate'] for t in g['templates']),1)
   self.assertEqual(sum(t['official_kind']=='sample' for t in g['templates']),2)
   self.assertFalse(g['published']);self.assertEqual(g['channel']['online_status'],'auth_required')
   self.assertEqual(g['evidence_template_status'],'not_found_in_checked_sources')
 def test_xiangjiang_double_label_is_local_not_inherited(self):
  g=with_capabilities(parse_capture('xiangjiang'));t=next(t for t in g['templates'] if t['can_generate'])
  self.assertEqual(g['scope_identity']['portal_area_label'],'湖南湘江新区')
  self.assertEqual(g['scope_identity']['selector_area_label'],'岳麓区')
  self.assertEqual(g['scope_identity']['portal_area_code'],'430104999000')
  for k,v in [('district','湖南省'),('region_code','430102'),('authority','岳麓区人力资源和社会保障局')]:
   changed=deepcopy(g);changed[k]=v;self.assertIsNone(blank_binding(changed,t),k)
  changed=deepcopy(g);changed['scope_identity']['portal_area_code']='430100000000';self.assertIsNone(blank_binding(changed,t))
 def test_same_original_bytes_do_not_bind_other_district(self):
  a=with_capabilities(parse_capture('tianxin'));b=with_capabilities(parse_capture('xiangjiang'))
  ta=next(t for t in a['templates'] if t['can_generate']);tb=next(t for t in b['templates'] if t['can_generate'])
  self.assertEqual(ta['sha256'],tb['sha256']);self.assertIsNone(blank_binding(a,tb))
  for t in a['templates']:
   if t['id']!=ta['id']:self.assertIsNone(blank_binding(a,t))
 def test_generic_or_previous_region_body_not_accepted(self):
  original=Evidence.load
  def load(e,relative):
   p=original(e,relative)
   if relative=='xiangjiang/formal-initial/page.json':p['text']=p['text'].replace(SPECS['xiangjiang']['authority'],'人力资源社会保障部门')
   return p
  with patch.object(Evidence,'load',load):
   with self.assertRaisesRegex(ValueError,'通用/其他地区正文'):parse_capture('xiangjiang')
 def test_missing_derived_closes_capability(self):
  g=with_capabilities(parse_capture('tianxin'));t=next(t for t in g['templates'] if t['can_generate'])
  with patch('regional_hunan_oct29b._derived',side_effect=FileNotFoundError):self.assertIsNone(blank_binding(g,t))
 def test_actual_fill_preserves_packages_signatures_and_downloads(self):
  for name in SPECS:
   g=with_capabilities(parse_capture(name));t=next(t for t in g['templates'] if t['can_generate']);path=ROOT/t['file'];before=path.read_bytes()
   data={'applicantName':'虚构测试甲','respondentName':'虚构测试乙','gender':'女','birthDate':'1990-01-02','nationality':'汉族',
      'committeeName':'虚构测试仲裁委员会','applicationDate':'2026-10-29','requests':['虚构测试请求100元。'],
      'factsReason':'全部为软件排版测试虚构内容。','submitterName':'不得自动填入手签','evidenceList':[{'name':'虚构证据甲','source':'虚构来源','purpose':'虚构证明目的'}]}
   with tempfile.TemporaryDirectory(dir=ROOT/REPORT) as tmp:
    p=Path(tmp)/'filled.docx';fill_document(g,t,'application',path,data).save(p)
    derived=ROOT/REPORT/'derived'/name/'1624951667887.docx'
    with ZipFile(derived) as a,ZipFile(p) as b:
     self.assertEqual(set(a.namelist()),set(b.namelist()));self.assertEqual([n for n in a.namelist() if a.read(n)!=b.read(n)],['word/document.xml'])
     xml=b.read('word/document.xml').decode('utf8');self.assertIn('虚构测试甲',xml);self.assertIn('100元',xml);self.assertNotIn('不得自动填入手签',xml)
   self.assertEqual(path.read_bytes(),before)
 def test_arbitrary_path_and_capacity_refused(self):
  g=with_capabilities(parse_capture('tianxin'));t=next(t for t in g['templates'] if t['can_generate'])
  with self.assertRaises(ValueError):fill_document(g,t,'application',ROOT/'other.doc',{})
  with self.assertRaises(ValueError):fill_document(g,t,'evidence',ROOT/t['file'],{})
  with self.assertRaises(ValueError):fill_document(g,t,'application',ROOT/t['file'],{'factsReason':'测'*1801})

if __name__=='__main__':unittest.main()
