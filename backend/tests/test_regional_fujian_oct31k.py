"""K own-source phase gates; Temp/counterfactual data, no public seed writes."""
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


class FujianKProviderTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'backend/regional_fujian_oct31k.py').is_file(), 'Independent K provider is required')
        self.o=importlib.import_module('regional_fujian_oct31k')

    def isolated(self):
        temp=tempfile.TemporaryDirectory(prefix='own-k-public-');self.addCleanup(temp.cleanup);root=Path(temp.name)
        for name in self.o.source_files(ROOT):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,path)
        return root

    def test_three_own_identities_four_blanks_and_no_city_or_foreign_facts(self):
        o=self.o;self.assertEqual(set(o.REGIONS),{'350111','350121','350105'})
        self.assertEqual(o.REGIONS['350121']['source_id'],'70d8f78ba93e94e9afecf7f3')
        total=0
        for code,meta in o.REGIONS.items():
            g=o.parse_capture(code,root=ROOT);self.assertFalse(g['can_generate']);self.assertFalse(g['published'])
            self.assertEqual(g['source_id'],o.digest(meta['source_url'])[:24]);self.assertEqual(g['source_version'],meta['manifest_sha256'])
            self.assertEqual(g['authority'],meta['authority']);self.assertIsNone(g['committee_full_name'])
            self.assertFalse(g['committee_autofill_allowed']);self.assertIsNone(g['official_version'])
            self.assertEqual([m['copies'] for m in g['materials']],[2,2,2]);self.assertEqual(len(g['materials']),3)
            self.assertEqual(g['fields']['业务办理项编码']['raw_value'],meta['service_code'])
            c=o.prepare_candidate(code,root=ROOT);total+=sum(t['can_generate'] for t in c['templates'])
            self.assertTrue(c['offline_candidate']);self.assertFalse(c['published'])
            for t in c['templates']:
                if t['can_generate']:
                    self.assertEqual(t['official_kind'],'blank');self.assertIn(meta['folder'],t['file'])
            self.assertIn('本区公开办事指南原文',g['sections'])
        self.assertEqual(total,4)
        for bad in ['350100','350103','350122','370100',350111,True]:
            with self.assertRaises(ValueError):o.parse_capture(bad,root=ROOT)

    def test_nonblank_evidence_is_unknown_not_absent_and_never_generates(self):
        for code in ['350121','350105']:
            g=self.o.prepare_candidate(code,root=ROOT)
            evidence=[t for t in g['templates'] if t['material_id']==g['materials'][1]['id']]
            self.assertEqual(len(evidence),2)
            for t in evidence:self.assertFalse(t['can_generate']);self.assertEqual(t['document_types'],[])
            self.assertEqual(g['materials'][1]['generation_status'],'UNKNOWN_NOT_ADAPTED')
            with self.assertRaises(ValueError):self.o.envelope(code,'evidence',{},root=ROOT)

    def test_minhou_unrelated_official_row_is_preserved_but_not_normalized_as_arbitration_fact(self):
        g=self.o.parse_capture('350121',root=ROOT);field=g['fields']['权责清单']
        self.assertEqual(field['raw_value'],'企业年金方案报备')
        self.assertIsNone(field['normalized_value']);self.assertEqual(field['verification_status'],'unverified')
        self.assertEqual(field['source_url'],g['source_url'])
        self.assertIn('官网部分说明与此事项不一致，需向办理机构核对',g['warnings'])
        body=self.o.candidate_fill(self.o.envelope('350121','application',{'applicantName':'虚构甲','respondentName':'虚构乙','requests':['纯虚构请求'],'factsReason':'仅测试'},root=ROOT),root=ROOT)
        with ZipFile(BytesIO(body)) as z:self.assertNotIn('企业年金',z.read('word/document.xml').decode())

    def test_own_time_fee_window_and_flow_are_exposed_without_imported_neighbor_values(self):
        for code in self.o.REGIONS:
            g=self.o.parse_capture(code,root=ROOT);raw=g['sections']['本区公开办事指南原文']
            for label in ['办理时间','办理地点','交通指引']:
                self.assertIn(label,g['fields']);f=g['fields'][label]
                self.assertIn(f['raw_value'],raw);self.assertEqual(f['source_url'],g['source_url'])
                self.assertIn('text/',f['source_pointer'])
            self.assertEqual(g['fields']['是否收费']['normalized_value'],'不收费')
            self.assertIn('受理后5个工作日',g['fields']['承诺时限']['raw_value'])
            self.assertIn('办理流程与窗口办理',g['sections'])
            self.assertIn('受理条件',g['sections'])

    def test_display_aliases_and_material_types_project_only_own_original_values(self):
        aliases={'承诺办结时限':'承诺时限','法定办结时限':'法定时限','咨询方式':'联系电话','必须到现场原因':'必须现场办理原因','服务对象':'申报对象'}
        for code,meta in self.o.REGIONS.items():
            g=self.o.parse_capture(code,root=ROOT)
            source=json.loads((ROOT/self.o.SOURCE_BASE/meta['folder']/'NORMALIZED-OWN-SOURCE.json').read_text('utf8'))
            self.assertEqual(g.get('province_name'),source['official_title'].split('网上办事大厅',1)[0])
            for alias,raw in aliases.items():
                self.assertIn(alias,g['fields']);self.assertEqual(g['fields'][alias],g['fields'][raw])
                self.assertEqual(g['fields'][raw]['raw_value'],source['raw_fields'][raw]['raw_value'])
            self.assertEqual([m.get('original_copy') for m in g['materials']],['原件','原件','复印件'])
            self.assertEqual([m['paper_copies'] for m in g['materials']],[2,2,2])
            for material,own in zip(g['materials'],source['materials']):
                self.assertEqual(material['raw_source_text'],own['raw_public_text'])
                self.assertEqual(material['copies_source_literal'],own['copies_literal'])
                self.assertIn(material['instructions'],own['raw_public_text'])

    def test_all_stage_final_and_forged_boolean_claims_fail_closed(self):
        o=self.o
        from regional_adapters import checked_reference_adapter
        with patch.object(o,'STAGE_SHA256',None),patch.object(o,'PUBLICATION_SHA256',None):
            for code in o.REGIONS:
                raw=o.parse_capture(code,root=ROOT);candidate=o.prepare_candidate(code,root=ROOT)
                self.assertEqual(o.with_capabilities(raw,root=ROOT),raw)
                t=next(t for t in candidate['templates'] if t['can_generate'])
                with self.assertRaises(ValueError):checked_reference_adapter(candidate,t,'application',root=ROOT)
                for call in [lambda:o.staged_candidate(code,root=ROOT),lambda:o.checked_adapter(candidate,t,'application',root=ROOT),lambda:o.with_capabilities(candidate,root=ROOT),lambda:o.with_publication_evidence(candidate,root=ROOT)]:
                    with self.assertRaises(ValueError):call()
                forged=deepcopy(raw);forged.update(can_generate=True,published=True)
                self.assertIsNone(o.public_evidence(forged,ROOT));self.assertFalse(o.approved_report_attachment(forged,t,ROOT))
        with patch.object(o,'STAGE_SHA256',True),self.assertRaises(ValueError):o.staged_candidate('350111',root=ROOT)

    def test_real_root_stage_remains_unpublished_and_final_pin_is_independent(self):
        o=self.o;self.assertEqual(o.STAGE_SHA256,'d23c44632e61878f597e74528c949603a868ca471f5c83245be579deb7bc8b19')
        self.assertEqual(o.PUBLICATION_SHA256,'3f24c81c617733000c85f1c76b4c2e4bcd0a08e82f34b5323dbeea0b6a7154be')
        for code in o.REGIONS:
            g=o.staged_candidate(code,root=ROOT)
            self.assertFalse(g['published']);self.assertEqual(g['publication_status'],'staged_own_word_qa')
            self.assertEqual(g['candidate_adapter_evidence']['sha256'],o.STAGE_SHA256)
            self.assertNotIn('publication_adapter_evidence',g)
            with patch.object(o,'PUBLICATION_SHA256',None),self.assertRaises(ValueError):o.with_publication_evidence(g,root=ROOT)

    def test_missing_or_tampered_own_source_has_no_root_fallback(self):
        o=self.o;root=self.isolated();code='350111';meta=o.REGIONS[code]
        path=root/o.SOURCE_BASE/meta['folder']/'own-guide-native-dom.json';body=path.read_bytes();path.write_bytes(body+b' ')
        with self.assertRaises(ValueError):o.parse_capture(code,root=root)
        path.write_bytes(body);path.unlink()
        with self.assertRaises(ValueError):o.parse_capture(code,root=root)
        self.assertEqual(o.parse_capture(code,root=ROOT)['region_code'],code)

    def test_changed_source_manifest_cannot_repin_itself(self):
        o=self.o;root=self.isolated();m=o.REGIONS['350121'];p=root/o.SOURCE_BASE/m['folder']/'SOURCE-PROJECTION-MANIFEST.json'
        data=json.loads(p.read_text('utf8'));data['authority']='foreign';p.write_text(json.dumps(data),encoding='utf8')
        with self.assertRaises(ValueError):o.parse_capture('350121',root=root)

    def test_request_rejects_counterfactual_source_region_template_schema_and_legacy_minhou_id(self):
        o=self.o
        for code,meta in o.REGIONS.items():
            request=o.envelope(code,'application',o.defaults(code,'application'),root=ROOT)
            for key,value in [('province','jiangsu'),('city','济南市'),('district','邻区'),('region_code','350100'),('source_id','3b6dd0535bf4cb4ed328fda4'),('source_url','https://example.gov.cn/foreign'),('source_version','0'*64),('material_id','foreign'),('template_id','98A0EE44D3D63B3D6A10FE60D4E83776'),('template_sha256','0'*64),('template_file','../../foreign.docx'),('schema_id','foreign'),('schema_version',True),('schema_version','1'),('kind','reference'),('mode','reference_adaptation')]:
                bad=deepcopy(request);bad[key]=value
                with self.subTest(code=code,key=key),self.assertRaises(ValueError):o.validate_request(bad,root=ROOT)

    def test_strict_field_types_controls_unknown_keys_and_capacity(self):
        o=self.o
        for data in [{'applicantName':True},{'applicantName':None},{'requests':'claim'},{'requests':[True]},{'requests':['x']*4},{'factsReason':'\x01bad'},{'factsReason':'\ud800'},{'unknown':'x'}]:
            with self.subTest(data=repr(data)),self.assertRaises(ValueError):o.candidate_fill(o.envelope('350111','application',data,root=ROOT),root=ROOT)
        for data in [{'evidenceList':'x'},{'evidenceList':[False]},{'evidenceList':[{'name':1}]},{'evidenceList':[{'originalType':'电子证据'}]},{'evidenceList':[{'pageCount':'-1'}]},{'evidenceList':[{'pageCount':True}]},{'evidenceList':[{'unexpected':'x'}]},{'evidenceList':[{}]*10}]:
            with self.subTest(data=repr(data)),self.assertRaises(ValueError):o.candidate_fill(o.envelope('350111','evidence',data,root=ROOT),root=ROOT)

    def test_blank_defaults_return_exact_own_original_and_evidence_default_has_one_row(self):
        o=self.o
        for code,meta in o.REGIONS.items():
            for kind in meta['allowed_kinds']:
                defaults=o.defaults(code,kind)
                if kind=='evidence':self.assertEqual(len(defaults['evidenceList']),1)
                self.assertEqual(o.candidate_fill(o.envelope(code,kind,defaults,root=ROOT),root=ROOT),o.template_path(code,kind,root=ROOT).read_bytes())

    def test_fictional_application_only_changes_document_member_and_never_autofills_committee_signature_date(self):
        o=self.o
        for code in o.REGIONS:
            original=o.template_path(code,'application',root=ROOT).read_bytes()
            body=o.candidate_fill(o.envelope(code,'application',{'applicantName':'虚构甲（仅测试）','respondentName':'虚构乙公司（仅测试）','requests':['虚构请求用于版式验证'],'factsReason':'纯虚构事实，不是实际案件。'},root=ROOT),root=ROOT)
            with ZipFile(BytesIO(original)) as a,ZipFile(BytesIO(body)) as b:
                self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist())
                for n in a.namelist():
                    if n!='word/document.xml':self.assertEqual(a.read(n),b.read(n))
                ar=o.E.fromstring(a.read('word/document.xml')).findall('w:body/w:p',o.N);br=o.E.fromstring(b.read('word/document.xml')).findall('w:body/w:p',o.N)
                for index in [16,19,20]:self.assertEqual(''.join(ar[index].itertext()),''.join(br[index].itertext()))
                self.assertIn('纯虚构事实',b.read('word/document.xml').decode())

    def test_evidence_one_row_has_real_totals_without_invented_remaining_rows(self):
        o=self.o;data={'evidenceList':[{'name':'纯虚构劳动合同（测试）','pageCount':'2','originalType':'复印件','purpose':'仅作版式检验','pageRange':'1-2'}]}
        body=o.candidate_fill(o.envelope('350111','evidence',data,root=ROOT),root=ROOT)
        with ZipFile(BytesIO(body)) as z:
            xml=o.E.fromstring(z.read('word/document.xml'));rows=xml.findall('.//w:tbl/w:tr',o.N)
            self.assertEqual(len(rows),3);self.assertIn('1份（组） 2页',''.join(rows[-1].itertext()))
            self.assertEqual(len(rows[-1].findall('w:tc',o.N)),1)
            self.assertEqual(''.join(xml.findall('w:body/w:p',o.N)[1].itertext()),'提交人：                 日期：          ')

    def test_safe_source_projection_does_not_require_legacy_private_records(self):
        o=self.o;root=self.isolated()
        for code in o.REGIONS:self.assertEqual(o.parse_capture(code,root=root)['region_code'],code)
        for name in o.source_files(root):
            self.assertTrue(name.startswith(o.SOURCE_BASE+'/'));self.assertNotIn('/.runtime/',name)
            if name.endswith('.json'):
                text=(root/name).read_text('utf8').lower()
                for forbidden in ['x-wbsign','set-cookie','access_token','authorization:','"cookie"','"headers"']:self.assertNotIn(forbidden,text)

    def test_sealed_eight_fictional_fixtures_reproduce_every_reviewed_ZIP_member(self):
        o=self.o;self.assertIsNotNone(o.WORD_SHA,'Own candidate Word QA must be sealed before review handoff')
        manifest=o._word_manifest(ROOT);self.assertEqual(manifest['fictional_fixtures'],8)
        index=json.loads((ROOT/o.QA_REPORT/'FICTIONAL-FIXTURE-INDEX.json').read_text('utf8'))
        self.assertEqual(len(index['cases']),8)
        for row in index['cases']:
            fixture=json.loads((ROOT/row['fixture']).read_text('utf8'));self.assertTrue(fixture['fictional_only'])
            saved=(ROOT/row['output']).read_bytes();regenerated=o.candidate_fill(fixture['request'],root=ROOT)
            self.assertEqual(sha256(saved).hexdigest(),row['sha256'])
            with ZipFile(BytesIO(saved)) as a,ZipFile(BytesIO(regenerated)) as b:
                self.assertIsNone(b.testzip());self.assertEqual(a.namelist(),b.namelist())
                for name in a.namelist():self.assertEqual(a.read(name),b.read(name))


if __name__=='__main__':unittest.main(verbosity=2)
