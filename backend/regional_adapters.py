"""Audited, explicit locality bindings. Equal bytes never imply equal jurisdiction."""
from copy import deepcopy
from regional_guides import digest
from regional_blank_documents import blank_binding, ADAPTER as BLANK_ADAPTER
from regional_jiangsu_candidates import candidate_contract, SUPPORTED as JIANGSU_OWN_CANDIDATES
from regional_rongjiang_documents import rongjiang_source_matches, ADAPTER as RONGJIANG_ADAPTER
from regional_zhejiang_documents import with_zhejiang_capabilities,checked_zhejiang_adapter,ADAPTER as ZHEJIANG_ADAPTER
from regional_shangcheng_documents import with_shangcheng_capabilities,checked_shangcheng_adapter,ADAPTER as SHANGCHENG_ADAPTER
from regional_zhejiang_oct29 import (with_capabilities as with_ningbo_capabilities,
    blank_binding as ningbo_blank_binding,ADAPTER as NINGBO_ADAPTER,SPECS as NINGBO_SPECS)
from regional_oct29_bindings import (with_capabilities as with_oct29_capabilities,jiangsu_binding as oct29_jiangsu_binding,
    feidong_canonical,JIANGSU_ADAPTER as OCT29_JIANGSU_ADAPTER,FEIDONG_ADAPTER)
from regional_hunan_oct29b import (with_capabilities as with_hunan_capabilities,
    blank_binding as hunan_blank_binding, ADAPTER as HUNAN_ADAPTER, SPECS as HUNAN_SPECS)

from regional_hunan_oct29c import (with_capabilities as with_hunan_c_capabilities, blank_binding as hunan_c_binding, ADAPTER as HUNAN_C_ADAPTER, SPECS as HUNAN_C_SPECS)
from regional_jiangsu_oct29c import (with_capabilities as with_jiangsu_c_capabilities, blank_binding as jiangsu_c_contract, ADAPTER as JIANGSU_C_ADAPTER, SUPPORTED as JIANGSU_C_CODES)

def jiangsu_c_binding(guide,template):
    try:return jiangsu_c_contract(guide,template)['kind']
    except (ValueError,OSError,KeyError,TypeError):return None


from regional_jiangsu_oct29d import (with_capabilities as with_jiangsu_d_capabilities,blank_binding as jiangsu_d_contract,ADAPTER as JIANGSU_D_ADAPTER,SUPPORTED as JIANGSU_D_CODES)
from regional_zhejiang_oct29d import (with_capabilities as with_zhejiang_d_capabilities,blank_binding as zhejiang_d_binding,ADAPTER as ZHEJIANG_D_ADAPTER,SPECS as ZHEJIANG_D_SPECS)

def jiangsu_d_binding(guide,template,root=None):
    try:return jiangsu_d_contract(guide,template,root=root)['kind']
    except (ValueError,OSError,KeyError,TypeError):return None



from regional_jiangsu_oct29e import (with_capabilities as with_jiangsu_e_capabilities,blank_binding as jiangsu_e_contract,ADAPTER as JIANGSU_E_ADAPTER,SUPPORTED as JIANGSU_E_CODES)
from regional_zhejiang_oct29e import (with_capabilities as with_zhejiang_e_capabilities,blank_binding as zhejiang_e_binding,ADAPTER as ZHEJIANG_E_ADAPTER,SPECS as ZHEJIANG_E_SPECS)
from regional_zhejiang_chunan_oct30 import (with_capabilities as with_chunan_capabilities,
    checked_adapter as checked_chunan_adapter, ADAPTER as CHUNAN_ADAPTER)
from regional_jiangsu_oct30f import (with_capabilities as with_jiangsu_f_capabilities,
    checked_adapter as checked_jiangsu_f_adapter, ADAPTER as JIANGSU_F_ADAPTER,
    SUPPORTED as JIANGSU_F_CODES)

def jiangsu_e_binding(guide,template,root=None):
    try:return jiangsu_e_contract(guide,template,root=root)['kind']
    except (ValueError,OSError,KeyError,TypeError):return None


