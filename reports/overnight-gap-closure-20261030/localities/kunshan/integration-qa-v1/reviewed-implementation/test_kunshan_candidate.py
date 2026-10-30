"""Private own-source Kunshan candidate tests; no registry, DB or network writes."""
from copy import deepcopy
from io import BytesIO
import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('kunshan_candidate',Path(__file__).with_name('kunshan_candidate.py'))
candidate=importlib.util.module_from_spec(spec)
if Path(spec.origin).exists():spec.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.guide=candidate.prepare_candidate(ROOT)
        self.application={'applicantName':'测试劳动者甲','respondentName':'昆山虚构制造有限公司',
                          'requests':['请求支付虚构工资1000元。'],'factsReason':'以下内容仅为离线测试。',
                          'applicationDate':'2026-10-31','birthDate':'1990-01-02'}
        self.evidence={'evidenceList':[{'name':'虚构工资记录','source':'测试劳动者','purpose':'说明虚构工资争议',
                                      'originalType':'复印件','pageCount':'1'}]}

    def fill(self,kind,data,guide=None,template=None,version=None):
        guide=self.guide if guide is None else guide
        template=candidate.template_for(guide,kind) if template is None else template
        return candidate.fill_candidate(guide,template,kind,data,root=ROOT,
            source_version=candidate.FREEZE_SHA if version is None else version)

    def test_source_candidate_is_exact_and_cannot_claim_publication(self):
        self.assertEqual(self.guide['region_code'],'320583')
        self.assertEqual(self.guide['source_id'],'d39444ab7f4bcaea2ea91473')
        self.assertEqual(self.guide['fields']['办理形式'],'窗口办理,网上办理,快递申请')
        self.assertEqual(self.guide['channel']['online_status'],'auth_required')
        self.assertEqual([m['paper_copies'] for m in self.guide['materials']],['2份','2份','1份','4份'])
        self.assertFalse(self.guide['can_generate']);self.assertFalse(self.guide['published'])
        self.assertTrue(all(not t['can_generate'] for t in self.guide['templates']))

    def test_region_source_and_version_mismatch_refused(self):
        for field,value in [('region_code','320581'),('district','常熟市'),('source_id','wrong'),
                            ('source_url','https://another.gov.cn/guide')]:
            changed=deepcopy(self.guide);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.fill('application',self.application,guide=changed)
        with self.assertRaises(ValueError):self.fill('application',self.application,version='stale')

    def test_template_annex_hash_region_sample_and_heading_refused(self):
        original=candidate.template_for(self.guide,'application')
        for field,value in [('id','foreign-annex'),('sha256','0'*64),('region_code','320582'),('official_kind','sample')]:
            changed=deepcopy(original);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.fill('application',self.application,template=changed)
        heading=self.guide['templates'][0]
        with self.assertRaises(ValueError):self.fill('application',self.application,template=heading)
        with self.assertRaises(ValueError):self.fill('unsupported',{})

    def test_default_evidence_has_one_empty_item(self):
        default=candidate.default_data('evidence')
        self.assertEqual(len(default['evidenceList']),1)
        self.assertTrue(all(v=='' for v in default['evidenceList'][0].values()))
        with self.assertRaises(ValueError):self.fill('evidence',default)

    def test_unknown_fields_bad_types_dates_and_blank_required_refused(self):
        for data in [{**self.application,'unknown':'x'},{**self.application,'copyCount':True},
                     {**self.application,'applicationDate':'2026-02-30'},
                     {**self.application,'requests':[]},{**self.application,'factsReason':' '},
                     {**self.application,'acceptMediation':'自动同意'}]:
            with self.subTest(data=data),self.assertRaises(ValueError):self.fill('application',data)
        for data in [{'evidenceList':[]},{'evidenceList':[{'name':'x','unknown':'x'}]}]:
            with self.assertRaises(ValueError):self.fill('evidence',data)

    def test_worker_form_uses_own_slots_and_preserves_blank_signature(self):
        document=self.fill('application',{**self.application,'acceptMediation':'否','legalAid':'是',
            'copyCount':1,'evidenceCopyCount':2})
        text='\n'.join(p.text for p in document.paragraphs)
        self.assertIn('测试劳动者甲',text);self.assertIn('昆山虚构制造有限公司',text)
        self.assertNotIn('用人单位申请',text);self.assertEqual(text.count('被申请人：'),1)
        self.assertIn('是否接受调解：否',text);self.assertIn('是否法律援助：是',text)
        self.assertIn('本申请书副本1份',text.replace(' ',''));self.assertIn('相关证据2份',text.replace(' ',''))
        signature=next(p.text for p in document.paragraphs if '签名、盖章或指模' in p.text)
        self.assertNotIn('测试劳动者甲',signature)
        self.assertEqual(document.paragraphs[0].text,'劳动人事争议仲裁申请书（劳动者申请）')

    def test_unselected_mediation_and_aid_remain_blank(self):
        document=self.fill('application',self.application)
        paragraph=next(p.text for p in document.paragraphs if '是否接受调解' in p.text)
        self.assertNotIn('是',paragraph.replace('是否',''));self.assertNotIn('否',paragraph.replace('是否',''))

    def test_evidence_six_own_columns_and_human_signatures_untouched(self):
        document=self.fill('evidence',{**self.evidence,'submitDate':'2026-10-31','caseNumber':'虚构测试号'})
        table=document.tables[0]
        self.assertEqual(len(table.rows),2)
        self.assertEqual([c.text for c in table.rows[1].cells],['1','虚构工资记录','测试劳动者','说明虚构工资争议','复印件','1'])
        self.assertIn('2026年10月31日',document.paragraphs[5].text)
        self.assertNotIn('测试劳动者',document.paragraphs[5].text)
        self.assertEqual(document.paragraphs[6].text,'接收人：                        接收时间：   年    月    日')

    def test_longer_evidence_list_expands_without_replacing_header(self):
        items=[{**self.evidence['evidenceList'][0],'name':f'虚构材料{i}'} for i in range(15)]
        document=self.fill('evidence',{'evidenceList':items})
        self.assertEqual(len(document.tables[0].rows),16)
        self.assertEqual(document.tables[0].rows[0].cells[1].text,'证据名称')
        self.assertEqual(document.tables[0].rows[-1].cells[1].text,'虚构材料14')

    def test_only_document_part_changes_in_saved_package(self):
        for kind,data in [('application',self.application),('evidence',self.evidence)]:
            document=self.fill(kind,data);target=BytesIO();document.save(target)
            template=candidate.template_for(self.guide,kind)
            original=(ROOT/template['file']).read_bytes()
            with ZipFile(BytesIO(original)) as before,ZipFile(BytesIO(target.getvalue())) as after:
                self.assertEqual(before.namelist(),after.namelist())
                self.assertEqual([name for name in before.namelist() if before.read(name)!=after.read(name)],['word/document.xml'])


if __name__=='__main__':unittest.main()
