import unittest
import json
from pathlib import Path

from chengdu_collection import select_service
from regional_capture import parse_sichuan_capture


class ChengduDiscoveryTests(unittest.TestCase):
    def test_gaoxin_official_full_name_not_arbitrary_substring(self):
        root = Path(__file__).resolve().parents[2]
        capture = json.loads((root / 'reports/chengdu-district-expansion-20261023/captures/510109000000/dom.json').read_text(encoding='utf8'))
        metadata = {'areaCode': '510109000000', 'shortName': '成都高新区', 'name': '成都高新技术产业开发区'}
        guide = parse_sichuan_capture(capture, '成都市', '成都高新区', region_metadata=metadata)
        self.assertEqual(guide['authority'], '中共成都高新技术产业开发区工作委员会社会工作部')
        self.assertEqual(guide['channel']['online_status'], 'unavailable')
        with self.assertRaises(ValueError):
            parse_sichuan_capture(capture, '成都市', '成都高新区', region_metadata={**metadata, 'areaCode': '510104000000'})

    def test_official_functional_area_full_name_with_matching_code(self):
        root = Path(__file__).resolve().parents[2]
        capture = json.loads((root / 'reports/chengdu-district-expansion-20261023/captures/510186000000/dom.json').read_text(encoding='utf8'))
        metadata = {'areaCode': '510186000000', 'shortName': '东部新区', 'name': '成都东部新区'}
        guide = parse_sichuan_capture(capture, '成都市', '东部新区', region_metadata=metadata)
        self.assertEqual(guide['region_code'], '510186000000')
        self.assertEqual(len(guide['materials']), 4)
        with self.assertRaises(ValueError):
            parse_sichuan_capture(capture, '成都市', '金牛区', region_metadata=metadata)

    def test_rejects_mediation_and_another_locality(self):
        result = {'data': [
            {'data': {'title': '劳动人事争议调解申请', 'areacode': '510106000000', 'url': 'https://www.sczwfw.gov.cn/jiq/front/transition/ywTransToDetail?areaCode=510106000000&itemCode=x'}},
            {'data': {'title': '劳动人事争议仲裁申请', 'areacode': '510104000000', 'url': 'https://www.sczwfw.gov.cn/jiq/front/transition/ywTransToDetail?areaCode=510104000000&itemCode=x'}},
        ]}
        self.assertIsNone(select_service(result, '510106000000'))

    def test_selects_exact_public_guide_not_summary_or_foreign_host(self):
        base = {'title': '劳动人事争议仲裁申请', 'areacode': '510106000000'}
        expected = 'https://www.sczwfw.gov.cn/jiq/front/transition/ywTransToDetail?areaCode=510106000000&itemCode=actual'
        rows = [{'data': {**base, 'url': url}} for url in [
            'https://www.sczwfw.gov.cn/jiq4/front/transition/ywTransToDetail_summary?areaCode=510106000000',
            'https://example.com/jiq/front/transition/ywTransToDetail?areaCode=510106000000', expected,
        ]]
        result = select_service({'data': rows}, '510106000000')
        self.assertIsNotNone(result)
        self.assertEqual(result['url'], expected)

    def test_ambiguous_distinct_guides_require_review(self):
        rows = [{'data': {'title': '劳动人事争议仲裁申请', 'areacode': '510106000000', 'url': f'https://www.sczwfw.gov.cn/jiq/front/transition/ywTransToDetail?areaCode=510106000000&itemCode={i}'}} for i in [1, 2]]
        with self.assertRaisesRegex(ValueError, '多个'):
            select_service({'data': rows}, '510106000000')


if __name__ == '__main__':
    unittest.main()