REFERENCE_SHA256 = '80d1dc3989e9da1ef2c763cbde54bd474d691a4febba48425fb2cc3471d94562'
BINDINGS = {
    '510110000000': ('天府新区', '1064c9ed5635a0d224e4eee5', 'ec3268e5fda94301ab40a7e086afe07a', 'tianfu_reference_v1'),
    '510104000000': ('锦江区', 'ee967bbf0dfe1d4c069bc829', '8cc65371b3224a63ba25a1af9d49c54d', 'sichuan_combined_reference_v1'),
    '510107000000': ('武侯区', '1f8b592edbfb62253a2b4212', '4452a5a18dc64c0f98b84461765b56d8', 'sichuan_combined_reference_v1'),
    # Independently collected on 2026-10-23; each own official guide and annex.
    # Audit evidence: reports/chengdu-district-expansion-20261023/captures/<code>/.
    '510106000000': ('金牛区', '41d7c737ee838cacf45ffccf', '2aa2e64883d34e05bf595ddebd167b72', 'sichuan_combined_reference_v1'),
    '510108000000': ('成华区', '7674a3f2d6d9b1b3e0264eea', '90938d2b9da240c9a96289a25bc6443a', 'sichuan_combined_reference_v1'),
    '510109000000': ('成都高新区', '5944a0e6f5e29ec842f25f78', '8c83fd146ca84c98b974b6ddb0814901', 'sichuan_combined_reference_v1'),
    '510112000000': ('龙泉驿区', '84e8eb6cfa101e1ef6fafbbf', 'fdfc15a960b34a53be84094fc5626fe2', 'sichuan_combined_reference_v1'),
    '510113000000': ('青白江区', 'f93f9e6ff2297219e3d4f60f', '6fa978af0f0344dc87d670bb372725c5', 'sichuan_combined_reference_v1'),
    '510114000000': ('新都区', '723b8156d90672586d2a0e06', 'b2ab992fb7434e20a54ba2cfba875b13', 'sichuan_combined_reference_v1'),
    '510115000000': ('温江区', 'f53a9addd293a17848fbdb86', 'e35831f858d5493eab094093ed7f2ef0', 'sichuan_combined_reference_v1'),
    '510116000000': ('双流区', 'c73bff752aa05b89de8c38a1', '394068b14c2f46bf8b6c9ad5a8dabc37', 'sichuan_combined_reference_v1'),
    '510121000000': ('金堂县', 'a187296296ddb419570b020a', '679bdc8044704eaf9dcc146c95e7629e', 'sichuan_combined_reference_v1'),
    '510124000000': ('郫都区', '38ac66a695aa729c38002802', '58c5ab6b56ea4c36b2409546807bafc0', 'sichuan_combined_reference_v1'),
    '510129000000': ('大邑县', '1861eb3f53222cf082ec05c0', '9264f7ed2d8c4523bc8b8c6aa20d83c2', 'sichuan_combined_reference_v1'),
    '510131000000': ('蒲江县', '01cf5085472f8f4e29b8cba0', 'b5a7b7619f71437eb0d9559929505ff0', 'sichuan_combined_reference_v1'),
    '510132000000': ('新津区', 'dbefd880f6e1bd9302e7771e', 'd40c2381186141d6b7135278b8b5e6f8', 'sichuan_combined_reference_v1'),
    '510181000000': ('都江堰市', '865105ba5efc7598bdbd3b5c', '98ef6418826b412b92d9e25b0c042cc5', 'sichuan_combined_reference_v1'),
    '510182000000': ('彭州市', '460cc5d2713bdeff9690389f', '22a4e270e4d742f9b753e81376bdb72e', 'sichuan_combined_reference_v1'),
    '510183000000': ('邛崃市', '7c19845162228786f4cd119a', '2e15d8796b80463a99a556a34b1d7878', 'sichuan_combined_reference_v1'),
    '510184000000': ('崇州市', 'cbf3b8d651949dc204fcd334', '81c74af620394755a033678df47a06a9', 'sichuan_combined_reference_v1'),
    '510185000000': ('简阳市', '1fac2a2b3c0e06017816aa21', 'fcf70d9714dc4e00a54a4081f32db45e', 'sichuan_combined_reference_v1'),
    '510186000000': ('东部新区', '31cc5e088ece18f79cb52756', '97655f91f2a24e7eb7cfe622d70f8958', 'sichuan_combined_reference_v1'),
}
ADAPTER_NAMES = {binding[3] for binding in BINDINGS.values()}

