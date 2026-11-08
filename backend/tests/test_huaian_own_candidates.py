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
    '321302': ('宿迁市', '宿城区', 'suqian-sucheng', '7fb7dc52dbd885bd96986222', '321302',
               'ff3e6b45-0e9a-40a3-b3ce-d726c559b76d', '613a5382-bee5-4fca-a3eb-d15444d222d0'),
    '321311': ('宿迁市', '宿豫区', 'suqian-suyu', '3651193e96ffa65fcbbdd653', '321311',
               '5990c48c-6204-433d-9b10-e382b38889a3', '32d04f5e-cf97-4ea5-9f81-3717ef74d558'),
    '321322': ('宿迁市', '沭阳县', 'suqian-shuyang', '3ccf422d02539ed77d426823', '321322',
               '08873dcb-d051-45ca-9277-f6923c2c0df0', '5202a3a3-78af-4e85-9968-7c5994b31624'),
    '321323': ('宿迁市', '泗阳县', 'suqian-siyang', 'af0c7311cc4d8d7e65d2349c', '321323',
               '5a3a4f0b-a665-49bf-b12f-3d9ce6c08239', 'f981c5e8-237d-4eec-be77-085706efad35'),
    '321324': ('宿迁市', '泗洪县', 'suqian-sihong', 'f4129dbab8e0725575533aee', '321324',
               '85458054-1daf-41d1-86b1-acb05993c2ad', 'd0186fb3-94db-467c-b6a0-423402654089'),
    '321325': ('宿迁市', '市湖滨新城', 'suqian-lake', '1666941b0227accabfd693bc', '321325',
               'f7852470-a737-4c9f-be71-b237a494b7d1', 'fb30f08f-d847-4bca-a05b-013c09e77e5c'),
    '321392': ('宿迁市', '苏州宿迁工业园区', 'suqian-ssip', '99b9ee49afeb34982c4cba87', '321392',
               'fd50790b-1455-4cf2-ae3f-6810ed58c3fb', '3e9bf615-0fa2-4279-a43d-7d0e58419b10'),
    '321002': ('扬州市', '广陵区', 'yangzhou-guangling', '6de416b60f069c12cc5794c9', '321002',
               '2af62df3-be3f-463a-81a3-b23ffb9be32b', '2992e2e4-12a8-421d-b384-eaa22adb4a0c'),
    '321003': ('扬州市', '邗江区', 'yangzhou-hanjiang', 'bbe69ce71284ba9c1c9d172f', '321003',
               'c07338df-d292-4048-a97f-3e97641e9b10', 'e7c1e164-5ebb-4d89-a751-c222cb3ea50d'),
    '321012': ('扬州市', '江都区', 'yangzhou-jiangdu', '9247a2c6de01992d26bb57b5', '321012',
               '688996b7-078a-43f7-ba4f-67bff2cd6426', 'e29a732c-b7e6-4324-9ba6-a6c97c61e3d0'),
    '321023': ('扬州市', '宝应县', 'yangzhou-baoying', '35c349b3ff699b188ad7cc46', '321023',
               '89baa947-8627-4383-8bff-a0c045d0c827', '156fa24b-782d-4775-aaa4-3d1371e05be5'),
    '321084': ('扬州市', '高邮市', 'yangzhou-gaoyou', 'b90a43c2a0cc8c0acb5c6516', '321084',
               '7d1c471c-2cca-4cba-a789-da6b3bee285b', '1db32a56-164a-4f1a-90c7-2cd1397c1f5c'),
    '320613': ('南通市', '崇川区', 'nantong-chongchuan', '1c3e1b1b5b4841a3fc4cc60a', '320613',
               'cb669356-efc2-48b9-895d-f449c807c17a', 'a3378d5e-a37c-4969-88b4-ca217fc71986'),
    '320612': ('南通市', '通州区', 'nantong-tongzhou', 'b56cff9f6b1e5da25b02ec6d', '320612',
               '583bbb1b-37f8-4cc6-b26d-438428da4072', '4db99020-0b45-4805-bed2-79cf14e9c388'),
    '320685': ('南通市', '海安市', 'nantong-haian', '9cfe280a096cd41035d85b91', '320621',
               'd9f23630-2121-4f9c-96ba-8a14f1bf5138', '61b6ae9f-1495-45bc-9db5-8ca9e9a00392'),
    '320623': ('南通市', '如东县', 'nantong-rudong', 'ea97908d9e453ef904316e6f', '320623',
               '3ed2162d-26c7-4314-b51e-998c2d5bdabf', 'c5ee786c-ee35-4166-a865-981a332aabea'),
    '320681': ('南通市', '启东市', 'nantong-qidong', 'abf05466ec62053aecfe1b04', '320681',
               '47a13e91-b667-4599-aad3-c01f3bd90417', 'fe2a393b-ee05-4197-abeb-a8d6be4f48ed'),
    '320682': ('南通市', '如皋市', 'nantong-rugao', 'a629b2cb8743aeaeeb37b4e3', '320682',
               'c3b37bd5-614e-46f4-8f43-9162d9e48419', '289ce92c-e82f-457e-914d-634d97aef332'),
    '320614': ('南通市', '海门区', 'nantong-haimen', 'b3ba940d72bebe2edaa50d97', '320684',
               '8d82918d-9572-404c-89d6-6a7a2f296316', 'dd5c213b-0c86-45c9-a169-31e7f0a92a35'),
    '320693': ('南通市', '苏锡通', 'nantong-suxitong', '2446c985a8e4028bc4729f14', '320693',
               '92e37500-fd55-4a4b-a256-5af92a57909a', '188616cb-8599-4c75-beca-834623fff1f5'),
    '321102': ('镇江市', '京口区', 'zhenjiang-jingkou', 'cb673500cd75bfe69de5e78b', '321102',
               '79e18b27-0e6d-4e1f-9b83-40690e6cee1e', '66bb003d-40ff-4f4f-9946-c7e1d3cb473a'),
    '321111': ('镇江市', '润州区', 'zhenjiang-runzhou', '4223ab831f52e1afbc0bc376', '321111',
               '58a27495-07b2-4c3b-a393-6857877c4f16', '5ff1ef03-df01-468e-b70b-12b640f81dfb'),
    '321112': ('镇江市', '丹徒区', 'zhenjiang-dantu', '34086ef3a9f8af8995c22fd5', '321112',
               '8335e104-614a-42bd-804d-5198d889fde2', '80c5cacb-31a4-4de0-96f1-1d05cdec2bec'),
    '321181': ('镇江市', '丹阳市', 'zhenjiang-danyang', '88f8a7fab3a029da739d7759', '321181',
               '0ddb0e56-9ebf-438c-8f4f-4aba1dd901cd', '2b489fa8-be63-4fb6-99c7-04948b3f866f'),
    '321182': ('镇江市', '扬中市', 'zhenjiang-yangzhong', '6faa24fecb0f43577eb71b76', '321182',
               '5aa121be-5f9c-410b-ba5d-623102c98a04', '853c7d53-dd54-4b50-863c-c23ec84baefe'),
    '321202': ('泰州市', '海陵区', 'taizhou-hailing', '75350ea6969cb0b55633fffa', '321202',
               '04cd6da4-4a0f-4963-a2c5-566646f1202e', 'f2ea5304-5dd6-481c-aca7-7b6a006c1ccd'),
    '321203': ('泰州市', '高港区', 'taizhou-gaogang', '4779366e0fc515afee109eb2', '321203',
               'e1c771ad-8591-4712-8bfb-7b4b0249a319', '32f732a0-a6c3-4b7d-a7fe-9bd810762624'),
    '321204': ('泰州市', '姜堰区', 'taizhou-jiangyan', '0e793fcf14a99306d4a8150d', '321204',
               '326a25a4-b666-4bb9-906d-77bda0902745', '33601a57-84f5-4f24-80c0-95f901f0dde8'),
    '321281': ('泰州市', '兴化市', 'taizhou-xinghua', 'd60aa7fc858807793aacd5fc', '321281',
               'eb3965fc-4b99-43b8-9468-0a6ae2dc408c', 'b20aab9e-9914-45df-a0a2-638ad8d80e46'),
    '321282': ('泰州市', '靖江市', 'taizhou-jingjiang', 'b013e0a468eedaa0271af6b3', '321282',
               '63042073-5235-4d52-91f3-335b802508a4', 'ab85e126-a6a5-4eb1-ae0c-a1b0498a6687'),
    '321283': ('泰州市', '泰兴市', 'taizhou-taixing', '896936fec0edc7f820d3d1f8', '321283',
               'a0509eef-f50d-411c-9760-1031f4a7a455', '98afe763-7824-4414-9e44-1ea4750d6bcd'),
    '320402': ('常州市', '天宁区', 'changzhou-tianning', 'e39c9ffd79563821016f0bac', '320402',
               'ce7347c3-9e8b-4c10-b295-97999321f710', 'd0d0588b-0586-4e9b-9bba-4291b2d9636a'),
    '320404': ('常州市', '钟楼区', 'changzhou-zhonglou', '81386cd870bc1302c9be58b6', '320404',
               '3cfba7f8-d1e9-4f29-a4d9-d68b0aae1470', 'ea51d49d-454c-4a75-960a-be34a3f7a9f1'),
    '320481': ('常州市', '溧阳市', 'changzhou-liyang', '9c6fe7efa0a96db41d1ba41e', '320481',
               '265ec962-29f4-4cd7-80af-728e7d339a2b', '6ece6338-906f-420d-b401-db0082a6001e'),
    '320413': ('常州市', '金坛区', 'changzhou-jintan', '73ccdcd47f33754e4fba164c', '320482',
               '7c921ce6-43ed-43fe-8c02-ee584dfece7a', 'a5296113-81cb-438b-86f2-9e85761a39da'),
    '320206': ('无锡市', '惠山区', 'wuxi-huishan', '54e5e7c2742c7957c8ffeaab', '320206',
               'c82fa538-5ffb-4673-a362-91175e049d12', '3afc1297-9e14-49d6-b2fb-2bfac66346d1'),
    '320211': ('无锡市', '滨湖区', 'wuxi-binhu', '197d3d1aaeca692cce9d43de', '320211',
               '6bfe76e1-90d8-4009-b6e1-df4d0491997a', '92d30519-96ad-4a39-a3c4-6c8a87c19f40'),
    '320213': ('无锡市', '梁溪区', 'wuxi-liangxi', '9eadb99cc598993e8e9bc93b', '320213',
               '9c46cc60-ede3-4d34-b818-17c6c2f7cfc0', 'cfebf172-bb48-497b-a994-6b78643f6d44'),
    '320214': ('无锡市', '新吴区', 'wuxi-xinwu', 'e17ee662008caa98a507f07c', '320214',
               '94e2383c-b816-4a53-a2a2-b72800d97afd', '5ca17072-fad9-4e42-ac9d-b4d3e3691673'),
    '320292': ('无锡市', '经济开发区', 'wuxi-edz', '8b7685fe81e6e7e82758b218', '320292',
               'c01bf318-d976-4d60-89a0-b0e87945c6b0', '95774b46-0f4e-4b96-b0a5-1c0c841bc57a'),
    '320585': ('苏州市', '太仓市', 'suzhou-taicang', '5a7d8504ff500321b04e076f', '320585',
               '3962a0b5-9808-48fc-8c6b-a635cdd7d644', '02c2d0d4-b08e-4071-a273-6baed007532c'),
    '320590': ('苏州市', '工业园区', 'suzhou-industrial-park', '866205b79a0218e31aa4812d', '320590',
               '5b8d38c4-49b6-4de8-adad-549f5c79ae7b', '19e8b533-37a9-41f8-889b-886a4cf9781d'),
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

    def test_jintan_current_code_preserves_original_directory_record(self):
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        legacy = next(r for r in rows if (r['city'], r['district'], r['code']) == ('常州市', '金坛区', '320482'))
        with TemporaryDirectory(prefix='jintan-directory-') as tmp:
            directory = DirectoryStore(Path(tmp) / 'directory.sqlite')
            directory.put_area(legacy)
            row, = directory.areas('jiangsu', '常州市')
            self.assertEqual((row['code'], row['region_code'], row['provider_code']),
                             ('320413', '320413', '320482'))
            with directory.connection() as db:
                original = json.loads(db.execute('SELECT payload FROM directory_areas').fetchone()['payload'])
            self.assertEqual(original['code'], '320482')

    def test_exact_local_originals_contracts_and_downloads(self):
        rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        with TemporaryDirectory(prefix='jiangsu-own-candidates-') as tmp:
            store = RegionalStore(Path(tmp) / 'guides.sqlite')
            directory = DirectoryStore(Path(tmp) / 'directory.sqlite')
            for city_code in ('320700', '320800', '320300', '320900', '321300', '321000', '320600', '321100', '321200', '320400', '320200', '320500'):
                directory.put_area(next(r for r in rows if r['code'] == city_code and r['level'] == 3))
                store.put_guide(forms.staged_jiangsu_municipal(ROOT, city_code))
            directory.put_area(next(r for r in rows if r['code'] == '320685' and r['city'] == '南通市'
                                    and r['district'] == '经济开发区'))
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
                            if code == '321204' and kind == 'evidence':
                                unavailable = next(t for t in guide['templates'] if t['id'] == annex)
                                self.assertFalse(unavailable['can_generate'])
                                self.assertNotEqual(unavailable['download_status'], 'downloaded')
                                self.assertEqual(client.get('/regional/form-contract', params=q).status_code, 409)
                                self.assertEqual(client.get(f'/regional/templates/{annex}', params=q).status_code, 409)
                                self.assertEqual(client.post('/regional/generate', json={
                                    **q, 'mode': 'blank', 'data': {},
                                }).status_code, 409)
                                continue
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
                            if code == '320685':
                                other, = (row for row in options if row['district'] == '经济开发区')
                                self.assertEqual(other['provider_code'], code)
                                self.assertIsNone(other['region_code'])
                                self.assertIsNone(other['source_id'])
                                self.assertFalse(other['can_generate'])
                                mismatch = client.post('/regional/generate', json={**payload, 'district': '经济开发区'})
                                self.assertEqual(mismatch.status_code, 409)
                            wrong_city = '淮安市' if city == '连云港市' else '连云港市'
                            mismatch = client.post('/regional/generate', json={**payload, 'city': wrong_city})
                            self.assertEqual(mismatch.status_code, 409)
