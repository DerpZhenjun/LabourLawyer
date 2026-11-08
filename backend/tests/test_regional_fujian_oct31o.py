"""Real standalone own-source, schema and cross-platform boundary tests."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
import importlib.util, json, shutil, tempfile, unittest
from unittest.mock import patch
HERE = Path(__file__).resolve().parents[2]
SOURCE = HERE / 'reports/overnight-gap-closure-20261030/localities/fujian-o-source-projection'
spec = importlib.util.spec_from_file_location('xq_proposal', HERE / 'backend/regional_fujian_oct31o.py') if (HERE / 'backend/regional_fujian_oct31o.py').exists() else None
P = importlib.util.module_from_spec(spec) if spec else None
if spec:
    spec.loader.exec_module(P)

class OwnProposalTests(unittest.TestCase):

    def setUp(self):
        self.assertIsNotNone(P, 'Own source-only parser/adapter proposal is not implemented')
        self.enterContext(patch.object(P, 'PUBLICATION_SHA256', None))

    def test_own_identities_and_metadata_raw_no_promotion(self):
        for code in P.REGIONS:
            g = P.parse_capture(code, root=HERE)
            self.assertFalse(g['can_generate'])
            self.assertEqual(g['guide_status'], 'partial')
            self.assertEqual(g['collected_at'], g['observed_at_utc'])
            self.assertEqual(g['verified_at'], g['observed_at_utc'])
            self.assertIsNone(g['committee_name'])
            self.assertIsNone(g['official_version'])
            self.assertTrue(g['sections'])
            self.assertGreater(len(g['fields']), 40)
            for field in g['fields'].values():
                self.assertIsNone(field['normalized_value'])
                self.assertEqual(field['source_id'], g['source_id'])
                self.assertEqual(field['verification_status'], 'observed_unverified')

    def test_notes_and_auth_stay_distinct(self):
        a = P.parse_capture('350322', root=HERE)
        b = P.parse_capture('350502', root=HERE)
        self.assertIn('被申请人人数', a['materials'][0]['instructions'])
        self.assertTrue(all((m['instructions'] is None for m in b['materials'])))
        self.assertEqual(a['online_boundary']['origin_path'], 'https://iam.e-govt.cn:8901/login')
        self.assertEqual(b['online_boundary']['origin_path'], 'https://fjzc.fjzhkj.cn:7881/')
        for g in [a, b]:
            self.assertIsNone(g['online_entry'])
            self.assertEqual([m['copies'] for m in g['materials']], ['原件份数2份', '原件份数2份', '复印件份数2份'])
            self.assertTrue(all((m['official_material_id'] is None and m['legal_default_copies'] is None for m in g['materials'])))

    def test_all_source_files_standalone_cold_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for file in P.source_files(root=HERE):
                q = root / file
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(HERE / file, q)
            for code in P.REGIONS:
                self.assertEqual(P.parse_capture(code, root=root), P.parse_capture(code, root=HERE))

    def test_source_tamper_missing_pin_and_wrong_root_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE, root / 'reports/overnight-gap-closure-20261030/localities/fujian-o-source-projection')
            shutil.copyfile(SOURCE / 'OWN-SOURCE-PINS.json', root / 'reports/overnight-gap-closure-20261030/localities/fujian-o-source-projection/OWN-SOURCE-PINS.json')
            p = root / 'reports/overnight-gap-closure-20261030/localities/fujian-o-source-projection/xianyou-350322/own-guide.json'
            p.write_bytes(p.read_bytes() + b' ')
            with self.assertRaises(ValueError):
                P.parse_capture('350322', root=root)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                P.parse_capture('350322', root=td)

    def test_paths_reject_both_platform_drives_UNC_root_traversal(self):
        for path in ['C:/escape', 'C:escape', 'c:\\escape', '\\\\server\\share\\x', '//server/share/x', '/tmp/x', '\\escape', '../x', 'a/../x', 'a\\..\\x', 'a//x', './x', 'a/./x', 'a:x', '']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                P.path_at(HERE, path)
        self.assertEqual(P.path_at(HERE, Path('reports/overnight-gap-closure-20261030/localities/fujian-o-source-projection') / 'xianyou-350322' / 'own-guide.json'), SOURCE / 'xianyou-350322/own-guide.json')

    def test_unknown_regions_kinds_and_roles_fail(self):
        for code in ['350304', '350303', '', None, 350322]:
            with self.assertRaises(ValueError):
                P.parse_capture(code, root=HERE)
        for kind in ['application-sample', 'evidence-material-format', 'evidence-material', 'sample', None]:
            with self.assertRaises(ValueError):
                P.envelope('350322', kind, {}, root=HERE)

    def test_originals_validate_each_own_whole_ZIP(self):
        for code in P.REGIONS:
            for kind in ['application', 'evidence']:
                raw = P.original_bytes(code, kind, root=HERE)
                audit = P.inspect_blank(code, kind, root=HERE)
                with ZipFile(BytesIO(raw)) as z:
                    self.assertIsNone(z.testzip())
                    self.assertEqual(audit['member_sha256'], {n: sha256(z.read(n)).hexdigest() for n in z.namelist()})

    def test_sample_instruction_and_material_IDs_not_blank(self):
        for code in P.REGIONS:
            g = P.parse_capture(code, root=HERE)
            self.assertEqual(len(g['templates']), 6)
            for t in g['templates']:
                self.assertFalse(t['can_generate'])
                self.assertIsNone(t['generation_permission'])
                self.assertIsNone(t['official_material_id'])
                if 'sample' in t['role'] or t['role'].startswith('evidence-material'):
                    self.assertIsNone(t['local_original'])

    def test_source_only_display_templates_have_explicit_no_document_kinds(self):
        for code in P.REGIONS:
            g = P.parse_capture(code, root=HERE)
            for t in g['templates']:
                self.assertIn('id', t, 'Source-only display needs a public-file identity, never a generation grant')
                self.assertEqual(t['id'], t['public_file_unid'])
                self.assertEqual(t['document_types'], [])
                self.assertEqual(t['official_kind'], t['official_control_type'])
                self.assertEqual(t['source_url'], g['source_url'])

    def test_one_evidence_default_capacities_not_law(self):
        for code in P.REGIONS:
            self.assertEqual(len(P.defaults(code, 'evidence')['evidenceList']), 1)
            s = P.schema_descriptor(code, 'application')
            self.assertFalse(s['policy']['capacity_is_legal_requirement'])
            self.assertFalse(s['policy']['capacity_is_official_requirement'])

    def test_valid_own_blank_returns_exact_bytes_and_private_gate(self):
        for code in P.REGIONS:
            for kind in ['application', 'evidence']:
                req = P.envelope(code, kind, P.defaults(code, kind), root=HERE)
                with self.assertRaises(PermissionError):
                    P.candidate_fill(req, root=HERE)
                self.assertEqual(P.candidate_fill(req, root=HERE, private_review=True), P.original_bytes(code, kind, root=HERE))

    def test_equal_SHA_does_not_authorize_other_source_or_contract(self):
        for code in P.REGIONS:
            other = next((x for x in P.REGIONS if x != code))
            for kind in ['application', 'evidence']:
                req = P.envelope(code, kind, P.example_data(code, kind), root=HERE)
                alien = P.envelope(other, kind, {}, root=HERE)
                self.assertEqual(req['template_sha256'], alien['template_sha256'])
                for key in ['source_id', 'source_url', 'source_version', 'region_code', 'schema_id', 'schema_sha256', 'local_material_key']:
                    bad = deepcopy(req)
                    bad[key] = alien[key]
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        P.candidate_fill(bad, root=HERE, private_review=True)

    def test_unknown_signature_date_committee_copies_and_bad_types_rejected(self):
        for code in P.REGIONS:
            for key in ['signature', 'date', 'committee', 'copies', 'unknown']:
                req = P.envelope(code, 'application', {key: 'forbidden'}, root=HERE)
                with self.assertRaises(ValueError):
                    P.candidate_fill(req, root=HERE, private_review=True)
            for data in [{'requests': 'bad'}, {'requests': ['a'] * 4}, {'applicantName': True}, {'factsReason': '\x00'}]:
                with self.assertRaises(ValueError):
                    P.candidate_fill(P.envelope(code, 'application', data, root=HERE), root=HERE, private_review=True)

    def test_fictional_fill_protects_signature_date_committee_and_other_members(self):
        for code in P.REGIONS:
            for kind in ['application', 'evidence']:
                raw = P.original_bytes(code, kind, root=HERE)
                req = P.envelope(code, kind, P.example_data(code, kind), root=HERE)
                filled = P.candidate_fill(req, root=HERE, private_review=True)
                P._layout_assert_protected(raw, filled, kind)
                with ZipFile(BytesIO(raw)) as a, ZipFile(BytesIO(filled)) as b:
                    self.assertEqual(a.namelist(), b.namelist())
                    self.assertTrue(all((a.read(n) == b.read(n) for n in a.namelist() if n != 'word/document.xml')))
                    self.assertIn('虚构', b.read('word/document.xml').decode())

    def test_public_and_stage_generation_remain_closed(self):
        self.assertIsNone(P.PUBLICATION_SHA256)
        for code in P.REGIONS:
            self.assertFalse(P.parse_capture(code, root=HERE)['can_generate'])
            with patch.object(P, 'WORD_SHA256', None), patch.object(P, 'STAGE_SHA256', None):
                with self.assertRaises((ValueError, PermissionError)):
                    P.staged_candidate(code, root=HERE)
            with self.assertRaises((ValueError, PermissionError)):
                P.published_guide(code, root=HERE)
        with self.assertRaises((ValueError, PermissionError)):
            P.checked_reference_adapter({}, {}, 'application', root=HERE)

    def test_macro_external_relationships_and_ZIP_traversal_refused(self):
        raw = P.original_bytes('350322', 'application', root=HERE)
        for filename, content in [('word/vbaProject.bin', b'macro'), ('../escape', b'x'), ('word/_rels/evil.rels', b'<Relationships><Relationship TargetMode="External" Target="https://example.com"/></Relationships>')]:
            output = BytesIO()
            with ZipFile(BytesIO(raw)) as a, ZipFile(output, 'w') as b:
                for info in a.infolist():
                    b.writestr(info, a.read(info.filename))
                b.writestr(filename, content)
            with self.assertRaises(ValueError):
                P._layout_inspect(output.getvalue(), 'application')

class StageProposalTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(P,'checked_adapter',None)),'Own stage receipt/canonical binding interface is not implemented')
        self.enterContext(patch.object(P, 'PUBLICATION_SHA256', None))
    def clone(self):
        temp=tempfile.TemporaryDirectory(prefix='o-own-stage-');self.addCleanup(temp.cleanup);root=Path(temp.name)
        for part in [P.SOURCE_BASE,Path(P.QA_REPORT)]:shutil.copytree(HERE/part,root/part)
        return root
    def test_four_stage_forms_rawsourceFalse_publicationNone(self):
        self.assertIsNone(P.PUBLICATION_SHA256)
        for code in P.REGIONS:
            self.assertFalse(P.parse_capture(code,root=HERE)['can_generate']);g=P.staged_candidate(code,root=HERE);self.assertTrue(g['can_generate']);self.assertFalse(g['published']);self.assertEqual(sum(t['can_generate'] for t in g['templates']),2)
            for kind in P.KINDS:
                t=next(t for t in g['templates'] if t['document_types']==[kind]);self.assertEqual(P.checked_adapter(g,t,kind,root=HERE),P.ADAPTER)
    def test_standalone_93_source_and_approval_files_no_parent_fallback(self):
        root=self.clone();self.assertEqual(len(P.source_files(root)),19);self.assertEqual(len(P.approval_files(root)),74)
        for code in P.REGIONS:self.assertEqual(P.staged_candidate(code,root=root),P.staged_candidate(code,root=HERE))
    def test_missing_None_and_publication_gates_failclosed(self):
        for key in ['WORD_SHA256','STAGE_SHA256']:
            with patch.object(P,key,None):
                with self.assertRaises(ValueError):P.staged_candidate('350322',root=HERE)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises((ValueError,OSError)):P.staged_candidate('350322',root=td)
        g=P.staged_candidate('350322',root=HERE)
        with self.assertRaises(ValueError):P.with_publication_evidence(g,root=HERE)
        with self.assertRaises(ValueError):P.checked_adapter({**g,'published':True},g['templates'][0],'application',root=HERE)
    def test_word_stage_fixture_page_tamper_refused(self):
        for relative in ['WORD-MANIFEST.json','STAGE-APPROVAL.json','fixtures/350322-application-normal.json','word/350322-application-normal.docx','pages/350322-application-normal-1.png']:
            root=self.clone();path=root/P.QA_REPORT/relative;path.write_bytes(path.read_bytes()+b' changed')
            with self.subTest(relative=relative),self.assertRaises((ValueError,OSError)):P.staged_candidate('350322',root=root)
    def test_foreign_M_N_receipts_never_authorize_despite_repin(self):
        project=HERE
        for namespace in ['fujian-m','fujian-n']:
            for filename,pin in [('WORD-MANIFEST.json','WORD_SHA256'),('STAGE-APPROVAL.json','STAGE_SHA256')]:
                root=self.clone();foreign=project/'reports/overnight-gap-closure-20261030/localities'/namespace/'integration-qa-v1'/filename
                if foreign.is_file():body=foreign.read_bytes()
                else:
                    body=json.dumps({'scope':'FOREIGN_'+namespace,'source_versions':{'350304':'0'*64},'identities':[{'region_code':'350304','source_id':'foreign'}]}).encode()
                (root/P.QA_REPORT/filename).write_bytes(body)
                with patch.object(P,pin,sha256(body).hexdigest()):
                    with self.assertRaises((ValueError,KeyError)):P.staged_candidate('350322',root=root)
    def test_fake_stage_scope_or_final_flags_refused_even_if_repin(self):
        for key,value in [('scope','PUBLICATION'),('can_publish',True),('Root_Word_review_sha256','0'*64),('browser_QA','PASS'),('stress_evidence_signature_continues_on_tenth_page',False)]:
            root=self.clone();path=root/P.STAGE_RECEIPT;body=json.loads(path.read_bytes());body[key]=value;raw=(json.dumps(body,ensure_ascii=False,indent=2)+'\n').encode();path.write_bytes(raw)
            with patch.object(P,'STAGE_SHA256',sha256(raw).hexdigest()):
                with self.subTest(key=key),self.assertRaises(ValueError):P.staged_candidate('350322',root=root)
    def test_raw_orphan_and_user_flags_never_approve(self):
        g=P.parse_capture('350322',root=HERE);self.assertFalse(P.with_capabilities(g,root=HERE)['can_generate'])
        for change in [{'can_generate':True},{'published':True},{'user_approved':True},{'generation_adapter':P.ADAPTER}]:
            with self.assertRaises(ValueError):P.with_capabilities({**g,**change},root=HERE)
        with patch.object(P,'STAGE_SHA256',None):
            with self.assertRaises(ValueError):P.checked_adapter({**g,'can_generate':True},g['templates'][0],'application',root=HERE)
    def test_fill_only_after_checked_stage_and_cannot_overwrite_source(self):
        g=P.staged_candidate('350322',root=HERE);t=next(t for t in g['templates'] if t['document_types']==['application']);path=P.template_path('350322','application',root=HERE);before=path.read_bytes()
        document=P.fill_document(g,t,'application',path,P.example_data('350322','application'),root=HERE)
        from io import BytesIO
        target=BytesIO();document.save(target);self.assertIn('虚构',ZipFile(BytesIO(target.getvalue())).read('word/document.xml').decode())
        with self.assertRaises(ValueError):document.save(path)
        self.assertEqual(path.read_bytes(),before)
        with patch.object(P,'STAGE_SHA256',None):
            with self.assertRaises(ValueError):P.fill_document(g,t,'application',path,{},root=HERE)
    def test_other_source_kind_sample_template_and_metadata_refused(self):
        a=P.staged_candidate('350322',root=HERE);b=P.staged_candidate('350502',root=HERE);t=next(t for t in a['templates'] if t['document_types']==['application'])
        for other in [next(t for t in b['templates'] if t['document_types']==['application']),next(t for t in a['templates'] if t['official_control_type']=='sample')]:
            with self.assertRaises(ValueError):P.checked_adapter(a,other,'application',root=HERE)
        with self.assertRaises(ValueError):P.checked_adapter(a,t,'evidence',root=HERE)
        for key,value in [('source_id',b['source_id']),('collected_at','changed'),('verified_at','changed'),('version',True),('unknown',True)]:
            with self.assertRaises(ValueError):P.with_capabilities({**a,key:value},root=HERE)
    def test_safe_public_proof_exact74_and_layout_note_no_final_claim(self):
        files=P.approval_files(HERE);self.assertEqual(len(files),74);word=P._word_manifest(HERE);self.assertEqual(len(word['files']),72);self.assertTrue(word['stress_evidence_signature_continues_on_tenth_page'])
        readme=(HERE/P.QA_REPORT/'README.md').read_text('utf8');self.assertIn('tenth page',readme);self.assertIn('89991',readme)
        for rel in [*P.source_files(HERE),*files]:
            if rel.endswith(('.json','.md')):
                text=(HERE/rel).read_text('utf8').lower()
                for forbidden in ['.runtime/','derpzhenjun','x-wbsign-fileunid','access_token=','own_pid','192.168.']:self.assertNotIn(forbidden,text)



class EvidenceMetadataTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(P, 'PUBLICATION_SHA256', None))

    def test_real_own_public_evidence_roundtrip_and_four_stage_forms(self):
        for code in P.REGIONS:
            guide=P.staged_candidate(code,root=HERE);proof=P.public_evidence(guide,HERE)
            self.assertEqual(set(proof),{'source_projection','source_projection_sha256'})
            persisted={**deepcopy(guide),'version':1,'evidence':deepcopy(proof)}
            self.assertTrue(P._matches(persisted,guide),'Actual public_seed evidence metadata must roundtrip against the same checked canonical guide')
            result=P.with_capabilities(persisted,root=HERE);self.assertEqual(result,persisted);self.assertTrue(result['can_generate'])
            self.assertEqual(P.public_evidence(persisted,HERE),proof)
            for kind in P.KINDS:
                template=next(t for t in result['templates'] if t['document_types']==[kind]);self.assertEqual(P.checked_adapter(result,template,kind,root=HERE),P.ADAPTER)
            self.assertEqual(persisted['evidence'],proof,'Validation must not mutate caller metadata')
    def test_raw_own_evidence_is_metadata_not_generation_approval(self):
        for code in P.REGIONS:
            raw=P.parse_capture(code,root=HERE);proof=P.public_evidence(raw,HERE);decorated={**deepcopy(raw),'evidence':proof}
            self.assertFalse(P.with_capabilities(decorated,root=HERE)['can_generate']);self.assertEqual(P.public_evidence(decorated,HERE),proof)
            for change in [{'can_generate':True},{'user_approved':True},{'published':True}]:
                with self.assertRaises(ValueError):P.with_capabilities({**decorated,**change},root=HERE)
    def test_None_bool_unknown_missing_wrong_path_SHA_and_source_refused(self):
        for code in P.REGIONS:
            canonical=P.staged_candidate(code,root=HERE);valid=P.public_evidence(canonical,HERE);other=next(c for c in P.REGIONS if c!=code);foreign=P.public_evidence(P.staged_candidate(other,root=HERE),HERE)
            invalid=[None,True,False,[],valid['source_projection'],{}, {'source_projection':valid['source_projection']},
                     {**valid,'extra':True},{**valid,'source_projection':None},{**valid,'source_projection':True},
                     {**valid,'source_projection':valid['source_projection'].replace('/','\\')},
                     {**valid,'source_projection':'../'+valid['source_projection']},
                     {**valid,'source_projection':'C:/'+valid['source_projection']},
                     {**valid,'source_projection_sha256':None},{**valid,'source_projection_sha256':True},
                     {**valid,'source_projection_sha256':'0'*64},
                     {**valid,'source_projection':foreign['source_projection']},
                     {**valid,'source_projection_sha256':foreign['source_projection_sha256']},foreign]
            for proof in invalid:
                with self.subTest(code=code,proof=proof):self.assertFalse(P._matches({**canonical,'evidence':proof},canonical))
            # Whole checked entry must also reject a forged proof, regardless of a valid shared template SHA.
            template=next(t for t in canonical['templates'] if t['document_types']==['application'])
            self.assertEqual(template['sha256'],next(t for t in P.staged_candidate(other,root=HERE)['templates'] if t['document_types']==['application'])['sha256'])
            with self.assertRaises(ValueError):P.checked_adapter({**canonical,'evidence':foreign},template,'application',root=HERE)
    def test_metadata_cannot_bypass_missing_Word_or_stage_proof(self):
        canonical=P.staged_candidate('350322',root=HERE);decorated={**canonical,'evidence':P.public_evidence(canonical,HERE)};template=next(t for t in canonical['templates'] if t['document_types']==['application'])
        for pin in ['WORD_SHA256','STAGE_SHA256']:
            with patch.object(P,pin,None):
                with self.assertRaises(ValueError):P.checked_adapter(decorated,template,'application',root=HERE)
        self.assertIsNone(P.PUBLICATION_SHA256)
        with self.assertRaises(ValueError):P.with_publication_evidence(decorated,root=HERE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
