"""Own Huian/Quangang API-bound review proposal. No stage/publication approval."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from lxml import etree as E
import json,shutil,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
IDENTITIES = {'350521': ('惠安县', '5a2049b6dd7a240d496c29d7', '11350521003825518W400201430200Y01', '惠安县人力资源和社会保障局', 'E7C8BF6056DBB7E17359DBDEB9F3CDDC', '9D2094A6856CE70EEFB065965B549417', 'A1FB6544199320AA309480566D3FDAF0', '3C7BF28B410DDBA48A6246EAFD4123C0'), '350505': ('泉港区', '4f9f8144ec2ae19a7f2e70cf', '11350505726453922H400201430200Y01', '泉州市泉港区人力资源和社会保障局', 'F3257A076DAB3D331C48D9A05BBECB38', 'AC4FB9C53EA01E760AAA60964DA50D65', '8BBAA03DFD19C7A087D9AF00E820F89D', '16BFF472076352C1A92C3BBA1E6921C1')}

class OwnSourceTests(unittest.TestCase):
 def temp_root(self):
  t=tempfile.TemporaryDirectory(prefix='HQ-public-only-tamper-');self.addCleanup(t.cleanup);root=Path(t.name)/'root';root.mkdir()
  for name in self.own.source_files(ROOT):
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
  return root

 @classmethod
 def setUpClass(cls):
     import regional_fujian_huian_quangang_nov1 as own
     cls.own = own

 def test_own_actual_versions_material_attachment_IDs_preserved(self):
     for code, (district, sid, service, authority, mid, aid, emid, eaid) in IDENTITIES.items():
         g = self.own.prepare_candidate(code, root=ROOT)
         self.assertEqual((g['district'], g['source_id'], g['service_code'], g['authority']), (district, sid, service, authority))
         self.assertEqual(g['official_version'], '1')
         self.assertFalse(g['committee_autofill_allowed'])
         self.assertIsNone(g['committee_full_name'])
         self.assertFalse(g['published'])
         self.assertFalse(g['can_generate'])
         rows = {t['eligible_own_kind']: t for t in g['templates'] if t['eligible_own_kind']}
         self.assertEqual((rows['application']['material_id'], rows['application']['id']), (mid, aid))
         self.assertEqual((rows['evidence']['material_id'], rows['evidence']['id']), (emid, eaid))
         self.assertEqual(len(g['materials']), 3)
         self.assertEqual(len(g['templates']), 6)
         for material in g['materials']:
             self.assertTrue(material['official_material_id'])
             self.assertIsNone(material['legal_default_copies'])
             self.assertEqual(material['source_id'], sid)

 def test_II_pre_review_link_not_generic_III_IV_submission_permission(self):
     for code in IDENTITIES:
         g = self.own.prepare_candidate(code, root=ROOT)
         ch = g['channel']
         self.assertEqual(ch['raw_value'], '窗口办，网上办，邮寄办')
         self.assertEqual(ch['online_depth_raw'], '材料预审（Ⅱ级）')
         self.assertEqual(ch['service_linked_accept_types'], ['02'])
         self.assertEqual(ch['generic_dictionary_types'], ['03', '04'])
         self.assertFalse(ch['submission_verified'])
         self.assertIsNone(ch['entry_url'])
         self.assertEqual(ch['observed_auth_boundary'], 'https://iam.e-govt.cn:8901/login')
         self.assertEqual(g['fields']['现场次数']['raw_value'], '1')
     q = self.own.prepare_candidate('350505', root=ROOT)
     self.assertEqual(q['UI_observations']['portal_header_observed'], '惠安县')
     self.assertEqual(q['region_code'], '350505')
     self.assertEqual(q['fields']['现场原因']['raw_value'], '需现场查验申请材料。')

 def test_only_two_verified_own_formats_are_private_candidates(self):
     for code in IDENTITIES:
         with self.assertRaises(PermissionError):
             self.own.private_candidate(code, root=ROOT)
         g = self.own.private_candidate(code, root=ROOT, private_review=True)
         self.assertFalse(g['published'])
         self.assertEqual(sum((t['can_generate'] for t in g['templates'])), 2)
         self.assertEqual(sum((t['file'] is None for t in g['templates'])), 4)
         for method in [self.own.staged_candidate, self.own.published_guide]:
             with patch.object(self.own, 'STAGE_SHA256', None), patch.object(self.own, 'PUBLICATION_SHA256', None), self.assertRaises(PermissionError):
                 method(code, root=ROOT)

 def test_missing_or_tampered_safe_source_or_own_original_rejected(self):
     root = self.temp_root()
     names = self.own.source_files(root)
     for name in [names[0], next((n for n in names if n.endswith('safe-material-list.json'))), next((n for n in names if n.endswith('application-format-public-retrieval.docx')))]:
         p = root / name
         body = p.read_bytes()
         p.write_bytes(body + b'TEMP_TAMPER')
         for code in IDENTITIES:
             with self.subTest(path=p.name, code=code), self.assertRaises((ValueError, OSError)):
                 self.own.source_files(root)
         p.write_bytes(body)

 def test_foreign_material_or_same_Word_SHA_cannot_borrow_own_scope(self):
     a = self.own.envelope('350521', 'application', {}, version=1, root=ROOT)
     b = self.own.envelope('350505', 'application', {}, version=1, root=ROOT)
     self.assertEqual(a['template_sha256'], b['template_sha256'])
     for key in ['source_id', 'source_version', 'template_id', 'district', 'schema_id']:
         bad = {**a, key: b[key]}
         with self.subTest(key=key), self.assertRaises(ValueError):
             self.own.validate_request(bad, root=ROOT)
     bad = {**a, 'data': {'material_id': IDENTITIES['350505'][4]}}
     with self.assertRaises(ValueError):
         self.own.validate_request(bad, root=ROOT)

 def test_full15_contract_and_actual_Temp_store_versions(self):
     from regional_guides import RegionalStore
     t = tempfile.TemporaryDirectory(prefix='HQ-own-contract-')
     self.addCleanup(t.cleanup)
     store = RegionalStore(Path(t.name) / 'regional.sqlite')
     for code in IDENTITIES:
         guide = self.own.private_candidate(code, root=ROOT, private_review=True)
         g = store.put_guide(guide)
         for kind in ['application', 'evidence']:
             c = self.own.build_contract(g, kind, root=ROOT, private_review=True)
             self.assertEqual(len(c['context']), 15)
             self.assertEqual(c['context']['source_id'], IDENTITIES[code][1])
             self.assertEqual(c['context']['version'], g['version'])
             self.assertFalse(c['policy']['capacity_is_official_requirement'])
             self.assertFalse(c['policy']['committee_autofill_allowed'])
             env = {**c['context'], 'contract_id': c['contract_id'], 'data': c['defaults']}
             self.own.validate_request(env, root=ROOT)

 def test_strict_types_unknown_context_XML_and_unsupported_legal_slots_rejected(self):
     a = self.own.envelope('350521', 'application', {}, version=1, root=ROOT)
     for change in [{'version': True}, {'version': '1'}, {'version': 0}, {'schema_version': True}, {'extra': 'x'}, {'contract_id': '0' * 64}, {'data': {'applicantName': 42}}, {'data': {'applicantName': 'bad\x00xml'}}, {'data': {'committeeName': 'invented'}}, {'data': {'signature': 'x'}}, {'data': {'copyCount': 2}}]:
         with self.subTest(keys=list(change)), self.assertRaises(ValueError):
             self.own.validate_request({**a, **change}, root=ROOT)

 def test_layout_capacity_rejects_fourth_request_and_tenth_evidence_row(self):
     for kind, data in [('application', {'requests': ['x'] * 4}), ('evidence', {'evidenceList': [{'name': 'x'}] * 10}), ('evidence', {'evidenceList': [{'pageCount': '0'}]}), ('evidence', {'evidenceList': [{'pageCount': True}]}), ('evidence', {'evidenceList': [{'originalType': 'other'}]})]:
         env = self.own.envelope('350521', kind, {}, version=1, root=ROOT)
         env['data'] = data
         with self.subTest(kind=kind, data_type=list(data)), self.assertRaises(ValueError):
             self.own.validate_request(env, root=ROOT)

 def test_exact_own_blank_bytes_and_normal_DOCX_protected_parts(self):
     for code in IDENTITIES:
         for kind in ['application', 'evidence']:
             blank = self.own.envelope(code, kind, self.own.defaults(kind), version=1, root=ROOT)
             original = self.own.original_bytes(code, kind, root=ROOT)
             with self.assertRaises(PermissionError):
                 self.own.candidate_fill(blank, root=ROOT)
             self.assertEqual(self.own.candidate_fill(blank, root=ROOT, private_review=True), original)
             normal = self.own.envelope(code, kind, self.own.example_data(kind), version=1, root=ROOT)
             out = self.own.candidate_fill(normal, root=ROOT, private_review=True)
             with ZipFile(BytesIO(original)) as a, ZipFile(BytesIO(out)) as b:
                 self.assertIsNone(b.testzip())
                 self.assertEqual(a.namelist(), b.namelist())
                 for name in a.namelist():
                     if name != 'word/document.xml':
                         self.assertEqual(a.read(name), b.read(name))
                     if name.endswith('.xml') or name.endswith('.rels'):
                         E.fromstring(b.read(name), E.XMLParser(resolve_entities=False, no_network=True))
                 self.assertIn('虚构', b.read('word/document.xml').decode('utf8'))

 def test_exact_observed_source_URL_query_order_uses_project_digest(self):
     from regional_guides import digest
     urls = {'350521': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?infoType=1&unid=A917E510341EA05C46948B616C3BE489', '350505': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?infoType=1&unid=746DE402C70F4CCCDFFDB52EA51A431A'}
     for code, url in urls.items():
         g = self.own.prepare_candidate(code, root=ROOT)
         self.assertEqual(g['source_url'], url)
         self.assertEqual(digest(url)[:24], IDENTITIES[code][1])
         self.assertNotEqual(digest(url.replace('?infoType=1&unid=', '?unid=') + '&infoType=1')[:24], g['source_id'])

 def test_model_limits_reject_text_overflow_and_keep_unknown_legal_slots_closed(self):
     for kind, data in [('application', {'applicantName': 'x' * 181}), ('application', {'requests': ['x' * 361]}), ('application', {'factsReason': 'x' * 2401}), ('evidence', {'evidenceList': [{'name': 'x' * 61}]}), ('evidence', {'evidenceList': [{'pageCount': '10000'}]}), ('evidence', {'evidenceList': [{'purpose': 'x' * 81}]}), ('evidence', {'evidenceList': [{'pageRange': 'x' * 33}]})]:
         env = self.own.envelope('350505', kind, {}, version=2, root=ROOT)
         env['data'] = data
         with self.subTest(kind=kind), self.assertRaises(ValueError):
             self.own.validate_request(env, root=ROOT)

 def test_original_signature_date_and_unused_paragraphs_survive_normal_fill(self):
     ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
     for code in IDENTITIES:
         for kind in ['application', 'evidence']:
             original = self.own.original_bytes(code, kind, root=ROOT)
             env = self.own.envelope(code, kind, self.own.example_data(kind), version=1, root=ROOT)
             filled = self.own.candidate_fill(env, root=ROOT, private_review=True)
             with ZipFile(BytesIO(original)) as a, ZipFile(BytesIO(filled)) as b:
                 ap = E.fromstring(a.read('word/document.xml')).findall('w:body/w:p', ns)
                 bp = E.fromstring(b.read('word/document.xml')).findall('w:body/w:p', ns)
                 self.assertEqual(len(ap), len(bp))
                 protected = set(range(len(ap))) - ({2, 3, 4, 7, 8, 9, 11} if kind == 'application' else set())
                 for index in protected:
                     self.assertEqual(E.tostring(ap[index]), E.tostring(bp[index]))
