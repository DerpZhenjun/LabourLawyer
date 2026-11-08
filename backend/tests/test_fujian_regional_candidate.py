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
    expected_kinds = {'application', 'evidence'}
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
                self.assertEqual(set(eligible), self.expected_kinds)
                if 'evidence' not in self.expected_kinds:
                    evidence_material, = [m['material_id'] for m in guide['materials'] if m['name'] == '证据清单']
                    blocked_evidence = [t for t in guide['templates'] if t['material_id'] == evidence_material]
                    self.assertEqual(len(blocked_evidence), 2)
                    for blocked in blocked_evidence:
                        evidence_query = {**self.region, 'source_id': self.source_id, 'version': guide['version'],
                                          'kind': 'evidence', 'template_id': blocked['id']}
                        self.assertFalse(blocked['can_generate'])
                        self.assertEqual(client.get('/regional/form-contract', params=evidence_query).status_code, 409)
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


class PuchengCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350722'
    source_id = 'a5f6eb9afcdba92231eccec3'
    source_version = 'c67a884ab39a3567ac59a367956016005f7d7d23ab29c73b8415857b92629ffc'
    authority = '浦城县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    expected_kinds = {'application'}
    region = {'province': 'fujian', 'city': '南平市', 'district': '浦城县'}
    source_folder = 'nanping-application-only-own-source/350722'
    foreign_code = '350702'


class ZhengheCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350725'
    source_id = '8cbb28e92dec4b9e84175e26'
    source_version = '7933966b1ba6e4315aa7dfbb556827aeba69f6c6146d1f33e51d5b5348f0b07e'
    authority = '政和县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    expected_kinds = {'application'}
    region = {'province': 'fujian', 'city': '南平市', 'district': '政和县'}
    source_folder = 'nanping-application-only-own-source/350725'
    foreign_code = '350702'


class JianyangCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350703'
    source_id = '27b3bacad17d7069dfd7ff81'
    source_version = 'c0d126eca85333839449c7ae1957a6d7b3d1a20eb2ee10eadfd3e9a9c5a80d83'
    authority = '南平市建阳区人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '南平市', 'district': '建阳区'}
    source_folder = 'nanping-jianyang-own-source/350703'
    foreign_code = '350702'


class XinluoCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350802'
    source_id = 'fdc6a88b3a22440ff0b7c40f'
    source_version = 'faf214ad5a505bf5d6be8d65e544db55fb9b9a4a999fb00ff7acaf7a2665e58a'
    authority = '新罗区人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '新罗区'}
    source_folder = 'longyan-first-two-own-source/350802'
    foreign_code = '350881'


class ZhangpingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350881'
    source_id = '8ddc5833de93302535e84616'
    source_version = '84b0bcb512748a2f60f8de3548366059de81b32abf0f4dd2aa39ab8f2ed44616'
    authority = '漳平市人力资源和社会保障局'
    handling_form = '窗口办，网上办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '漳平市'}
    source_folder = 'longyan-first-two-own-source/350881'
    foreign_code = '350802'


class YongdingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350803'
    source_id = '1e23aca032c08ea09d8de2e2'
    source_version = 'aaf624f1e6ddaa91b58d5b50853fe9344882ba0ad3b1543d704e6fef123e337e'
    authority = '龙岩市永定区人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '永定区'}
    source_folder = 'longyan-next-two-own-source/350803'
    foreign_code = '350821'


class ChangtingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350821'
    source_id = 'd74f09e4c5b1c5c09225add6'
    source_version = '049e3655e0b88c3fe66fbf5dd309c14baf80f93705f6255729feff84447acd45'
    authority = '长汀县人社局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '长汀县'}
    source_folder = 'longyan-next-two-own-source/350821'
    foreign_code = '350803'


class ShanghangCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350823'
    source_id = '7c8b83a0120243ba4bf74d4a'
    source_version = '4f90e0f66d5fd28b0f5d9db9d33264df0d48c371fdfd35ecb1f4639224429527'
    authority = '上杭县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '上杭县'}
    source_folder = 'longyan-next-three-own-source/350823'
    foreign_code = '350802'


class WupingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350824'
    source_id = 'e83e81785d88fec226301f13'
    source_version = 'e1a5bbb57a5038f572b4bfbf7ac554961f2f190080a12ce22b0f36fbb4c415a3'
    authority = '龙岩市武平县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '武平县'}
    source_folder = 'longyan-next-three-own-source/350824'
    foreign_code = '350802'


class LianchengCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350825'
    source_id = '9d72686d21ca8390335e0261'
    source_version = 'ab56b74e06274ec4abfea00f5305c91910fe3c66cb71317757db829b3696b372'
    authority = '连城县人力资源和社会保障局'
    handling_form = '窗口办，网上办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '连城县'}
    source_folder = 'longyan-next-three-own-source/350825'
    foreign_code = '350802'


class _MunicipalCandidateChecks(_FujianCandidateChecks):
    def test_city_level_is_offered_only_for_an_exact_guide_and_explicitly_selected(self):
        directory_rows = json.loads((ROOT / 'data/public-regions/directory.json').read_bytes())
        city_row = next(row for row in directory_rows if row['code'] == self.code and row['level'] == 3)
        with TemporaryDirectory(prefix='municipal-candidate-') as folder:
            store = RegionalStore(Path(folder) / 'guides.sqlite')
            directory = routes.DirectoryStore(Path(folder) / 'directory.sqlite')
            directory.put_area(city_row)
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), \
                    patch.object(routes, 'directory_store', return_value=directory), TestClient(app) as client:
                selection = {key: self.region[key] for key in ('province', 'city')}
                self.assertEqual(client.get('/regional/areas', params=selection).json()['items'], [])
                staged = own.staged_candidate(self.code, root=ROOT)
                self.assertEqual(staged['scope_level'], 'municipal')
                store.put_guide(staged)
                row, = client.get('/regional/areas', params=selection).json()['items']
                self.assertEqual((row['district'], row['region_code'], row['level']), ('市本级', self.code, 3))
                self.assertTrue(row['can_generate'])
                self.assertEqual(row['source_id'], self.source_id)
                self.assertEqual(client.get('/regional/lookup', params=self.region).json()['source_id'], self.source_id)
                for district in ('', '未核验的区县'):
                    other = client.get('/regional/lookup', params={**selection, 'district': district}).json()
                    self.assertIsNone(other['source_id'])
                    self.assertFalse(any(t['can_generate'] for t in other['templates']))
                wrong_city = client.get('/regional/lookup', params={**self.region, 'city': '其他城市'}).json()
                self.assertIsNone(wrong_city['source_id'])


class NingdeMunicipalCandidateTests(_MunicipalCandidateChecks, TestCase):
    code = '350900'
    source_id = '015fbbb3a4bf80fcb5d8d065'
    source_version = '7acf19fe027acd5e93e93e5e21e65c0802527758b1e9dcf90c4364434a6d9a2a'
    authority = '宁德市人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '宁德市', 'district': '市本级'}
    source_folder = 'ningde-municipal-own-source/350900'
    foreign_code = '350902'


class NanpingMunicipalCandidateTests(_MunicipalCandidateChecks, TestCase):
    code = '350700'
    source_id = 'f94ef9ec2ad2020932331f5a'
    source_version = '706c1574ab63bbe59b2e3fd320a8fdab0191d2864fd5411a953f18bdee11ef8f'
    authority = '南平市人力资源和社会保障局'
    handling_form = '窗口办，网上办'
    region = {'province': 'fujian', 'city': '南平市', 'district': '市本级'}
    source_folder = 'nanping-municipal-own-source/350700'
    foreign_code = '350702'


class LongyanMunicipalCandidateTests(_MunicipalCandidateChecks, TestCase):
    code = '350800'
    source_id = 'eeda6db9dc8414446292f9c0'
    source_version = '79c90f32395f126733067e274ece79bb06f00704144fd402543c356e4e82e317'
    authority = '龙岩市人力资源和社会保障局'
    handling_form = '窗口办，网上办'
    region = {'province': 'fujian', 'city': '龙岩市', 'district': '市本级'}
    source_folder = 'longyan-municipal-own-source/350800'
    foreign_code = '350802'


class YouxiCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350426'
    source_id = 'c4a1025ea6a8038fcb55baa3'
    source_version = '2ef0c5c3cec90a841d088dea938e4addb098852b97f9bcaefaaf9b6c18fe4227'
    authority = '尤溪县人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    expected_kinds = {'evidence', 'application'}
    region = {'province': 'fujian', 'city': '三明市', 'district': '尤溪县'}
    source_folder = 'sanming-youxi-own-source/350426'
    foreign_code = '350825'


