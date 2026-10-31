"""Private N own-source/provider proposal; pure local qualification only."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from zipfile import ZipFile
from io import BytesIO
import importlib.util,json,shutil,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
try:import regional_fujian_oct31n as own
except ModuleNotFoundError:own=None
class ProposalNTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(own,'Formal own N provider proposal missing')
    def clone(self):
        t=tempfile.TemporaryDirectory(prefix='n-projection-cold-');self.addCleanup(t.cleanup);r=Path(t.name)
        for rel in own.source_files(ROOT):
            dst=r/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dst)
        return r
    def clone_stage(self):
        r=self.clone()
        for src in (ROOT/own.QA_REPORT).rglob('*'):
            if src.is_file():
                rel=src.relative_to(ROOT);dst=r/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
        return r
    def test_two_own_identities_Y01_and_exact_top_metadata(self):
        expected={'350304':('荔城区','c2f441391f073f71f55ce9de','113503210037128046400201430200Y01'),'350305':('秀屿区','758cc6043c5d57e5574a766e','1135030448877165XX400201430200Y01')}
        for code,(district,source,service) in expected.items():
            g=own.parse_capture(code,root=ROOT);self.assertEqual((g['city'],g['district'],g['source_id'],g['service_code']),('莆田市',district,source,service));self.assertEqual(g['collected_at'],own.REGIONS[code]['observed_at_utc']);self.assertEqual(g['verified_at'],g['collected_at']);self.assertIsNone(g['official_version']);self.assertIsNone(g['committee_full_name']);self.assertFalse(g['can_generate']);self.assertEqual(g['verification_status'],'partial')
    def test_eighteen_cold_source_files_no_private_parent_fallback(self):
        self.assertEqual(len(own.source_files(ROOT)),18);r=self.clone()
        for code in own.REGIONS:self.assertEqual(own.parse_capture(code,root=r)['region_code'],code);self.assertEqual(len(own.source_files(r,code)),9)
        for r in [None,'']:
            with self.assertRaises(ValueError):own.parse_capture('350304',root=r)
    def test_only_formal_module_and_public_source_paths_are_runtime_dependencies(self):
        self.assertEqual(Path(own.__file__).resolve(),ROOT/'backend/regional_fujian_oct31n.py')
        self.assertTrue(all(p.startswith('reports/overnight-gap-closure-20261030/localities/fujian-n-source-projection/') for p in own.source_files(ROOT)))
        self.assertNotIn('.runtime',Path(own.__file__).read_text('utf8'))
    def test_own_stress_examples_are_fictional_and_protected_ZIP_members_exact(self):
        for code in own.REGIONS:
            for kind in own.TEMPLATES:
                data=own.example_data(code,kind,True,root=ROOT);self.assertIn('虚构',json.dumps(data,ensure_ascii=False));self.assertIn(own.REGIONS[code]['district'],json.dumps(data,ensure_ascii=False));e=own.envelope(code,kind,data,root=ROOT);self.assertTrue(e['schema_id'].startswith('fujian-n-'));raw=own.original_bytes(code,kind,root=ROOT);new=own.candidate_fill(e,root=ROOT,private_review=True)
                with ZipFile(BytesIO(raw)) as a,ZipFile(BytesIO(new)) as b:
                    self.assertEqual(a.namelist(),b.namelist());self.assertIsNone(b.testzip());self.assertTrue(all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml'))
                own._layout_assert_protected(raw,new,kind)
                if kind=='application':self.assertEqual(len(data['requests']),3);self.assertEqual(len(data['factsReason']),2400)
                else:self.assertEqual(len(data['evidenceList']),9)
    def test_cross_other_kind_contract_and_full_identity_mismatch_refused(self):
        for code in own.REGIONS:
            a=own.envelope(code,'application',{},root=ROOT);e=own.envelope(code,'evidence',{},root=ROOT)
            for key in ['template_id','template_sha256','schema_id','schema_sha256']:
                bad=deepcopy(a);bad[key]=e[key]
                with self.assertRaises(ValueError):own.validate_request(bad,root=ROOT)
            for key,value in [('province','other'),('city','福州市'),('authority','其他区机关'),('service_code','wrong')]:
                bad=deepcopy(a);bad[key]=value
                with self.assertRaises(ValueError):own.validate_request(bad,root=ROOT)
    def test_every_raw_field_exact_own_cell_unverified_and_capture_SHA(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertGreater(len(g['fields']),40)
            for f in g['fields'].values():self.assertEqual(f['source_id'],g['source_id']);self.assertEqual(f['region_code'],code);self.assertEqual(f['verification_status'],'observed_unverified');self.assertIsNone(f['normalized_value']);self.assertEqual(sha256((ROOT/f['capture_file']).read_bytes()).hexdigest(),f['capture_sha256'])
    def test_own_fee_window_visit_and_time_display_no_M_fact_fallback(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);f=g['fields'];self.assertEqual(f['是否收费']['raw_value'],'不收费');self.assertEqual(f['到办事现场次数']['raw_value'],'1 次');self.assertIn(g['district'],f['办理地点']['raw_value']);self.assertTrue(f['办理时间']['raw_value']);self.assertEqual(f['承诺办结时限']['raw_value'].strip(),'受理后5个工作日');self.assertEqual(f['法定办结时限']['raw_value'].strip(),'受理后5个工作日')
    def test_unknown_official_material_ID_and_own_raw_copies_notes(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertEqual([m['copies'] for m in g['materials']],['原件份数2份','原件份数2份','复印件份数2份'])
            for i,m in enumerate(g['materials'],1):self.assertIsNone(m['material_id']);self.assertIsNone(m['official_material_id']);self.assertEqual(m['id'],g['source_id']+':dom-material:'+str(i));self.assertEqual(m['id_kind'],'local_source_row_pointer_not_official_ID')
            self.assertIn('被申请人人数',g['materials'][0]['instructions']);self.assertIn('当事人人数',g['materials'][1]['instructions'])
    def test_roles_format_sample_scanning_and_no_approval(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertEqual(len(g['templates']),6);self.assertEqual(sum(t['eligible_own_kind'] is not None for t in g['templates']),2)
            for t in g['templates']:self.assertFalse(t['can_generate']);self.assertEqual(t['document_types'],[]);self.assertIsNone(t['material_id'])
            scan=[t for t in g['templates'] if t['content_role']=='scanning_instruction_NOT_blank_template'];self.assertEqual(len(scan),2);self.assertEqual(scan[0]['sha256'],scan[1]['sha256']);self.assertTrue(all(t['file'] is None for t in g['templates'] if t['eligible_own_kind'] is None))
    def test_own_auth_boundary_stops_no_conflict_event(self):
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertEqual(g['channel']['online_status'],'auth_required');self.assertIsNone(g['channel']['entry_url']);self.assertFalse(g['channel']['submission_verified']);self.assertEqual(g['qualifications']['visit_scope_relationship'],'compatible_different_scopes');self.assertEqual(g['qualifications']['operational_issue_events'],[])
    def test_raw_source_and_missing_stage_or_final_approval_always_refuse(self):
        self.assertIsNone(own.PUBLICATION_SHA256)
        for code in own.REGIONS:
            g=own.parse_capture(code,root=ROOT);self.assertFalse(own.with_capabilities(g,root=ROOT)['can_generate'])
            with patch.object(own,'WORD_SHA',None),patch.object(own,'STAGE_SHA256',None):
                with self.assertRaises(ValueError):own.staged_candidate(code,root=ROOT)
            with self.assertRaises(ValueError):own.with_publication_evidence(g,root=ROOT)
            with self.assertRaises(ValueError):own.checked_adapter(g,g['templates'][0],'application',root=ROOT)
    def test_independent_own_stage_exposes_only_four_blank_forms_not_publication(self):
        self.assertRegex(own.WORD_SHA,r'^[a-f0-9]{64}$');self.assertRegex(own.STAGE_SHA256,r'^[a-f0-9]{64}$')
        count=0
        for code in own.REGIONS:
            raw=own.parse_capture(code,root=ROOT);g=own.staged_candidate(code,root=ROOT);self.assertFalse(raw['can_generate']);self.assertTrue(g['can_generate']);self.assertFalse(g['published']);self.assertEqual(g['candidate_adapter_evidence']['sha256'],own.STAGE_SHA256);self.assertTrue(own.with_capabilities(g,root=ROOT)['can_generate'])
            enabled=[t for t in g['templates'] if t['can_generate']];self.assertEqual([t['document_types'] for t in enabled],[['application'],['evidence']]);count+=len(enabled)
            self.assertTrue(all(not t['can_generate'] for t in g['templates'] if t['eligible_own_kind'] is None))
        self.assertEqual(count,4)
    def test_stage_fill_matches_all_eight_Root_viewed_bodies_and_exact_requests(self):
        for code in own.REGIONS:
            g=own.staged_candidate(code,root=ROOT)
            for kind in own.TEMPLATES:
                t=next(t for t in g['templates'] if t['id']==own.TEMPLATES[kind]['file_id']);self.assertEqual(own.checked_adapter(g,t,kind,root=ROOT),own.ADAPTER)
                for stress in [False,True]:
                    scenario='stress' if stress else 'normal';data=own.example_data(code,kind,stress,root=ROOT);expected=json.loads((ROOT/own.QA_REPORT/'fixtures'/f'{code}-{scenario}-{kind}.json').read_bytes());self.assertTrue(own.exact(own.envelope(code,kind,data,root=ROOT),expected))
                    out=BytesIO();own.fill_document(g,t,kind,own.template_path(code,kind,root=ROOT),data,root=ROOT).save(out);self.assertEqual(out.getvalue(),(ROOT/own.QA_REPORT/'word'/f'{code}-{scenario}-{kind}.docx').read_bytes())
    def test_orphan_raw_source_userflags_and_wrong_roots_cannot_enable_stage(self):
        root=self.clone();g=own.parse_capture('350304',root=root)
        with self.assertRaises((ValueError,OSError)):own.staged_candidate('350304',root=root)
        for change in [{'can_generate':True},{'candidate_adapter_evidence':{'sha256':own.STAGE_SHA256}},{'published':True},{'generation_adapter':own.ADAPTER}]:
            bad={**g,**change}
            with self.assertRaises((ValueError,OSError)):own.checked_adapter(bad,bad['templates'][0],'application',root=root)
        with self.assertRaises(ValueError):own.staged_candidate('350304',root=None)
    def test_wrong_source_template_kind_reference_or_sample_never_gets_stage_adapter(self):
        g=own.staged_candidate('350304',root=ROOT);template=next(t for t in g['templates'] if t['can_generate'] and t['document_types']==['application'])
        for change in [{'region_code':'350305'},{'official_kind':'sample'},{'generation_mode':'reference_adaptation'},{'document_types':[]},{'local_material_key':'foreign'},{'can_generate':False}]:
            with self.assertRaises(ValueError):own.checked_adapter(g,{**template,**change},'application',root=ROOT)
        for row in g['templates']:
            if row['eligible_own_kind'] is None:
                with self.assertRaises(ValueError):own.checked_adapter(g,row,'application',root=ROOT)
        for kind in ['sample','reference',None]:
            with self.assertRaises(ValueError):own.checked_adapter(g,template,kind,root=ROOT)
        foreign=deepcopy(g);foreign['source_id']='28a4418211ce36fedd8069f6'
        with self.assertRaises(ValueError):own.checked_adapter(foreign,template,'application',root=ROOT)
    def test_tampered_word_stage_fixture_or_page_refuses_approval(self):
        for relative in ['WORD-MANIFEST.json','STAGE-APPROVAL.json','fixtures/350304-normal-application.json','pages/350304-application-normal-1.png']:
            root=self.clone_stage();f=root/own.QA_REPORT/relative;f.write_bytes(f.read_bytes()+b' changed')
            with self.subTest(relative=relative),self.assertRaises((ValueError,OSError)):own.staged_candidate('350304',root=root)
    def test_actual_M_Word_and_stage_receipts_never_authorize_N(self):
        m=ROOT/'reports/overnight-gap-closure-20261030/localities/fujian-m/integration-qa-v1'
        for filename,pin in [('WORD-MANIFEST.json','WORD_SHA'),('STAGE-APPROVAL.json','STAGE_SHA256')]:
            root=self.clone_stage();body=(m/filename).read_bytes();(root/own.QA_REPORT/filename).write_bytes(body)
            with patch.object(own,pin,sha256(body).hexdigest()):
                with self.assertRaises(ValueError):own.staged_candidate('350304',root=root)
    def test_stage_final_None_and_original_source_overwrite_refuse(self):
        g=own.staged_candidate('350304',root=ROOT);t=next(t for t in g['templates'] if t['document_types']==['application'])
        with self.assertRaises(ValueError):own.with_publication_evidence(g,root=ROOT)
        with self.assertRaises(ValueError):own.checked_adapter({**g,'published':True},t,'application',root=ROOT)
        doc=own.fill_document(g,t,'application',own.template_path('350304','application',root=ROOT),own.example_data('350304','application',root=ROOT),root=ROOT)
        with self.assertRaises(ValueError):doc.save(own.template_path('350304','application',root=ROOT))
    def test_private_candidate_requires_explicit_review(self):
        e=own.envelope('350304','application',{},root=ROOT)
        with self.assertRaises(PermissionError):own.candidate_fill(e,root=ROOT)
    def test_one_evidence_default_no_legal_copies_and_schema_own(self):
        for code in own.REGIONS:
            self.assertEqual(len(own.defaults(code,'evidence')['evidenceList']),1);s=own.schema_descriptor(code,'evidence');self.assertEqual(s['source_id'],own.REGIONS[code]['source_id']);self.assertEqual(s['source_version'],own.SOURCE_SHAS[code]);self.assertFalse(s['policy']['capacity_is_official_requirement']);self.assertNotIn('copies',own.defaults(code,'application'))
    def test_own_four_originals_whole_ZIP_and_blank_defaults_exact(self):
        for code in own.REGIONS:
            for kind in own.TEMPLATES:
                raw=own.original_bytes(code,kind,root=ROOT);self.assertTrue(own.inspect_blank(code,kind,root=ROOT)['CRC']);self.assertEqual(own.candidate_fill(own.envelope(code,kind,own.defaults(code,kind),root=ROOT),root=ROOT,private_review=True),raw)
    def test_in_memory_fictional_candidate_non_document_parts_protected(self):
        for code in own.REGIONS:
            for kind in own.TEMPLATES:
                data=own.example_data(code,kind,root=ROOT);self.assertIn('虚构',json.dumps(data,ensure_ascii=False));raw=own.original_bytes(code,kind,root=ROOT);new=own.candidate_fill(own.envelope(code,kind,data,root=ROOT),root=ROOT,private_review=True)
                with ZipFile(BytesIO(raw)) as a,ZipFile(BytesIO(new)) as b:
                    self.assertEqual(a.namelist(),b.namelist());self.assertIsNone(b.testzip());self.assertTrue(all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml'))
                own._layout_assert_protected(raw,new,kind)
    def test_cross_source_and_schema_both_directions_both_kinds(self):
        for code,other in [('350304','350305'),('350305','350304')]:
            for kind in own.TEMPLATES:
                e=own.envelope(code,kind,{},root=ROOT);f=own.envelope(other,kind,{},root=ROOT)
                for key in ['district','source_id','source_version','authority','service_code','local_material_key','schema_id','schema_sha256']:
                    bad=deepcopy(e);bad[key]=f[key]
                    with self.subTest(key=key),self.assertRaises(ValueError):own.validate_request(bad,root=ROOT)
    def test_M_source_not_authorized_despite_same_original_SHA(self):
        good=own.envelope('350304','application',{},root=ROOT)
        for key,val in [('region_code','350302'),('source_id','28a4418211ce36fedd8069f6'),('material_id','INVENTED'),('schema_version',True),('template_id','sample'),('template_sha256','0'*64),('mode','reference_adaptation')]:
            bad=deepcopy(good);bad[key]=val
            with self.assertRaises(ValueError):own.validate_request(bad,root=ROOT)
    def test_unknown_signature_date_committee_copies_XML_and_types(self):
        for data in [{'signature':'x'},{'applicationDate':'x'},{'committeeName':'x'},{'copies':2},{'factsReason':'bad\0text'},{'applicantName':True},{'requests':['x']*4}]:
            with self.assertRaises(ValueError):own.validate_request(own.envelope('350305','application',data,root=ROOT),root=ROOT)
    def test_bad_evidence_values_capacity_and_unknown(self):
        for rows in [[{'pageCount':v}] for v in [True,1,'0','01','1.5','10000']]+[[{'unknown':'x'}],[{}]*10,[{'originalType':'other'}]]:
            with self.assertRaises(ValueError):own.validate_request(own.envelope('350304','evidence',{'evidenceList':rows},root=ROOT),root=ROOT)
    def test_source_manifest_original_or_DOM_tamper_refuse(self):
        for name in ['SOURCE-PROJECTION-MANIFEST.json','application-own-format.docx','own-materials-native-dom.json']:
            root=self.clone();p=root/own.SOURCE_BASE/own.REGIONS['350304']['folder']/name;p.write_bytes(p.read_bytes()+b' ')
            with self.assertRaises(ValueError):own.parse_capture('350304',root=root)
    def test_top_metadata_missing_or_forged_refuses_canonical_source(self):
        g=own.parse_capture('350304',root=ROOT)
        for key in ['collected_at','verified_at']:
            bad=deepcopy(g);bad.pop(key)
            with self.assertRaises(ValueError):own.with_capabilities(bad,root=ROOT)
            bad=deepcopy(g);bad[key]='2020-01-01T00:00:00Z'
            with self.assertRaises(ValueError):own.with_capabilities(bad,root=ROOT)
    def test_safe_JSON_no_private_paths_signatures_or_runtime_fallback(self):
        for rel in own.source_files(ROOT):
            if rel.endswith('.json'):
                text=(ROOT/rel).read_text('utf8');self.assertNotIn('.runtime/',text);self.assertNotIn('DerpZhenjun',text);self.assertNotIn('x-wbsign-fileunid',text.lower());self.assertNotIn('access_token=',text.lower())
if __name__=='__main__':unittest.main(verbosity=2)
