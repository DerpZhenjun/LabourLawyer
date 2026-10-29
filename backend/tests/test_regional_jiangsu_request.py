"""Exact Suzhou E JSON request slots; no source writes or application submission."""
import importlib.util
from pathlib import Path
import sys
import unittest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
request = __import__('regional_jiangsu_request') if importlib.util.find_spec('regional_jiangsu_request') else None
import regional_jiangsu_oct29e as provider

APPLICATION = {'committeeName', 'applicantName', 'birthDate', 'gender', 'idNumber', 'idAddress',
    'otherDocumentType', 'otherDocumentNumber', 'applicantMailingAddress', 'phone', 'acceptMediation', 'legalAid',
    'respondentName', 'respondentType', 'registeredAddress', 'socialCreditCode', 'legalRepName', 'legalRepPosition',
    'departmentHead', 'departmentHeadPosition', 'mailingAddress', 'companyContact', 'companyContactPhone',
    'requests', 'factsReason', 'applicationDate', 'copyCount', 'evidenceCopyCount'}
EVIDENCE = {'committeeName', 'caseNumber', 'submitDate', 'evidenceList'}
ITEM = {'name', 'source', 'purpose', 'originalType', 'pageCount'}


class RegionalJiangsuRequestTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(request, 'Exact Jiangsu E request contract is not implemented')

    def test_exact_declared_fields_and_blank_defaults_have_no_non_slots(self):
        for model, fields in [(request.ApplicationRequest, APPLICATION), (request.EvidenceRequest, EVIDENCE),
                              (request.EvidenceItem, ITEM)]:
            self.assertEqual(set(model.model_fields), fields)
            data = model().model_dump()
            self.assertEqual(set(data), fields)
            self.assertTrue(all(v in ('', None, []) for v in data.values()))
        self.assertEqual(APPLICATION, provider.DATA_FIELDS['application'])
        self.assertEqual(EVIDENCE, provider.DATA_FIELDS['evidence'])
        self.assertEqual(ITEM, provider.DATA_FIELDS['evidence_item'])

    def test_unknown_keys_even_empty_and_non_slot_evidence_copies_are_rejected(self):
        for model, data in [(request.ApplicationRequest, {'nationality': ''}),
                            (request.ApplicationRequest, {'wrong': None}),
                            (request.EvidenceRequest, {'copyCount': ''}),
                            (request.EvidenceRequest, {'evidenceCopyCount': None}),
                            (request.EvidenceItem, {'wrong': ''}),
                            (request.EvidenceRequest, {'evidenceList': [{'name': '', 'wrong': ''}]})]:
            with self.subTest(model=model.__name__, data=data), self.assertRaises(ValidationError):
                model.model_validate(data)

    def test_optional_partial_fields_and_free_text_choices_are_lossless(self):
        data = {'phone': '虚构电话', 'otherDocumentNumber': '虚构证件号', 'birthDate': '1991-05-09',
                'acceptMediation': '待纸面确认', 'legalAid': '自行咨询', 'otherDocumentType': '虚构其他证件'}
        parsed = request.ApplicationRequest.model_validate(data).model_dump()
        for k, v in data.items(): self.assertEqual(parsed[k], v)
        partial = request.EvidenceRequest.model_validate({'evidenceList': [{'source': '虚构仅填来源',
                       'purpose': '虚构用途', 'originalType': '原件及复印件'}]}).model_dump()
        self.assertEqual(partial['evidenceList'][0]['name'], '')
        self.assertEqual(partial['evidenceList'][0]['source'], '虚构仅填来源')
        self.assertEqual(partial['evidenceList'][0]['originalType'], '原件及复印件')
        self.assertNotIn('copyCount', partial)

    def test_copy_counts_are_independent_and_match_provider_integer_rules(self):
        for value, expected in [('', None), (None, None), (1, 1), (30, 30), ('3', 3)]:
            parsed = request.ApplicationRequest.model_validate({'copyCount': value, 'evidenceCopyCount': value})
            self.assertEqual((parsed.copyCount, parsed.evidenceCopyCount), (expected, expected))
        parsed = request.ApplicationRequest(copyCount=3, evidenceCopyCount=2)
        self.assertEqual((parsed.copyCount, parsed.evidenceCopyCount), (3, 2))
        for value in [True, False, 0, 31, 1.0, 3.5, '0', '3.0', ' 3 ', '-1']:
            for key in ['copyCount', 'evidenceCopyCount']:
                with self.subTest(value=value, key=key), self.assertRaises(ValidationError):
                    request.ApplicationRequest.model_validate({key: value})

    def test_dates_require_actual_iso_calendar_date_before_type_coercion(self):
        for model, key in [(request.ApplicationRequest, 'birthDate'), (request.ApplicationRequest, 'applicationDate'),
                           (request.EvidenceRequest, 'submitDate')]:
            for value in ['', None, '1991-05-09', '2024-02-29']:
                result = model.model_validate({key: value}).model_dump()
                self.assertEqual(result[key], value or '')
            for value in ['1991-02-30', '2023-02-29', '1991-5-9', '1991/05/09', ' 1991-05-09 ', 19910509]:
                with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                    model.model_validate({key: value})

    def test_unicode_xml_and_wrong_types_rejected_without_replacing_or_truncating(self):
        valid = '虚构汉字🙂𠀀\n\t尾'
        self.assertEqual(request.ApplicationRequest(phone=valid).phone, valid)
        for value in ['\x00', '\x01', '\x0b', '\ud800', '\udfff', '\ufffe', '\uffff', 123, True, [], {}]:
            for model, data in [(request.ApplicationRequest, {'phone': value}),
                                (request.EvidenceItem, {'purpose': value}),
                                (request.EvidenceRequest, {'evidenceList': [{'source': value}]})]:
                with self.subTest(value=repr(value), model=model.__name__), self.assertRaises(ValidationError):
                    model.model_validate(data)

    def test_limits_accept_boundaries_and_reject_overflow_or_wrong_collection_types(self):
        self.assertEqual(len(request.ApplicationRequest(phone='字' * 300).phone), 300)
        self.assertEqual(len(request.ApplicationRequest(factsReason='字' * 12000).factsReason), 12000)
        self.assertEqual(len(request.ApplicationRequest(requests=['字' * 1200] * 4).requests), 4)
        self.assertEqual(request.ApplicationRequest(requests=[None]).requests, [''])
        self.assertEqual(len(request.EvidenceRequest(evidenceList=[{'purpose': '字' * 1200}] * 40).evidenceList), 40)
        for model, data in [(request.ApplicationRequest, {'phone': '字' * 301}),
                            (request.ApplicationRequest, {'factsReason': '字' * 12001}),
                            (request.ApplicationRequest, {'requests': ['字' * 1201]}),
                            (request.ApplicationRequest, {'requests': ['项'] * 5}),
                            (request.ApplicationRequest, {'requests': '一项'}),
                            (request.EvidenceRequest, {'evidenceList': [{}] * 41}),
                            (request.EvidenceRequest, {'evidenceList': '证据'}),
                            (request.EvidenceItem, {'purpose': '字' * 1201}),
                            (request.EvidenceItem, {'pageCount': '字' * 301})]:
            with self.subTest(model=model.__name__, data=str(data)[:35]), self.assertRaises(ValidationError):
                model.model_validate(data)

    def test_model_dump_is_accepted_by_actual_provider_validator(self):
        data = request.ApplicationRequest(phone='虚构电话', copyCount='3', evidenceCopyCount=2).model_dump()
        self.assertEqual(provider._validate_data('application', data), data)
        item = request.EvidenceItem(source='虚构来源')
        data = request.EvidenceRequest(evidenceList=[item]).model_dump()
        self.assertEqual(provider._validate_data('evidence', data), data)


if __name__ == '__main__':
    unittest.main()
