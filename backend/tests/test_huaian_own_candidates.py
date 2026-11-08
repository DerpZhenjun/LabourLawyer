"""Exact district/functional-area candidates must not inherit city sources."""
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
AREAS = {
    '320804': ('淮安市', '淮阴区', 'huaiyin', 'af10b6358a0cea5389de88b7', '320804',
               'eca65f46-5178-4c29-a6f5-cea523aa5595', '857d0650-f222-465d-9687-54459d9e3bb0'),
    '320813': ('淮安市', '洪泽区', 'hongze', '353f307d6c7fc7e41924a8cf', '320829',
               'db154c19-9478-4644-9120-2a9bf727c70b', '70b69cb8-9011-464c-b31c-15bc6339e391'),
    '320871': ('淮安市', '经济开发区', 'huaian-edz', 'd80293457ba981b81997c7f9', '320871',
               'e3661b6a-1991-4fa4-9471-4f5975d7586a', '2d24580f-7c60-4ac0-880d-fc3437ba71be'),
    '320830': ('淮安市', '盱眙县', 'xuyi', '70ab0102a5469dbbfa060551', '320830',
               '393e1c03-9727-4099-a8b9-0948596ec8e5', '342980c8-2a11-4917-9124-d02f0bd28e60'),
    '320703': ('连云港市', '连云区', 'lianyun', '43affed1b2f460165b7d11d0', '320703',
               'd00271ab-a748-47c3-84d4-172f3c9ba531', 'c56e13df-1ad6-403b-997d-a80c51a1e8dd'),
    '320707': ('连云港市', '赣榆区', 'ganyu', '2846cc27d49c263550444626', '320707',
               'c6b17cfe-c40b-4f0b-be2b-9319b0448042', '7c4cb9c1-016c-478d-ad15-828edecc8d60'),
    '320722': ('连云港市', '东海县', 'donghai', '2e7e7fa46c45730b32762bea', '320722',
               'fcfd5b3f-0595-4b98-bda3-bdfaf0ea0c57', 'c1aea292-44c1-4c7b-8eb6-8d4e415eda96'),
    '320723': ('连云港市', '灌云县', 'guanyun', 'b329533cd5ca25e92a69f081', '320723',
               'a49c5d14-2f99-4594-a68e-af0c524813ec', '8b9768fb-77c5-41e2-9a3b-0a0566596ee7'),
    '320724': ('连云港市', '灌南县', 'guannan', '89ac4e45ae810866811cf20e', '320724',
               '526eb9d5-f756-4c3d-a2d5-50abcff3dc2b', 'c62b7731-21df-43cf-883a-907d1fa3ac68'),
    '320771': ('连云港市', '经济开发区', 'lianyungang-edz', '358a2d7a25da49bd5e51dea0', '320771',
               '27a93b11-b2d2-4668-a1d3-6d43903bb787', 'a457b10c-74fe-4d3c-ae83-f3dedcc419f1'),
    '320302': ('徐州市', '鼓楼区', 'xuzhou-gulou', 'e1342562632579ac5f32aaa0', '320302',
               'ca661200-f1f2-4b96-8ffd-599582d67bb3', 'c53b1d76-ace8-4cfb-be16-55b5c0195457'),
    '320303': ('徐州市', '云龙区', 'xuzhou-yunlong', '343d1bc839fee96beefbe2e3', '320303',
               '5fe62cc7-974d-4731-8a9e-6ab4cc00f549', 'e0cdb850-aea7-4189-b982-b563c08ff372'),
    '320305': ('徐州市', '贾汪区', 'xuzhou-jiawang', 'b3eb9f21c007ba0b14abef76', '320305',
               '7c8d87a6-9978-4c1d-a9bd-c258ffc7edd7', '24ada876-fe3a-4e29-9ea4-c6639149efd0'),
    '320312': ('徐州市', '铜山区', 'xuzhou-tongshan', '2d647bb6acf5a4a6f1d6c81a', '320312',
               '787e934f-1526-4081-ba1b-c787801f54f6', '8b0ceaf3-0696-48ca-a02c-5f7345792649'),
    '320321': ('徐州市', '丰县', 'xuzhou-feng', '6523327f018a58fffc5f1e5e', '320321',
               '10a8ef9b-dff0-4fb2-8d85-902d8f42e6cf', 'bb897fd3-e822-43f5-9074-e50cbd56d12a'),
    '320322': ('徐州市', '沛县', 'xuzhou-pei', 'b79b5838dfd99e297b127f05', '320322',
               '249c5be1-ddbe-4dd1-b7a3-e30a6a8e1bdf', '1594c8ba-1c01-400b-9f0d-d5663877f61d'),
    '320324': ('徐州市', '睢宁县', 'xuzhou-suining', '5d71b17ee619a49ab0b3e47a', '320324',
               'eb891ead-804a-4718-ad78-28109de610a3', 'bd2224b9-7a18-4436-9fc1-325dfbb94e9b'),
    '320381': ('徐州市', '新沂市', 'xuzhou-xinyi', '020c3850ed4cd886ff0d2739', '320381',
               '4b37d83f-2bc2-4bb9-aaa3-e4fb69c76bab', '8a03c432-a9fc-46c6-8652-3f62d9eb6dde'),
    '320382': ('徐州市', '邳州市', 'xuzhou-pizhou', 'd2a0a2956e6a022d7bef2cf7', '320382',
               'b02a3340-4ef3-4230-84f0-39b595fd94b0', 'fd36a7f6-e516-4d36-bbab-62b09fef3538'),
    '320902': ('盐城市', '亭湖区', 'yancheng-tinghu', 'd56231312b263cd2c5a42b96', '320902',
               'b2ef8a79-637b-4c49-bbbd-82f0082c2bbf', '103d2584-4128-49dc-a177-72bb3904afa2'),
    '320903': ('盐城市', '盐都区', 'yancheng-yandu', '56d382f2893c03e7c7e2fbd6', '320903',
               '73bc8138-5dba-4b3f-ae15-9f8d3f90b717', 'c99c9cba-a1f6-4107-9084-45adbb9002da'),
    '320921': ('盐城市', '响水县', 'yancheng-xiangshui', '7d83756f2c94a39e125a20aa', '320921',
               'cb2d28f4-a4d8-4633-9e89-238ebe8604ac', '59d0356b-d251-4424-9a29-17f0491edc19'),
    '320922': ('盐城市', '滨海县', 'yancheng-binhai', '07a281abbc4c6050825a9534', '320922',
               'a0b76715-d491-4a89-8d3d-e08462f1f0f4', '5008f178-fe89-4f89-9839-4b6b69eef95b'),
    '320924': ('盐城市', '射阳县', 'yancheng-sheyang', 'cd4add4b09c7631a71b0d02f', '320924',
               '85e7e12b-18a8-458f-90f5-5a9ea44439a1', 'c3833b5a-b6ea-40aa-a3ff-905a50e83a4d'),
    '320981': ('盐城市', '东台市', 'yancheng-dongtai', '0b0e7b33454afdc0221e164e', '320981',
               'd5a8d1f0-ba28-4fa3-8e0d-0c12fb5e8120', '5d848c02-a62a-4686-9f25-2e320b1b32ae'),
    '320971': ('盐城市', '盐城开发区', 'yancheng-edz', 'cfdea0ddc6c9122dd461f617', '320971',
               '7b18187c-ed1a-4b52-917f-d46bb1850af6', 'db8d22b6-69d6-429b-8a7e-1b6c65b8eff8'),
}


