"""Document adaptation for individually captured Fujian sources using the reviewed layout."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import stat

from hq_phase_proof import strict_json
from hq_word_mechanics import _layout_fill
from regional_fujian_huian_quangang_nov1 import _DocumentBytes, exact, form_fields
from regional_guides import digest, official_content, region_key
from regional_huian_quangang_request import Application, Evidence


ADAPTER = 'fujian_quanzhou_next4_own_api_v1'
PUBLICATION_SHA256 = '5099dede84960def038d59c15ed6bd71bd95e3231eb6733985d563a9713e5149'
STAGE_SHA256 = '6473592bd0f24498e499b1c94da2f224498372bd63de723cf90eb5d4684d12b3'
BROWSER_SHA256 = '71ba37232b2077ce0927f61c64809ca32c51773865424c13cfb2ed4d6d60713a'
STAGE_VERIFIED_AT = '2026-11-08T02:57:48Z'
LOCALITIES = 'reports/overnight-gap-closure-20261030/localities'
BASE = LOCALITIES + '/quanzhou-next4-own-source-projection'
REVIEW_RECEIPT = LOCALITIES + '/quanzhou-next4-word-review/WORD-REVIEW-QUEUE.json'
BROWSER_RECEIPT = LOCALITIES + '/quanzhou-next4-word-review/BROWSER-CANDIDATE.json'
PUBLICATION_RECEIPT = LOCALITIES + '/quanzhou-next4-word-review/FINAL-PUBLICATION.json'
FIXTURES = LOCALITIES + '/fujian-huian-quangang/word-qa-nov1-v1/fixtures'
DY_BASE = LOCALITIES + '/quanzhou-dehua-yongchun-own-source'
DY_STAGE_RECEIPT = DY_BASE + '/WORD-PREFLIGHT.json'
DY_STAGE_SHA256 = 'e5c0a48a53e0b4b96b30f9e8acfd7dc545654e274e9b22a5e5eefa766dc3fa40'
DY_SOURCE_FREEZE_SHA256 = '3eb5d587708c2e420bf91e7320ac4e661215ce6ab26fa7bd3fe1ad8505a57781'
DY_BROWSER_RECEIPT = DY_BASE + '/BROWSER-CANDIDATE.json'
DY_BROWSER_SHA256 = '9669479f5e1e0a7f6f3e5ffef23dbc458efc57bb13080177188b5973ef831f54'
DY_PUBLICATION_RECEIPT = DY_BASE + '/FINAL-PUBLICATION.json'
DY_PUBLICATION_SHA256 = 'c88b22b572422a4630eff6be9c1403eae6296f3daf55b1b377952c4ec18b279c'
INVESTMENT_CODE = '350599'
INVESTMENT_BASE = LOCALITIES + '/quanzhou-investment-zone-own-source'
INVESTMENT_STAGE_RECEIPT = INVESTMENT_BASE + '/WORD-PREFLIGHT.json'
INVESTMENT_STAGE_SHA256 = '60bd331d59be45e072b112a4c63785e98fd293b9e6aa962b8a3646b3c35b9990'
INVESTMENT_SOURCE_FREEZE_SHA256 = '7b752522ecfe5ca30a4ea2a81f6f266777b1f94126b9c45ceea5808fc8fcbba3'
XIANGCHENG_CODE = '350602'
XIANGCHENG_BASE = LOCALITIES + '/zhangzhou-own-source'
XIANGCHENG_STAGE_RECEIPT = XIANGCHENG_BASE + '/WORD-PREFLIGHT.json'
XIANGCHENG_STAGE_SHA256 = '2031524a853e6c2c478478c8314e3d05650778eb340577844fe18030abc85f92'
XIANGCHENG_SOURCE_FREEZE_SHA256 = '4c41d8d1717ffa7d34ba01d2ae7bf6757b169f1d48474d155121aac1a976f21a'
LONGHAI_CODE = '350681'
LONGHAI_BASE = LOCALITIES + '/zhangzhou-longhai-own-source'
LONGHAI_STAGE_RECEIPT = LONGHAI_BASE + '/WORD-PREFLIGHT.json'
LONGHAI_STAGE_SHA256 = '651c28d38274c3837b1f0573fe26143c14f438bdbb36d23decff8a92c093c2a1'
LONGHAI_SOURCE_FREEZE_SHA256 = '12d06ae95b62ae8482f905e05e79b01cf832f527d308cdaf8a2d3ff618009bac'
ZHANGZHOU_FOUR_BASE = LOCALITIES + '/zhangzhou-four-own-source'
ZHANGZHOU_NEXT_FOUR_BASE = LOCALITIES + '/zhangzhou-next-four-own-source'
ZHANGZHOU_FUNCTIONAL_BASE = LOCALITIES + '/zhangzhou-functional-own-source'
NINGDE_FIRST_FOUR_BASE = LOCALITIES + '/ningde-first-four-own-source'
NINGDE_NEXT_FIVE_BASE = LOCALITIES + '/ningde-next-five-own-source'
NANPING_FIRST_THREE_BASE = LOCALITIES + '/nanping-first-three-own-source'
NANPING_NEXT_FOUR_BASE = LOCALITIES + '/nanping-next-four-own-source'
NANPING_APPLICATION_ONLY_BASE = LOCALITIES + '/nanping-application-only-own-source'
NANPING_JIANYANG_BASE = LOCALITIES + '/nanping-jianyang-own-source'
LONGYAN_FIRST_TWO_BASE = LOCALITIES + '/longyan-first-two-own-source'
LONGYAN_NEXT_TWO_BASE = LOCALITIES + '/longyan-next-two-own-source'
LONGYAN_NEXT_THREE_BASE = LOCALITIES + '/longyan-next-three-own-source'
SANMING_NEXT_THREE_BASE = LOCALITIES + '/sanming-next-three-own-source'
REGIONS = {
    '350582': {
        'district': '晋江市', 'source_id': 'd8353a4bb91532863fb03802',
        'source_manifest_sha256': '7a4b19e40bd16f66b256d7fc7d0b88d7c05289827feae7df4eb2a05a2048a503',
        'original_kinds': ('application', 'evidence'),
    },
    '350581': {
        'district': '石狮市', 'source_id': 'b954b9477907608d6cf530ed',
        'source_manifest_sha256': '8a63a89cf7048a359eb43495281378da5bd3d00885eedd1bc2e78eba95ec3e2d',
        'original_kinds': ('application',),
    },
    '350583': {
        'district': '南安市', 'source_id': '02b8e589e4891bdcbdacdc09',
        'source_manifest_sha256': '9dd8f9fdf8f88fc781301124ea58d0f67e8f4a4862b2b27bd8a6106f07630213',
        'original_kinds': ('application', 'evidence'),
    },
    '350524': {
        'district': '安溪县', 'source_id': 'ecd5bfaec46d03d4f6ae3860',
        'source_manifest_sha256': 'a3713d78625cc4267c628b5fb70ce3ecdce46005c4314d840560974449601d13',
        'original_kinds': ('application', 'evidence'),
    },
}
DY_REGIONS = {
    '350526': {
        'district': '德化县', 'source_id': '286f2f5801a4ad101b464ff7',
        'source_manifest_sha256': '983353486646af7070909393be75730aa7de42a127dec79e464695878f4605da',
        'original_kinds': ('application', 'evidence'),
    },
    '350525': {
        'district': '永春县', 'source_id': 'dce92327ed30b9ea92994e08',
        'source_manifest_sha256': 'c535d2d00bb7e8a47dfad8d0c368774e607ac4897bd20cfaf04b55d7c162fb30',
        'original_kinds': ('application', 'evidence'),
    },
}
ZHANGZHOU_FOUR_REGIONS = {
    '350628': {
        'district': '平和县',
        'source_id': '1c435a8e909867d2119efe16',
        'source_manifest_sha256': '798eba503cadb717fb74727aaff074c1389a69feed03c577f63642325f36c70d',
        'stage_sha256': '5b5fb2ede945b648655ec2d66302190f23da68fa3609835425324dae649227d9',
        'source_freeze_sha256': 'd649f37190852fc8c2ead529a3ddf784452d42bb3fff55208360917d2f046a0d',
        'original_kinds': ('application', 'evidence'),
    },
    '350625': {
        'district': '长泰区',
        'source_id': '2ea92c5adb81421b892f2994',
        'source_manifest_sha256': '74786aec7221088ada6a7923a38e13b9d74cb9ba042ac877db57211e35f3ae50',
        'stage_sha256': 'a66c404f9445db4dc7a68f3d73a025178ff4aca7e65e15f7f3634246a9f6da0c',
        'source_freeze_sha256': 'de643907f2f6aa78ed38b1e116cba9568e28a56e59a83d4fd9fe88b6b1ac9314',
        'original_kinds': ('application', 'evidence'),
    },
    '350623': {
        'district': '漳浦县',
        'source_id': '48e65b2c27fc105366706caa',
        'source_manifest_sha256': 'de8110bb1a971d508bffb8d94c8545d5bef504dee090b55955736105f7ac91ac',
        'stage_sha256': 'bb28ff85ef05455e2fb721d83803223ec57533d64fdd432ff58aaeba7906d971',
        'source_freeze_sha256': '443a18ad6d4e564fe0ea82ac0782430090d26d4be7a64fc38171994b330fda4a',
        'original_kinds': ('application', 'evidence'),
    },
    '350629': {
        'district': '华安县',
        'source_id': 'd61089df6a682a0affd5d18c',
        'source_manifest_sha256': 'd21b0110552ff1568fe6a7b7049faf9df6939f55f651d24191f8b472d1f3dc44',
        'stage_sha256': '0821fd8cde65ff0cb4260bbfc1009bbbbc1d4b57f6b2a52dd991324ff23b358f',
        'source_freeze_sha256': 'bc72e242e0da64e8a5a69c7588e56acea926dcdf5d1b5d1038f55670b9505e0a',
        'original_kinds': ('application', 'evidence'),
    },
}
ZHANGZHOU_NEXT_FOUR_REGIONS = {
    '350622': {
        'district': '云霄县',
        'source_id': '41be287d59db2eae92eac0f1',
        'source_manifest_sha256': '5edc06c82bc94fa0452c3ea8edc3d8d1d9d6ef586bf19f55f5ded5786d860be5',
        'stage_sha256': 'c2bd4a357692389e96c5bc9f714a2a10857a0555b48bd8e6a13bb9926b8d2def',
        'source_freeze_sha256': '79abef3428fc5bbd6e289ee25ee1a9ba34a1d49e0a7454b7771bce6ae74dd6a3',
        'original_kinds': ('application', 'evidence'),
    },
    '350624': {
        'district': '诏安县',
        'source_id': '32f582f436d0fcb48afeb66f',
        'source_manifest_sha256': '04159ca519d958593a71b8147c0d517268bbbb7f9a82f535b4230a0be31ff7fe',
        'stage_sha256': '8b9a57a262f518b8f041fea6d1298d63859e23427e3b02d650750651e97f754a',
        'source_freeze_sha256': '301c204373f6aeef9c9ec9335b768cdb82ddad221815f1e675aaa26d6bbc722a',
        'original_kinds': ('application', 'evidence'),
    },
    '350627': {
        'district': '南靖县',
        'source_id': '6af5580aaa3c66970cd8c61b',
        'source_manifest_sha256': 'e2a8449a5f26bed7477dd706167ebcce2137f69fe711eb6335a26f2532ef4477',
        'stage_sha256': 'b790152f95297a72cfb62200e924bee846494d0674c17dc67672822936c08509',
        'source_freeze_sha256': '4ed06850ecb05fee7008685245affe3172402beffed8fd9d1b6aa4c8f0dabff0',
        'original_kinds': ('application', 'evidence'),
    },
    '350626': {
        'district': '东山县',
        'source_id': '2a8fc5dd930c86940a551377',
        'source_manifest_sha256': 'bce4b0e47eaad6a9508e295e64da4a720ca9d8d06e7252cf46e92be51b1646e3',
        'stage_sha256': '15094328b8ffc90e7d4f32129a6b48362fc6da9f00e5a41e8cb39a7436dff781',
        'source_freeze_sha256': 'ae452dd47d228b7966fadbad8fb8a1a0feb5776d5b7159c6ec23fc6cf62678b4',
        'original_kinds': ('application', 'evidence'),
    },
}
ZHANGZHOU_FUNCTIONAL_REGIONS = {
    '350692': {
        'district': '漳州台商投资区',
        'source_id': 'ba43712a330a421eb5306aed',
        'source_manifest_sha256': 'c657a98361f5d3e69af383ffe4a57afc401f5930c729a4227eda52d7e83a263d',
        'stage_sha256': '93f90f98f998f0e006be5f6b8374ae519d29dd0c9cee46b4e7a07d91f845ce1e',
        'source_freeze_sha256': 'e6ba624ca27e3d9b04ff7a9efeb72b4d37a198eeb1b591fa8a26cb5e731f20d7',
        'original_kinds': ('application', 'evidence'),
    },
}
NINGDE_FIRST_FOUR_REGIONS = {
    '350902': {
        'district': '蕉城区',
        'source_id': '0b4a45eb9c9f0624c92bc3dc',
        'source_manifest_sha256': '2612dfc3a4102f564e2cdbe167021ed4e3319804f9a244f8464eca81622bc79c',
        'stage_sha256': '3471e2b92c2b08ffae8d8a415f7f4ecf2da778d19e926c1a637763370222efc1',
        'source_freeze_sha256': '3ebafabde5fd5b0c028fd5d08acec6d2115a2e1ab67ed4787521a301dbd9e891',
        'original_kinds': ('application', 'evidence'),
    },
    '350981': {
        'district': '福安市',
        'source_id': 'aa1e6889629caa4ec08b894b',
        'source_manifest_sha256': 'ff0afc8c38f5fa8dc26f9ad2212a60c5d3f58189b138e93a51510811d90dfd0e',
        'stage_sha256': '52d198f7f88dfe163f72960847fd3120bacbe95d674d2fadbeca436b529619d0',
        'source_freeze_sha256': 'eeca8b347aff17826dd5e41c3a1413ef6cc2fa2bbde283de4ff93e9a7bf835e7',
        'original_kinds': ('application', 'evidence'),
    },
    '350982': {
        'district': '福鼎市',
        'source_id': '837907d624340a4f4b36ea71',
        'source_manifest_sha256': '3a6e28b0cfd9d5b4939720e230e2252b34884e5ac764d2bbd4b4823b382ab3f9',
        'stage_sha256': 'b7598093c667578a5dcdcc64b09d46482657173f2dad0f0b077c7a4fd76facfc',
        'source_freeze_sha256': 'bd6bdb9d9f33b6543e21d3c6ac864c0bc49e86c3cef99c231facf3825e9d4832',
        'original_kinds': ('application', 'evidence'),
    },
    '350921': {
        'district': '霞浦县',
        'source_id': 'ae035da9c2109496258da1f7',
        'source_manifest_sha256': 'da32d388bf65ec1a2c8b275647c99afcc706a88fe4443d63927fe7fd59442e6d',
        'stage_sha256': '81a6c4ec9e272fc26e20f3e7c18a54f099042780d586091b66f84adc13fce7ce',
        'source_freeze_sha256': '150f9120579de439fba621443ed80475e29e5541989ac7b0426469eb1288ce20',
        'original_kinds': ('application', 'evidence'),
    },
}
NINGDE_NEXT_FIVE_REGIONS = {
    '350922': {
        'district': '古田县',
        'source_id': 'b001fa88aecf2dca266120e3',
        'source_manifest_sha256': 'd72a825eb8cac6f049ca64b76fe6ff824a222325fecfea5bfa6b58d7e3cab65f',
        'stage_sha256': '0df6539ef36e89415a08bbd83c46b7960bb3be7f6a55992a676ced7b9012bdd4',
        'source_freeze_sha256': '654c253c357d5831c0ee5f1f241f28e9ca2bb075b7e3406ca9d9103738663f60',
        'original_kinds': ('application', 'evidence'),
    },
    '350923': {
        'district': '屏南县',
        'source_id': '272f1398c7c84fdbcb241d55',
        'source_manifest_sha256': '4cca508c10e685dcc0cc2db5167450f1313a8d354036fc135e73c43119486dbc',
        'stage_sha256': '29ad304cfafd8fd6b5d9118edc619aafe448a7cf55b3572f89f5c2c92bc2f714',
        'source_freeze_sha256': 'ef4ec2ed6a916fe56893392d795645bb328472da482be357f457915441666b36',
        'original_kinds': ('application', 'evidence'),
    },
    '350924': {
        'district': '寿宁县',
        'source_id': '1ebfe0ec7e5a13953ed7b26c',
        'source_manifest_sha256': '1846eddaab2674891da8eca114cc28d45e952f1d7e641d7de0d2f6a009d23285',
        'stage_sha256': '7254cb23f1b02d25c948e7e28f6f79357f092b4510ce10d3e05ce978b60f85a3',
        'source_freeze_sha256': '0faa9c4dbb404e725cc2151c62657329bdd4ef83730cf9b0451bda5c1f69705f',
        'original_kinds': ('application', 'evidence'),
    },
    '350925': {
        'district': '周宁县',
        'source_id': '93c89d232bac720d254d951b',
        'source_manifest_sha256': '2925904df42021fa7392b580b9d02d8d7193ff5daca4ee87985c1bf64ddb537b',
        'stage_sha256': '6b5e5748743a019e561f973357c5a47a4f66808f4bb1689fc3df931576d78f1b',
        'source_freeze_sha256': 'd0bd63762ebcf63a9673cfa2534b8b6114f3416b7c0927d2821fa5e273ccb055',
        'original_kinds': ('application', 'evidence'),
    },
    '350926': {
        'district': '柘荣县',
        'source_id': 'b5dede071093f619366f7212',
        'source_manifest_sha256': 'cb08426c5bebc559997940c644845c5a29b06c3fd0c60b69d601570a5a3bc04f',
        'stage_sha256': '4b18509c3bdb457cf18beb5fc7a0385d48939692eb41ee0db3094191db39d659',
        'source_freeze_sha256': 'b314421df6a6149a01d21dd57d314c799f99d09817bc458b7974005404121dcc',
        'original_kinds': ('application', 'evidence'),
    },
}
NANPING_FIRST_THREE_REGIONS = {
    '350702': {
        'district': '延平区',
        'source_id': 'f780a2e27a9ef10965a9a398',
        'source_manifest_sha256': '3a8fe2101325254e0ab8814a29af66da9653780d3baa7e3b8273c51de2e18bd2',
        'stage_sha256': '916a9546e5f002df95230f9f4c0c9d77dac5100ece08fd6e812712e59aec2af1',
        'source_freeze_sha256': '31f64e7721db5d72a3d76bfc00b092af66bebe83e1e0ad5969c537788e954533',
        'original_kinds': ('application', 'evidence'),
    },
    '350781': {
        'district': '邵武市',
        'source_id': '7b2e6d218619d6a4b7dd3b18',
        'source_manifest_sha256': 'cb5892f69d77ab6342a21a912b5c342d94cd7a17c9df75c2fc14332f4fbffe6a',
        'stage_sha256': 'df8da4be4b0e3810d806c75ed1dded5afa50a8369abb21db9e47fb93b4e0f506',
        'source_freeze_sha256': 'ab55f43962ea9eb31ec031e19fadb6abbffce9219fec0b59acf0839e63be0498',
        'original_kinds': ('application', 'evidence'),
    },
    '350782': {
        'district': '武夷山市',
        'source_id': 'f07923c1454cce539678a805',
        'source_manifest_sha256': '19b7ea84bc6d1c272ae491705a87f22657b43e65729ef57b79d01ac1a60b95e1',
        'stage_sha256': '05f003dcb37e74c7edc31483c1a57aea9fb9cc1f95ddd1dc743fdf90901fb70c',
        'source_freeze_sha256': '3d7607fa39c8e0623aa72d47d707e5901ef37b5f899c7066dcef0edcb7c0b857',
        'original_kinds': ('application', 'evidence'),
    },
}
NANPING_NEXT_FOUR_REGIONS = {
    '350783': {
        'district': '建瓯市',
        'source_id': 'db760e316b1f5abf85a0e791',
        'source_manifest_sha256': 'c4ca52093ae26b8bcdf5a1e467bb116acf2b23b92af5ebccf77ec8514fc55065',
        'stage_sha256': '649fd6d87c792818da4b702d5532d4ce0974314a45e40f566f818d1ce1e5f120',
        'source_freeze_sha256': '81ab760097600566c2d6dc6dd28e603573849db708aef83fec45a906219c3337',
        'original_kinds': ('application', 'evidence'),
    },
    '350721': {
        'district': '顺昌县',
        'source_id': '04c84b5c09ac6325710f35ee',
        'source_manifest_sha256': '7c5d5269bcb3a21b776b1a3639e7853e518a1ee0ea1f5636640596431d038149',
        'stage_sha256': '702d240478f5baf94c40b99f21ce022d4ae873ee6f7bfeec3a5988e8f387a656',
        'source_freeze_sha256': 'a2d3d6a5e10e459c93bfdaa2bc00b6ee6b1f3543731af989dc77bd6b1e75c5d9',
        'original_kinds': ('application', 'evidence'),
    },
    '350723': {
        'district': '光泽县',
        'source_id': '012ffa540bf8300a303b0b8a',
        'source_manifest_sha256': 'e82a712e2b512ef21e4a5de3f9bb9bacfc425dc97b8b40ffaf8945be6e09ba2d',
        'stage_sha256': '0a4d74968728d583f4b2b9cfaa3c2b0b368155e6cf39062984f66b8592b8c28a',
        'source_freeze_sha256': 'f324705bc793bc1813d7a12e5de3736398915039590d038a18371041fe5ff535',
        'original_kinds': ('application', 'evidence'),
    },
    '350724': {
        'district': '松溪县',
        'source_id': '5367845e0fb0ae0340bfeb3a',
        'source_manifest_sha256': '147248df85a42120b7a90af9bb6b6652205e6038071377bab1da9f66299c502b',
        'stage_sha256': 'a33494cae9a98464633abb76dece183895e6c88afcd83710d7ef10016b0c172b',
        'source_freeze_sha256': 'c4b748817a0179c41a72462fdfb3828932c3431a07857f524f42c924a4698131',
        'original_kinds': ('application', 'evidence'),
    },
}
NANPING_APPLICATION_ONLY_REGIONS = {
    '350722': {
        'district': '浦城县',
        'source_id': 'a5f6eb9afcdba92231eccec3',
        'source_manifest_sha256': 'c67a884ab39a3567ac59a367956016005f7d7d23ab29c73b8415857b92629ffc',
        'stage_sha256': 'd2525bd268748321552e41756e95480bae05e41c8aebed27eddbc685910bfc3d',
        'source_freeze_sha256': '9b998011fcded9622fdabbfc07aa4436b4b0b857d73958850bbca7f47c7771af',
        'original_kinds': ('application',),
    },
    '350725': {
        'district': '政和县',
        'source_id': '8cbb28e92dec4b9e84175e26',
        'source_manifest_sha256': '7933966b1ba6e4315aa7dfbb556827aeba69f6c6146d1f33e51d5b5348f0b07e',
        'stage_sha256': 'e7b5d8c1169d57d971d13f818347d390ad5bed38d49e878e72d9a09550dea502',
        'source_freeze_sha256': '0d268279a2ced36a4d00af13dab4a549b7684252b5cd970e054462b922e6d2ee',
        'original_kinds': ('application',),
    },
}
NANPING_JIANYANG_REGIONS = {
    '350703': {
        'district': '建阳区',
        'source_id': '27b3bacad17d7069dfd7ff81',
        'source_manifest_sha256': 'c0d126eca85333839449c7ae1957a6d7b3d1a20eb2ee10eadfd3e9a9c5a80d83',
        'stage_sha256': '4ccbbab194c4fd4ebe441548a212795d6704ac442809cdeeea8ffeab44ddb839',
        'source_freeze_sha256': '9de3f84b2a725458f0c94019b55128fa150025971475cb0bfe226fa8aa6e8096',
        'original_kinds': ('application', 'evidence'),
    },
}
LONGYAN_FIRST_TWO_REGIONS = {
    '350802': {
        'district': '新罗区',
        'source_id': 'fdc6a88b3a22440ff0b7c40f',
        'source_manifest_sha256': 'faf214ad5a505bf5d6be8d65e544db55fb9b9a4a999fb00ff7acaf7a2665e58a',
        'stage_sha256': '51d343114fbf920ffcbabd2d3a8912179c857473ff479363ed789cdcd0b9e984',
        'source_freeze_sha256': '96edf353f6106eb36271b69adc9835f090786337a65792c8a27e8869258dcf22',
        'original_kinds': ('application', 'evidence'),
    },
    '350881': {
        'district': '漳平市',
        'source_id': '8ddc5833de93302535e84616',
        'source_manifest_sha256': '84b0bcb512748a2f60f8de3548366059de81b32abf0f4dd2aa39ab8f2ed44616',
        'stage_sha256': '58b8f7299f35dded945c5601dd7592f83ff16399b30d9be833f19b0efbefa0b4',
        'source_freeze_sha256': '1e3af4ae09f8b3b0e790a9deadfcfe6489b7424c7baf173aad363d4e301972cb',
        'original_kinds': ('application', 'evidence'),
    },
}
LONGYAN_NEXT_TWO_REGIONS = {
    '350803': {
        'district': '永定区',
        'source_id': '1e23aca032c08ea09d8de2e2',
        'source_manifest_sha256': 'aaf624f1e6ddaa91b58d5b50853fe9344882ba0ad3b1543d704e6fef123e337e',
        'stage_sha256': 'b27c8d43db9909cc1cd9549de39faa7089758d850af06a3288051df8861f9488',
        'source_freeze_sha256': 'fc73c14411257140d70eda4e16427145942fe9b0050ecff83d0fc9d1fc68dd76',
        'original_kinds': ('application', 'evidence'),
    },
    '350821': {
        'district': '长汀县',
        'source_id': 'd74f09e4c5b1c5c09225add6',
        'source_manifest_sha256': '049e3655e0b88c3fe66fbf5dd309c14baf80f93705f6255729feff84447acd45',
        'stage_sha256': '3a07079ce52e8f4779e9c72ef5781677d017dd5a5eeb6f419c91c9e2728d489a',
        'source_freeze_sha256': '408608a67e50eea744e0b5f9352d96148393205edb70c8b3198dff65a34e7551',
        'original_kinds': ('application', 'evidence'),
    },
}
LONGYAN_NEXT_THREE_REGIONS = {
    '350823': {
        'district': '上杭县',
        'source_id': '7c8b83a0120243ba4bf74d4a',
        'source_manifest_sha256': '4f90e0f66d5fd28b0f5d9db9d33264df0d48c371fdfd35ecb1f4639224429527',
        'stage_sha256': '20f2b6d58763d1b7a57884f3eeea10b28b9ecedc0360de47b22ada17c11305e1',
        'source_freeze_sha256': '7657a3921be47c32a6b24aaa145ccb62f9c59e16b897ffcf4cd192cb9845dbb3',
        'original_kinds': ('application', 'evidence'),
    },
    '350824': {
        'district': '武平县',
        'source_id': 'e83e81785d88fec226301f13',
        'source_manifest_sha256': 'e1a5bbb57a5038f572b4bfbf7ac554961f2f190080a12ce22b0f36fbb4c415a3',
        'stage_sha256': 'f357ad762fda13414b7597c8eae03e65f85624ade56be0f8c26a2028668f49cf',
        'source_freeze_sha256': '1b6faaec185eee432e7f4b960445f9e12095ebdf3e25efb3a90d2ea9006dd97d',
        'original_kinds': ('application', 'evidence'),
    },
    '350825': {
        'district': '连城县',
        'source_id': '9d72686d21ca8390335e0261',
        'source_manifest_sha256': 'ab56b74e06274ec4abfea00f5305c91910fe3c66cb71317757db829b3696b372',
        'stage_sha256': '23a54480f1218ca3bb35f9091a5d2bbc239b33f93f5ddc3793a6ba2345e47349',
        'source_freeze_sha256': 'a267803f3ab1f7a87a9ec06301a706bdd2a635e031d292fa83ddaead569922b6',
        'original_kinds': ('application', 'evidence'),
    },
}
FUJIAN_MUNICIPAL_SELECTION = "市本级"
FUJIAN_MUNICIPAL_REGIONS = {
    '350400': {
        'district': '',
        'city': '三明市',
        'source_base': LOCALITIES + '/sanming-municipal-own-source',
        'source_id': 'da959113b9c50e887043f638',
        'source_manifest_sha256': 'c796921f5893dcce538f51a44393332cdb8b2e95f426a0476ea965dad9e03390',
        'stage_sha256': 'fc29ca02fbe3ab6888acc6463bd046a500564397d5b6749e0203ca8fbf716b48',
        'source_freeze_sha256': '8d685d5c892e93e1e4061b9a08bb3957591e28bbb73103f6cc0337797d4e535d',
        'original_kinds': ('application',),
    },
    '350900': {
        'district': '',
        'city': '宁德市',
        'source_base': LOCALITIES + '/ningde-municipal-own-source',
        'source_id': '015fbbb3a4bf80fcb5d8d065',
        'source_manifest_sha256': '7acf19fe027acd5e93e93e5e21e65c0802527758b1e9dcf90c4364434a6d9a2a',
        'stage_sha256': '137e000ee2dc8b2d1699556f719e661434ece3f596167f8ec4c5363b17580af0',
        'source_freeze_sha256': '3b16c0caeb5f6a23afdd2a9af26654f15630278f2e4c662e1c1ec81ebca2d55f',
        'original_kinds': ('application', 'evidence'),
    },
    '350700': {
        'district': '',
        'city': '南平市',
        'source_base': LOCALITIES + '/nanping-municipal-own-source',
        'source_id': 'f94ef9ec2ad2020932331f5a',
        'source_manifest_sha256': '706c1574ab63bbe59b2e3fd320a8fdab0191d2864fd5411a953f18bdee11ef8f',
        'stage_sha256': '34a1dfb349b2a3a674b9c454814e3ec8904797cb88c58affa6ae12e51e0b088e',
        'source_freeze_sha256': 'e4dfe82e68f06d0affb5627e479325a585d3d0101d7f616430043c4917b68168',
        'original_kinds': ('application', 'evidence'),
    },
    '350800': {
        'district': '',
        'city': '龙岩市',
        'source_base': LOCALITIES + '/longyan-municipal-own-source',
        'source_id': 'eeda6db9dc8414446292f9c0',
        'source_manifest_sha256': '79c90f32395f126733067e274ece79bb06f00704144fd402543c356e4e82e317',
        'stage_sha256': 'dbcfff4e014aecf15227ad85f6ea006e76bee5a927b95ca73adf02d7a43a0c61',
        'source_freeze_sha256': '69975e91bd9ab99106ef619f0ca73a7cbe1bd92b6c2078d2287ba691adcacc45',
        'original_kinds': ('application', 'evidence'),
    },
}
SANMING_YOUXI_REGIONS = {
    '350426': {
        'district': '尤溪县',
        'city': '三明市',
        'source_base': LOCALITIES + '/sanming-youxi-own-source',
        'source_id': 'c4a1025ea6a8038fcb55baa3',
        'source_manifest_sha256': '2ef0c5c3cec90a841d088dea938e4addb098852b97f9bcaefaaf9b6c18fe4227',
        'stage_sha256': 'c7a60a4f2d9fad5ea7ba8cc5bba75d359c08f911e0a94812b0bb9f0d56489b69',
        'source_freeze_sha256': '9dd7b343fe02951a902afae25bb403f6df9bcf8440e01fa68c70349a9e6a8f9e',
        'original_kinds': ('application', 'evidence'),
    },
}
SANMING_NEXT_THREE_REGIONS = {
    '350424': {
        'district': '宁化县',
        'city': '三明市',
        'source_id': '2e7221316b15f1d1b0fcf034',
        'source_manifest_sha256': 'c9ce260340747c75b7271f069088c27a4a912609e971d340af03325c318d408a',
        'stage_sha256': '9b0b48ddd2f95683d4124777232099ce0141db3ce26b05a4e760237b568f09ab',
        'source_freeze_sha256': '73b79b5b214be8a1e0284a5cfbf4e394a23e72da9a03630b60a3510d19cd3462',
        'original_kinds': ('application', 'evidence'),
    },
    '350421': {
        'district': '明溪县',
        'city': '三明市',
        'source_id': '0344451e5d72c7ff36543fe9',
        'source_manifest_sha256': 'a49fbaba629c04954b07d1ea4923b03ba2269f16ca6e98183266c4609300f403',
        'stage_sha256': '6f2f8adbfa4f4501690551ef71929a32c8f6292eb9a0b777df02a0bfbddab60d',
        'source_freeze_sha256': '50d4997ea73149f8de879ee85509db8f8092f5a28fe2dd0f7fd4d28abcf74538',
        'original_kinds': ('application', 'evidence'),
    },
    '350428': {
        'district': '将乐县',
        'city': '三明市',
        'source_id': '23bd108d76ca3647bfc597c8',
        'source_manifest_sha256': 'b8978e2977dfe8b8ff88fa3e76a341de64444110620140902dce04c389a041b9',
        'stage_sha256': 'a81e6f81e7f32c2075934fcb7cdaff79263d0c0aa3484403d348d00b2883552f',
        'source_freeze_sha256': '16b18ed72ecf56329fcc8eec6c80363ee92aee6d99d987e1b3437f633da7d706',
        'original_kinds': ('application', 'evidence'),
    },
}
SANMING_QINGLIU_REGIONS = {
    '350423': {
        'district': '清流县',
        'city': '三明市',
        'source_base': LOCALITIES + '/sanming-qingliu-own-source',
        'source_id': 'e1fcf92db221a6feebb6a287',
        'source_manifest_sha256': '28be1c6fcf51bb3688f57ab5354eefbeac604b4eae5186a1805951587d1a5ab6',
        'stage_sha256': '1a6e0d77e77440b6725d0dc9e3495ffef5b24807b4d6760fdb8a5b4dac0f4167',
        'source_freeze_sha256': 'fedb0e57a60ffe9f7bae07a3110dc8b5ba3ce4daf1060191d10bab452c9b695f',
        'original_kinds': ('application',),
    },
}
SUPPORTED_REGIONS = {
    **REGIONS,
    **DY_REGIONS,
    **ZHANGZHOU_FOUR_REGIONS,
    **ZHANGZHOU_NEXT_FOUR_REGIONS,
    **ZHANGZHOU_FUNCTIONAL_REGIONS,
    **NINGDE_FIRST_FOUR_REGIONS,
    **NINGDE_NEXT_FIVE_REGIONS,
    **NANPING_FIRST_THREE_REGIONS,
    **NANPING_NEXT_FOUR_REGIONS,
    **NANPING_APPLICATION_ONLY_REGIONS,
    **NANPING_JIANYANG_REGIONS,
    **LONGYAN_FIRST_TWO_REGIONS,
    **LONGYAN_NEXT_TWO_REGIONS,
    **LONGYAN_NEXT_THREE_REGIONS,
    **FUJIAN_MUNICIPAL_REGIONS,
    **SANMING_YOUXI_REGIONS,
    **SANMING_NEXT_THREE_REGIONS,
    **SANMING_QINGLIU_REGIONS,
    INVESTMENT_CODE: {
        'district': '台商投资区', 'source_id': 'cf089c0b9ee9b764b564e269',
        'source_manifest_sha256': '297b56b936b8c43d5598c4fc115c26b881936d21fcd3da08722523ca74319fc2',
        'original_kinds': ('application', 'evidence'),
    },
    XIANGCHENG_CODE: {
        'district': '芗城区', 'source_id': 'f8e8351e86b1c41530f16dec',
        'source_manifest_sha256': 'f00f84d5e6ed1a90e7d064760966c36735950d2e734c2fa6493db2186956ab41',
        'original_kinds': ('application', 'evidence'),
    },
    LONGHAI_CODE: {
        'district': '龙海区', 'source_id': 'ed191bcdf82538767ff7bc25',
        'source_manifest_sha256': '60cb15eedb5f3d3fa70c2cd38037c93ab972e3866f530cf9fb65f6c6251bdafc',
        'original_kinds': ('application', 'evidence'),
    },
}
_CANDIDATE_PREFLIGHTS = {
    **{
        code: (
            profile['source_base'], f"{profile['source_base']}/{code}/WORD-PREFLIGHT.json",
            profile['stage_sha256'], profile['source_freeze_sha256'],
        )
        for code, profile in FUJIAN_MUNICIPAL_REGIONS.items()
    },
    INVESTMENT_CODE: (INVESTMENT_BASE, INVESTMENT_STAGE_RECEIPT, INVESTMENT_STAGE_SHA256, INVESTMENT_SOURCE_FREEZE_SHA256),
    XIANGCHENG_CODE: (XIANGCHENG_BASE, XIANGCHENG_STAGE_RECEIPT, XIANGCHENG_STAGE_SHA256, XIANGCHENG_SOURCE_FREEZE_SHA256),
    LONGHAI_CODE: (LONGHAI_BASE, LONGHAI_STAGE_RECEIPT, LONGHAI_STAGE_SHA256, LONGHAI_SOURCE_FREEZE_SHA256),
    **{
        code: (
            base, f'{base}/{code}/WORD-PREFLIGHT.json',
            profile['stage_sha256'], profile['source_freeze_sha256'],
        )
        for base, regions in (
            (ZHANGZHOU_FOUR_BASE, ZHANGZHOU_FOUR_REGIONS),
            (ZHANGZHOU_NEXT_FOUR_BASE, ZHANGZHOU_NEXT_FOUR_REGIONS),
            (ZHANGZHOU_FUNCTIONAL_BASE, ZHANGZHOU_FUNCTIONAL_REGIONS),
            (NINGDE_FIRST_FOUR_BASE, NINGDE_FIRST_FOUR_REGIONS),
            (NINGDE_NEXT_FIVE_BASE, NINGDE_NEXT_FIVE_REGIONS),
            (NANPING_FIRST_THREE_BASE, NANPING_FIRST_THREE_REGIONS),
            (NANPING_NEXT_FOUR_BASE, NANPING_NEXT_FOUR_REGIONS),
            (NANPING_APPLICATION_ONLY_BASE, NANPING_APPLICATION_ONLY_REGIONS),
            (NANPING_JIANYANG_BASE, NANPING_JIANYANG_REGIONS),
            (LONGYAN_FIRST_TWO_BASE, LONGYAN_FIRST_TWO_REGIONS),
            (LONGYAN_NEXT_TWO_BASE, LONGYAN_NEXT_TWO_REGIONS),
            (LONGYAN_NEXT_THREE_BASE, LONGYAN_NEXT_THREE_REGIONS),
            (LOCALITIES + '/sanming-youxi-own-source', SANMING_YOUXI_REGIONS),
            (SANMING_NEXT_THREE_BASE, SANMING_NEXT_THREE_REGIONS),
            (LOCALITIES + '/sanming-qingliu-own-source', SANMING_QINGLIU_REGIONS),
        )
        for code, profile in regions.items()
    },
}
_MODELS = {'application': Application, 'evidence': Evidence}
_FAILURES = (ValueError, OSError, TypeError, KeyError)


def _require(condition):
    if not condition:
        raise ValueError('本区指南或候选文书证明不匹配')


def _read(root, name):
    _require(isinstance(root, (str, Path)) and str(root).strip())
    base = Path(root).absolute()
    relative = PurePosixPath(name)
    _require(name.startswith(LOCALITIES + '/') and relative.as_posix() == name
             and not relative.is_absolute() and '\\' not in name and ':' not in name
             and all(not part.startswith('.') for part in relative.parts))
    path = base / name
    _require(path.is_file() and path.resolve() == path)
    for entry in (path, *path.parents):
        _require(not entry.is_symlink() and not getattr(entry.lstat(), 'st_file_attributes', 0)
                 & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
    return path.read_bytes()


def _source_folder(code):
    _require(type(code) is str and code in SUPPORTED_REGIONS)
    if code in _CANDIDATE_PREFLIGHTS:
        base, *_ = _CANDIDATE_PREFLIGHTS[code]
        return f'{base}/{code}'
    return f'{DY_BASE if code in DY_REGIONS else BASE}/{code}'


def _manifest_path(code):
    return f'{_source_folder(code)}/SOURCE-PROJECTION-MANIFEST.json'


def production_source(code, *, root):
    folder = _source_folder(code)
    profile = SUPPORTED_REGIONS[code]
    manifest_raw = _read(root, _manifest_path(code))
    version = profile['source_manifest_sha256']
    _require(sha256(manifest_raw).hexdigest() == version)
    manifest = strict_json(manifest_raw)
    _require(manifest['region_code'] == code and manifest['source_id'] == profile['source_id'])
    files = {}
    for name, pin in manifest['files'].items():
        raw = _read(root, f'{folder}/{name}')
        _require(len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256'])
        files[name] = raw
    guide = strict_json(files['guide.json'])
    _require(guide['region_code'] == code and guide['district'] == profile['district']
             and guide['source_id'] == profile['source_id']
             and guide['source_id'] == digest(guide['source_url'])[:24]
             and guide['source_url'] == manifest['source_url']
             and guide['published'] is False and guide['can_generate'] is False)
    if code in FUJIAN_MUNICIPAL_REGIONS:
        service = strict_json(files['safe-api-getMatterBasicInfo.json'])['data']['apasService']
        _require(guide['scope_level'] == 'municipal'
                 and guide['city'] == guide['official_area_name'] == profile['city']
                 and service['areacode'] == code and service['areaname'] == profile['city'])
        # Existing region contracts use three strings. This explicit choice is a
        # routing value, while the captured district stays empty for a city-level source.
        guide['district'] = FUJIAN_MUNICIPAL_SELECTION
    guide.update(source_version=version, online_entry=None)
    guide['sections'] = {
        'apply_method_raw': strict_json(files['safe-api-getMatterBasicInfo.json'])['data']['applyMethod'],
        'flow_nodes_raw': strict_json(files['safe-api-getFlowNode.json'])['data'],
        'legal_basis_raw': strict_json(files['safe-api-getLegalBasis.json'])['data'],
        'matter_according_raw': strict_json(files['safe-api-getMatterAccording.json'])['data'],
    }
    for field in guide['fields'].values():
        field['source_version'] = version
    for material in guide['materials']:
        material.update(id=material['material_id'], official_material_id=material['material_id'])
    for template in guide['templates']:
        eligible = template['source_original_eligible'] is True
        template.update(region_code=code, original_name=template['official_label'],
                        local_original=template['file'],
                        download_status='downloaded' if eligible else 'not_downloaded')
        if eligible:
            kind = template['eligible_own_kind']
            filename = f'{kind}-format-public-retrieval.docx'
            _require(template['file'] == f'{folder}/{filename}'
                     and sha256(files[filename]).hexdigest() == template['sha256'])
            template['official_kind'] = 'blank'
    _require(sorted(t['eligible_own_kind'] for t in guide['templates'] if t['source_original_eligible'])
             == sorted(profile['original_kinds']))
    guide['channel'].update(raw_value=guide['channel']['handling_form_raw'],
                            online_depth_raw=guide['channel']['depth_raw'],
                            online_status='unverified', entry_check={'status': 'unvisited'})
    return guide


def staged_candidate(code, *, root):
    guide, _ = _staged_guide(code, root=root)
    return guide


def _staged_guide(code, *, root):
    guide = production_source(code, root=root)
    if code in DY_REGIONS:
        return _word_preflight_guide(
            guide, DY_STAGE_RECEIPT, DY_STAGE_SHA256, DY_SOURCE_FREEZE_SHA256, 12, root=root,
        )
    if code in _CANDIDATE_PREFLIGHTS:
        _, receipt, stage_sha, source_sha = _CANDIDATE_PREFLIGHTS[code]
        case_count = 3 * len(SUPPORTED_REGIONS[code]['original_kinds'])
        return _word_preflight_guide(guide, receipt, stage_sha, source_sha, case_count, root=root)
    raw = _read(root, REVIEW_RECEIPT)
    _require(sha256(raw).hexdigest() == STAGE_SHA256)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'OFFLINE_PARITY_VERIFIED_REGISTRATION_PENDING'
             and receipt['published'] is False and len(receipt['records']) == 21)
    verified_forms = []
    for template in guide['templates']:
        if not template['source_original_eligible']:
            continue
        kind = template['eligible_own_kind']
        matching = [
            row for row in receipt['records']
            if row['source']['region_code'] == code and row['source']['kind'] == kind
        ]
        _require(len(matching) == 3 and {r['case'] for r in matching} == {'original', 'normal', 'stress'})
        for row in matching:
            binding = row['source']
            _require(binding['source_id'] == guide['source_id']
                     and binding['source_version'] == guide['source_version']
                     and binding['template_sha256'] == template['sha256']
                     and binding['attachment_id'] == template['id']
                     and binding['material_id'] == template['material_id']
                     and binding['public_file_unid'] == template['public_file_unid'])
        template.update(can_generate=True, adapter=ADAPTER, document_types=[kind], generation_mode='blank')
        verified_forms.append({'region_code': code, 'kind': kind, 'source_id': guide['source_id'],
                               'template_id': template['id'], 'sha256': {row['case']: row['sha256'] for row in matching}})
    _mark_candidate(guide, REVIEW_RECEIPT, STAGE_SHA256, STAGE_VERIFIED_AT)
    return guide, verified_forms


def _mark_candidate(guide, receipt, pin, verified_at):
    guide.update(registration_status='CANDIDATE_ONLY', can_generate=True, generation_adapter=ADAPTER,
                 verified_at=verified_at, publication_status='candidate',
                 candidate_adapter_evidence={'file': receipt, 'sha256': pin})


def _word_preflight_guide(guide, receipt_path, receipt_sha, source_freeze_sha, case_count, *, root):
    raw = _read(root, receipt_path)
    _require(sha256(raw).hexdigest() == receipt_sha)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'OWN_ORIGINALS_AND_TEST_LAYOUTS_BYTE_EQUIVALENT'
             and receipt['source_freeze_sha256'] == source_freeze_sha
             and receipt['published'] is False and receipt['adapter_registered'] is False
             and receipt['web_accepted'] is False and len(receipt['records']) == case_count)
    forms = []
    for template in guide['templates']:
        if not template['source_original_eligible']:
            continue
        kind = template['eligible_own_kind']
        matches = [row for row in receipt['records']
                   if row['region_code'] == guide['region_code'] and row['kind'] == kind]
        _require(len(matches) == 3 and {row['case'] for row in matches} == {'original', 'normal', 'stress'})
        _require(all(row['source_id'] == guide['source_id'] and row['attachment_id'] == template['id']
                     and row['template_sha256'] == template['sha256'] for row in matches))
        _require(next(row['sha256'] for row in matches if row['case'] == 'original') == template['sha256'])
        template.update(can_generate=True, adapter=ADAPTER, document_types=[kind], generation_mode='blank')
        forms.append({'region_code': guide['region_code'], 'kind': kind, 'source_id': guide['source_id'],
                      'template_id': template['id'], 'sha256': {row['case']: row['sha256'] for row in matches}})
    _mark_candidate(guide, receipt_path, receipt_sha, receipt['verified_at'])
    return guide, forms


def published_guide(code, *, root):
    _require(type(code) is str and (code in REGIONS or code in DY_REGIONS))
    if code in DY_REGIONS:
        return _dy_published_guide(code, root=root)
    _require(PUBLICATION_SHA256 is not None)
    raw = _read(root, PUBLICATION_RECEIPT)
    _require(sha256(raw).hexdigest() == PUBLICATION_SHA256)
    _require(sha256(_read(root, BROWSER_RECEIPT)).hexdigest() == BROWSER_SHA256)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'INDEPENDENT_NATIVE_AND_WORD_PARITY_APPROVED'
             and receipt['schema_version'] == 1 and receipt['stage_sha256'] == STAGE_SHA256
             and receipt['browser_sha256'] == BROWSER_SHA256
             and receipt['source_manifests'] == {c: p['source_manifest_sha256'] for c, p in REGIONS.items()}
             and receipt['browser_downloads'] == 14 and receipt['word_cases'] == 21
             and receipt['viewports'] == 21 and receipt['cancellations'] == 7
             and receipt['stone_evidence_enabled'] is False and len(receipt['forms']) == 7)
    return _promote_reviewed(code, receipt, PUBLICATION_RECEIPT, PUBLICATION_SHA256, root=root)


def _dy_published_guide(code, *, root):
    _require(DY_PUBLICATION_SHA256 is not None)
    raw = _read(root, DY_PUBLICATION_RECEIPT)
    _require(sha256(raw).hexdigest() == DY_PUBLICATION_SHA256)
    _require(sha256(_read(root, DY_BROWSER_RECEIPT)).hexdigest() == DY_BROWSER_SHA256)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'INDEPENDENT_NATIVE_AND_WORD_PARITY_APPROVED'
             and receipt['schema_version'] == 1 and receipt['stage_sha256'] == DY_STAGE_SHA256
             and receipt['browser_sha256'] == DY_BROWSER_SHA256
             and receipt['source_manifests'] == {c: p['source_manifest_sha256'] for c, p in DY_REGIONS.items()}
             and receipt['browser_downloads'] == 8 and receipt['word_cases'] == 12
             and receipt['viewports'] == 12 and receipt['cancellations'] == 4 and len(receipt['forms']) == 4)
    return _promote_reviewed(code, receipt, DY_PUBLICATION_RECEIPT, DY_PUBLICATION_SHA256, root=root)


def _promote_reviewed(code, receipt, file, pin, *, root):
    guide, verified_forms = _staged_guide(code, root=root)
    approved_forms = [form for form in receipt['forms'] if form['region_code'] == code]
    _require(exact(sorted(approved_forms, key=lambda form: form['kind']),
                   sorted(verified_forms, key=lambda form: form['kind'])))
    guide.update(published=True, publication_status='published', registration_status='OWN_FORM_APPROVED',
                 verified_at=receipt['reviewed_at'],
                 publication_adapter_evidence={'file': file, 'sha256': pin})
    return guide


def _evidence(code):
    return {'source_projection': _manifest_path(code),
            'source_projection_sha256': SUPPORTED_REGIONS[code]['source_manifest_sha256']}


def _bound(guide, *, root, stage_required):
    _require(type(guide) is dict)
    code = guide.get('region_code')
    if stage_required:
        _require(guide.get('can_generate') is True)
    if guide.get('published') is True:
        canonical = published_guide(code, root=root)
    elif guide.get('can_generate') is True:
        canonical = staged_candidate(code, root=root)
    else:
        canonical = production_source(code, root=root)
    data = {k: v for k, v in guide.items() if k not in {'version', 'region_id', 'content_hash', 'evidence'}}
    _require(exact(data, canonical))
    if 'version' in guide:
        _require(type(guide['version']) is int and guide['version'] > 0)
    if 'region_id' in guide:
        _require(guide['region_id'] == region_key(canonical['province'], canonical['city'], canonical['district']))
    if 'content_hash' in guide:
        _require(guide['content_hash'] == digest(official_content(canonical)))
    if 'evidence' in guide:
        _require(exact(guide['evidence'], _evidence(code)))
    return canonical


def with_capabilities(guide, *, root):
    _bound(guide, root=root, stage_required=False)
    return guide


def public_evidence(guide, root):
    try:
        canonical = _bound(guide, root=root, stage_required=False)
        return _evidence(canonical['region_code'])
    except _FAILURES:
        return None


def approved_report_attachment(guide, template, root):
    try:
        canonical = _bound(guide, root=root, stage_required=False)
        return any(t['source_original_eligible'] and exact(t, template) for t in canonical['templates'])
    except _FAILURES:
        return False


def checked_adapter(guide, template, kind, *, root):
    canonical = _bound(guide, root=root, stage_required=True)
    _require(any(t['can_generate'] and t['eligible_own_kind'] == kind and exact(t, template)
                 for t in canonical['templates']))
    return ADAPTER


def production_schema_descriptor(code, kind):
    _require(type(code) is str and code in SUPPORTED_REGIONS and kind in SUPPORTED_REGIONS[code]['original_kinds'])
    # Only the independently verified geometry is shared across the official originals.
    labels = {
        'applicantName': '申请人', 'agentName': '委托代理人', 'respondentName': '被申请人',
        'requests': '仲裁请求', 'factsReason': '事实和理由', 'evidenceList': '证据清单',
        'name': '证据名称', 'pageCount': '页数', 'originalType': '原件或复印件',
        'purpose': '证明对象', 'pageRange': '页码',
    }
    fields = form_fields(kind)
    for field in fields:
        field['label'] = labels[field['key']]
        for column in field.get('fields', []):
            column['label'] = labels[column['key']]
    return {
        'schema_id': f'fujian-quanzhou-own-{code}-{kind}-v1',
        'schema_version': 1,
        'source_version': SUPPORTED_REGIONS[code]['source_manifest_sha256'],
        'fields': fields,
        'defaults': _MODELS[kind]().model_dump(),
        'policy': {
            'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
            'trim_text': True, 'capacity_is_official_requirement': False,
            'capacity_is_legal_requirement': False, 'committee_autofill_allowed': False,
            'signature_date_copies_fields': 'not_accepted',
        },
    }


def fill_document(guide, template, kind, path, data, *, root):
    checked_adapter(guide, template, kind, root=root)
    _require(Path(path).resolve() == (Path(root) / template['file']).resolve())
    raw = _read(root, template['file'])
    _require(sha256(raw).hexdigest() == template['sha256'])
    parsed = _MODELS[kind].model_validate(data, strict=True).model_dump()
    return _DocumentBytes(_layout_fill(raw, kind, parsed), root)
