"""J own public projections/offline generation; no registered or live capability."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
MODULE=ROOT/'backend/regional_fujian_oct31j.py'


class FujianJProviderTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(),'Need independent J safe-projection-only provider')
        self.o=importlib.import_module('regional_fujian_oct31j')

    def isolated(self):
        temp=tempfile.TemporaryDirectory(prefix='own-j-public-');self.addCleanup(temp.cleanup);root=Path(temp.name).resolve()
        paths=set(self.o.source_files(ROOT))|{self.o.WORD_MANIFEST}
        paths.update(r['path'] for r in json.loads((ROOT/self.o.WORD_MANIFEST).read_bytes())['files'])
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        return root

    def test_six_own_sources_eleven_blanks_and_special_boundaries(self):
        o=self.o;eligible=0
        for code,meta in o.REGIONS.items():
            g=o.parse_capture(code,root=ROOT);candidate=o.prepare_candidate(code,root=ROOT)
            self.assertEqual((g['region_code'],g['source_id'],g['service_code']),(code,meta['source_id'],meta['service_code']))
            self.assertEqual(g['source_version'],meta['manifest_sha256']);self.assertEqual(g['verification_status'],'partial')
            self.assertFalse(g['can_generate']);self.assertFalse(g['published']);self.assertIsNone(g['committee_full_name'])
            self.assertFalse(g['committee_autofill_allowed']);self.assertEqual([m['copies'] for m in g['materials']],[2,2,2])
            self.assertEqual(g['channel']['online_status'],'auth_required');self.assertIsNone(g['channel']['entry_url'])
            eligible+=sum(t['can_generate'] is True for t in candidate['templates'])
            for t in candidate['templates']:
                if t['can_generate']:
                    self.assertEqual(t['region_code'],code);self.assertIn(meta['folder'],t['file'])
                    self.assertNotIn('fujian-i',t['file']);self.assertNotIn('fujian-h',t['file'])
            if code=='350125':self.assertEqual(meta['allowed_kinds'],['application'])
            if code=='350124':self.assertTrue(g['service_code'].endswith('202'))
            if code=='350182':
                self.assertEqual(g['channel']['entry_check']['observed_title'],'福建省数字身份管理服务平台')
                self.assertIn('iam.e-govt.cn',g['channel']['observed_entry_url'])
                spec=meta['templates']['evidence'];self.assertEqual(spec['file_id'],'C0D98561149170947B4366BCA0299DD9')
                self.assertEqual(spec['sha256'],'511d213073af6e25b0f9f8ed2b914b7b31ee47bf6cef2fbb85a0422e3d6a4f56')
            else:self.assertEqual(g['channel']['entry_check']['observed_title'],'福建省智慧调解仲裁平台')
            for f in g['fields'].values():
                self.assertIsInstance(f['raw_value'],str);self.assertEqual(f['source_url'],g['source_url']);self.assertEqual(f['region_code'],code)
        self.assertEqual(eligible,11)

    def test_no_stage_final_or_boolean_markers_can_grant_shared_capability(self):
        o=self.o
        with patch.object(o,'STAGE_SHA256',None),patch.object(o,'PUBLICATION_SHA256',None):
            for code in o.REGIONS:
                raw=o.parse_capture(code,root=ROOT);offline=o.prepare_candidate(code,root=ROOT)
                self.assertEqual(o.with_capabilities(raw,root=ROOT),raw)
                t=next(t for t in offline['templates'] if t['can_generate'])
                for f in [lambda:o.with_capabilities(offline,root=ROOT),lambda:o.checked_adapter(offline,t,'application',root=ROOT),
                    lambda:o.staged_candidate(code,root=ROOT),lambda:o.with_publication_evidence(offline,root=ROOT)]:
                    with self.assertRaises((ValueError,OSError)):f()
                forged=deepcopy(raw);forged.update(can_generate=True,published=True)
                with self.assertRaises(ValueError):o.with_capabilities(forged,root=ROOT)

    def test_material_ids_follow_own_native_panels_not_retrieval_order(self):
        for code,meta in self.o.REGIONS.items():
            guide=self.o.parse_capture(code,root=ROOT)
            self.assertEqual(guide['materials'][0]['id'],meta['templates']['application']['material_id'])
            if 'evidence' in meta['allowed_kinds']:
                self.assertEqual(guide['materials'][1]['id'],meta['templates']['evidence']['material_id'])

    def test_own_material_observed_format_required_and_instructions_are_displayed(self):
        for code in self.o.REGIONS:
            guide=self.o.parse_capture(code,root=ROOT);application=guide['materials'][0]
            self.assertEqual(application['name'],'仲裁申请书')
            self.assertEqual(application['required'],'必要');self.assertIn('纸质',application['format'])
            self.assertIn('签字',application['instructions']);self.assertEqual(application['original_copy'],'原件')
            self.assertEqual(application['official_badges'],[])

    def test_yongtai_samples_references_wrong_regions_and_cross_own_sha_are_closed(self):
        o=self.o
        for call in [lambda:o.defaults('350125','evidence'),lambda:o.envelope('350125','evidence',{},root=ROOT),lambda:o.schema_descriptor('350125','evidence')]:
            with self.assertRaises(ValueError):call()
        for code in ['350102','350103','350104','350100',350122]:
            with self.assertRaises(ValueError):o.parse_capture(code,root=ROOT)
        original=o.envelope('350122','application',{},root=ROOT)
        other=o.envelope('350123','application',{},root=ROOT)
        self.assertEqual(original['template_sha256'],other['template_sha256'])
        for key in ['region_code','district','source_id','source_url','source_version','material_id','template_file','schema_id']:
            changed={**original,key:other[key]}
            with self.subTest(key=key),self.assertRaises(ValueError):o.candidate_fill(changed,root=ROOT)

    def test_exact_new_envelopes_versions_templates_schema_and_unknown_fields(self):
        o=self.o
        for code,meta in o.REGIONS.items():
            for kind in meta['allowed_kinds']:
                request=o.envelope(code,kind,{},root=ROOT)
                for key,value in [('source_version','0'*64),('source_id','old'),('material_id','foreign'),('template_id','sample'),
                    ('template_sha256','0'*64),('template_version','old'),('template_file','reports/other.docx'),('schema_id','foreign'),
                    ('schema_version',True),('schema_version',2),('kind','reference'),('mode','reference_adaptation')]:
                    with self.subTest(code=code,kind=kind,key=key),self.assertRaises(ValueError):o.candidate_fill({**request,key:value},root=ROOT)
                with self.assertRaises(ValueError):o.candidate_fill({**request,'extra':''},root=ROOT)

    def test_blank_default_bytes_strict_slots_and_page_count_types(self):
        o=self.o
        for code,meta in o.REGIONS.items():
            for kind in meta['allowed_kinds']:
                source=o.template_path(code,kind,root=ROOT).read_bytes()
                for data in [{},o.defaults(code,kind)]:self.assertEqual(o.candidate_fill(o.envelope(code,kind,data,root=ROOT),root=ROOT),source)
                if kind=='evidence':self.assertEqual(len(o.defaults(code,kind)['evidenceList']),1)
                for key in ['committeeName','signature','applicationDate','copyCount','unknown']:
                    with self.assertRaises(ValueError):o.candidate_fill(o.envelope(code,kind,{key:'auto'},root=ROOT),root=ROOT)
        for value in [True,2,2.5,None,'0','02','10000','-1']:
            with self.assertRaises(ValueError):o.candidate_fill(o.envelope('350182','evidence',{'evidenceList':[{'pageCount':value}]},root=ROOT),root=ROOT)
        for data in [{'agentName':'x\t'},{'factsReason':'x'*2401},{'requests':['x']*4}]:
            with self.assertRaises(ValueError):o.candidate_fill(o.envelope('350122','application',data,root=ROOT),root=ROOT)

    def test_real_regeneration_new_safe_versions_and_twenty_two_zip_parities(self):
        o=self.o;manifest=json.loads((ROOT/o.WORD_MANIFEST).read_bytes());self.assertEqual((manifest['original_pages'],manifest['generated_pages']),(17,60))
        parity=json.loads((ROOT/o.PARITY_REPORT).read_bytes());self.assertEqual(len(parity['outputs']),22)
        self.assertTrue(parity['actual_new_safe_projection_regeneration']);self.assertFalse(parity['same_request_claimed'])
        for item in parity['outputs']:
            fixture=json.loads((ROOT/item['new_fixture']).read_bytes());request=fixture['request'];before=deepcopy(request)
            actual=o.candidate_fill(request,root=ROOT);self.assertEqual(request,before)
            reviewed=(ROOT/item['regenerated_docx']).read_bytes();self.assertEqual(actual,reviewed)
            self.assertEqual(sha256(actual).hexdigest(),item['previous_reviewed_docx_sha256'])
            self.assertNotEqual(request['source_version'],item['previous_source_version'])
            self.assertEqual(request['source_version'],o.REGIONS[item['region_code']]['manifest_sha256'])
            with ZipFile(BytesIO(actual)) as archive:
                self.assertEqual([{'name':p.filename,'bytes':len(archive.read(p)),'sha256':sha256(archive.read(p)).hexdigest()} for p in archive.infolist()],item['zip_members'])

    def test_cold_public_root_no_runtime_history_checkout_and_source_tamper(self):
        o=self.o;root=self.isolated()
        self.assertFalse((root/'.runtime').exists());self.assertFalse((root/'reports/overnight-gap-closure-20261030/localities/fujian-own-source-discovery').exists())
        with patch.object(o,'ROOT',root/'absent'):
            for code in o.REGIONS:
                g=o.parse_capture(code,root=root);self.assertIsNotNone(o.public_evidence(g,root))
                self.assertTrue(o.prepare_candidate(code,root=root)['can_generate'])
        for absent in [None,'',' ']:
            with self.assertRaises(ValueError):o.parse_capture('350122',root=absent)
        path=root/o.SOURCE_BASE/o.REGIONS['350182']['folder']/'boundary-qualification.json';path.write_bytes(b'{}')
        with self.assertRaises(ValueError):o.parse_capture('350182',root=root)
        self.assertEqual(o.parse_capture('350122',root=root)['region_code'],'350122')

    def test_public_source_and_qa_contain_no_private_or_signing_payload(self):
        o=self.o;paths=set(o.source_files(ROOT))|{o.WORD_MANIFEST}
        paths.update(r['path'] for r in json.loads((ROOT/o.WORD_MANIFEST).read_bytes())['files'])
        for name in paths:
            self.assertNotIn('.runtime/',name);self.assertNotIn('fujian-own-source-discovery/',name)
            if name.endswith('.json'):
                body=(ROOT/name).read_text(encoding='utf8').lower()
                for forbidden in ['x-wbsign','authorization": "bearer','c:\\\\users\\\\','"access_token"','"password"']:self.assertNotIn(forbidden,body,name)


if __name__=='__main__':unittest.main()