# Each entry has its own formal city/district guide, independently downloaded
# sample and browser capture in reports/nationwide-localization-20261023-night.
# This is NOT a province-wide or equal-SHA fallback.
EXTRA_BINDINGS = {
    '510302000000': ('自贡市', '自流井区', 'b5aa123e9cd62e86b366d73f', 'a432fa772f8c407b9cef0758f3274a54'),
    '510303000000': ('自贡市', '贡井区', '0d7176d6f8adeb20dfa8edf5', '894b646760c242d4ba385c17ee768d17'),
    '510304000000': ('自贡市', '大安区', 'e4677861555562963cb00d60', '2d83ce55f1f74af39b0cbdaa8993d2c5'),
    '510311000000': ('自贡市', '沿滩区', '699b6af00e27de1e1e53fba3', '2402d44cfbc64824a97320d365b297eb'),
    '510321000000': ('自贡市', '荣县', 'd0bbb47bb82b4c95dba9480d', '59f27958c3de4824a908a435df7ce97a'),
    '510322000000': ('自贡市', '富顺县', '5e8bad63fed77d1275f6700f', 'da4c7828397a430a9137bd77f577af25'),
    # Own formal guides and downloaded sample files, audited 2026-10-23.
    '510402000000': ('攀枝花市', '东区', '4be146f298e2d8ec6e1780b8', 'fd5cf982b23744f58d0af2ac24dd29a5'),
    '510403000000': ('攀枝花市', '西区', '87804a0b7eaa61ff64a09fac', '4ec27ff702b248dea835fb2c23f25eb1'),
    '510411000000': ('攀枝花市', '仁和区', 'ff1f93aff8f7dd536d9d913a', '61d65f176cfd4dd3b45371e0c97d508e'),
    '510421000000': ('攀枝花市', '米易县', 'ee9c01334d455216b8420e81', 'd3ff2ca8fbba4489bfb59c096aedb270'),
    '510422000000': ('攀枝花市', '盐边县', 'de50b9fbf14412318186bf20', '2e706a2fd4de4cd4b89b817e65e8dbad'),
    # Individually audited Luzhou and Guangyuan guides and own sample annexes.
    '510502000000': ('泸州市', '江阳区', '5588a8fad8b03055a638cf21', '7c24ed4e5c734557890552e7d6d0b800'),
    '510503000000': ('泸州市', '纳溪区', 'c1bb9d2609328a40030f8767', '2d976e395e1d46439fd0327e737c1286'),
    '510504000000': ('泸州市', '龙马潭区', '3d3600b70ca22c61dd52701f', '3af246523e5a499f99bfd510a1b1ce8f'),
    '510521000000': ('泸州市', '泸县', 'e147fde7f0259337f6ff7045', '492902d877744a69be898f68dd16f43e'),
    '510522000000': ('泸州市', '合江县', '238616cb41f4f72e9425d016', '30420ab7f58747f3866550d282d79de6'),
    '510524000000': ('泸州市', '叙永县', 'd37ef42a091e063a72eb8391', '7773b67a89e54bb693a84285b56cf359'),
    '510525000000': ('泸州市', '古蔺县', '4d428a5817bab306ce939357', '6759c561021c4c2fa32e7e7037501861'),
    '510802000000': ('广元市', '利州区', '5826890067ba9dfe4f25aaa7', 'b4ce29501d6d4dbf8d9d2f88d402e1b3'),
    '510811000000': ('广元市', '昭化区', 'eab7904ad603e42d42c82407', '53a9f3da75f94fdb8c5cb6c2d034f0d7'),
    '510812000000': ('广元市', '朝天区', '03717e639e4bb4fb70e28545', '5dfac74c0fff4b05ba1237da94f7d939'),
    '510821000000': ('广元市', '旺苍县', '24ca5810e096848d3c496050', '96d45f9cf8734a4e949397132163d6c4'),
    '510822000000': ('广元市', '青川县', '00e56d8db183156225f14b68', '4015386169344e3f8a8221003b166b94'),
    '510823000000': ('广元市', '剑阁县', 'fb5dc58ca8baf365e5c00419', 'eb4eeca82450492e8a82be7768bfa760'),
    '510824000000': ('广元市', '苍溪县', '4d8042e18b2bf155bab173f1', 'b7df424ec75e45f38302a3357d2de500'),
    # Own Suining/Neijiang guide captures, materials and downloaded samples.
    '510903000000': ('遂宁市', '船山区', '79d7d9c33283205ff027dc7b', 'b15ce7bf8fde4903bf3b428de2e051d5'),
    '510904000000': ('遂宁市', '安居区', '6356e2a413a59c1f2de24ea0', 'ea4796fa1a034db39eb17bb0058735a0'),
    '510923000000': ('遂宁市', '大英县', '757f0cb9f5acc1bfd11c5806', 'c1538a986cb944bbb3b74f165c2b2506'),
    '510981000000': ('遂宁市', '射洪市', 'd3259b27cfbd27b99c7a67ae', '17c838a0add74d90ab7f652380598e12'),
    '511002000000': ('内江市', '市中区', 'd7f98675320d41a264a90424', 'bf3d512c9bc14eb0832cf56aa4c26332'),
    '511011000000': ('内江市', '东兴区', '64ff1af0dc6cf1cfd67b5844', '97a01aefdecd445dafdd7ebdf9408d0a'),
    '511024000000': ('内江市', '威远县', 'c13431d9f7729785426c7851', '06e13e1836674f1ea73dd83f071eb9e2'),
    '511025000000': ('内江市', '资中县', '868d5c03d283c80f95dabefa', 'd477bf537d6a45858a7a4ef8a6361277'),
    '511028000000': ('内江市', '隆昌市', '0c0d7bd58127bfe21c1ef22e', '01761ebde4384544a8278748268c41a3'),
    # Each own Leshan/Nanchong formal guide and annex, never provincial fallback.
    '511102000000': ('乐山市', '市中区', '2776c1fbeddaa1c547836e94', 'd4105fec3f5241c7875282e4d520b1cb'),
    '511111000000': ('乐山市', '沙湾区', 'a91a7061432b000fd4d0e999', '506d015590ba4cf5a2841a3b0a382699'),
    '511112000000': ('乐山市', '五通桥区', '0094adafc1b8deb55809aedd', '6d591d5b31d54063bfd8d971e2877426'),
    '511113000000': ('乐山市', '金口河区', 'aec6ed7ea283ac8f6bf3cced', 'ae8e374a5fe84110b8164779ee8d0495'),
    '511123000000': ('乐山市', '犍为县', '79b664c035b48291ea88bf1d', '77f21f8171f648b69bd9f05956f6fd19'),
    '511124000000': ('乐山市', '井研县', '6983b349627ac2b408df2468', 'b978e3b84d3648e094345afe900a5d4c'),
    '511126000000': ('乐山市', '夹江县', '98edc1bb563ad370d4d11469', '3bac20ae0ee0472bb813b47248669fd4'),
    '511129000000': ('乐山市', '沐川县', '9c83201dcd5fab775ca6780b', 'fec6ff6131da43e18ace90ddc29cb3e2'),
    '511132000000': ('乐山市', '峨边彝族自治县', 'c855239220ca419d13cdf042', 'e32a7f2e3dea4815acf7e9a3af325634'),
    '511133000000': ('乐山市', '马边彝族自治县', '52a7cc57264fb39fa753fd85', '50561589f1b44682b5355bdbf90f591f'),
    '511302000000': ('南充市', '顺庆区', '6a15ff76b00d9ebab910307b', 'd9cdbcadc6fa469a81f148159752b728'),
    '511303000000': ('南充市', '高坪区', '2266810525f089f48b81cb05', '33261aa06e2e4871b5634b70999d6f0a'),
    '511304000000': ('南充市', '嘉陵区', 'e3f05d0583986c4551027fbb', '084685e3b6ce486ebc3d955bea002014'),
    '511321000000': ('南充市', '南部县', '13019590097f4b52d2a849ff', 'df360488161b41999d2eb0d6fbd68597'),
    '511322000000': ('南充市', '营山县', 'cf8a36dabb1c97e48db2e387', '8486319fc4ee4bc094fe62a7e86da3c2'),
    '511323000000': ('南充市', '蓬安县', 'd29aac175cf17316b81e0e51', '1398154ed4e6455abd7ca3012d8d60ae'),
    '511324000000': ('南充市', '仪陇县', 'f221c93af5374b1d78582dae', '346a5f09795040a5b6c4e81b66f2b540'),
    '511325000000': ('南充市', '西充县', 'e6a53db12df25ff7f5ab5e4b', 'a328a939cb18460487f6b7860ce7bc00'),
    '511381000000': ('南充市', '阆中市', '3f63f48831c5e2179cc7fa43', 'b3ae2ca141264a0e90e4b928c8112d03'),
    # Own Meishan/Yibin guides and annexes; unresolved functional areas excluded.
    '511402000000': ('眉山市', '东坡区', '6b4a8f4be2fbc86be1c8a4f4', '7ced925454c94eb5b4bdd6920fc347fa'),
    '511403000000': ('眉山市', '彭山区', 'b343ed97c09f939b1eb6d1d0', '14f06b6195b44c7f93d5c1aefddc2bb5'),
    '511421000000': ('眉山市', '仁寿县', '3f2acd6df2e41f0306710f4f', 'ed989c1317bc44b4a595fcc08061c1bb'),
    '511423000000': ('眉山市', '洪雅县', '7deb5e94b193428b55f41380', '37dad991f76b47048bff01303a7aa914'),
    '511424000000': ('眉山市', '丹棱县', '061a6d8944cd05a137c2a100', 'f50cd37e774f42c9a47399dd6271c8c7'),
    '511425000000': ('眉山市', '青神县', '548a239a5e912c33f68a67df', 'bb0fdd407fd34f35936b36d1cec66d8d'),
    '511502000000': ('宜宾市', '翠屏区', 'cc6ed19b27e6ef921ad68830', 'f522e68b9da84cfa85c34dd934ca3102'),
    '511503000000': ('宜宾市', '南溪区', '97a5f4ac51d27b7dec8c5af2', 'bbccddba4d6d45fc92e9b723ff044b01'),
    '511521000000': ('宜宾市', '叙州区', '6dfc9a8b70ff73ec5ecde944', '04f8dbcadb9c464193cfdb6e85ae79c2'),
    '511523000000': ('宜宾市', '江安县', '8ff407c1383b1c8f06e97717', 'f1702a4cba8c49d38d38a13ad21cf23f'),
    '511524000000': ('宜宾市', '长宁县', '65e08a96c85220c98567a8c8', '71ded9e9a05d4a4db1a215f805c8a7f8'),
    '511525000000': ('宜宾市', '高县', '597c1bccd8ddfce041247a76', '9289f5cf227f442da0f9bb39a0cf29b7'),
    '511526000000': ('宜宾市', '珙县', '7f113dd70f3ca0617d31343b', '54352e64308047d5b25b2cdb3c356638'),
    '511527000000': ('宜宾市', '筠连县', '6178cbb4e3c4814ade7ec0ed', '55ec2bfb7aa544b0b574ce4d509f9e1a'),
    '511528000000': ('宜宾市', '兴文县', '81160f46e6812c1315c22e23', '40b21039674e412ebe85b16d315f17e4'),
    '511529000000': ('宜宾市', '屏山县', '6acd19a540915b84dc0990c3', '15f4110c15504a348b4dd81b5a603ae2'),
    # Independently captured Guangan/Dazhou/Bazhong guides and own annexes.
    '511602000000': ('广安市', '广安区', '34bf5afb172b659cc594c350', 'a87da0edec844b3d963e1db708b20faf'),
    '511603000000': ('广安市', '前锋区', '7442a9bbe49a937d170d3363', 'e6e9c0383e814a508aaf368b720ba67b'),
    '511621000000': ('广安市', '岳池县', 'a290b45628eaccb32d30f469', '6063c2a51154414d89f30678b710a90e'),
    '511622000000': ('广安市', '武胜县', '54ea0785295573506e1e10ae', 'c4c78ec241ae476aaeee57b625aacbba'),
    '511623000000': ('广安市', '邻水县', '242c8893e845e9b1b0479ca7', '17167a6edb62496ba1095ed552fd8a7b'),
    '511681000000': ('广安市', '华蓥市', '94f645411fd8f4c1021eabdf', '4b870329810c47c68e377a9be1f9007d'),
    '511702000000': ('达州市', '通川区', '0a07642f1ede208681ac9099', 'ca09f6ca0e354e9d897187ac9d144d9a'),
    '511703000000': ('达州市', '达川区', '577613b9ca6ee5fbfc1f7865', '2c0b5e60b3ec41fabaac481459055c7e'),
    '511722000000': ('达州市', '宣汉县', 'f1d64edfa7a90a15a1eb8c07', '99b4a3ba321349348852a499620439e3'),
    '511725000000': ('达州市', '渠县', '16203e4931907567e93d670d', 'e0f6f5b1f6ac4cb5a79f564d5d9303c1'),
    '511781000000': ('达州市', '万源市', '2b22fe7ffb795cdf5fcd6251', '63bfe84db9f241448dab7c6532539b17'),
    '511902000000': ('巴中市', '巴州区', '2c6cd910c097983105b086ef', '40294caddc0b4208a0c2af474fd93ccb'),
    '511903000000': ('巴中市', '恩阳区', 'ebb0dc55337fd3aeebd32fb7', '235d07b21cb1489eb2d8812f3e846b27'),
    '511921000000': ('巴中市', '通江县', 'f657e3320e6d2bb09d2fccf8', 'b392a699103a420f94c09b7526c53694'),
    '511922000000': ('巴中市', '南江县', '0afc61bc6abf457460bb544d', '8435e5bb63884ac3beaaefccc015486d'),
    '511923000000': ('巴中市', '平昌县', '736821d8ed2e87018609ec0e', '0fe99eeb5e324a7a8a3cbb7d3cbd21f4'),
    # Own Yaan/Ziyang/Aba guides and annexes, no provincial or equal-byte fallback.
    '511802000000': ('雅安市', '雨城区', '978f9d48a4c0754cea718425', '0f3046dfbf9847a7baec7761f1ec257c'),
    '511803000000': ('雅安市', '名山区', '70761249de53dd947e902d3c', '3499fb9c4f5c44d1a0234eff85a34729'),
    '511822000000': ('雅安市', '荥经县', 'f0f1c3b0567e1ad1a2bbb6da', '4527b62806aa4c82b56ccddcda80e2dc'),
    '511823000000': ('雅安市', '汉源县', 'e1794fe08cf35e4ac4495733', 'a0a5b017495342a0bc89c4be365f37a6'),
    '511824000000': ('雅安市', '石棉县', '35cb9fb7e9d7fa9eda040583', 'db9841f58c2e485d8e563adea522c568'),
    '511825000000': ('雅安市', '天全县', 'e784a8b50368bc5f29df2887', 'd3adb5e96b5c476d8acf861a3925a22c'),
    '511826000000': ('雅安市', '芦山县', '081d0de2870fe40067c626fc', 'bbcfcad93849498db6ad951972ba77dd'),
    '511827000000': ('雅安市', '宝兴县', '17377c71bc18542d85b41207', 'f9622b3f9ab04dc2a14b4189a8469491'),
    '512002000000': ('资阳市', '雁江区', '44a1c54f3383b18cd0f22c21', 'b9865bf4423f45efaf54acb88c0770fa'),
    '512021000000': ('资阳市', '安岳县', '50a60a8acb249d12c724c3db', '95c6a346cf6e41de8f8eb29a32d3f1a1'),
    '512022000000': ('资阳市', '乐至县', '3df570d1d346fb7541ee0536', '2cb77fcae5b147e1aee3327607afc7a3'),
    '513201000000': ('阿坝州', '马尔康市', '6b5a1283d96ff59a3773cb82', '1261927df4d047fe9cbd4d4be6153fe4'),
    '513221000000': ('阿坝州', '汶川县', '032201023d897d13c1e3e969', '7a4aeeebe5e9400e9741c51ae470a47a'),
    '513222000000': ('阿坝州', '理县', 'f712bf36532768e9d84ddd5c', 'ab0a9ec3eda44df9999244cf1f96d8f2'),
    '513223000000': ('阿坝州', '茂县', 'd0ed186acfa8288f5c0bd83b', 'bee3a5137b4a466da87bd1040c9a3f6b'),
    '513224000000': ('阿坝州', '松潘县', '71bad9a64880f21f369c835b', '482bfd10152141f38c5dcef961b2af4f'),
    '513225000000': ('阿坝州', '九寨沟县', 'e6e0c520f1db0b6b47dc3061', '9d921e853a844b26ad8653df030daa45'),
    '513226000000': ('阿坝州', '金川县', '17fa0d7bc16847baeacaa3ee', '07272b2cee7c429e83481cbc27527e2e'),
    '513227000000': ('阿坝州', '小金县', '1fe6c99baa6beb8d5a1fcdbc', '1e9dfc81de764f49b2b93cae2ac47efb'),
    '513228000000': ('阿坝州', '黑水县', '3adde6c1db0d49d55b95e00d', 'f3d3bba16d2645699123143503c35e6e'),
    '513230000000': ('阿坝州', '壤塘县', '7a3fc196b16521da50d0927a', 'a7f5553275fa4b61b60baba9b480dd40'),
    '513231000000': ('阿坝州', '阿坝县', '23612e3a1c66c24619afcba6', '2e939810724a4752acb3f157c6ce642c'),
    '513232000000': ('阿坝州', '若尔盖县', '5cc1a8243cbbdd04691e7ed3', 'be18b861e5354a51923543e20c1ee6f1'),
    '513233000000': ('阿坝州', '红原县', 'a05931e4e560d0aa6802ce2a', '62e54dba220d4694a089c05ae148e704'),
    # Independently captured Ganzi local sources; channel conflicts remain conflicts.
    '513301000000': ('甘孜州', '康定市', '290e526f33ba82ed572ea6da', '659ed58e0b604e648eaedaf52982f9a2'),
    '513322000000': ('甘孜州', '泸定县', 'd6bb8b28b49318e4239959b2', 'e5e999d9480b43bd8c19232777980b83'),
    '513323000000': ('甘孜州', '丹巴县', '2b201fc0af5e5e66213318e2', '42965f3e18b44aa0a4b1f674fc9e7d06'),
    '513324000000': ('甘孜州', '九龙县', 'f2f355779e92b7e6948b3471', '9cacff5b1f06468ea84cd435b12c603b'),
    '513325000000': ('甘孜州', '雅江县', '7e335c7217ec3e4bce533d61', 'fff6ff72ee454093bead7d27b28e78d1'),
    '513326000000': ('甘孜州', '道孚县', 'efa457272077629e9524efb4', '24bdfeab36c64a048642a542272a571a'),
    '513327000000': ('甘孜州', '炉霍县', 'f6fd8714b11eb772c4989600', '5dd67516d2cf4241af30df7490f62a34'),
    '513329000000': ('甘孜州', '新龙县', '2feccd05761b1561d32ffad9', '97c356be0e6947e6bd8903fae3b98793'),
    '513330000000': ('甘孜州', '德格县', '3519a95d776993434b08e412', '9d396d19dfcc4e7facc3109d08c912ef'),
    '513331000000': ('甘孜州', '白玉县', '0975a087ceb15b47fb7c5d29', 'e187ca6c4dcd4f709064cb76c69c75c1'),
    '513332000000': ('甘孜州', '石渠县', 'cc9fb265f03b35b6789d5a1f', '71a8d25ce54340d2aaa0eec4f24b189e'),
    '513334000000': ('甘孜州', '理塘县', '98bdd08ea71b3b2bb52a2f29', 'a181c9a6bb2e461a9d370b13868c7b1c'),
    '513335000000': ('甘孜州', '巴塘县', 'f94505a973b8e338a73ffdaf', '60262197146a4e1692193944430453b8'),
    '513336000000': ('甘孜州', '乡城县', '9235aad1baf680dee43206c1', '2acc1ee7edf04be4b40dcd05b5549603'),
    '513337000000': ('甘孜州', '稻城县', 'a7f2b7dc526d0acd7443a230', '158fa06affab482c87b0d733dff0d46d'),
    '513338000000': ('甘孜州', '得荣县', 'f837a8d97e003474bd25969e', '4d491126e5b7450daa80e84e4df2a5d4'),
    # Own Liangshan guides and annexes; held Muli alias is not enabled.
    '513401000000': ('凉山州', '西昌市', '065baf36fa46abff75d091f8', 'f4bc0a8979ac4424867e9ea828fc6230'),
    '513423000000': ('凉山州', '盐源县', '0fccf2d8067ccfcbd6f681e2', 'c6cb29c66cb04ab58268bb13ac631b05'),
    '513424000000': ('凉山州', '德昌县', 'c67cac6245d2fd819187a2e9', 'ef4935fd548249e88be380a5dda6ed73'),
    '513425000000': ('凉山州', '会理市', '01380d3a35043802fe8065a6', 'f04fc76fee1e46a49d4e01ac725d12a1'),
    '513426000000': ('凉山州', '会东县', '0376c4a1ef9968b98c4bcbd4', '69730f5cb3e446fca85d43e8565e8ab1'),
    '513427000000': ('凉山州', '宁南县', '52ebf9663e0022151f88e14e', '6fef2aa501c94b4f9f4a06f164edbaa4'),
    '513428000000': ('凉山州', '普格县', '7bdbb32c5315cadaabf57aca', '30f4bb6d96d443dd923bdf9d5d1e54a1'),
    '513429000000': ('凉山州', '布拖县', '79296870b0a60df8184ea5f7', 'ab6db07eb6f94233a389ae6592e1ca27'),
    '513430000000': ('凉山州', '金阳县', 'a0bceff6fbdcf466ac826a93', '63c352cd63f54eb1ac30c178da62f7f9'),
    '513432000000': ('凉山州', '喜德县', '11a33aa81652ca7db47ac903', 'b79db85467c34eb087f187552e616c40'),
    '513433000000': ('凉山州', '冕宁县', '0f593058bcc5c73928257ea5', 'f8474dbd4020456da65318ddd80e44dc'),
    '513434000000': ('凉山州', '越西县', '537c93ac773124264779d1c8', 'ed9393bbd50f45d784c36032e4655244'),
    '513435000000': ('凉山州', '甘洛县', 'bd622aab769a98de8cade8eb', '9707a54f9dfc47c5bfc489a5867d6afa'),
    '513436000000': ('凉山州', '美姑县', 'e2c603fed9897cc18b7e08a2', 'bb8ba77793774005b4f72a5657e270c0'),
    '513437000000': ('凉山州', '雷波县', '7628ca9c8a7adbe91989804e', 'a7f1aa69d5a54f28b9eceb3460940e77'),
    # Own identities rechecked against exact official directory long/short names.
    '511411000000': ('眉山市', '天府新区', '121727dfa10e719d49964ca9', '147acee5e1b447f897f7e41388e1c0ff'),
    '513422000000': ('凉山州', '木里县', '61164800ee7d6561f634928f', 'e7b53d19f2ff427b9c21ffde53ca20c3'),
}


