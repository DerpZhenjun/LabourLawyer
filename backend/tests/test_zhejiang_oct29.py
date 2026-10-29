"""Own-source binding, refusal and package preservation for the Ningbo candidates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zipfile import ZipFile
from unittest.mock import patch

from regional_zhejiang_oct29 import (ROOT,REPORT,SPECS,Evidence,parse_capture,blank_binding,with_capabilities,fill_document)

class ZhejiangOct29Tests(unittest.TestCase):
    def test_each_own_guide_materials_channel_and_samples(self):
        for name,spec in SPECS.items():
            guide=with_capabilities(parse_capture(name))
            self.assertEqual(guide['city'],'宁波市');self.assertEqual(guide['region_code'],spec['code'])
            self.assertEqual(len(guide['materials']),5)
            self.assertEqual([t['can_generate'] for t in guide['templates']],[True,True,False])
            self.assertFalse(guide['published']);self.assertEqual(guide['channel']['online_status'],'auth_required')
            self.assertEqual(guide['fields']['受理决定时限']['scope'],'acceptance_decision_only')
            self.assertTrue(all(m['required'] is None for m in guide['materials']))

    def test_same_file_sha_does_not_authorize_other_district(self):
        first=with_capabilities(parse_capture('haishu'));second=with_capabilities(parse_capture('yinzhou'))
        self.assertEqual(first['templates'][0]['sha256'],second['templates'][0]['sha256'])
        self.assertIsNone(blank_binding(first,second['templates'][0]))
        for key,value in [('city','杭州市'),('region_code','330110'),('source_url',second['source_url']),('authority','未知机关'),('verification_status','missing')]:
            changed=deepcopy(first);changed[key]=value
            self.assertIsNone(blank_binding(changed,changed['templates'][0]),key)

    def test_changed_material_or_template_identity_refused(self):
        guide=with_capabilities(parse_capture('haishu'))
        changed=deepcopy(guide);changed['materials'][0]['copies']='1'
        self.assertIsNone(blank_binding(changed,changed['templates'][0]))
        for key,value in [('official_kind','sample'),('file','templates/other.docx'),('material_id','unbound'),('download_url','https://example.invalid/form.docx')]:
            template=deepcopy(guide['templates'][0]);template[key]=value
            self.assertIsNone(blank_binding(guide,template),key)

    def test_tampered_capture_is_rejected_without_resigning(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'reports/nationwide-verification-20261029/zhejiang') as tmp:
            dest=Path(tmp);shutil.copytree(ROOT/REPORT,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns(dest.name,'attempts','render','qa'))
            page=dest/'haishu/materials/page.json';value=json.loads(page.read_text(encoding='utf8'));value['text']+=' tampered'
            page.write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
            with self.assertRaises(ValueError):parse_capture('haishu',dest)

    def test_same_guide_url_with_previous_district_body_is_rejected(self):
        original=Evidence.load
        def load(evidence,relative):
            value=original(evidence,relative)
            if relative=='yinzhou/materials/page.json':
                previous=original(evidence,'haishu/materials/page.json')
                value['text']=previous['text']
            return value
        # Isolate the semantic identity check from the immutable-byte gate:
        # a correct new URL must not make an old district's SPA body valid.
        with patch.object(Evidence,'load',load):
            with self.assertRaisesRegex(ValueError,'切换前地区数据'):parse_capture('yinzhou')

    def test_fill_preserves_package_and_signature_and_original(self):
        for name in SPECS:
            guide=with_capabilities(parse_capture(name))
            for template in guide['templates'][:2]:
                kind=blank_binding(guide,template);path=ROOT/template['file'];before=path.read_bytes()
                data={'committeeName':'宁波市'+guide['district']+'劳动人事争议仲裁委员会','applicantName':'虚构测试甲','respondentName':'虚构测试公司乙',
                    'requests':['请求支付虚构工资100元。'],'factsReason':'全部为软件测试虚构内容。','caseNumber':'测试案号','submitterName':'不可自动填入手签',
                    'applicationDate':'2026-10-29','submitDate':'2026-10-29','evidenceList':[{'name':'虚构材料','pageCount':'2页','purpose':'虚构证明目的'}]}
                with tempfile.TemporaryDirectory(dir=ROOT/REPORT) as tmp:
                    output=Path(tmp)/'filled.docx';fill_document(guide,template,kind,path,data).save(output)
                    with ZipFile(path) as old,ZipFile(output) as new:
                        self.assertEqual(set(old.namelist()),set(new.namelist()))
                        self.assertEqual([n for n in old.namelist() if old.read(n)!=new.read(n)],['word/document.xml'])
                        xml=new.read('word/document.xml').decode('utf8')
                        self.assertNotIn('不可自动填入手签',xml)
                        self.assertIn('虚构',xml)
                self.assertEqual(path.read_bytes(),before)

    def test_arbitrary_input_path_and_sample_refused(self):
        guide=with_capabilities(parse_capture('yinzhou'));template=guide['templates'][0]
        with self.assertRaises(ValueError):fill_document(guide,template,'application',ROOT/'different.docx',{})
        with self.assertRaises(ValueError):fill_document(guide,guide['templates'][2],'application',ROOT/guide['templates'][2]['file'],{})

if __name__=='__main__':unittest.main()
