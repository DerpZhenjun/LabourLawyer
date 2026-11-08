"""Fujian candidates generate only from separately observed local files."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes
import regional_quanzhou_next4 as own


ROOT = Path(__file__).resolve().parents[2]
LOCALITIES = ROOT / 'reports/overnight-gap-closure-20261030/localities'


class _FujianCandidateChecks:
    handling_form = '窗口办，网上办，邮寄办'

    def test_candidate_contracts_and_downloads_use_exact_local_lineage(self):
        source = own.production_source(self.code, root=ROOT)
        self.assertEqual(source['source_id'], self.source_id)
        self.assertEqual(source['source_version'], self.source_version)
        self.assertEqual(source['authority'], self.authority)
        self.assertEqual(source['channel']['handling_form_raw'], self.handling_form)
        self.assertEqual(source['channel']['depth_raw'], '材料预审（Ⅱ级）')
        self.assertIsNone(source['channel']['entry_url'])
        self.assertFalse(source['can_generate'])

        receipt = json.loads((LOCALITIES / self.source_folder / 'WORD-PREFLIGHT.json').read_bytes())['records']
        expected = {(row['kind'], row['case']): row for row in receipt}
        candidate = own.staged_candidate(self.code, root=ROOT)
        with TemporaryDirectory(prefix='zz-candidate-') as folder:
            store = RegionalStore(Path(folder) / 'guides.sqlite')
            store.put_guide(candidate)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.dict('os.environ', {'LABOURLAWYER_DATA_DIR': folder}), TestClient(app) as client:
                response = client.get('/regional/lookup', params=self.region)
                self.assertEqual(response.status_code, 200)
                guide = response.json()
                self.assertFalse(guide['published'])
                self.assertEqual(len(guide['materials']), 3)
                self.assertEqual(len(guide['templates']), 6)
                eligible = {t['eligible_own_kind']: t for t in guide['templates'] if t['can_generate']}
                self.assertEqual(set(eligible), {'application', 'evidence'})
                for kind, template in eligible.items():
                    with self.subTest(kind=kind):
                        query = {**self.region, 'source_id': self.source_id, 'version': guide['version'],
                                 'kind': kind, 'template_id': template['id']}
                        response = client.get('/regional/form-contract', params=query)
                        self.assertEqual(response.status_code, 200, response.text)
                        contract = response.json()
                        self.assertEqual(contract['context']['source_version'], self.source_version)
                        self.assertEqual(template['id'], expected[kind, 'original']['attachment_id'])
                        response = client.get(f"/regional/templates/{template['id']}", params=query)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(sha256(response.content).hexdigest(), expected[kind, 'original']['sha256'])
                        for case in ('original', 'normal', 'stress'):
                            fixture = ROOT / own.FIXTURES / f'350521-{kind}-{case}.json'
                            data = contract['defaults'] if case == 'original' else json.loads(fixture.read_bytes())['data']
                            payload = {**query, 'mode': 'blank', 'data': data, 'contract_id': contract['contract_id']}
                            response = client.post('/regional/generate', json=payload)
                            self.assertEqual(response.status_code, 200, response.text if not response.is_success else '')
                            self.assertEqual(response.headers['X-Guide-Source-ID'], self.source_id)
                            self.assertEqual(sha256(response.content).hexdigest(), expected[kind, case]['sha256'])
                        other = own.staged_candidate(self.foreign_code, root=ROOT)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'source_id': other['source_id']}).status_code, 409)
                        foreign = next(t['id'] for t in other['templates'] if t['eligible_own_kind'] == kind)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'template_id': foreign}).status_code, 409)
                        for sample in (t for t in guide['templates'] if not t['can_generate']):
                            bad = {**query, 'template_id': sample['id']}
                            self.assertEqual(client.get('/regional/form-contract', params=bad).status_code, 409)

    def test_previous_publication_and_tampered_preflight_do_not_authorize_local_candidate(self):
        staged = own.staged_candidate(self.code, root=ROOT)
        self.assertTrue(staged['can_generate'])
        self.assertFalse(staged['published'])
        with self.assertRaises(ValueError):
            own.published_guide(self.code, root=ROOT)
        dehua = own.published_guide('350526', root=ROOT)
        forged = {**staged, 'published': True, 'publication_adapter_evidence': dehua['publication_adapter_evidence']}
        with self.assertRaises(ValueError):
            own.with_capabilities(forged, root=ROOT)

        read = own._read
        def tampered(root, name):
            value = read(root, name)
            return value + b' ' if name == f'{own.LOCALITIES}/{self.source_folder}/WORD-PREFLIGHT.json' else value

        with patch.object(own, '_read', side_effect=tampered), self.assertRaises(ValueError):
            own.staged_candidate(self.code, root=ROOT)


class XiangchengCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350602'
    source_id = 'f8e8351e86b1c41530f16dec'
    source_version = 'f00f84d5e6ed1a90e7d064760966c36735950d2e734c2fa6493db2186956ab41'
    authority = '漳州市芗城区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '芗城区'}
    source_folder = 'zhangzhou-own-source'
    foreign_code = '350526'


class LonghaiCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350681'
    source_id = 'ed191bcdf82538767ff7bc25'
    source_version = '60cb15eedb5f3d3fa70c2cd38037c93ab972e3866f530cf9fb65f6c6251bdafc'
    authority = '龙海区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '龙海区'}
    source_folder = 'zhangzhou-longhai-own-source'
    foreign_code = '350602'


class PingheCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350628'
    source_id = '1c435a8e909867d2119efe16'
    source_version = '798eba503cadb717fb74727aaff074c1389a69feed03c577f63642325f36c70d'
    authority = '平和县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '平和县'}
    source_folder = 'zhangzhou-four-own-source/350628'
    foreign_code = '350625'


class ChangtaiCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350625'
    source_id = '2ea92c5adb81421b892f2994'
    source_version = '74786aec7221088ada6a7923a38e13b9d74cb9ba042ac877db57211e35f3ae50'
    authority = '漳州市长泰区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '长泰区'}
    source_folder = 'zhangzhou-four-own-source/350625'
    foreign_code = '350628'


class ZhangpuCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350623'
    source_id = '48e65b2c27fc105366706caa'
    source_version = 'de8110bb1a971d508bffb8d94c8545d5bef504dee090b55955736105f7ac91ac'
    authority = '漳浦县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '漳浦县'}
    source_folder = 'zhangzhou-four-own-source/350623'
    foreign_code = '350628'


class HuaanCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350629'
    source_id = 'd61089df6a682a0affd5d18c'
    source_version = 'd21b0110552ff1568fe6a7b7049faf9df6939f55f651d24191f8b472d1f3dc44'
    authority = '华安县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '华安县'}
    source_folder = 'zhangzhou-four-own-source/350629'
    foreign_code = '350628'


class YunxiaoCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350622'
    source_id = '41be287d59db2eae92eac0f1'
    source_version = '5edc06c82bc94fa0452c3ea8edc3d8d1d9d6ef586bf19f55f5ded5786d860be5'
    authority = '云霄县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '云霄县'}
    source_folder = 'zhangzhou-next-four-own-source/350622'
    foreign_code = '350624'


class ZhaoanCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350624'
    source_id = '32f582f436d0fcb48afeb66f'
    source_version = '04159ca519d958593a71b8147c0d517268bbbb7f9a82f535b4230a0be31ff7fe'
    authority = '诏安县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '诏安县'}
    source_folder = 'zhangzhou-next-four-own-source/350624'
    foreign_code = '350622'


class NanjingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350627'
    source_id = '6af5580aaa3c66970cd8c61b'
    source_version = 'e2a8449a5f26bed7477dd706167ebcce2137f69fe711eb6335a26f2532ef4477'
    authority = '南靖县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '南靖县'}
    source_folder = 'zhangzhou-next-four-own-source/350627'
    foreign_code = '350622'


class DongshanCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350626'
    source_id = '2a8fc5dd930c86940a551377'
    source_version = 'bce4b0e47eaad6a9508e295e64da4a720ca9d8d06e7252cf46e92be51b1646e3'
    authority = '东山县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '东山县'}
    source_folder = 'zhangzhou-next-four-own-source/350626'
    foreign_code = '350622'


class InvestmentZoneCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350692'
    source_id = 'ba43712a330a421eb5306aed'
    source_version = 'c657a98361f5d3e69af383ffe4a57afc401f5930c729a4227eda52d7e83a263d'
    authority = '漳州台商投资区社会事业管理局'
    region = {'province': 'fujian', 'city': '漳州市', 'district': '漳州台商投资区'}
    source_folder = 'zhangzhou-functional-own-source/350692'
    foreign_code = '350599'


class JiaochengCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350902'
    source_id = '0b4a45eb9c9f0624c92bc3dc'
    source_version = '2612dfc3a4102f564e2cdbe167021ed4e3319804f9a244f8464eca81622bc79c'
    authority = '蕉城区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '蕉城区'}
    source_folder = 'ningde-first-four-own-source/350902'
    foreign_code = '350981'


class FuanCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350981'
    source_id = 'aa1e6889629caa4ec08b894b'
    source_version = 'ff0afc8c38f5fa8dc26f9ad2212a60c5d3f58189b138e93a51510811d90dfd0e'
    authority = '福安市人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '福安市'}
    source_folder = 'ningde-first-four-own-source/350981'
    foreign_code = '350902'


class FudingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350982'
    source_id = '837907d624340a4f4b36ea71'
    source_version = '3a6e28b0cfd9d5b4939720e230e2252b34884e5ac764d2bbd4b4823b382ab3f9'
    authority = '福鼎市人力资源与社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '福鼎市'}
    source_folder = 'ningde-first-four-own-source/350982'
    foreign_code = '350902'


class XiapuCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350921'
    source_id = 'ae035da9c2109496258da1f7'
    source_version = 'da32d388bf65ec1a2c8b275647c99afcc706a88fe4443d63927fe7fd59442e6d'
    authority = '霞浦县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '霞浦县'}
    source_folder = 'ningde-first-four-own-source/350921'
    foreign_code = '350902'


class GutianCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350922'
    source_id = 'b001fa88aecf2dca266120e3'
    source_version = 'd72a825eb8cac6f049ca64b76fe6ff824a222325fecfea5bfa6b58d7e3cab65f'
    authority = '古田县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '古田县'}
    source_folder = 'ningde-next-five-own-source/350922'
    foreign_code = '350902'


class PingnanCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350923'
    source_id = '272f1398c7c84fdbcb241d55'
    source_version = '4cca508c10e685dcc0cc2db5167450f1313a8d354036fc135e73c43119486dbc'
    authority = '屏南县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '屏南县'}
    source_folder = 'ningde-next-five-own-source/350923'
    foreign_code = '350902'


class ShouningCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350924'
    source_id = '1ebfe0ec7e5a13953ed7b26c'
    source_version = '1846eddaab2674891da8eca114cc28d45e952f1d7e641d7de0d2f6a009d23285'
    authority = '寿宁县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '寿宁县'}
    source_folder = 'ningde-next-five-own-source/350924'
    foreign_code = '350902'


class ZhouningCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350925'
    source_id = '93c89d232bac720d254d951b'
    source_version = '2925904df42021fa7392b580b9d02d8d7193ff5daca4ee87985c1bf64ddb537b'
    authority = '周宁县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '周宁县'}
    source_folder = 'ningde-next-five-own-source/350925'
    foreign_code = '350902'


class ZherongCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350926'
    source_id = 'b5dede071093f619366f7212'
    source_version = 'cb08426c5bebc559997940c644845c5a29b06c3fd0c60b69d601570a5a3bc04f'
    authority = '柘荣县民政和人力资源社会保障局'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '柘荣县'}
    source_folder = 'ningde-next-five-own-source/350926'
    foreign_code = '350902'


class YanpingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350702'
    source_id = 'f780a2e27a9ef10965a9a398'
    source_version = '3a8fe2101325254e0ab8814a29af66da9653780d3baa7e3b8273c51de2e18bd2'
    authority = '南平市延平区人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '南平市', 'district': '延平区'}
    source_folder = 'nanping-first-three-own-source/350702'
    foreign_code = '350781'


class ShaowuCandidateTests(_FujianCandidateChecks, TestCase):
    handling_form = '窗口办，网上办'
    code = '350781'
    source_id = '7b2e6d218619d6a4b7dd3b18'
    source_version = 'cb5892f69d77ab6342a21a912b5c342d94cd7a17c9df75c2fc14332f4fbffe6a'
    authority = '邵武市人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '南平市', 'district': '邵武市'}
    source_folder = 'nanping-first-three-own-source/350781'
    foreign_code = '350702'


class WuyishanCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350782'
    source_id = 'f07923c1454cce539678a805'
    source_version = '19b7ea84bc6d1c272ae491705a87f22657b43e65729ef57b79d01ac1a60b95e1'
    authority = '武夷山市人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '南平市', 'district': '武夷山市'}
    source_folder = 'nanping-first-three-own-source/350782'
    foreign_code = '350702'


class JianouCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350783'
    source_id = 'db760e316b1f5abf85a0e791'
    source_version = 'c4ca52093ae26b8bcdf5a1e467bb116acf2b23b92af5ebccf77ec8514fc55065'
    authority = '建瓯市人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '南平市', 'district': '建瓯市'}
    source_folder = 'nanping-next-four-own-source/350783'
    foreign_code = '350702'


class ShunchangCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350721'
    source_id = '04c84b5c09ac6325710f35ee'
    source_version = '7c5d5269bcb3a21b776b1a3639e7853e518a1ee0ea1f5636640596431d038149'
    authority = '顺昌县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '南平市', 'district': '顺昌县'}
    source_folder = 'nanping-next-four-own-source/350721'
    foreign_code = '350702'


class GuangzeCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350723'
    source_id = '012ffa540bf8300a303b0b8a'
    source_version = 'e82a712e2b512ef21e4a5de3f9bb9bacfc425dc97b8b40ffaf8945be6e09ba2d'
    authority = '光泽县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '南平市', 'district': '光泽县'}
    source_folder = 'nanping-next-four-own-source/350723'
    foreign_code = '350702'


class SongxiCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350724'
    source_id = '5367845e0fb0ae0340bfeb3a'
    source_version = '147248df85a42120b7a90af9bb6b6652205e6038071377bab1da9f66299c502b'
    authority = '松溪县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '南平市', 'district': '松溪县'}
    source_folder = 'nanping-next-four-own-source/350724'
    foreign_code = '350702'
