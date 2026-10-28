import copy
import json
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_directory as module


SOURCE = ROOT / 'reports/chengdu-district-expansion-20261023/official-region-tree.json'


class SichuanDirectoryImportTests(unittest.TestCase):
    def parse(self, capture):
        parser = getattr(module, 'sichuan_city_areas', None)
        self.assertIsNotNone(parser, 'Own official Sichuan city directory parser is missing')
        return parser(capture)

    def setUp(self):
        self.capture = json.loads(SOURCE.read_text('utf8'))

    def test_own_23_districts_keep_raw_identity_without_granting_generation(self):
        rows = self.parse(self.capture)
        places = {r['district']: r for r in rows if r['level'] == 4}
        self.assertEqual(len(places), 23)
        self.assertEqual(places['锦江区']['city'], '成都市')
        self.assertEqual(places['锦江区']['code'], '510104000000')
        self.assertEqual(places['天府新区']['official_name'], '四川天府新区')
        self.assertEqual(places['成都高新区']['official_name'], '成都高新技术产业开发区')
        self.assertEqual(places['青羊区']['parent_code'], '510100000000')
        self.assertTrue(all(r['provider'] == 'sichuan_portal' for r in rows))
        self.assertTrue(all(r['collected_at'] == '2026-10-23T12:44:18.339829+00:00' for r in rows))
        self.assertTrue(all(not r.get('can_generate') and not r.get('source_id') for r in rows))

    def test_wrong_city_source_or_parent_is_rejected_before_any_import(self):
        for change in ('url', 'parent', 'district_code'):
            value = copy.deepcopy(self.capture)
            if change == 'url':
                value['source_url'] = value['source_url'].replace('510100000000', '370100000000')
            elif change == 'parent':
                value['response']['data']['group']['sonAreas'][0]['pid'] = 'other-city'
            else:
                value['response']['data']['group']['sonAreas'][0]['areaCode'] = '../../bad'
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.parse(value)

    def test_failed_or_inactive_rows_never_become_current_directory_targets(self):
        failed = copy.deepcopy(self.capture)
        failed['response']['code'] = '500'
        with self.assertRaises(ValueError):
            self.parse(failed)
        inactive = copy.deepcopy(self.capture)
        inactive['response']['data']['group']['sonAreas'][0]['status'] = 'US02'
        self.assertEqual(sum(r['level'] == 4 for r in self.parse(inactive)), 22)

    def test_reimport_is_idempotent_and_preserves_other_provider_functional_area(self):
        with tempfile.TemporaryDirectory() as directory:
            store = module.DirectoryStore(Path(directory) / 'directory.sqlite')
            store.put_area({'provider': 'national', 'code': '510109000000', 'province': 'sichuan',
                            'city': '成都市', 'district': '独立行政记录', 'level': 4,
                            'source_url': 'https://gjzwfw.www.gov.cn/', 'collected_at': '2026-10-28T00:00:00Z'})
            rows = self.parse(self.capture)
            for _ in range(2):
                for row in rows:
                    store.put_area(row)
            self.assertEqual(len(store.areas('sichuan', '成都市')), 24)
            self.assertEqual(len([r for r in store.areas('sichuan', '成都市') if r['district'] == '成都高新区']), 1)
            self.assertTrue(all(not r['can_generate'] and r['source_id'] is None for r in store.areas('sichuan', '成都市')))
