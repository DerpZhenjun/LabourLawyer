"""Independent I namespaces; writable artifacts/approval fixtures stay in Temp."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import importlib.util
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

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
SCRIPT=ROOT/'backend/regional_fujian_oct31i.py'
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


class FujianIProviderTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(),'Need safe-projection-only, unregistered I provider')
        import regional_fujian_oct31i as own
        self.o=own

    def isolated(self):
        o=self.o;temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        names=o.source_files(ROOT)+[o.WORD_MANIFEST]
        names += [r['path'] for r in json.loads((ROOT/o.WORD_MANIFEST).read_bytes())['files']]
        for relative in names:
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,target)
        self.assertFalse((root/'.runtime').exists())
        self.assertFalse((root/'reports/overnight-gap-closure-20261030/localities/fujian-own-source-discovery').exists())
        return root

    def receipt(self,root,stage=True,**changes):
        o=self.o;body=o.approval_requirements(stage=stage)
        files=json.loads((root/o.WORD_MANIFEST).read_bytes())['files']
        body.update(files=files,synthetic_temp_test_only=True);body.update(changes)
        relative=o.STAGE_RECEIPT if stage else o.PUBLICATION_RECEIPT
        raw=json.dumps(body,ensure_ascii=False).encode();(root/relative).write_bytes(raw)
        return sha256(raw).hexdigest()

    def test_source_own_fields_materials_roles_partial_no_committee(self):
        o=self.o
        for code,meta in o.REGIONS.items():
            g=o.parse_capture(code,root=ROOT)
            self.assertEqual((g['district'],g['source_id'],g['source_version']),(meta['district'],meta['source_id'],meta['manifest_sha256']))
            self.assertFalse(g['can_generate']);self.assertFalse(g['published']);self.assertEqual(g['verification_status'],'partial')
            self.assertIsNone(g['committee_full_name']);self.assertEqual(g['official_version'],'')
            self.assertEqual([m['copies'] for m in g['materials']],[meta['copies']]*3)
            self.assertTrue(all(m['required']=='必要' and '纸质' in m['format'] for m in g['materials']))
            self.assertEqual(g['fields']['实施主体']['raw_value'],meta['authority'])
            self.assertEqual(g['fields']['承诺办结时限']['raw_value'],'受理后5个工作日')
            self.assertEqual(g['fields']['法定办结时限']['raw_value'],'受理后5个工作日')
            self.assertEqual(g['fields']['是否收费']['raw_value'],'不收费')
            self.assertIn(meta['district'],g['fields']['办理地点']['raw_value'])
            self.assertEqual(g['channel']['online_status'],'auth_required');self.assertIsNone(g['channel']['entry_url'])
            for field in g['fields'].values():
                self.assertIsInstance(field['raw_value'],str);self.assertEqual(field['source_url'],g['source_url'])
                self.assertEqual(field['region_code'],code);self.assertEqual(field['normalized_value'],field['raw_value'])
                self.assertIn(field['capture_file'],o.source_files(ROOT,code));self.assertRegex(field['capture_sha256'],r'^[a-f0-9]{64}$')
            self.assertIsInstance(g['sections'],dict);self.assertIn('本区公开办事指南原文',g['sections'])
            self.assertEqual(len(g['templates']),6)
            self.assertTrue(all(not t['can_generate'] and t['document_types']==[] for t in g['templates']))
            self.assertEqual(len([t for t in g['templates'] if t['official_kind']=='sample']),3)
            self.assertEqual(len([t for t in g['templates'] if t['content_role']=='scanning_instructions_only']),2)

    def test_safe_only_temp_root_and_exact_private_root_independence(self):
        o=self.o;root=self.isolated()
        with patch.object(o,'ROOT',root/'absent-checkout'):
            for code in o.REGIONS:
                self.assertEqual(o.parse_capture(code,root=root),o.parse_capture(code,root=ROOT))
                g=o.prepare_candidate(code,root=root)
                self.assertTrue(g['can_generate']);self.assertFalse(g['published']);self.assertEqual(g['publication_status'],'unregistered_offline_candidate')
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises((ValueError,OSError)):o.parse_capture('350103',root=empty)
        for missing in [None,'',' ']:
            with self.assertRaises(ValueError):o.parse_capture('350103',root=missing)

    def test_stage_and_publication_are_separate_public_guards_not_offline_capability(self):
        o=self.o;root=self.isolated()
        with patch.object(o,'STAGE_SHA256',None),patch.object(o,'PUBLICATION_SHA256',None):
            for code in o.REGIONS:
                raw=o.parse_capture(code,root=root);candidate=o.prepare_candidate(code,root=root)
                template=next(t for t in candidate['templates'] if t.get('document_types')==['application'])
                self.assertEqual(o.with_capabilities(raw,root=root),raw)
                for call in [lambda:o.checked_adapter(candidate,template,'application',root=root),lambda:o.with_capabilities(candidate,root=root),
                             lambda:o.staged_candidate(code,root=root),lambda:o.with_publication_evidence(candidate,root=root)]:
                    with self.assertRaises((ValueError,OSError)):call()
        stage=self.receipt(root)
        with patch.object(o,'STAGE_SHA256',stage):
            for code in o.REGIONS:
                staged=o.staged_candidate(code,root=root);self.assertTrue(staged['can_generate']);self.assertFalse(staged['published'])
                t=next(t for t in staged['templates'] if t.get('document_types')==['application'])
                self.assertEqual(o.checked_adapter(staged,t,'application',root=root),o.ADAPTER)
                with self.assertRaises((ValueError,OSError)):o.with_publication_evidence(staged,root=root)
            final=self.receipt(root,False)
            with patch.object(o,'PUBLICATION_SHA256',final):
                for code in o.REGIONS:
                    published=o.with_publication_evidence(o.staged_candidate(code,root=root),root=root)
                    self.assertTrue(published['published']);self.assertIsNotNone(o.public_evidence(published,root))

    def test_own_envelope_source_version_template_schema_mode_and_extra_negatives(self):
        o=self.o
        for code in o.REGIONS:
            for kind in ['application','evidence']:
                request=o.envelope(code,kind,o.defaults(code,kind),root=ROOT)
                for field,value in [('region_code','350104' if code=='350103' else '350103'),('district','鼓楼区'),('source_id','foreign'),
                    ('source_version','0'*64),('template_id','sample'),('template_sha256','0'*64),('template_version','old'),
                    ('schema_id','foreign'),('schema_version',True),('schema_version',2),('kind','reference'),('mode','reference_adaptation')]:
                    q=deepcopy(request);q[field]=value
                    with self.subTest(code=code,field=field),self.assertRaises(ValueError):o.candidate_fill(q,root=ROOT)
                q=deepcopy(request);q['unknown']='x'
                with self.assertRaises(ValueError):o.candidate_fill(q,root=ROOT)
        for code in ['350102','350105',350103,'350100']:
            with self.assertRaises(ValueError):o.prepare_candidate(code,root=ROOT)

    def test_data_schema_defaults_capacities_signature_date_committee_and_copies_rejected(self):
        o=self.o
        for code in o.REGIONS:
            self.assertEqual(len(o.defaults(code,'evidence')['evidenceList']),1)
            self.assertIn(code,o.schema_descriptor(code,'application')['schema_id'])
            for kind in ['application','evidence']:
                for key in ['signature','applicationDate','submitDate','committeeName','copyCount','unknown']:
                    with self.assertRaises(ValueError):o.candidate_fill(o.envelope(code,kind,{key:'auto'},root=ROOT),root=ROOT)
            for data in [{'applicantName':'x\x00y'},{'agentName':'x\ty'},{'requests':['x']*4},{'factsReason':'x'*2401}]:
                with self.assertRaises(ValueError):o.candidate_fill(o.envelope(code,'application',data,root=ROOT),root=ROOT)
            for pages in [True,2,2.5,None,'0','02','10000']:
                with self.assertRaises(ValueError):o.candidate_fill(o.envelope(code,'evidence',{'evidenceList':[{'pageCount':pages}]},root=ROOT),root=ROOT)
            for data in [{'evidenceList':[{}]*16},{'evidenceList':[{'name':'x'*61}]},{'evidenceList':[{'purpose':'x'*81}]}]:
                with self.assertRaises(ValueError):o.candidate_fill(o.envelope(code,'evidence',data,root=ROOT),root=ROOT)

    def test_regenerated_safe_envelope_all_eight_reviewed_zip_members_exact(self):
        o=self.o
        for code in o.REGIONS:
            for kind in ['application','evidence']:
                source=o.template_path(code,kind,root=ROOT).read_bytes()
                for data in [{},o.defaults(code,kind)]:
                    self.assertEqual(o.candidate_fill(o.envelope(code,kind,data,root=ROOT),root=ROOT),source)
                for scenario in ['normal','stress']:
                    fixture=o.fixture(code,kind,scenario,root=ROOT)
                    request=o.envelope(code,kind,fixture['data'],root=ROOT)
                    self.assertEqual(request,fixture['request'])
                    body=o.candidate_fill(request,root=ROOT);reviewed=(ROOT/fixture['reviewed_docx']).read_bytes()
                    self.assertEqual(sha256(body).hexdigest(),sha256(reviewed).hexdigest())
                    with ZipFile(BytesIO(body)) as actual,ZipFile(BytesIO(reviewed)) as expected,ZipFile(BytesIO(source)) as original:
                        self.assertEqual(actual.namelist(),expected.namelist())
                        for member in actual.namelist():
                            self.assertEqual(actual.read(member),expected.read(member))
                            if member!='word/document.xml':self.assertEqual(actual.read(member),original.read(member))
                        after=E.fromstring(actual.read('word/document.xml'));before=E.fromstring(original.read('word/document.xml'))
                        ps=after.findall('w:body/w:p',N);bs=before.findall('w:body/w:p',N)
                        if kind=='application':
                            for i in [16,19,20]:
                                self.assertEqual(''.join(ps[i].itertext()),''.join(bs[i].itertext()))
                        else:self.assertEqual(E.tostring(ps[1]),E.tostring(bs[1]))

    def test_no_cross_region_blank_or_sample_reference_generation_even_equal_bytes(self):
        o=self.o;root=self.isolated();stage=self.receipt(root)
        with patch.object(o,'STAGE_SHA256',stage):
            a=o.staged_candidate('350103',root=root);b=o.staged_candidate('350104',root=root)
            t=next(t for t in a['templates'] if t.get('document_types')==['application'])
            with self.assertRaises(ValueError):o.checked_adapter(b,t,'application',root=root)
            for template in a['templates']:
                if template['official_kind']!='blank':
                    with self.assertRaises(ValueError):o.checked_adapter(a,template,'evidence',root=root)
            for field,value in [('fields',{}),('sections',None),('source_version','0'*64),('version',True),('can_generate',1)]:
                wrong=deepcopy(a);wrong[field]=value
                with self.assertRaises(ValueError):o.with_capabilities(wrong,root=root)

    def test_source_proof_missing_tamper_and_approval_phase_types_are_closed(self):
        o=self.o;root=self.isolated()
        path=root/o.SOURCE_BASE/o.REGIONS['350104']['folder']/'application-own-format-public-retrieval.docx'
        path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaises((ValueError,OSError)):o.parse_capture('350104',root=root)
        self.assertEqual(o.parse_capture('350103',root=root)['region_code'],'350103')
        root=self.isolated()
        for change in [{'can_publish':True},{'approved_by':'candidate_agent'},{'model_calls':False},{'identities':[]},{'files':[None]}]:
            stage=self.receipt(root,**change)
            with patch.object(o,'STAGE_SHA256',stage),self.assertRaises((ValueError,OSError)):o.staged_candidate('350103',root=root)
        stage=self.receipt(root)
        with patch.object(o,'STAGE_SHA256',stage):
            staged=o.staged_candidate('350103',root=root);final=self.receipt(root,False,stage_receipt_sha256='0'*64)
            with patch.object(o,'PUBLICATION_SHA256',final),self.assertRaises(ValueError):o.with_publication_evidence(staged,root=root)
        for missing in [None,'',' ']:self.assertIsNone(o.public_evidence(staged,missing))

    def test_original_attachment_downloads_are_exact_and_public_generation_still_denied(self):
        o=self.o
        for code in o.REGIONS:
            raw=o.parse_capture(code,root=ROOT)
            for t in raw['templates']:
                self.assertTrue(o.approved_report_attachment(raw,t,ROOT))
                wrong=deepcopy(t);wrong['region_code']='350104' if code=='350103' else '350103'
                self.assertFalse(o.approved_report_attachment(raw,wrong,ROOT))

    def test_stage_fill_exact_path_and_source_report_overwrite_protection(self):
        o=self.o;root=self.isolated();stage=self.receipt(root)
        with patch.object(o,'STAGE_SHA256',stage):
            for code in o.REGIONS:
                g=o.staged_candidate(code,root=root)
                for kind in ['application','evidence']:
                    t=next(t for t in g['templates'] if t.get('document_types')==[kind]);original=root/t['file']
                    document=o.fill_document(g,t,kind,original,{},root=root);buffer=BytesIO();document.save(buffer)
                    self.assertEqual(buffer.getvalue(),original.read_bytes())
                    with self.assertRaises(ValueError):document.save(original)
                    with self.assertRaises(ValueError):o.fill_document(g,t,kind,root/'wrong.docx',{},root=root)

    def test_actual_shared_typescript_parser_and_display_all_phases(self):
        self.assertTrue(shutil.which('node'),'Actual shared TS replay requires Node')
        o=self.o;root=self.isolated();stage=self.receipt(root);guides=[]
        guides.extend(o.parse_capture(code,root=root) for code in o.REGIONS)
        guides.extend(o.prepare_candidate(code,root=root) for code in o.REGIONS)
        with patch.object(o,'STAGE_SHA256',stage):
            for code in o.REGIONS:guides.append(o.staged_candidate(code,root=root))
            final=self.receipt(root,False)
            with patch.object(o,'PUBLICATION_SHA256',final):
                for code in o.REGIONS:guides.append(o.with_publication_evidence(o.staged_candidate(code,root=root),root=root))
        for g in guides:g['version']=1
        result=subprocess.run(['node',str(ROOT/'scripts/test-fujian-i-guide-wire.mjs')],cwd=ROOT,input=json.dumps(guides,ensure_ascii=False),encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main(verbosity=2)