class HuaianOwnCandidatesTests(TestCase):
    def test_hongze_current_code_keeps_legacy_provider_value(self):
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        legacy = next(r for r in rows if r['code'] == '320829' and r['district'] == '洪泽区')
        with TemporaryDirectory(prefix='hongze-directory-') as tmp:
            directory = DirectoryStore(Path(tmp) / 'directory.sqlite')
            directory.put_area(legacy)
            row, = directory.areas('jiangsu', '淮安市')
            self.assertEqual((row['code'], row['provider_code'], row['district']),
                             ('320813', '320829', '洪泽区'))
            with directory.connection() as db:
                stored = json.loads(db.execute('SELECT payload FROM directory_areas').fetchone()['payload'])
            self.assertEqual(stored['code'], '320829')

    def test_exact_local_originals_contracts_and_downloads(self):
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        with TemporaryDirectory(prefix='jiangsu-own-candidates-') as tmp:
            store = RegionalStore(Path(tmp) / 'guides.sqlite')
            directory = DirectoryStore(Path(tmp) / 'directory.sqlite')
            for city_code in ('320700', '320800', '320300', '320900'):
                directory.put_area(next(r for r in rows if r['code'] == city_code and r['level'] == 3))
                store.put_guide(forms.staged_jiangsu_municipal(ROOT, city_code))
            for code, (city, district, slug, source, provider, app_id, evidence_id) in AREAS.items():
                directory.put_area(next(r for r in rows if r['code'] == provider and r['city'] == city and r['district'] == district))
                base = ROOT / f'reports/overnight-gap-closure-20261030/localities/{slug}-own-source'
                only_source = json.loads((base / 'GUIDE.json').read_bytes())
                app_original = next(t for t in only_source['templates'] if t['id'] == app_id)
                self.assertIsNone(forms.blank_binding(only_source, app_original))
                candidate = forms.staged_jiangsu_locality(ROOT, code)
                self.assertFalse(candidate['published'])
                self.assertEqual(candidate['source_id'], source)
                self.assertIsNone(forms.blank_binding({**candidate, 'district': '市本级'}, app_original))
                self.assertIsNone(forms.blank_binding({**candidate, 'scope_level': 'municipal'}, app_original))
                store.put_guide(candidate)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.object(routes, 'directory_store', return_value=directory), TestClient(app) as client:
                for code, (city, district, _, source, _, app_id, evidence_id) in AREAS.items():
                    with self.subTest(city=city, district=district):
                        area = {'province': 'jiangsu', 'city': city}
                        options = client.get('/regional/areas', params=area).json()['items']
                        option, = (row for row in options if row['district'] == district)
                        self.assertEqual((option['code'], option['source_id']), (code, source))
                        scope = {**area, 'district': district}
                        guide = client.get('/regional/lookup', params=scope).json()
                        for kind, annex in (('application', app_id), ('evidence', evidence_id)):
                            q = {**scope, 'source_id': source, 'version': guide['version'],
                                 'kind': kind, 'template_id': annex}
                            response = client.get('/regional/form-contract', params=q)
                            self.assertEqual(response.status_code, 200, response.text)
                            contract = response.json()
                            original = client.get(f'/regional/templates/{annex}', params=q)
                            self.assertEqual(original.status_code, 200)
                            template = next(t for t in guide['templates'] if t['id'] == annex)
                            self.assertEqual(original.content, (ROOT / template['file']).read_bytes())
                            data = deepcopy(contract['defaults'])
                            label = f'{district}虚构验证'
                            if kind == 'application':
                                data['applicantName'] = label
                            else:
                                data['evidenceList'] = [{'name': label, 'source': '本人保存', 'purpose': '核验',
                                                        'pageCount': '3页', 'originalType': '复印件'}]
                            payload = {**q, 'mode': 'blank', 'contract_id': contract['contract_id'], 'data': data}
                            result = client.post('/regional/generate', json=payload)
                            self.assertEqual(result.status_code, 200, result.text if not result.is_success else '')
                            self.assertEqual(result.headers['X-Guide-Source-ID'], source)
                            document = Document(BytesIO(result.content))
                            if kind == 'application':
                                self.assertTrue(any(label in p.text for p in document.paragraphs))
                            else:
                                self.assertEqual(document.tables[0].rows[1].cells[1].text, label)
                            for wrong in ('市本级', '清江浦区', ''):
                                mismatch = client.post('/regional/generate', json={**payload, 'district': wrong})
                                self.assertEqual(mismatch.status_code, 409)
                            wrong_city = '淮安市' if city == '连云港市' else '连云港市'
                            mismatch = client.post('/regional/generate', json={**payload, 'city': wrong_city})
                            self.assertEqual(mismatch.status_code, 409)
