"""Gulou own provider only; synthetic approvals live exclusively in temp roots."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from lxml import etree as E
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

class GulouOwnProviderTests(unittest.TestCase):
    def setUp(self):
        import regional_fujian_oct31h as own
        self.o=own

    def isolated(self):
        o=self.o;t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name)
        manifest=json.loads((ROOT/o.WORD_MANIFEST).read_bytes())
        for relative in o.source_files(ROOT)+[o.SOURCE_FREEZE,o.OFFLINE_REVIEW,o.WORD_MANIFEST]+[r['path'] for r in manifest['files']]:
            p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,p)
        return root

    def fake_receipt(self,root,stage=True,**changes):
        o=self.o;relative=o.STAGE_RECEIPT if stage else o.PUBLICATION_RECEIPT
        evidence=root/o.QA_REPORT/'test-only-proof.txt';evidence.parent.mkdir(parents=True,exist_ok=True);evidence.write_bytes(b'synthetic receipt test only')
        body=o.approval_requirements(stage=stage)
        files=json.loads((root/o.WORD_MANIFEST).read_bytes())['files'] if stage else [{'path':evidence.relative_to(root).as_posix(),'bytes':evidence.stat().st_size,'sha256':sha256(evidence.read_bytes()).hexdigest()}]
        body.update(files=files,synthetic_test_fixture_only=True)
        body.update(changes);raw=json.dumps(body,ensure_ascii=False).encode();(root/relative).write_bytes(raw)
        return sha256(raw).hexdigest()

    def test_source_partial_exact_own_fields_and_auth_boundary(self):
        o=self.o;g=o.parse_capture(root=ROOT)
        self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('fujian','福州市','鼓楼区','350102'))
        captured=json.loads((ROOT/o.FOLDER/'own-guide-native-dom.json').read_bytes())
        self.assertEqual(g['sections']['本区公开办事指南原文'],captured['text'])
        self.assertEqual(g['verification_status'],'partial')
        self.assertFalse(g['can_generate']);self.assertFalse(g['published'])
        self.assertEqual(len(o.source_files(ROOT)),24)
        self.assertEqual(g['channel']['online_status'],'auth_required')
        self.assertFalse(g['channel']['submission_verified'])
        self.assertEqual(g['fields']['承诺时限']['raw_value'],'受理后5个工作日')
        self.assertEqual(g['fields']['咨询方式']['raw_value'],'0591-87710981')
        self.assertIn('软件大道89号',g['fields']['办理地点']['raw_value'])
        self.assertEqual(g['fields']['必须到现场原因']['source_label'],'必须现场办理原因：')
        self.assertEqual([m['copies'] for m in g['materials']],[2,2,2])
        for v in g['fields'].values():
            self.assertIsInstance(v,dict);self.assertIsInstance(v['raw_value'],str)
            self.assertEqual(v['source_url'],g['source_url']);self.assertIn(v['capture_file'],o.source_files(ROOT))
            self.assertRegex(v['capture_sha256'],r'^[a-f0-9]{64}$')
        samples=[t for t in g['templates'] if t['official_kind']=='sample']
        self.assertEqual(len(samples),3)
        self.assertTrue(all(t['download_status']=='unverified' and not t['can_generate'] and not t['document_types'] for t in samples))
        self.assertEqual(o.with_capabilities(g,root=ROOT),g)

    def test_captured_display_facts_and_attachment_roles_are_not_hidden(self):
        o=self.o;g=o.parse_capture(root=ROOT)
        self.assertEqual(g['fields']['承诺办结时限']['raw_value'],'受理后5个工作日')
        self.assertEqual(g['fields']['法定办结时限']['raw_value'],'受理后5个工作日')
        self.assertEqual(g['fields']['是否收费']['raw_value'],'不收费')
        self.assertEqual(g['fields']['到办事现场次数']['raw_value'],'1 次')
        self.assertEqual(g['source_version'],o.FREEZE_SHA)
        self.assertEqual(g['official_version'],'')
        for value in g['fields'].values():
            self.assertEqual(value['normalized_value'],value['raw_value'])
            self.assertEqual(value['region_code'],'350102')
            self.assertEqual(value['verification_status'],'verified')
            self.assertTrue(value['collected_at'] and value['verified_at'])
        self.assertTrue(all(m['official_badges']==[] and m['attachment_labels']==['格式文本'] for m in g['materials']))
        boundary=json.loads((ROOT/o.FOLDER/'online-native-scan-login-boundary.json').read_bytes())
        self.assertIsNone(g['channel']['entry_url'])
        self.assertEqual(g['channel']['observed_entry_url'],boundary['entry_url'])
        self.assertEqual(g['channel']['online_status'],'auth_required')

    def test_offline_review_never_implies_stage_or_final(self):
        o=self.o
        raw=o.parse_capture(root=ROOT)
        self.assertFalse(raw['can_generate']);self.assertFalse(raw['published'])
        if o.STAGE_SHA256 is not None:
            staged=o.prepare_candidate(root=ROOT)
            self.assertTrue(staged['can_generate']);self.assertFalse(staged['published'])
            self.assertFalse(o.with_capabilities(raw,root=ROOT)['can_generate'])
        with patch.object(o,'STAGE_SHA256',None),patch.object(o,'PUBLICATION_SHA256',None):
            with self.assertRaises((ValueError,OSError)):o.prepare_candidate(root=ROOT)
            with self.assertRaises((ValueError,OSError)):o.with_publication_evidence(raw,root=ROOT)
        for absent in [None,'',' ']:self.assertIsNone(o.public_evidence(raw,absent))
        self.assertIsNotNone(o.public_evidence(raw,ROOT))
        for code in ['350103','350100','320583']:
            with self.assertRaises(ValueError):o.parse_capture(code,root=ROOT)

    def test_temporary_stage_and_final_are_separate_and_strict(self):
        o=self.o;root=self.isolated();pin=self.fake_receipt(root)
        with patch.object(o,'STAGE_SHA256',pin):
            g=o.prepare_candidate(root=root);self.assertTrue(g['can_generate']);self.assertFalse(g['published'])
            self.assertEqual(g['verification_status'],'partial')
            self.assertEqual(len([t for t in g['templates'] if t['can_generate']]),2)
            with self.assertRaises(ValueError):o.with_publication_evidence(g,root=root)
            final=self.fake_receipt(root,False)
            with patch.object(o,'PUBLICATION_SHA256',final):
                published=o.with_publication_evidence(g,root=root)
                self.assertTrue(published['published']);self.assertEqual(published['verification_status'],'partial')
                self.assertIsNotNone(o.public_evidence(published,root))
            self.assertFalse(o.with_capabilities(o.parse_capture(root=root),root=root)['can_generate'])
            for field,value in [('region_code','350103'),('source_id','wrong'),('source_version','0'*64),('fields',{}),('sections',None),('version',True),('can_generate',1)]:
                q=deepcopy(g);q[field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):o.with_capabilities(q,root=root)
            for t in g['templates']:
                if t['official_kind']=='sample' or t['content_role']=='scanning_instructions_only':
                    with self.assertRaises(ValueError):o.checked_adapter(g,t,'application',root=root)
            t=next(t for t in g['templates'] if t.get('document_types')==['application'])
            for field,value in [('id','wrong'),('sha256','0'*64),('official_kind','sample'),('region_code','350103')]:
                q=deepcopy(t);q[field]=value
                with self.assertRaises(ValueError):o.checked_adapter(g,q,'application',root=root)

    def test_tampered_sources_receipts_and_explicit_roots_fail_closed(self):
        o=self.o;root=self.isolated();pin=self.fake_receipt(root)
        with patch.object(o,'STAGE_SHA256',pin):
            g=o.prepare_candidate(root=root)
            original=root/o.STAGE_RECEIPT;raw=original.read_bytes();original.write_bytes(b'{}')
            self.assertIsNone(o.public_evidence(g,root))
            with self.assertRaises(ValueError):o.prepare_candidate(root=root)
            original.write_bytes(raw)
            own=root/o.FOLDER/o.SPECS['application']['file'];own.write_bytes(own.read_bytes()+b'x')
            with self.assertRaises(ValueError):o.parse_capture(root=root)
            self.assertIsNone(o.public_evidence(g,root))
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(ValueError):o.parse_capture(root=empty)
        for bad in ['../escape','/absolute']:
            with self.assertRaises(ValueError):o.path_at(root,bad)

    def test_own_models_defaults_and_fictional_examples(self):
        o=self.o
        self.assertEqual(set(o.ApplicationRequest.model_fields),{'applicantName','agentName','respondentName','requests','factsReason'})
        self.assertEqual(len(o.defaults('evidence')['evidenceList']),1)
        for kind,model in [('application',o.ApplicationRequest),('evidence',o.EvidenceRequest)]:
            model.model_validate(o.defaults(kind));model.model_validate(o.example_data(kind))
            for bad in [{'signature':'auto'},{'copyCount':4},{'committeeName':'foreign'},{'sample_verified':True}]:
                with self.assertRaises(ValidationError):model.model_validate(bad)
        for pages in [True,2,2.5,'0','-1','10000','2x']:
            with self.assertRaises(ValidationError):o.EvidenceRequest.model_validate({'evidenceList':[{'pageCount':pages}]})
        for bad in [{'requests':['x']*4},{'factsReason':'x'*2401},{'applicantName':'x\x00y'}]:
            with self.assertRaises(ValidationError):o.ApplicationRequest.model_validate(bad)
        with self.assertRaises(ValidationError):o.EvidenceRequest.model_validate({'evidenceList':[{}]*16})

    def test_source_blanks_and_reviewed_fixture_packages(self):
        o=self.o
        reviewed={('normal','application'):'9389b65ae59fcdbdcc79eb9f0a5511b92b0b816e87173199ca6a5939f0c5fdc1',
            ('normal','evidence'):'39e64186bfcdf92619dbd71bf0a8dc7867cc0fc1a01d8dbe5295d82344fe7f59',
            ('stress','application'):'8ba5247934628fbd5d48ec1f0671d5790f485d4992aaefd24fb69a186289491b',
            ('stress','evidence'):'19f8a7fccb4d4c6c4fdfbd0df6f6e490f287fbf8eb0e4169744e22e20f6f836e'}
        for kind in ['application','evidence']:
            raw=(ROOT/o.FOLDER/o.SPECS[kind]['file']).read_bytes()
            for data in [{},o.defaults(kind)]:
                buf=BytesIO();o.fill_offline(kind,data,root=ROOT).save(buf)
                self.assertEqual(buf.getvalue(),raw)
            with self.assertRaises(ValueError):o.fill_offline(kind,o.example_data(kind),root=ROOT).save(ROOT/o.FOLDER/o.SPECS[kind]['file'])
            for prefix in ['normal','stress']:
                data=o.example_data(kind,stress=prefix=='stress')
                buf=BytesIO();o.fill_offline(kind,data,root=ROOT).save(buf)
                self.assertEqual(sha256(buf.getvalue()).hexdigest(),reviewed[prefix,kind])
                with ZipFile(buf) as actual,ZipFile(BytesIO(raw)) as source:
                    self.assertEqual(actual.namelist(),source.namelist())
                    for part in source.namelist():
                        if part!='word/document.xml':self.assertEqual(actual.read(part),source.read(part))
                root=E.fromstring(ZipFile(buf).read('word/document.xml'))
                ps=root.findall('w:body/w:p',N)
                if kind=='application':self.assertEqual(''.join(ps[19].itertext()),'申请人：')
                else:self.assertEqual(''.join(ps[1].itertext()),'提交人：                 日期：          ')
        with self.assertRaises(ValueError):o.fill_offline('scanning_reference',{},root=ROOT)

    def test_exact_own_original_download_and_generation_path(self):
        o=self.o;root=self.isolated();pin=self.fake_receipt(root)
        raw=o.parse_capture(root=root)
        for t in raw['templates']:
            self.assertEqual(o.approved_report_attachment(raw,t,root),t['download_status']=='downloaded')
        with patch.object(o,'STAGE_SHA256',pin):
            g=o.prepare_candidate(root=root)
            for kind in ('application','evidence'):
                t=next(t for t in g['templates'] if t.get('document_types')==[kind])
                p=root/t['file'];buf=BytesIO();o.fill_document(g,t,kind,p,{},root=root).save(buf)
                self.assertEqual(buf.getvalue(),p.read_bytes())
                with self.assertRaises(ValueError):o.fill_document(g,t,kind,root/'wrong.docx',{},root=root)

    def test_wrong_approval_roles_phases_and_typed_values_rejected(self):
        o=self.o;root=self.isolated()
        for change in [{'can_publish':True},{'approved_by':'candidate_agent'},{'model_calls':False},
                       {'offline_review_sha256':'0'*64},{'identities':[{'region_code':'350103','source_id':o.SOURCE_ID,'service_code':o.SERVICE}]}]:
            pin=self.fake_receipt(root,**change)
            with patch.object(o,'STAGE_SHA256',pin),self.assertRaises(ValueError):o.prepare_candidate(root=root)
        pin=self.fake_receipt(root)
        with patch.object(o,'STAGE_SHA256',pin):
            g=o.prepare_candidate(root=root)
            final=self.fake_receipt(root,False,stage_receipt_sha256='0'*64)
            with patch.object(o,'PUBLICATION_SHA256',final),self.assertRaises(ValueError):o.with_publication_evidence(g,root=root)

    def test_selective_public_word_manifest_is_complete_and_immutable(self):
        o=self.o;root=self.isolated();manifest=json.loads((root/o.WORD_MANIFEST).read_bytes())
        self.assertEqual(manifest['generated_pages'],21);self.assertEqual(len(manifest['files']),27)
        self.assertEqual(len([r for r in manifest['files'] if r['path'].endswith('.docx')]),4)
        self.assertEqual(len([r for r in manifest['files'] if r['path'].endswith('.png')]),21)
        pin=self.fake_receipt(root)
        with patch.object(o,'STAGE_SHA256',pin):
            o.prepare_candidate(root=root)
            target=root/manifest['files'][0]['path'];target.write_bytes(target.read_bytes()+b'tamper')
            with self.assertRaises(ValueError):o.prepare_candidate(root=root)
        self.assertFalse(manifest['stage_approved']);self.assertFalse(manifest['can_publish'])

    def test_strict_typescript_guide_and_display_replay(self):
        if not shutil.which('node'):self.skipTest('Node unavailable for actual shared TypeScript parser replay')
        o=self.o;guides=[o.parse_capture(root=ROOT)];root=self.isolated();pin=self.fake_receipt(root)
        with patch.object(o,'STAGE_SHA256',pin):
            staged=o.prepare_candidate(root=root);guides.append(staged)
            final=self.fake_receipt(root,False)
            with patch.object(o,'PUBLICATION_SHA256',final):guides.append(o.with_publication_evidence(staged,root=root))
        for g in guides:g['version']=1
        result=subprocess.run(['node',str(ROOT/'scripts/test-gulou-guide-wire.mjs')],cwd=ROOT,input=json.dumps(guides,ensure_ascii=False),encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
