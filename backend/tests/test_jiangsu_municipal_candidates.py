"""Candidate-only municipal sources must preserve their own document scope."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

import regional_blank_documents as forms
from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from routes import regional_guides as routes

ROOT = Path(__file__).resolve().parents[2]
PROOFS = ROOT / 'reports/overnight-gap-closure-20261030/localities'
CITIES = {
    '320300': ('徐州市', '云龙区', 'xuzhou', 'dd3ac475c600106bea879583',
               '28a69aad-d74b-47a8-93a4-48788d60f332', '6e67dfad-ebaa-40cf-b9ac-a15dbea3505d'),
    '320800': ('淮安市', '清江浦区', 'huaian', '632425a93185f0f45d827cac',
               '5d1ce46e-2878-4454-aad3-d45e6173c871', '1d721abe-2ab6-454e-b73b-0518bbc66cfc'),
    '320900': ('盐城市', '亭湖区', 'yancheng', '6b119ec8140e1d3ed38c25c3',
               '8a193295-0ccd-498b-8b0c-a461d2859c9f', '0976ca90-3679-4634-b1e6-4ca2e21e1a35'),
    '321000': ('扬州市', '广陵区', 'yangzhou', '8c8aaf5af507c4ae65d8b7ea',
               'cb95bc3e-68cc-43a1-b409-da2e6f324fd3', 'e8b97aa9-2475-4fb4-bf55-99f690b725c1'),
    '321100': ('镇江市', '京口区', 'zhenjiang', '27626805973015340d56732b',
               '456ed620-c6d4-45d6-838f-e086fceb814c', '0490fd04-5659-4479-9680-57aa5ffa3349'),
    '321200': ('泰州市', '海陵区', 'taizhou', 'b9d1e481edaa0219e36312fa',
               '1a094502-26db-4208-be47-11f3fce8fb58', 'd29f0a2b-dc5f-451b-99db-be8a26ff55f4'),
    '321300': ('宿迁市', '宿城区', 'suqian', 'd976408fd03de4277b278053',
               'b882276a-02d6-49cb-80f6-3b8e26c704fd', '224056b1-b2b2-4abf-9ac4-63c1e700e0aa'),
    '320100': ('南京市', '玄武区', 'nanjing', 'd93582141e3316c4c481ffbc',
               '726e5815-4417-4e53-8e9e-1f68acbe748a', '8b762eb1-770a-47f5-bba3-659ccb4b4df6'),
    '320200': ('无锡市', '梁溪区', 'wuxi', '7ae202cc5af7b2b8db835c1d',
               '597afb1e-1da3-4004-a863-3ce44db8ca2f', 'ac2cbf44-10a8-4424-a097-97d8aebb85aa'),
    '320400': ('常州市', '天宁区', 'changzhou', '9e8d445cba18341a2a84a74a',
               '5fbef6ff-26cc-41a3-ba18-ae93a402892d', '24b6ad01-aafd-4ce6-b6e2-cd625bad7638'),
    '320500': ('苏州市', '姑苏区', 'suzhou', '6ee84910096097334c275d64',
               'ff27ba51-7f54-4e23-ab80-f0037ba11367', 'f04db924-03ea-463a-918f-21c926bb23f2'),
    '320600': ('南通市', '崇川区', 'nantong', 'c3bef84e98a9d6ca2afe986a',
               '5b040d4e-663b-4860-bcef-d8c12cf54741', 'c8260c13-5490-40f7-9be7-3071bb957c58'),
}


class JiangsuMunicipalCandidatesTests(TestCase):
    def test_source_only_and_mismatched_receipts_do_not_grant_generation(self):
        for code, (city, district, slug, source_id, application, evidence) in CITIES.items():
            with self.subTest(city=city):
                guide = json.loads((PROOFS / f'{slug}-municipal-own-source/GUIDE.json').read_bytes())
                template = next(t for t in guide['templates'] if t['id'] == application)
                self.assertIsNone(forms.blank_binding(guide, template))
                candidate = forms.staged_jiangsu_municipal(ROOT, code)
                self.assertFalse(candidate['published'])
                self.assertEqual(candidate['source_id'], source_id)
                self.assertEqual({t['id'] for t in candidate['templates'] if t['can_generate']},
                                 {application, evidence})
                self.assertEqual(forms.blank_binding(candidate, template), 'application')
                for key, wrong in (('district', district), ('city', '连云港市'), ('authority', '其他市人社局'),
                                   ('source_version', '0' * 64), ('candidate_adapter_evidence', {}),
                                   ('published', True)):
                    with self.subTest(key=key):
                        self.assertIsNone(forms.blank_binding({**candidate, key: wrong}, template))

    def test_city_selection_and_download_contracts_are_isolated(self):
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        with TemporaryDirectory(prefix='jiangsu-municipal-candidates-') as tmp:
            store = RegionalStore(Path(tmp) / 'guides.sqlite')
            directory = DirectoryStore(Path(tmp) / 'directory.sqlite')
            for code in CITIES:
                city_row = next(r for r in rows if r['code'] == code and r['level'] == 3)
                directory.put_area(city_row)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.object(routes, 'directory_store', return_value=directory), TestClient(app) as client:
                for code in CITIES:
                    store.put_guide(forms.staged_jiangsu_municipal(ROOT, code))
                for code, (city, district, _, source_id, application, evidence) in CITIES.items():
                    with self.subTest(city=city):
                        area = {'province': 'jiangsu', 'city': city}
                        options = client.get('/regional/areas', params=area).json()['items']
                        choice, = options
                        self.assertEqual((choice['district'], choice['region_code'], choice['source_id']),
                                         ('市本级', code, source_id))
                        for other in ('', district):
                            unavailable = client.get('/regional/lookup', params={**area, 'district': other}).json()
                            self.assertIsNone(unavailable['source_id'])
                            self.assertFalse(any(t['can_generate'] for t in unavailable['templates']))
                        scope = {**area, 'district': '市本级'}
                        guide = client.get('/regional/lookup', params=scope).json()
                        for kind, annex in (('application', application), ('evidence', evidence)):
                            query = {**scope, 'source_id': source_id, 'version': guide['version'],
                                     'kind': kind, 'template_id': annex}
                            form = client.get('/regional/form-contract', params=query)
                            self.assertEqual(form.status_code, 200, form.text)
                            contract = form.json()
                            original = client.get(f'/regional/templates/{annex}', params=query)
                            self.assertEqual(original.status_code, 200)
                            template = next(t for t in guide['templates'] if t['id'] == annex)
                            self.assertEqual(original.content, (ROOT / template['file']).read_bytes())
                            data = deepcopy(contract['defaults'])
                            label = f'{city}虚构验证'
                            if kind == 'application':
                                data['applicantName'] = label
                            else:
                                data['evidenceList'] = [{'name': label, 'source': '本人保存', 'purpose': '版式核验',
                                                        'pageCount': '3页', 'originalType': '复印件'}]
                            payload = {**query, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': data}
                            result = client.post('/regional/generate', json=payload)
                            self.assertEqual(result.status_code, 200, result.text if not result.is_success else '')
                            self.assertEqual(result.headers['X-Guide-Source-ID'], source_id)
                            generated = Document(BytesIO(result.content))
                            if kind == 'application':
                                self.assertTrue(any(label in p.text for p in generated.paragraphs))
                            else:
                                self.assertEqual(generated.tables[0].rows[1].cells[1].text, label)
                            wrong_city = next(other[0] for other in CITIES.values() if other[0] != city)
                            for changes in ({'district': district}, {'city': wrong_city}):
                                mismatch = client.post('/regional/generate', json={**payload, **changes})
                                self.assertEqual(mismatch.status_code, 409)