def reference_binding(guide, template):
    code = guide.get('region_code')
    binding = BINDINGS.get(code)
    city='成都市'
    if binding:
        district, source_id, annex_id, adapter = binding
    elif code in EXTRA_BINDINGS:
        city,district,source_id,annex_id=EXTRA_BINDINGS[code]
        adapter='sichuan_combined_reference_v1'
    else:
        return None
    if (guide.get('province'), guide.get('city'), guide.get('district')) != ('sichuan', city, district):
        return None
    if guide.get('verification_status') not in {'verified', 'partial', 'conflict'}:
        return None
    if digest(guide.get('source_url', ''))[:24] != source_id:
        return None
    if guide.get('source_id') not in {None, source_id}:
        return None
    expected_file = f'templates/_docx/_regional/{code}/{annex_id}-仲裁申请书(模板).docx'
    expected = {'id': annex_id, 'annex_id': annex_id, 'region_code': code,
                'sha256': REFERENCE_SHA256, 'official_kind': 'sample',
                'download_status': 'downloaded', 'file': expected_file}
    if any(template.get(key) != value for key, value in expected.items()):
        return None
    if template.get('source_url') != guide.get('source_url'):
        return None
    return adapter


def with_reference_capabilities(guide,root=None):
    """Publish platform adaptation separately from the retained official content."""
    if guide.get('province') == 'jiangsu' and guide.get('region_code') in JIANGSU_F_CODES:
        return with_jiangsu_f_capabilities(guide, root=root)
    if guide.get('province') == 'zhejiang' and guide.get('region_code') == '330127':
        return with_chunan_capabilities(guide, root=root)
    result = with_shangcheng_capabilities(with_zhejiang_capabilities(guide)) if guide.get('province')=='zhejiang' else deepcopy(guide)
    if result.get('province')=='zhejiang' and result.get('region_code') in {s['code'] for s in NINGBO_SPECS.values()}:
        try:result=with_ningbo_capabilities(result)
        except (ValueError,OSError,KeyError):
            for template in result.get('templates',[]):template.update(can_generate=False,document_types=[])
    own_jiangsu_ready=True
    if result.get('region_code') in JIANGSU_OWN_CANDIDATES:
        try:candidate_contract(result)
        except ValueError:own_jiangsu_ready=False
    for template in result.get('templates', []):
        if rongjiang_source_matches(result,template):
            template.update(can_generate=True,adapter=RONGJIANG_ADAPTER,document_types=['application','evidence'],
                            content_kind='filled_converted_official_blank',derived_from_format='doc',
                            generation_label='依据蓉江新区官方DOC转换副本填写（非官方原件下载）',
                            classification_note='官方原件为两页空白DOC；填写使用本平台核验的转换副本，原件下载保持不变。')
            result['warnings']=[w for w in result.get('warnings',[]) if not w.startswith('尚未完成原DOC本地填写适配')]
            notice='填写结果由本平台依据自己的官方DOC转换副本生成，不是官方下载原件；仍须本人核对并手写签名。'
            if notice not in result['warnings']:result['warnings'].append(notice)
            continue
        blank_kind=blank_binding(result,template)
        if blank_kind:
            if not own_jiangsu_ready:
                template.update(can_generate=False,document_types=[])
                continue
            template.update(can_generate=True,adapter=BLANK_ADAPTER,document_types=[blank_kind],
                            content_kind='filled_official_blank',generation_label=f"依据{result['district']}官方空白表格填写")
            continue
        adapter = reference_binding(result, template)
        if adapter:
            template.update(can_generate=True, adapter=adapter, document_types=['application', 'evidence'],
                            content_kind='filled_example', generation_label='依据当地官方参考样表辅助填写（非官方空白模板）')
        elif template.get('adapter') in ADAPTER_NAMES | {BLANK_ADAPTER,RONGJIANG_ADAPTER,ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER}:
            if template.get('adapter') in {ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER} and result.get('province')=='zhejiang':
                continue
            template.update(can_generate=False, document_types=[])
    result=with_oct29_capabilities(result)
    if result.get('province')=='hunan' and result.get('region_code') in {s['code'] for s in HUNAN_SPECS.values()}:
        return with_hunan_capabilities(result)
    if result.get('province')=='hunan' and result.get('region_code') in {s['code'] for s in HUNAN_C_SPECS.values()}:
        return with_hunan_c_capabilities(result)
    if result.get('province')=='jiangsu' and result.get('region_code') in JIANGSU_C_CODES:
        result=with_jiangsu_c_capabilities(result)
        for template in result['templates']:
            if template.get('can_generate'):template.update(adapter=JIANGSU_C_ADAPTER,content_kind='filled_official_blank',generation_label='依据本区自身官方空白表格填写')
        return result
    if result.get('province')=='jiangsu' and result.get('region_code') in JIANGSU_E_CODES:
        return with_jiangsu_e_capabilities(result,root=root)
    if result.get('province')=='zhejiang' and result.get('region_code') in {v['code'] for v in ZHEJIANG_E_SPECS.values()}:
        return with_zhejiang_e_capabilities(result,root=root)
    if result.get('province')=='jiangsu' and result.get('region_code') in JIANGSU_D_CODES:
        return with_jiangsu_d_capabilities(result,root=root)
    if result.get('province')=='zhejiang' and result.get('region_code') in {v['code'] for v in ZHEJIANG_D_SPECS.values()}:
        return with_zhejiang_d_capabilities(result,root=root)
    return result


