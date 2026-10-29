"""Own-source Jiangyin/Yixing guards, independent of DB and private captures."""
from copy import deepcopy
from io import BytesIO
import hashlib
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
import regional_jiangsu_oct29 as adapter


def guide(code):
    return json.loads((ROOT/f'reports/nationwide-verification-20261029/jiangsu/{code}/guide.json').read_text(encoding='utf8'))


def payload():
    return dict(applicantName='虚构测试甲',respondentName='虚构测试单位',birthDate='1990-01-02',
                gender='女',nationality='汉',idNumber='000000199001020000',phone='00000000000',
                idAddress='虚构地址1号',registeredAddress='虚构单位2号',committeeName='虚构仲裁委员会',
                requests=['请求支付虚构工资100元。'],factsReason='仅供软件测试，所有信息均为虚构。',
                copyCount=3,evidenceCopyCount=2,evidenceList=[dict(name='虚构合同',source='虚构保存',
                purpose='虚构劳动关系',originalType='复印件',pageCount='3页')])


class JiangsuOwnSourceOct29Tests(unittest.TestCase):
    def test_independent_copy_counts_and_missing_evidence_count(self):
        for code in ['320281','320282']:
            g=guide(code)
            text='\n'.join(p.text for p in adapter.fill_candidate_document(g,'application',payload()).paragraphs)
            self.assertIn('本申请书副本3份',text)
            self.assertIn('相关证据2份',text)
            data=payload();data.pop('evidenceCopyCount')
            text='\n'.join(p.text for p in adapter.fill_candidate_document(g,'application',data).paragraphs)
            self.assertIn('相关证据    份',text)

    def test_own_forms_fill_preserving_unedited_package(self):
        for code in ['320281','320282']:
            g=guide(code);contract=adapter.candidate_contract(g)
            self.assertFalse(contract['published']);self.assertFalse(contract['generation_enabled'])
            for kind,item in contract['documents'].items():
                output=BytesIO();adapter.fill_candidate_document(g,kind,payload()).save(output)
                original=ROOT/item['source_file']
                self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),item['source_sha256'])
                with ZipFile(original) as a,ZipFile(output) as b:
                    self.assertEqual(a.namelist(),b.namelist())
                    self.assertEqual([n for n in a.namelist() if a.read(n)!=b.read(n)],['word/document.xml'])

    def test_reject_changed_locality_source_and_agency(self):
        for field,value in [('source_url','https://wxyx.jszwfw.gov.cn/'),('region_code','320205'),
            ('district','宜兴市'),('city','盐城市'),('authority','宜兴市人力资源和社会保障局'),
            ('service_code','002014302002'),('service_name','劳动人事争议调解申请'),('source_title','other'),
            ('source_id','wrong'),('verification_status','unverified'),('province','zhejiang')]:
            with self.subTest(field=field):
                g=guide('320281');g[field]=value
                with self.assertRaises(ValueError):adapter.fill_candidate_document(g,'application',payload())

    def test_reject_changed_annex_kind_hash_download_and_path(self):
        for field,value in [('id','9949cd24-29df-4db9-af04-b4395a22aa61'),('annex_id','wrong'),('sha256','0'*64),
            ('official_kind','sample'),('download_status','not_downloaded'),('region_code','320282'),
            ('source_url','https://example.test/'),('download_url','https://example.test/a.docx'),
            ('file','backend/regional_jiangsu.py'),('original_name','another.docx'),('material_id','wrong')]:
            with self.subTest(field=field):
                g=guide('320281');template=next(t for t in g['templates'] if t['id']=='2213bd5f-676c-4db0-9a4e-d9dd8b851919')
                template[field]=value
                with self.assertRaises(ValueError):adapter.fill_candidate_document(g,'application',payload())

    def test_reject_duplicate_and_changed_nested_authority(self):
        g=guide('320281');template=next(t for t in g['templates'] if t['id']=='2213bd5f-676c-4db0-9a4e-d9dd8b851919')
        g['templates'].append(deepcopy(template))
        with self.assertRaises(ValueError):adapter.candidate_contract(g)
        g=guide('320281');g['fields']['实施主体']['raw_value']='其他机关'
        with self.assertRaises(ValueError):adapter.candidate_contract(g)

    def test_clean_public_root_missing_or_corrupt_original_closes_generation(self):
        g=guide('320281');contract=adapter.candidate_contract(g)
        with tempfile.TemporaryDirectory() as temp:
            tmp_path=Path(temp)
            for item in contract['documents'].values():
                target=tmp_path/item['source_file'];target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/item['source_file'],target)
            with patch.object(adapter,'ROOT',tmp_path):
                self.assertEqual(adapter.candidate_contract(g)['region_code'],'320281')
                item=contract['documents']['application'];path=tmp_path/item['source_file'];path.write_bytes(b'corrupt')
                with self.assertRaises(ValueError):adapter.fill_candidate_document(g,'application',payload())
                path.unlink()
                with self.assertRaises(ValueError):adapter.candidate_contract(g)

    def test_unsupported_kind_and_sample_only_not_adapted(self):
        g=guide('320281')
        with self.assertRaises(ValueError):adapter.fill_candidate_document(g,'identity',payload())
        g['templates']=[t for t in g['templates'] if t['official_kind']=='sample']
        with self.assertRaises(ValueError):adapter.candidate_contract(g)
