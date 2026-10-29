"""Evidence review must never turn an unknown locality into an absence claim."""
import importlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class VerificationTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('regional_verification')

    def record(self):
        return {'province': 'sichuan', 'city': '成都市', 'district': '青羊区',
                'region_code': '510105000000', 'checked_at': '2026-10-29T08:40:36Z',
                'source_url': 'https://www.sczwfw.gov.cn/guide?areaCode=510105000000',
                'authority': '成都市青羊区人力资源和社会保障局',
                'reviewed_sections': ['基本信息', '申请材料'],
                'guide_status': 'candidate', 'generation_enabled': False,
                'templates': [], 'application_template_status': 'not_found_in_checked_sources',
                'evidence_template_status': 'not_checked',
                'note': '本次核验材料栏未找到申请书；不能推断其他官方页面也没有。'}

    def test_search_miss_and_unreviewed_are_distinct_and_never_prove_absence(self):
        record = self.module().validate_record(self.record())
        self.assertEqual(record['application_template_status'], 'not_found_in_checked_sources')
        self.assertEqual(record['evidence_template_status'], 'not_checked')
        self.assertFalse(record['generation_enabled'])

    def test_official_absence_requires_actual_public_quote_and_bounded_document_kind(self):
        record = self.record(); record['application_template_status'] = 'officially_not_provided'
        with self.assertRaisesRegex(ValueError, '官方明确'):
            self.module().validate_record(record)
        record['official_statements'] = {'application': {'quote': '暂无相关结果', 'source_url': record['source_url']}}
        with self.assertRaises(ValueError):
            self.module().validate_record(record)

    def test_explicit_absence_is_bound_to_its_retained_quote_and_own_document_kind(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);file=root/'reports/source.txt';file.parent.mkdir()
            quote='该事项不提供仲裁申请书空白模板。';file.write_bytes(quote.encode('utf-8'))
            record=self.record();record['application_template_status']='officially_not_provided'
            record['official_statements']={'application':{'quote':quote,'source_url':record['source_url'],
                'scope':'checked_source_only','evidence_file':'reports/source.txt','sha256':hashlib.sha256(file.read_bytes()).hexdigest()}}
            self.assertEqual(self.module().validate_record(record,root)['application_template_status'],'officially_not_provided')
            record['official_statements']['application']['sha256']='0'*64
            with self.assertRaises(ValueError):self.module().validate_record(record,root)
            record['application_template_status']='not_found_in_checked_sources';record['evidence_template_status']='officially_not_provided'
            record['official_statements']['evidence']=record['official_statements'].pop('application')
            with self.assertRaises(ValueError):self.module().validate_record(record,root)

    def test_sample_is_not_blank_and_other_locality_or_unhashed_file_is_not_evidence(self):
        record = self.record(); record['application_template_status'] = 'blank_found'
        sample = {'region_code': record['region_code'], 'kind': 'sample', 'document_types': ['application'],
                  'sha256': 'a'*64, 'source_url': record['source_url'], 'original_name': '申请书样例.docx'}
        record['templates'] = [sample]
        with self.assertRaises(ValueError): self.module().validate_record(record)
        sample['kind'] = 'blank'; sample['region_code'] = '510107000000'
        with self.assertRaises(ValueError): self.module().validate_record(record)
        sample['region_code'] = record['region_code']; sample['sha256'] = ''
        with self.assertRaises(ValueError): self.module().validate_record(record)
        sample['sha256'] = 'a'*64
        self.assertEqual(self.module().validate_record(record)['application_template_status'], 'blank_found')

    def test_review_registry_cannot_enable_generation_or_claim_publication(self):
        for key, value in [('generation_enabled', True), ('guide_status', 'published')]:
            record = self.record(); record[key] = value
            with self.assertRaises(ValueError): self.module().validate_record(record)

    def test_discovery_without_a_matched_guide_does_not_invent_an_authority_or_absence(self):
        record=self.record();record['guide_status']='discovery_only';record['authority']=None
        record['application_template_status']='not_checked'
        valid=self.module().validate_record(record)
        self.assertIsNone(valid['authority'])
        self.assertFalse(valid['generation_enabled'])

    def test_sources_are_official_https_and_dates_real(self):
        for url in ['https://gov.cn.example.com/guide', 'http://www.sczwfw.gov.cn/guide', 'https://example.com']:
            record = self.record(); record['source_url'] = url
            with self.assertRaises(ValueError): self.module().validate_record(record)
        record = self.record(); record['checked_at'] = 'recent'
        with self.assertRaises(ValueError): self.module().validate_record(record)

    def test_registry_rejects_duplicate_exact_locality_and_has_no_inherited_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path = root/'config/regional_verifications.json'; path.parent.mkdir()
            path.write_text(json.dumps([self.record(), self.record()]), encoding='utf-8')
            with self.assertRaises(ValueError): self.module().load_registry(root)
            path.write_text(json.dumps([self.record()]), encoding='utf-8')
            result = self.module().load_registry(root)
            self.assertEqual(len(result), 1)
            self.assertNotIn('武汉市', json.dumps(result, ensure_ascii=False))
            self.assertEqual(self.module().lookup_review(result, 'sichuan', '成都市', '武侯区'),
                             {'guide_status': 'not_checked', 'application_template_status': 'not_checked',
                              'evidence_template_status': 'not_checked', 'generation_enabled': False})


if __name__ == '__main__': unittest.main()
