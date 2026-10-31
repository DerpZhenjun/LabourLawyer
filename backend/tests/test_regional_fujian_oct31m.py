"""Putian M own public-source/provider contracts; no raw/private runtime input."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import json, shutil, tempfile, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
try:import regional_fujian_oct31m as own
except ModuleNotFoundError:own=None

class PutianOwnProviderTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(own,'Own formal M provider missing')
    def clone(self):
        temp=tempfile.TemporaryDirectory(prefix='m-own-cold-');self.addCleanup(temp.cleanup);root=Path(temp.name)
        for rel in own.source_files(ROOT):
            dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dst)
        return root
    def test_own_identity_service_Y01_vs201_and_qualification(self):
        for code,suffix,district in [('350302','Y01','城厢区'),('350303','201','涵江区')]:
            g=own.parse_capture(code,root=ROOT);self.assertEqual((g['city'],g['district']),('莆田市',district));self.assertTrue(g['service_code'].endswith(suffix));self.assertFalse(g['can_generate']);self.assertFalse(g['published']);self.assertIsNone(g['official_version']);self.assertIsNone(g['committee_full_name']);self.assertEqual(g['verification_status'],'partial')
            source=json.loads((ROOT/own.SOURCE_BASE/own.REGIONS[code]['folder']/'own-guide.json').read_bytes())
            self.assertEqual(g['collected_at'],source['observed_at_utc']);self.assertEqual(g['verified_at'],source['observed_at_utc'])
    def test_eighteen_self_contained_source_files_and_cold_root(self):
        self.assertEqual(len(own.source_files(ROOT)),18);cold=self.clone()
        for code in own.REGIONS:self.assertEqual(len(own.source_files(cold,code)),9);self.assertEqual(own.parse_capture(code,root=cold)['region_code'],code)
        for root in [None,'']:
            with self.assertRaises(ValueError):own.parse_capture('350302',root=root)
    def test_phase_independent_raw_source_and_missing_approval_refuse(self):
        self.assertRegex(own.WORD_SHA,r'^[a-f0-9]{64}$');self.assertRegex(own.STAGE_SHA256,r'^[a-f0-9]{64}$');self.assertEqual(own.PUBLICATION_SHA256,'7a9a65f57253d24588014dd254471f039ac40099cad319706f2ea10afb98c813')
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertFalse(own.with_capabilities(g,root=ROOT)['can_generate'])
            stage=own.staged_candidate(code,root=ROOT);self.assertTrue(stage['can_generate']);self.assertFalse(stage['published'])
            self.assertEqual([t['document_types'] for t in stage['templates'] if t['can_generate']],[['application'],['evidence']])
            self.assertTrue(all(t['material_id'] is None for t in stage['templates']))
            published=own._published(code,ROOT);self.assertTrue(published['published']);self.assertTrue(published['can_generate']);self.assertEqual(published['verification_status'],'partial')
            with patch.object(own,'STAGE_SHA256',None),patch.object(own,'WORD_SHA',None):
                with self.assertRaises(ValueError):own.staged_candidate(code,root=ROOT)
                with self.assertRaises(ValueError):own.checked_adapter(g,g['templates'][0],'application',root=ROOT)
            with patch.object(own,'PUBLICATION_SHA256',None):
                with self.assertRaises(ValueError):own.with_publication_evidence(g,root=ROOT)
    def test_unknown_official_material_ID_local_keys_and_copies_notes(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertEqual([m['copies'] for m in g['materials']],['原件份数2份','原件份数2份','复印件份数2份'])
            for i,m in enumerate(g['materials'],1):self.assertIsNone(m['material_id']);self.assertIsNone(m['official_material_id']);self.assertEqual(m['id'],g['source_id']+':dom-material:'+str(i));self.assertEqual(m['id_kind'],'local_source_row_pointer_not_official_ID')
            self.assertIn('被申请人人数',g['materials'][0]['instructions']);self.assertIn('当事人人数',g['materials'][1]['instructions'])
    def test_source_fields_provenance_sections_and_auth_boundary(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertTrue(g['sections']);self.assertEqual(g['channel']['online_status'],'auth_required');self.assertIsNone(g['channel']['entry_url']);self.assertFalse(g['channel']['submission_verified'])
            for field in g['fields'].values():self.assertEqual(field['source_id'],g['source_id']);self.assertEqual(field['region_code'],code);self.assertEqual(field['verification_status'],'observed_unverified');self.assertIsNone(field['normalized_value']);self.assertRegex(field['capture_sha256'],r'^[a-f0-9]{64}$')
    def test_own_fee_time_window_and_visit_display_uses_only_own_raw(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);f=g['fields'];self.assertEqual(f['是否收费']['raw_value'],'不收费');self.assertEqual(f['到办事现场次数']['raw_value'],'1 次');self.assertEqual(f['承诺办结时限']['raw_value'],f['承诺时限']['raw_value']);self.assertEqual(f['法定办结时限']['raw_value'],f['法定时限']['raw_value']);self.assertEqual(f['咨询方式']['raw_value'],f['联系电话']['raw_value']);self.assertIn(g['district'],f['办理地点']['raw_value']);self.assertTrue(f['办理时间']['raw_value']);self.assertTrue(f['交通指引']['raw_value']);self.assertEqual(f['是否收费']['verification_status'],'observed_unverified')
    def test_every_field_capture_hash_matches_its_exact_public_file(self):
        for code in own.REGIONS:
            for field in own.parse_capture(code,root=ROOT)['fields'].values():self.assertEqual(sha256((ROOT/field['capture_file']).read_bytes()).hexdigest(),field['capture_sha256'])
    def test_raw_time_compatible_visits_and_admin_wording_not_rules(self):
        a=own.parse_capture('350302',root=ROOT);b=own.parse_capture('350303',root=ROOT);self.assertEqual(a['qualifications']['time']['raw_explanation'],'60');self.assertIsNone(a['qualifications']['time']['normalized_legal_deadline']);self.assertEqual(a['qualifications']['visits']['relationship'],'compatible_different_scopes');self.assertFalse(a['qualifications']['issue_event_created']);self.assertIn('行政确认',b['qualifications']['administrative_wording']['raw'][0])
    def test_originals_and_blank_defaults_exact(self):
        for code in own.REGIONS:
            for kind in own.TEMPLATES:
                raw=own.original_bytes(code,kind,root=ROOT);self.assertEqual(own.template_path(code,kind,root=ROOT).read_bytes(),raw);self.assertTrue(own.inspect_blank(code,kind,root=ROOT)['CRC']);self.assertEqual(own.candidate_fill(own.envelope(code,kind,own.defaults(code,kind),root=ROOT),root=ROOT),raw)
    def test_regenerated_normal_stress_own_tuple_and_complete_ZIP_members(self):
        for code in own.REGIONS:
            for kind in own.TEMPLATES:
                for stress in [False,True]:
                    data=own.example_data(code,kind,stress,root=ROOT);self.assertIn('虚构',json.dumps(data,ensure_ascii=False));e=own.envelope(code,kind,data,root=ROOT);self.assertNotIn('.runtime',json.dumps(e));self.assertTrue(e['schema_id'].startswith('fujian-m-'));self.assertIsNone(e['material_id']);raw=own.original_bytes(code,kind,root=ROOT);filled=own.candidate_fill(e,root=ROOT)
                    with ZipFile(BytesIO(raw)) as a,ZipFile(BytesIO(filled)) as b:
                        self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist())
                        for n in a.namelist():
                            if n!='word/document.xml':self.assertEqual(a.read(n),b.read(n))
                    own._layout_assert_protected(raw,filled,kind)
    def test_cross_own_sources_both_directions_and_kinds_refuse(self):
        for code,other in [('350302','350303'),('350303','350302')]:
            for kind in own.TEMPLATES:
                e=own.envelope(code,kind,{},root=ROOT);f=own.envelope(other,kind,{},root=ROOT)
                for key in ['district','source_id','source_version','service_code','authority','schema_id','schema_sha256','local_material_key']:
                    bad=deepcopy(e);bad[key]=f[key]
                    with self.subTest(code=code,kind=kind,key=key),self.assertRaises(ValueError):own.candidate_fill(bad,root=ROOT)
    def test_wrong_template_version_mode_schema_and_invented_materialID(self):
        good=own.envelope('350302','application',{},root=ROOT)
        for key,val in [('material_id','INVENTED'),('template_id','CC300F5D9DD5DC404D65C68116D50C55'),('template_sha256','0'*64),('schema_version',True),('schema_sha256','0'*64),('mode','reference_adaptation'),('template_version','old')]:
            bad=deepcopy(good);bad[key]=val
            with self.subTest(key=key),self.assertRaises(ValueError):own.candidate_fill(bad,root=ROOT)
    def test_samples_and_scanning_instruction_never_blank_permission(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertEqual(len(g['templates']),6);self.assertEqual(g['templates'][4]['sha256'],g['templates'][5]['sha256'])
            for t in g['templates']:self.assertFalse(t['can_generate']);self.assertEqual(t['document_types'],[]);self.assertIsNone(t['material_id'])
            self.assertFalse(own.approved_report_attachment(g,g['templates'][1],ROOT));self.assertFalse(own.approved_report_attachment(g,g['templates'][4],ROOT));self.assertTrue(own.approved_report_attachment(g,g['templates'][0],ROOT))
    def test_one_evidence_capacity_not_legal_rule(self):
        for code in own.REGIONS:
            self.assertEqual(len(own.defaults(code,'evidence')['evidenceList']),1);s=own.schema_descriptor(code,'evidence');self.assertFalse(s['policy']['capacity_is_official_requirement']);self.assertEqual(s['fields'][0]['maxItems'],9)
    def test_unknown_signature_date_committee_copies_and_XML(self):
        for data in [{'signature':'x'},{'applicationDate':'2026-01-01'},{'committeeName':'x'},{'copies':2},{'factsReason':'bad\0text'},{'applicantName':False},{'requests':['x']*4}]:
            with self.subTest(data=data),self.assertRaises(ValueError):own.candidate_fill(own.envelope('350303','application',data,root=ROOT),root=ROOT)
    def test_evidence_page_type_option_capacity_and_unknown_refuse(self):
        for rows in [[{'pageCount':x}] for x in [1,True,'0','01','1.5','10000']]+[[{'originalType':'other'}],[{'unknown':'x'}],[{}]*10]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):own.candidate_fill(own.envelope('350302','evidence',{'evidenceList':rows},root=ROOT),root=ROOT)
    def test_tampered_source_manifest_original_and_proof_refuse(self):
        for name in ['SOURCE-PROJECTION-MANIFEST.json','application-own-format.docx','SOURCE-PROOF-SUPPLEMENT.json']:
            cold=self.clone();f=cold/own.SOURCE_BASE/own.REGIONS['350302']['folder']/name;f.write_bytes(f.read_bytes()+b' ')
            with self.subTest(name=name),self.assertRaises(ValueError):own.parse_capture('350302',root=cold)
    def test_unknown_code_kinds_and_path_escape_refuse(self):
        for code in ['350302 ',350302,'350128',None]:
            with self.assertRaises(ValueError):own.parse_capture(code,root=ROOT)
        for kind in ['sample','reference',None]:
            with self.assertRaises(ValueError):own.envelope('350302',kind,{},root=ROOT)
        for path in ['../x','C:/private/x']:
            with self.assertRaises(ValueError):own.path_at(ROOT,path)
    def test_public_source_json_no_private_paths_or_sensitive_query(self):
        for rel in own.source_files(ROOT):
            if rel.endswith('.json'):
                text=(ROOT/rel).read_text('utf8');self.assertNotIn('.runtime/',text);self.assertNotIn('DerpZhenjun',text);self.assertNotIn('x-wbsign-fileunid',text.lower());self.assertNotIn('access_token=',text.lower());self.assertNotIn('cookie',text.lower())
    def test_forged_source_capabilities_and_receipts_refuse(self):
        g=own.parse_capture('350302',root=ROOT)
        for key,val in [('can_generate',True),('published',True),('source_version','0'*64)]:
            bad=deepcopy(g);bad[key]=val
            with self.assertRaises(ValueError):own.with_capabilities(bad,root=ROOT)
        bad=deepcopy(g);bad['candidate_adapter_evidence']={'sha256':'0'*64}
        self.assertIsNone(own.public_evidence(bad,ROOT))

if __name__=='__main__':unittest.main(verbosity=2)