class SanmingMunicipalCandidateTests(_MunicipalCandidateChecks, TestCase):
    code = '350400'
    source_id = 'da959113b9c50e887043f638'
    source_version = 'c796921f5893dcce538f51a44393332cdb8b2e95f426a0476ea965dad9e03390'
    authority = '三明市人力资源和社会保障局'
    handling_form = '窗口办，网上办'
    expected_kinds = {'application'}
    region = {'province': 'fujian', 'city': '三明市', 'district': '市本级'}
    source_folder = 'sanming-municipal-own-source/350400'
    foreign_code = '350426'


class NinghuaCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350424'
    source_id = '2e7221316b15f1d1b0fcf034'
    source_version = 'c9ce260340747c75b7271f069088c27a4a912609e971d340af03325c318d408a'
    authority = '宁化县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '三明市', 'district': '宁化县'}
    source_folder = 'sanming-next-three-own-source/350424'
    foreign_code = '350426'

class MingxiCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350421'
    source_id = '0344451e5d72c7ff36543fe9'
    source_version = 'a49fbaba629c04954b07d1ea4923b03ba2269f16ca6e98183266c4609300f403'
    authority = '明溪县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '三明市', 'district': '明溪县'}
    source_folder = 'sanming-next-three-own-source/350421'
    foreign_code = '350426'

class JiangleCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350428'
    source_id = '23bd108d76ca3647bfc597c8'
    source_version = 'b8978e2977dfe8b8ff88fa3e76a341de64444110620140902dce04c389a041b9'
    authority = '将乐县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '三明市', 'district': '将乐县'}
    source_folder = 'sanming-next-three-own-source/350428'
    foreign_code = '350426'


class QingliuCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350423'
    source_id = 'e1fcf92db221a6feebb6a287'
    source_version = '28be1c6fcf51bb3688f57ab5354eefbeac604b4eae5186a1805951587d1a5ab6'
    authority = '清流县人力资源和社会保障局'
    handling_form = '窗口办，网上办'
    expected_kinds = {'application'}
    region = {'province': 'fujian', 'city': '三明市', 'district': '清流县'}
    source_folder = 'sanming-qingliu-own-source/350423'
    foreign_code = '350426'


class JianningCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350430'
    source_id = '64ad9887fd1677ef049bac0b'
    source_version = 'c8021b2eca9928d2dfc4defabab59df134f93d837c67c5f768762abc661cf342'
    authority = '建宁县人力资源和社会保障局'
    region = {'province': 'fujian', 'city': '三明市', 'district': '建宁县'}
    source_folder = 'sanming-jianning-own-source/350430'
    foreign_code = '350426'


class SimingCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350203'
    source_id = '344a290c8ef651a27389ed99'
    source_version = 'a38b0e084d3bdd4164b811c406af8866312256c2eb4aa4731618090f98efbb8a'
    authority = '厦门市思明区人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '厦门市', 'district': '思明区'}
    source_folder = 'xiamen-first-four-own-source/350203'
    foreign_code = '350430'


class HuliCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350206'
    source_id = '72f29a0f432cbb59fe6e1eb3'
    source_version = '410d2985e0d923b65ec362a8856df41f6a1d71b9050b71e1c2b87b95601c2955'
    authority = '厦门市湖里区人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '厦门市', 'district': '湖里区'}
    source_folder = 'xiamen-first-four-own-source/350206'
    foreign_code = '350430'


class JimeiCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350211'
    source_id = '6f719c328875cd3cd16646ff'
    source_version = '752f2cdb03e972f0eacc2eac96052fc79fb7914d7b28263887e7fcd0338834be'
    authority = '厦门市集美区人力资源和社会保障局'
    handling_form = '窗口办，网上办'
    region = {'province': 'fujian', 'city': '厦门市', 'district': '集美区'}
    source_folder = 'xiamen-first-four-own-source/350211'
    foreign_code = '350430'


class HaicangCandidateTests(_FujianCandidateChecks, TestCase):
    code = '350205'
    source_id = '59e32cc0aee11a28de7c607f'
    source_version = 'bd61ba685b94c9e1197f24a28a630364e50934dadb0449dc29c0aefa49abe5e8'
    authority = '厦门市海沧区人力资源和社会保障局'
    handling_form = '窗口办，网上办，邮寄办'
    region = {'province': 'fujian', 'city': '厦门市', 'district': '海沧区'}
    source_folder = 'xiamen-haicang-own-source/350205'
    foreign_code = '350430'
    expected_kinds = {'application'}