def checked_reference_adapter(guide, template, kind,root=None):
    if template.get('adapter') == JIANGSU_F_ADAPTER:
        return checked_jiangsu_f_adapter(guide, template, kind, root=root)
    if template.get('adapter') == CHUNAN_ADAPTER:
        return checked_chunan_adapter(guide, template, kind, root=root)
    if template.get('adapter') in {JIANGSU_E_ADAPTER,ZHEJIANG_E_ADAPTER}:
        own_kind=jiangsu_e_binding(guide,template,root=root) if template['adapter']==JIANGSU_E_ADAPTER else zhejiang_e_binding(guide,template,root=root)
        if own_kind!=kind or template.get('can_generate') is not True or template.get('document_types')!=[kind]:
            raise ValueError('本区自身来源与文书类型未通过核验')
        return template['adapter']
    if template.get('adapter') in {JIANGSU_D_ADAPTER,ZHEJIANG_D_ADAPTER}:
        own_kind=jiangsu_d_binding(guide,template,root=root) if template['adapter']==JIANGSU_D_ADAPTER else zhejiang_d_binding(guide,template,root=root)
        if own_kind!=kind or template.get('can_generate') is not True or template.get('document_types')!=[kind]:
            raise ValueError('本区D批自身来源与文书类型未通过核验')
        return template['adapter']
    if template.get('adapter') in {HUNAN_C_ADAPTER,JIANGSU_C_ADAPTER}:
        own_kind=hunan_c_binding(guide,template) if template['adapter']==HUNAN_C_ADAPTER else jiangsu_c_binding(guide,template)
        if own_kind!=kind or template.get('can_generate') is not True or template.get('document_types')!=[kind]:
            raise ValueError('本区C批自身来源与文书类型未通过核验')
        return template['adapter']
    if template.get('adapter')==HUNAN_ADAPTER:
        if (hunan_blank_binding(guide,template)!=kind or kind!='application'
            or template.get('can_generate') is not True or template.get('document_types')!=[kind]):
            raise ValueError('湖南本区自身劳动者申请书来源不匹配')
        return HUNAN_ADAPTER
    if template.get('adapter') in {OCT29_JIANGSU_ADAPTER,FEIDONG_ADAPTER}:
        own_kind=oct29_jiangsu_binding(guide,template) if template['adapter']==OCT29_JIANGSU_ADAPTER else 'application' if feidong_canonical(guide,template) else None
        if own_kind!=kind or template.get('can_generate') is not True or template.get('document_types')!=[kind]:
            raise ValueError('本地区自身来源、空白文书或文书类型不匹配')
        return template['adapter']
    if template.get('adapter')==NINGBO_ADAPTER:
        if (ningbo_blank_binding(guide,template)!=kind or kind not in {'application','evidence'}
                or template.get('can_generate') is not True or template.get('document_types')!=[kind]):
            raise ValueError('宁波本区自身来源或官方空白文书绑定不匹配')
        return NINGBO_ADAPTER
    if template.get('adapter')==SHANGCHENG_ADAPTER:
        return checked_shangcheng_adapter(guide,template,kind)
    if template.get('adapter')==ZHEJIANG_ADAPTER:
        return checked_zhejiang_adapter(guide,template,kind)
    if (rongjiang_source_matches(guide,template) and template.get('adapter')==RONGJIANG_ADAPTER
        and kind in {'application','evidence'}):return RONGJIANG_ADAPTER
    if blank_binding(guide,template)==kind and template.get('adapter')==BLANK_ADAPTER:return BLANK_ADAPTER
    adapter = reference_binding(guide, template)
    if not adapter or template.get('adapter') != adapter or kind not in {'application', 'evidence'}:
        raise ValueError('当地附件尚未通过填写适配核验，请重新核对地区和文书来源')
    return adapter
