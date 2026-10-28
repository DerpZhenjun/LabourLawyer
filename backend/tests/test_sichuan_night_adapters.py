import copy
import hashlib
import json
import unittest
from pathlib import Path

from regional_adapters import with_reference_capabilities

ROOT=Path(__file__).resolve().parents[2]
CAPTURES=ROOT/'reports/nationwide-localization-20261023-night/sichuan/captures'


class SichuanNightAdapters(unittest.TestCase):
    def guide(self,code):
        return json.loads((CAPTURES/code/'guide.json').read_text('utf8'))

    def test_zigong_six_own_sources_enable_two_documents(self):
        sources=set()
        for code in ['510302000000','510303000000','510304000000','510311000000','510321000000','510322000000']:
            with self.subTest(code=code):
                guide=with_reference_capabilities(self.guide(code))
                template=next(t for t in guide['templates'] if t['original_name']=='仲裁申请书(模板).docx')
                self.assertTrue(template['can_generate'])
                self.assertEqual(template['document_types'],['application','evidence'])
                self.assertEqual(hashlib.sha256((ROOT/template['file']).read_bytes()).hexdigest(),template['sha256'])
                sources.add(guide['source_url'])
        self.assertEqual(len(sources),6)

    def test_same_attachment_bytes_never_allow_wrong_city_or_source(self):
        original=self.guide('510302000000')
        for field,value in [('city','成都市'),('district','锦江区'),('source_url','https://www.sczwfw.gov.cn/?areaCode=510104000000')]:
            with self.subTest(field=field):
                changed=copy.deepcopy(original);changed[field]=value
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_panzhihua_five_own_sources_enable_only_their_combined_sample(self):
        expected={
            '510402000000':('东区','4be146f298e2d8ec6e1780b8','fd5cf982b23744f58d0af2ac24dd29a5'),
            '510403000000':('西区','87804a0b7eaa61ff64a09fac','4ec27ff702b248dea835fb2c23f25eb1'),
            '510411000000':('仁和区','ff1f93aff8f7dd536d9d913a','61d65f176cfd4dd3b45371e0c97d508e'),
            '510421000000':('米易县','ee9c01334d455216b8420e81','d3ff2ca8fbba4489bfb59c096aedb270'),
            '510422000000':('盐边县','de50b9fbf14412318186bf20','2e706a2fd4de4cd4b89b817e65e8dbad'),
        }
        for code,(district,sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                self.assertEqual((g['city'],g['district']),('攀枝花市',district))
                for field,value in [('city','自贡市'),('district','自流井区'),('source_id','b5aa123e9cd62e86b366d73f')]:
                    changed={**g,field:value}
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_sample_cannot_be_reclassified_or_use_neighbor_annex(self):
        original=self.guide('510302000000')
        for field,value in [('official_kind','blank'),('annex_id','894b646760c242d4ba385c17ee768d17'),('sha256','0'*64)]:
            with self.subTest(field=field):
                changed=copy.deepcopy(original)
                next(t for t in changed['templates'] if t['original_name']=='仲裁申请书(模板).docx')[field]=value
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_luzhou_guangyuan_fourteen_use_own_sources_and_reject_neighbor_annex(self):
        expected={
            '510502000000':('5588a8fad8b03055a638cf21','7c24ed4e5c734557890552e7d6d0b800'),
            '510503000000':('c1bb9d2609328a40030f8767','2d976e395e1d46439fd0327e737c1286'),
            '510504000000':('3d3600b70ca22c61dd52701f','3af246523e5a499f99bfd510a1b1ce8f'),
            '510521000000':('e147fde7f0259337f6ff7045','492902d877744a69be898f68dd16f43e'),
            '510522000000':('238616cb41f4f72e9425d016','30420ab7f58747f3866550d282d79de6'),
            '510524000000':('d37ef42a091e063a72eb8391','7773b67a89e54bb693a84285b56cf359'),
            '510525000000':('4d428a5817bab306ce939357','6759c561021c4c2fa32e7e7037501861'),
            '510802000000':('5826890067ba9dfe4f25aaa7','b4ce29501d6d4dbf8d9d2f88d402e1b3'),
            '510811000000':('eab7904ad603e42d42c82407','53a9f3da75f94fdb8c5cb6c2d034f0d7'),
            '510812000000':('03717e639e4bb4fb70e28545','5dfac74c0fff4b05ba1237da94f7d939'),
            '510821000000':('24ca5810e096848d3c496050','96d45f9cf8734a4e949397132163d6c4'),
            '510822000000':('00e56d8db183156225f14b68','4015386169344e3f8a8221003b166b94'),
            '510823000000':('fb5dc58ca8baf365e5c00419','eb4eeca82450492e8a82be7768bfa760'),
            '510824000000':('4d8042e18b2bf155bab173f1','b7df424ec75e45f38302a3357d2de500'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                raw=self.guide(code);g=with_reference_capabilities(raw)
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','自贡市'),('source_id','4be146f298e2d8ec6e1780b8')]:
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities({**g,field:value})['templates']))
                changed=copy.deepcopy(g)
                own=next(t for t in changed['templates'] if t['id']==annex)
                own['annex_id']='fd5cf982b23744f58d0af2ac24dd29a5'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_suining_neijiang_nine_enable_only_their_own_sample_source(self):
        expected={
            '510903000000':('79d7d9c33283205ff027dc7b','b15ce7bf8fde4903bf3b428de2e051d5'),
            '510904000000':('6356e2a413a59c1f2de24ea0','ea4796fa1a034db39eb17bb0058735a0'),
            '510923000000':('757f0cb9f5acc1bfd11c5806','c1538a986cb944bbb3b74f165c2b2506'),
            '510981000000':('d3259b27cfbd27b99c7a67ae','17c838a0add74d90ab7f652380598e12'),
            '511002000000':('d7f98675320d41a264a90424','bf3d512c9bc14eb0832cf56aa4c26332'),
            '511011000000':('64ff1af0dc6cf1cfd67b5844','97a01aefdecd445dafdd7ebdf9408d0a'),
            '511024000000':('c13431d9f7729785426c7851','06e13e1836674f1ea73dd83f071eb9e2'),
            '511025000000':('868d5c03d283c80f95dabefa','d477bf537d6a45858a7a4ef8a6361277'),
            '511028000000':('0c0d7bd58127bfe21c1ef22e','01761ebde4384544a8278748268c41a3'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','自贡市'),('source_id','5588a8fad8b03055a638cf21')]:
                    changed=copy.deepcopy(g);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(g)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='7c24ed4e5c734557890552e7d6d0b800'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_leshan_nanchong_nineteen_require_their_exact_source_and_annex(self):
        expected={
            '511102000000':('2776c1fbeddaa1c547836e94','d4105fec3f5241c7875282e4d520b1cb'),
            '511111000000':('a91a7061432b000fd4d0e999','506d015590ba4cf5a2841a3b0a382699'),
            '511112000000':('0094adafc1b8deb55809aedd','6d591d5b31d54063bfd8d971e2877426'),
            '511113000000':('aec6ed7ea283ac8f6bf3cced','ae8e374a5fe84110b8164779ee8d0495'),
            '511123000000':('79b664c035b48291ea88bf1d','77f21f8171f648b69bd9f05956f6fd19'),
            '511124000000':('6983b349627ac2b408df2468','b978e3b84d3648e094345afe900a5d4c'),
            '511126000000':('98edc1bb563ad370d4d11469','3bac20ae0ee0472bb813b47248669fd4'),
            '511129000000':('9c83201dcd5fab775ca6780b','fec6ff6131da43e18ace90ddc29cb3e2'),
            '511132000000':('c855239220ca419d13cdf042','e32a7f2e3dea4815acf7e9a3af325634'),
            '511133000000':('52a7cc57264fb39fa753fd85','50561589f1b44682b5355bdbf90f591f'),
            '511302000000':('6a15ff76b00d9ebab910307b','d9cdbcadc6fa469a81f148159752b728'),
            '511303000000':('2266810525f089f48b81cb05','33261aa06e2e4871b5634b70999d6f0a'),
            '511304000000':('e3f05d0583986c4551027fbb','084685e3b6ce486ebc3d955bea002014'),
            '511321000000':('13019590097f4b52d2a849ff','df360488161b41999d2eb0d6fbd68597'),
            '511322000000':('cf8a36dabb1c97e48db2e387','8486319fc4ee4bc094fe62a7e86da3c2'),
            '511323000000':('d29aac175cf17316b81e0e51','1398154ed4e6455abd7ca3012d8d60ae'),
            '511324000000':('f221c93af5374b1d78582dae','346a5f09795040a5b6c4e81b66f2b540'),
            '511325000000':('e6a53db12df25ff7f5ab5e4b','a328a939cb18460487f6b7860ce7bc00'),
            '511381000000':('3f63f48831c5e2179cc7fa43','b3ae2ca141264a0e90e4b928c8112d03'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','自贡市'),('source_id','d7f98675320d41a264a90424')]:
                    changed=copy.deepcopy(g);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(g)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='bf3d512c9bc14eb0832cf56aa4c26332'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_meishan_yibin_sixteen_require_their_exact_source_and_annex(self):
        expected={
            '511402000000':('6b4a8f4be2fbc86be1c8a4f4','7ced925454c94eb5b4bdd6920fc347fa'),
            '511403000000':('b343ed97c09f939b1eb6d1d0','14f06b6195b44c7f93d5c1aefddc2bb5'),
            '511421000000':('3f2acd6df2e41f0306710f4f','ed989c1317bc44b4a595fcc08061c1bb'),
            '511423000000':('7deb5e94b193428b55f41380','37dad991f76b47048bff01303a7aa914'),
            '511424000000':('061a6d8944cd05a137c2a100','f50cd37e774f42c9a47399dd6271c8c7'),
            '511425000000':('548a239a5e912c33f68a67df','bb0fdd407fd34f35936b36d1cec66d8d'),
            '511502000000':('cc6ed19b27e6ef921ad68830','f522e68b9da84cfa85c34dd934ca3102'),
            '511503000000':('97a5f4ac51d27b7dec8c5af2','bbccddba4d6d45fc92e9b723ff044b01'),
            '511521000000':('6dfc9a8b70ff73ec5ecde944','04f8dbcadb9c464193cfdb6e85ae79c2'),
            '511523000000':('8ff407c1383b1c8f06e97717','f1702a4cba8c49d38d38a13ad21cf23f'),
            '511524000000':('65e08a96c85220c98567a8c8','71ded9e9a05d4a4db1a215f805c8a7f8'),
            '511525000000':('597c1bccd8ddfce041247a76','9289f5cf227f442da0f9bb39a0cf29b7'),
            '511526000000':('7f113dd70f3ca0617d31343b','54352e64308047d5b25b2cdb3c356638'),
            '511527000000':('6178cbb4e3c4814ade7ec0ed','55ec2bfb7aa544b0b574ce4d509f9e1a'),
            '511528000000':('81160f46e6812c1315c22e23','40b21039674e412ebe85b16d315f17e4'),
            '511529000000':('6acd19a540915b84dc0990c3','15f4110c15504a348b4dd81b5a603ae2'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','成都市'),('source_id','1064c9ed5635a0d224e4eee5')]:
                    changed=copy.deepcopy(g);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(g)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='ec3268e5fda94301ab40a7e086afe07a'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_guangan_dazhou_bazhong_sixteen_require_exact_local_source_and_annex(self):
        expected={
            '511602000000':('34bf5afb172b659cc594c350','a87da0edec844b3d963e1db708b20faf'),
            '511603000000':('7442a9bbe49a937d170d3363','e6e9c0383e814a508aaf368b720ba67b'),
            '511621000000':('a290b45628eaccb32d30f469','6063c2a51154414d89f30678b710a90e'),
            '511622000000':('54ea0785295573506e1e10ae','c4c78ec241ae476aaeee57b625aacbba'),
            '511623000000':('242c8893e845e9b1b0479ca7','17167a6edb62496ba1095ed552fd8a7b'),
            '511681000000':('94f645411fd8f4c1021eabdf','4b870329810c47c68e377a9be1f9007d'),
            '511702000000':('0a07642f1ede208681ac9099','ca09f6ca0e354e9d897187ac9d144d9a'),
            '511703000000':('577613b9ca6ee5fbfc1f7865','2c0b5e60b3ec41fabaac481459055c7e'),
            '511722000000':('f1d64edfa7a90a15a1eb8c07','99b4a3ba321349348852a499620439e3'),
            '511725000000':('16203e4931907567e93d670d','e0f6f5b1f6ac4cb5a79f564d5d9303c1'),
            '511781000000':('2b22fe7ffb795cdf5fcd6251','63bfe84db9f241448dab7c6532539b17'),
            '511902000000':('2c6cd910c097983105b086ef','40294caddc0b4208a0c2af474fd93ccb'),
            '511903000000':('ebb0dc55337fd3aeebd32fb7','235d07b21cb1489eb2d8812f3e846b27'),
            '511921000000':('f657e3320e6d2bb09d2fccf8','b392a699103a420f94c09b7526c53694'),
            '511922000000':('0afc61bc6abf457460bb544d','8435e5bb63884ac3beaaefccc015486d'),
            '511923000000':('736821d8ed2e87018609ec0e','0fe99eeb5e324a7a8a3cbb7d3cbd21f4'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','眉山市'),('source_id','6b4a8f4be2fbc86be1c8a4f4')]:
                    changed=copy.deepcopy(g);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(g)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='7ced925454c94eb5b4bdd6920fc347fa'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_yaan_ziyang_aba_twenty_four_require_exact_local_source_and_annex(self):
        expected={
            '511802000000':('978f9d48a4c0754cea718425','0f3046dfbf9847a7baec7761f1ec257c'),
            '511803000000':('70761249de53dd947e902d3c','3499fb9c4f5c44d1a0234eff85a34729'),
            '511822000000':('f0f1c3b0567e1ad1a2bbb6da','4527b62806aa4c82b56ccddcda80e2dc'),
            '511823000000':('e1794fe08cf35e4ac4495733','a0a5b017495342a0bc89c4be365f37a6'),
            '511824000000':('35cb9fb7e9d7fa9eda040583','db9841f58c2e485d8e563adea522c568'),
            '511825000000':('e784a8b50368bc5f29df2887','d3adb5e96b5c476d8acf861a3925a22c'),
            '511826000000':('081d0de2870fe40067c626fc','bbcfcad93849498db6ad951972ba77dd'),
            '511827000000':('17377c71bc18542d85b41207','f9622b3f9ab04dc2a14b4189a8469491'),
            '512002000000':('44a1c54f3383b18cd0f22c21','b9865bf4423f45efaf54acb88c0770fa'),
            '512021000000':('50a60a8acb249d12c724c3db','95c6a346cf6e41de8f8eb29a32d3f1a1'),
            '512022000000':('3df570d1d346fb7541ee0536','2cb77fcae5b147e1aee3327607afc7a3'),
            '513201000000':('6b5a1283d96ff59a3773cb82','1261927df4d047fe9cbd4d4be6153fe4'),
            '513221000000':('032201023d897d13c1e3e969','7a4aeeebe5e9400e9741c51ae470a47a'),
            '513222000000':('f712bf36532768e9d84ddd5c','ab0a9ec3eda44df9999244cf1f96d8f2'),
            '513223000000':('d0ed186acfa8288f5c0bd83b','bee3a5137b4a466da87bd1040c9a3f6b'),
            '513224000000':('71bad9a64880f21f369c835b','482bfd10152141f38c5dcef961b2af4f'),
            '513225000000':('e6e0c520f1db0b6b47dc3061','9d921e853a844b26ad8653df030daa45'),
            '513226000000':('17fa0d7bc16847baeacaa3ee','07272b2cee7c429e83481cbc27527e2e'),
            '513227000000':('1fe6c99baa6beb8d5a1fcdbc','1e9dfc81de764f49b2b93cae2ac47efb'),
            '513228000000':('3adde6c1db0d49d55b95e00d','f3d3bba16d2645699123143503c35e6e'),
            '513230000000':('7a3fc196b16521da50d0927a','a7f5553275fa4b61b60baba9b480dd40'),
            '513231000000':('23612e3a1c66c24619afcba6','2e939810724a4752acb3f157c6ce642c'),
            '513232000000':('5cc1a8243cbbdd04691e7ed3','be18b861e5354a51923543e20c1ee6f1'),
            '513233000000':('a05931e4e560d0aa6802ce2a','62e54dba220d4694a089c05ae148e704'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','眉山市'),('source_id','6b4a8f4be2fbc86be1c8a4f4')]:
                    changed=copy.deepcopy(g);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(g)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='7ced925454c94eb5b4bdd6920fc347fa'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_ganzi_sixteen_require_exact_local_source_and_annex(self):
        # Break caught: missing own binding or accepting a neighbouring source/annex.
        expected={
            '513301000000':('290e526f33ba82ed572ea6da','659ed58e0b604e648eaedaf52982f9a2'),
            '513322000000':('d6bb8b28b49318e4239959b2','e5e999d9480b43bd8c19232777980b83'),
            '513323000000':('2b201fc0af5e5e66213318e2','42965f3e18b44aa0a4b1f674fc9e7d06'),
            '513324000000':('f2f355779e92b7e6948b3471','9cacff5b1f06468ea84cd435b12c603b'),
            '513325000000':('7e335c7217ec3e4bce533d61','fff6ff72ee454093bead7d27b28e78d1'),
            '513326000000':('efa457272077629e9524efb4','24bdfeab36c64a048642a542272a571a'),
            '513327000000':('f6fd8714b11eb772c4989600','5dd67516d2cf4241af30df7490f62a34'),
            '513329000000':('2feccd05761b1561d32ffad9','97c356be0e6947e6bd8903fae3b98793'),
            '513330000000':('3519a95d776993434b08e412','9d396d19dfcc4e7facc3109d08c912ef'),
            '513331000000':('0975a087ceb15b47fb7c5d29','e187ca6c4dcd4f709064cb76c69c75c1'),
            '513332000000':('cc9fb265f03b35b6789d5a1f','71a8d25ce54340d2aaa0eec4f24b189e'),
            '513334000000':('98bdd08ea71b3b2bb52a2f29','a181c9a6bb2e461a9d370b13868c7b1c'),
            '513335000000':('f94505a973b8e338a73ffdaf','60262197146a4e1692193944430453b8'),
            '513336000000':('9235aad1baf680dee43206c1','2acc1ee7edf04be4b40dcd05b5549603'),
            '513337000000':('a7f2b7dc526d0acd7443a230','158fa06affab482c87b0d733dff0d46d'),
            '513338000000':('f837a8d97e003474bd25969e','4d491126e5b7450daa80e84e4df2a5d4'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','阿坝州'),('source_id','a05931e4e560d0aa6802ce2a')]:
                    changed=copy.deepcopy(g);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(g)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='62e54dba220d4694a089c05ae148e704'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_liangshan_fifteen_require_exact_local_source_and_annex(self):
        # Missing own binding or accepting another county's identical bytes must fail.
        expected={
            '513401000000':('065baf36fa46abff75d091f8','f4bc0a8979ac4424867e9ea828fc6230'),
            '513423000000':('0fccf2d8067ccfcbd6f681e2','c6cb29c66cb04ab58268bb13ac631b05'),
            '513424000000':('c67cac6245d2fd819187a2e9','ef4935fd548249e88be380a5dda6ed73'),
            '513425000000':('01380d3a35043802fe8065a6','f04fc76fee1e46a49d4e01ac725d12a1'),
            '513426000000':('0376c4a1ef9968b98c4bcbd4','69730f5cb3e446fca85d43e8565e8ab1'),
            '513427000000':('52ebf9663e0022151f88e14e','6fef2aa501c94b4f9f4a06f164edbaa4'),
            '513428000000':('7bdbb32c5315cadaabf57aca','30f4bb6d96d443dd923bdf9d5d1e54a1'),
            '513429000000':('79296870b0a60df8184ea5f7','ab6db07eb6f94233a389ae6592e1ca27'),
            '513430000000':('a0bceff6fbdcf466ac826a93','63c352cd63f54eb1ac30c178da62f7f9'),
            '513432000000':('11a33aa81652ca7db47ac903','b79db85467c34eb087f187552e616c40'),
            '513433000000':('0f593058bcc5c73928257ea5','f8474dbd4020456da65318ddd80e44dc'),
            '513434000000':('537c93ac773124264779d1c8','ed9393bbd50f45d784c36032e4655244'),
            '513435000000':('bd622aab769a98de8cade8eb','9707a54f9dfc47c5bfc489a5867d6afa'),
            '513436000000':('e2c603fed9897cc18b7e08a2','bb8ba77793774005b4f72a5657e270c0'),
            '513437000000':('7628ca9c8a7adbe91989804e','a7f1aa69d5a54f28b9eceb3460940e77'),
        }
        for code,(sid,annex) in expected.items():
            with self.subTest(code=code):
                g=with_reference_capabilities(self.guide(code))
                enabled=[t for t in g['templates'] if t.get('can_generate')]
                self.assertEqual([t['id'] for t in enabled],[annex])
                self.assertEqual(hashlib.sha256(json.dumps(g['source_url']).encode()).hexdigest()[:24],sid)
                self.assertEqual(enabled[0]['document_types'],['application','evidence'])
                self.assertEqual(enabled[0]['official_kind'],'sample')
                for field,value in [('city','甘孜州'),('source_id','290e526f33ba82ed572ea6da')]:
                    changed=copy.deepcopy(g);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(g)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='659ed58e0b604e648eaedaf52982f9a2'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_night_directory_identity_rejects_wrong_city_code_and_short_name(self):
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from sichuan_night_evidence import own_region_metadata
        from regional_capture import parse_sichuan_capture
        directory=CAPTURES.parent/'directory'
        expected=[('511411000000','眉山市','天府新区','天府新区（眉山片区）'),
                  ('513422000000','凉山州','木里县','木里藏族自治县')]
        for code,city,district,header in expected:
            with self.subTest(code=code):
                metadata=own_region_metadata(directory,code,city,district)
                self.assertEqual(metadata['name'],header)
                captured=json.loads((CAPTURES/code/'dom.json').read_text('utf8'))
                guide=parse_sichuan_capture(captured,city,district,region_metadata=metadata)
                self.assertEqual(guide['region_code'],code)
                for bad_code,bad_city,bad_district in [(code,'成都市',district),('510164000000',city,district),(code,city,'邻区测试')]:
                    with self.assertRaises((ValueError,FileNotFoundError)):
                        own_region_metadata(directory,bad_code,bad_city,bad_district)
                with self.assertRaises(ValueError):
                    parse_sichuan_capture(captured,'成都市',district,region_metadata=metadata)
                with self.assertRaises(ValueError):
                    parse_sichuan_capture(captured,city,district,region_metadata={**metadata,'areaCode':'510164000000'})

    def test_official_long_names_survive_publication_preflight(self):
        import importlib.util
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        spec=importlib.util.spec_from_file_location('night_publication',ROOT/'scripts/publish-sichuan-night.py')
        publication=importlib.util.module_from_spec(spec);spec.loader.exec_module(publication)
        expected={
            '511411000000':('眉山市','天府新区','147acee5e1b447f897f7e41388e1c0ff'),
            '513422000000':('凉山州','木里县','e7b53d19f2ff427b9c21ffde53ca20c3'),
        }
        for code,(city,district,annex) in expected.items():
            with self.subTest(code=code):
                try:
                    guide=publication.prepare(code)
                except ValueError as error:
                    self.fail('Own official directory identity was dropped in preflight: '+str(error))
                self.assertEqual((guide['city'],guide['district'],guide['region_code']),(city,district,code))
                self.assertEqual([t['id'] for t in guide['templates'] if t.get('can_generate')],[annex])
                for field,value in [('city','成都市'),('region_code','510164000000')]:
                    changed=copy.deepcopy(guide);changed[field]=value
                    self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))
                changed=copy.deepcopy(guide)
                next(t for t in changed['templates'] if t['id']==annex)['annex_id']='659ed58e0b604e648eaedaf52982f9a2'
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_application_does_not_keep_spacer_for_removed_following_form(self):
        from regional_documents import fill_tianfu_reference
        original=self.guide('510302000000')
        template=next(t for t in original['templates'] if t['original_name']=='仲裁申请书(模板).docx')
        doc=fill_tianfu_reference(ROOT/template['file'],'application',{})
        self.assertTrue(doc.paragraphs[-1].text.strip(),'Trailing combined-form spacer can push an otherwise empty second page')

    def test_public_night_capture_screenshot_is_available_but_not_private_files(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.regional_guides import router
        app=FastAPI();app.include_router(router,prefix='/api/regional-guides');client=TestClient(app)
        capture=json.loads((CAPTURES/'510302000000/guide.json').read_text('utf8'))
        response=client.get('/api/regional-guides/evidence/'+capture['evidence']['screenshot'])
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['content-type'],'image/png')
        self.assertEqual(client.get('/api/regional-guides/evidence/reports/../backend/app.py').status_code,404)
