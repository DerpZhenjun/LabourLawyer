"""Explicit own-source blank forms. Sharing a field layout grants no jurisdiction."""
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import parse_qs,urlsplit
from regional_guides import digest
from regional_documents import PreservedPackageDocument
from WenShu.exact_template_fill import fill_application, fill_evidence
from WenShu.template_fill import replace_span

ADAPTER='jiangsu_xishan_blank_v1'
SOURCE_ID='b1f8ab307b0a4f634081c052'
BINDINGS={
    'e1ae7409-3195-4eeb-aace-c9de16282335':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '2d7b1fe9-8bdb-4e9b-b0ef-7616a6b87c97':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
}
LIANYUNGANG_CODE = '320700'
LIANYUNGANG_SOURCE_ID = '798345f56be3804472dc90b1'
CANDIDATE_BASE = Path('reports/overnight-gap-closure-20261030/localities')
# Guide and Word receipt are pinned separately from the verified official annex bytes.
MUNICIPAL_PROOFS = {
    LIANYUNGANG_CODE: ('lianyungang', 'a569d9a0cde1c4534ac4f1fe5b2414ca0e6e6612952098b49f773ede817d6ee7',
                       '3a354ec4b95e18b4124df88e0380ab27236cbaa46c6e7644446667e0081a711d'),
    '320300': ('xuzhou', '9743684a48405a882d7e62d4a45d6798a8f12bac3a2e867d38d51abfe15ac31c',
               '37c407a3b985ee0246d4142371e7df5041d7e2c4031cd3965776da8291fd7c02'),
    '320800': ('huaian', '931e2122c1f833bb2c979bcc75a0a7210825dc0302a85bd04603e5d9f857d28a',
               '17aa6cf0616b5b4cf80a204fc800b0996b6c7ed1aa5feeecbf232f27e97798b4'),
    '320900': ('yancheng', '48a8b42c3816d0efeb088e1996baa4ebbfb49043bb39d97507e89d075a727df2',
               '2b2dfb134c1dfdec37236d2f36ad35938ff85b29bbc34261c6b9ccc4908ff51f'),
    '321000': ('yangzhou', '3dff462a109bfbfbcef5150da390ce5f3c099cab9fd98caeed022dde9b670f88',
               '3c11bce5bd4648d1c15e5fc7e618f8f74fa1b8b0ac2bff2878635564b70f1d6c'),
    '321100': ('zhenjiang', '80f8b64f45800ffa22987b488703ff5149d44b9dbd7c5bb02bfe07adfea84959',
               'baea1a366155d2939f024a3b6fe220430f894e9bb9760949a4cd0572aa42b1d5'),
    '321200': ('taizhou', '0f9174c185b05fe665c6dce6c3c964878d8a2081c87e5417172e5fbca38df39a',
               '0973ffca960b6531140f3f1cb48417c7735df61c77eef3c5db42d0a83b2346fa'),
    '321300': ('suqian', 'f9a85425c18fba9a8f931877ac3149c825df872faf77dda023f3519a9348fbcb',
               '0209c0b4f562dd2a77b748a94fa2972ee50dca88adf8343e227f142249a028d3'),
    '320100': ('nanjing', '28300a49320ab9d37c1ea86fb90685e6a75781975a9db7d1786e3ed975ebe9a1',
               '6fdfd3a04c946146e83814c782e97a9373e9cc97ca766a8a9343e68b796717cc'),
    '320200': ('wuxi', 'd4f79c49f561b21a744c8109216ad7b3e1cad1b75cf7284c3f2b1525dc6e5f6d',
               'd513ba96f527f071b6435105bf899942dc53dd7e946b0eff562333ff6d383685'),
    '320400': ('changzhou', '8805e8335bcfdceca46647613d50d615392b17af575afda8a389a21385e3f607',
               'de3f29cb3cdda7169dae5e08a386cbb6a966554aaec06b413c38e6fd132add39'),
    '320500': ('suzhou', 'c20af0af3618a92516a5d59773bdb51b2e460c1449d1e8bfc94b290aa44a01eb',
               'd658606d6664ef843875f085a91563113b579024502ddef8907831d1a9820bb8'),
    '320600': ('nantong', '7c857ebc72bae9298a98a86b84169b3589b9ef999a7293551b9bb607c961d9c1',
               '97fad4437bdbbc86693c93077cf082ebb625c533787a8e346374a2608f12d8f0'),
}
LOCAL_PROOFS = {
    '320804': ('huaiyin-own-source', 'district',
               'e1dcd1bcd5bddf6bf703bfb766c0db43ece2df03c277cd17155d7bdc39c6498f',
               '9af9a2ab83440a8da7eb12328cfb11b582ab69a0f06ab540f2c42204a55b8c21'),
    '320813': ('hongze-own-source', 'district',
               '12a6da46ce46d5afbcc2a921d6447969eeb99aef3111ecff4020891cda816756',
               '719445644202ffcb3d29d37e7cd8049e79ae29a08c750157cd0fd2ebb7a63b1d'),
    '320871': ('huaian-edz-own-source', 'functional_area',
               '31b435d609df5f165af1634d49ffce0ec3f696e3cd53ed95cc420e55c6c3d41b',
               'a4493c0b9bb324d6c4b3853f530b17db2c7b53f0f8c336fa381df4f1eed5353c'),
    '320830': ('xuyi-own-source', 'district',
               '0918b875b8211fc3f7e92a36c2170cdae882f678ba5730fc5a00097c4a3dd301',
               '4c9d10ebb08fd5bacb2963f6bde848079ee755e3ecc00f1c02fc3c4fbae5e045'),
    '320703': ('lianyun-own-source', 'district',
               '8819c78c080bb064738668713f9fa2a65d271860805f60962d10ea88817bf407',
               '57eb37e846d4d4aaa49c052375c5a7b5395e4a4dc1d726cb86b00de9d83c10c8'),
    '320707': ('ganyu-own-source', 'district',
               'aa378e113054959f50d95c03247eb2dce6fea50b2fcb288c14759fa758195934',
               '19126e19db41e830579cfd2de489789baff3e2561181563ff8c10dbd4edef9c0'),
    '320722': ('donghai-own-source', 'district',
               'db89b589a40e5d5497b83e8103241dfc98391262cc6ca3b8e7c92f6dd0cf9154',
               'a542bb79ae03be5bc3379d7495d8878688429fda643d23a902f1dc3cbea49796'),
    '320723': ('guanyun-own-source', 'district',
               '58c75c7289d4a4e19c37b4ddaba5c90291a5937b69ac2dbd0c32bd4d79d46074',
               'bd1845bb8a8e6cf344de5d9010d1440bb797b37aba4d33cbceb0c3fd15f477be'),
    '320724': ('guannan-own-source', 'district',
               'f17e313271c0d463c2a7d85ad231ffe5b59e0d313b9d212b5474955e03c8bdf7',
               '35a127004b35babd4508235a326a31672aa0e19f438023dbf05647234a562921'),
    '320771': ('lianyungang-edz-own-source', 'functional_area',
               '7e8d044475941112eb4632237f6051dbd5699081fc343b12c02ff4d9f067a70b',
               '48a8281e697a71888373e5c6b2f24e99f22e3c270d8e5f6a7f90593cb3fde6d9'),
 '320302':('xuzhou-gulou-own-source','district','45cd224a0f524784f7235be6e99fc54ebcee82c67d9acb6e27dfac4f7ba9ca2f','950d444824a51b04a721e99105fbe6ab5931d6dd504fe2d00544a208b65e3fe8'),
 '320303':('xuzhou-yunlong-own-source','district','9c3b33917fad0dafeae996833eb534456fd44ac8b0780347ce1175a97e50b539','16cd8629d41523776fff14e2a3215d9e36e133cbd5ae981e102fc8ef8e1f5b90'),
 '320305':('xuzhou-jiawang-own-source','district','a155d0a22e5c0752286d4d51f58f390ce74541473755e3167f8f9a6a8c4f1ff1','adfaac591bb6a268a79fc06fc85dd05fdd272909e77a6f72bfcdce99f49e5fb2'),
 '320312':('xuzhou-tongshan-own-source','district','353d8a27d66c0ea033d82dc37cc3c79bb863fd31113e48048e915e1f5ef3ca34','63f65a69972e259dd1f5763e889c20cd3f62be4a2618b00c51627a43438d5219'),
 '320321':('xuzhou-feng-own-source','district','00fe7d5e095e2b5caa82a22a634e0d9d4caa9dc1dd89f1e968c88224275a0ffb','7757fb990fa09e0e1e0e699479f8eca5fb7a40c4f2146fb6805637b4351804a5'),
 '320322':('xuzhou-pei-own-source','district','d78fd8fefa50c5dbe7d5229d821f43a3c7fa3d55ef28f322d8e1155e35108eaa','e0dcec8e7702f30a672315a7e01abdc64c521e0e41e7ad7ecac05f7273e7b11f'),
 '320324':('xuzhou-suining-own-source','district','c57be529a40f834a135b8b389a501ec732b203e48af6fb64198e253dc6c3df3e','823c2abf97bc182358b665a109391fe9f704f2318fc0da7c24c12d8ed95d437b'),
 '320381':('xuzhou-xinyi-own-source','district','96bcc337bbfe75ae94475c630e6c2aef86a7604dc34fa4a4ae310783a4bfe9a8','311b2335975be4b0fdc9775d9106e252fa3973853c2f350ed3df50b1d33c39b6'),
 '320382':('xuzhou-pizhou-own-source','district','cc2be80db9e79c3bdf4e37525d1c554bb939f5aaf7667666a36d64b9de700d39','b067167cf9ba3e9cf1c2da42d95e485f886571aebaeb06862cdb46a4ff9ce5e6'),
 '320902':('yancheng-tinghu-own-source','district','ec0d0ac90cafa109b925e332038ca99932339fdf78555d3268188eaea22db61e','3fb2436afb04df1979935567b3eadeeb2f8dcf9905132c6a2e84c1631c9db6dc'),
 '320903':('yancheng-yandu-own-source','district','1abda73be8a5a0367726649166c64b0548bc39ea6804862e69baaa5c359b4cc4','e376937551089d42799f21efab9d1d1b89286c4b7f099ace0ccadb5b3b121a3a'),
 '320921':('yancheng-xiangshui-own-source','district','ba44ae4f15ee579a02c0dd16aecb08abf199b51247c842c9e725a12890e01b2b','72cb3380750014bca55f6e66a0af385d79a1e42fec2c8226c535d158fa07ef12'),
 '320922':('yancheng-binhai-own-source','district','3680053ad124bbad54d44193f149eefb8032b203eba5982872794e590f3a85ff','9e5445f02fb79eda6b2b0a606054740a7919efcc82f3aee07c7c030e8e04e0bf'),
 '320924':('yancheng-sheyang-own-source','district','db6f18f5eb7c5b2d19aecc2aabac8ef1480f81379a1a9a3421765ec181702c3f','f493a588353292ed55a8b583dd4f001295622f290087f5ca3e49a710101c4235'),
 '320981':('yancheng-dongtai-own-source','district','abce7cacfb828cc69b7ea6d54d217b70d1e559b536f7b89139b2fb464210d9b2','e73cf9ab865a2c8c5fd464efcd62e45d4067caddc91ebd7d96d854183e2d064d'),
 '320971':('yancheng-edz-own-source','functional_area','57af93268de0a393a452973ab08a4264f54dfda726a4943529b187a97d4f035b','93f503efbac6c2c6b0c943ddb40a2c3a8f6c2855e89d11130bbb991ae28c1245'),
 '321302':('suqian-sucheng-own-source','district','3deaf922db96552aafb49396afd01d3fa494226ba1e68ad87b7323a5ab5eebac','6197bae6feb4030d6eb6e6607fcd6d94174d7c8f9cae289c5717b794d48df1cf'),
 '321311':('suqian-suyu-own-source','district','95091e9c962524b12eba3f63269605a42c340a2fcf5a52effa5f4fccbf1617c0','b9518499f99b12935a65c346e0dcc2ba9335566f80a32c428d4095e3d01a237b'),
 '321322':('suqian-shuyang-own-source','district','1de2bc92345016fce1ca06177857614c4402defbe4029952bf1ba6be02ae22bb','47ea55eef92a83e6beada49dc28eb33ff13a42fdfc3d5763d2cee331e601d7f9'),
 '321323':('suqian-siyang-own-source','district','e811f1bbddffd4f797e07c844ec55ae04f92be30768708d87924c106b62776c9','5812a53fbf794f36bafe044aab4f0d49280e3fc510c44c2c964ee9cd057cf72e'),
 '321324':('suqian-sihong-own-source','district','a1d4d4faeda9e9f4dc5a94120982816c95cb84bc0ef1511ce82a336744af21cc','1161e7ba8cba428f52325cd3dea1172b7ed54a74006159e891e937d777e08967'),
 '321325':('suqian-lake-own-source','functional_area','472fdbc4ee0c4aca0d1495f34ad31ad8de3d207d71f8c91fccf59b29d98a36d4','a5aa9593c673b129ed0ce1568c47431a60f605f7d94740e2a5b512f354052ed0'),
 '321392':('suqian-ssip-own-source','functional_area','1a418811d2bc2a08106400fcde89d82a09f304f77498dee3fafae7dc1c504b99','3ce4bf27aebeaa989b97b0d129af7b09a3bd086e3326f04d9236b6649fe97bbf'),
 '321002':('yangzhou-guangling-own-source','district','a7695bd2e0404a27647cf7fb8312ecd7f3a145afd522b6df171e7cad61be7c46','225ac5f76073d15b0d26b5d45a6c2096ea62ae979a965a6c0b873f500fb3206a'),
 '321003':('yangzhou-hanjiang-own-source','district','cfb130c7c8ba56097455c34bf97ab29f31e276888290586c5c6b821f71dbb586','26db788b65fc016466a138519363213e961378d82dd731819238f2b575a0040b'),
 '321012':('yangzhou-jiangdu-own-source','district','ea6940b1de0fce532665a900d2d2494ced75839f4fa65b9a6de19f5d4ba9e35f','3e2f27626e2bea9ad1fbeafc6f86dc71d84723b926a0556237f5c3ac4417aa25'),
 '321023':('yangzhou-baoying-own-source','district','7242c5935cafcfdb13e40c342d6ad6680eb67044f55675eb8d38b07a0ed75719','db55d5b9713c57d6df8c374b6ecede0e946bc9bd9427c3ff4baad8aebc5bc62e'),
 '321084':('yangzhou-gaoyou-own-source','district','6b6530d92acd5331489d758d6bc235788bbd2f98b7c034f78fae034634ee9205','dbfa1412d92e3f97e6c5d365072fad1e0ac9dcee07c3dde976cb540367a5d660'),
 '320613':('nantong-chongchuan-own-source','district','1b4cac0ffa6489f819d512a69af2ede65998a073f402696c804a4af7f4c7dc4d','e09a0af5a142c5e6a39b73c7800a89637f2c334c4268c89b7bf7066d913c173b'),
 '320612':('nantong-tongzhou-own-source','district','774315e91d50c335ff65fefd9c0185ab461adb9623a8f995edc14c4e4375c93c','1e57705879a1bd8d1dd90a96274621fb1aa9f9706a2f163a725e3990a1bd6318'),
 '320685':('nantong-haian-own-source','district','6f8ca1bc4c93b3ffe1066e966acebb50cef0704d708e949535b985ddf9be49aa','625f914a9c49fa01700a32897f38b6ac2284a6481a0b98050d8f8132785af50c'),
 '320623':('nantong-rudong-own-source','district','9d506b8662d218478dc5183947d76b07a3b73289e21034a9db347cb8b91f0ff0','8a9a72dedbb858138876261ceb1c544478a600677f7613952e2fa5fbc7cbabbb'),
 '320681':('nantong-qidong-own-source','district','8b065301f47865fd3ea6ff41d960fce58b0f2348e2a62958039434f9d7479213','a962ea67650ed79c45afaadda389d21fe6377a041ea09c1a1cadfc3cd9493c38'),
 '320682':('nantong-rugao-own-source','district','9ba5253ef80b07f66ec45ce4181c3b6032715ecb2ff71e1342f84f58d94bb06d','1cb64a1f8f530b50f51bd00c353f728fde7e12562d04702168915ef03d8fc1fc'),
 '320614':('nantong-haimen-own-source','district','fa1448af8265afe7c93a402c4066854bf0a0bb8d329ad9af6064e9005d29516a','8038e9c2c39119269d7a80a850656548b24b0f9645091d2da1ce13dccc7f0d3a'),
 '320693':('nantong-suxitong-own-source','functional_area','159a7e8653b3db207d00d432701c9083a06a035c9bc5acc2aa4a067a5d7575fc','13a068aca61399bf2bf9a03a3d317b10a7c2915b772ba56af92cd05448885e8e'),
 '321102':('zhenjiang-jingkou-own-source','district','02471e1e828612a69e97ff6134dffb9d470d98ed606076f87949fea549888772','5d444c181770fd238c24846fd3b262a8336f90c32485fecfc950463033a9374d'),
 '321111':('zhenjiang-runzhou-own-source','district','407931b632f2710296b6094b52aeef64fcbe191184257a724b941132397891a6','17d630ad1b4c0036d1cc330d51c685391a2ec83835f60839fd9ed7023b236b06'),
 '321112':('zhenjiang-dantu-own-source','district','10ca1feedcf8b5fff6618a46abf5f8074f9a349f72f72134d18eba10e94cb565','9f29e239b08789a89e72192f6332853c7a856d6c4c2df0d725441e141415a24e'),
 '321181':('zhenjiang-danyang-own-source','district','8dec73ecc07242213ea5ff90cce04cb4cc6e1f91877a1c6537bb4ca48abfd91f','7fe41a1c7c8bd674d56e4e9b33167884ff1cb0fba06e5ef04f80adb9fff56046'),
 '321182':('zhenjiang-yangzhong-own-source','district','b160d446423320f51c87c60f2804b8d867acd5b2dd2adda718825289326ecf24','02903b1ccb1675b294ceee4052293f157b8b0c817b77283ccddc9479e0e3b575'),
 '321202':('taizhou-hailing-own-source','district','cacf7597648dc9cd6a3c002adc24344b373c61f75b57e7b1363b5dcd28ae8e53','1d90938b6bda4d68d9513a6143bfcd9c14ed1ab0c070f4653a73e71298eb98e7'),
 '321203':('taizhou-gaogang-own-source','district','9c37ba6e1b26fceecfb068b0155c49aaab3659104362cdc4f01f89218019d88e','f63e2a71488e4d7a92f498b89a731ddaa52e9a278202f5668c47ac1f1182d7bc'),
 '321204':('taizhou-jiangyan-own-source','district','748aa7e03a42e3ac6c715fcaf67393f6f5cc59b9fd9d67a410d0563a594c4e45','ef8452836821fd4fc5701a938ac2a00ed13299be1a544deb5670265462e03a51'),
 '321281':('taizhou-xinghua-own-source','district','a18482b0a760b04a1d2da29486f507fdd7c5d0d532a12a1dd9af09a305b6a931','7be32d8f347985753e1e66575f557a4d42236f5e661e465797013c924e86b7d2'),
 '321282':('taizhou-jingjiang-own-source','district','d1838564d0c25adcec6044b78450fde2f8e9ac91a078439ba856e583600cd47d','b3048a849bdced08eaf69a081f2e1be330866c1a583079aa4348da2af69c8f74'),
 '321283':('taizhou-taixing-own-source','district','b3193bd4b1d693620f34a10bc09e4eeac660b342af7b774567643153d0d02a46','d180dff7f5ab84000eaf68ff7fafd62134c529c9ed9cfad673cf2f623d325466'),
 '320402':('changzhou-tianning-own-source','district','08fb45261a4a717d38b0a77f4d54bc35a58206a9a5f28fccdefb7e7eb289ebcd','20467c250126bd9287912e6adabc29bda3c36629a5878044acc7fd33e87bd985'),
 '320404':('changzhou-zhonglou-own-source','district','7cac02ad4712e8e9ddef30ab2043252b6b34cff3b87b0b1b68d037b3aea41fd3','e30b6f1fdd7edfe9cb2240459812dcedcb6a97be0a158ff67852d7a5bdd4eb6b'),
 '320481':('changzhou-liyang-own-source','district','0710f7c51f82d90bc43b3710877be697297bed825b5ed7eb668f9c49aca4afa3','b478cb6c0c814976888e955015d2425d0d0ef99db11cfbb957ff93d631525bb2'),
 '320413':('changzhou-jintan-own-source','district','c91910ee04ad83fdbb0c99303946b98cbb5f167735cc66d236f50babad60f79e','a3804539b86e0159b0d0d044c08e5cc8a908c1bd3e70b537fd937781ac2f35bb'),
 '320206':('wuxi-huishan-own-source','district','477006a6945e16e60af6f427703c1120c351aea93e5f2ae17948ed14403f7e0e','015c9b216207bf991cdeadef0185a1e3cf317c52728cbc2f07c5d7c9a6608222'),
 '320211':('wuxi-binhu-own-source','district','f2097db873c288951f26ef8b1344b0cb7b9ea92e1a222629b3504c3b0856ff22','69c635f88c06395e3e0a9aa19bdcf841407a1d9fd652e75c893f83039fb7a9fc'),
 '320213':('wuxi-liangxi-own-source','district','99252fdc0c19337ca951da479b217407d3e1c4b95f87021106c8cc77d8d3d90c','31fa5a6699e80e6211e8af4af90b854770c324ac5005e8f6e089564084116bae'),
 '320214':('wuxi-xinwu-own-source','district','05b5dbc75ee3c33f896046a9ab1205b30122a1c56314f8ec828886cbc998b6ff','745dcb371dd90be2c84dfdef73c31d284815f1659ad47563b6638a7d473d6668'),
 '320292':('wuxi-edz-own-source','functional_area','d547975bfa08f5dc16667910f2984b876b81d6e56ad8c2190cc669e522e53508','5386a7e17da9e0e2f25808ed2df8f5c46486fc2a54fdb39a0b86a92c9d8475b4'),
 '320585':('suzhou-taicang-own-source','district','070a60c3ce71d02ba606f22a5352fe7869dbd9a306779ac40ffd0f4cfdcf4a84','f779b268a4e476e81066c538e112a415655004a941f6df41aa90653b898af184'),
 '320590':('suzhou-industrial-park-own-source','functional_area','8e1147b6c998732e64e519c08b821db459fd13ac8c2d88e0296e8ea1f91add8c','791888911781c1cef54c9bd85b50eb5b8524a8b62f0948264254c598b349afbb'),
 '320104':('nanjing-qinhuai-own-source','district','8d97ae2dfc07f52dd8058a7fc904b0248471c46496b02ea549775676668e72d4','ea731a7a958b938aa2e28a4c19099d40e185ddb2a06ff722423806fb5dc9c51d'),
 '320105':('nanjing-jianye-own-source','district','5900d5d4b2d404e62ba8ff68ba8c64976cee1ec3932709c9ebaae4e88be77cea','a21114dcb5f149a3f5fafae921d262dec9a1c4de2ac482cc9d8eedd33ca2ac3f'),
 '320106':('nanjing-gulou-own-source','district','9d167f15e179e903b7a44091082eea7312a8f41b438a2a4a2e726a87235c905b','ae8a1e7795f297944c96dc1ead405269a994d9f41a49803aa0a5b9fd5a567614'),
 '320102':('nanjing-xuanwu-own-source','district','65b8f6ca542563fce642fac03a7287b1d09f99259b0898b19e0dca0c65c35394','6a018be169c15a042cf16262155632623160612c185762407f9ca0d65182c866'),
 '320113':('nanjing-qixia-own-source','district','7f047779de042ebfc20ff57547ab2c3fe19fb01aaebaa0839d3016cd93641465','5f4ee06be030bf0d4803c41f05bae4db7e499c7e9a13c5126ea9d4867c44452a'),
 '320114':('nanjing-yuhuatai-own-source','district','5f79ff1833dffd70628e4fd63e23b94cf4262ebac4ddb9b07a12c2f556fef03e','a8b5bea8da17a897b9e26acb1d2b8a29c17e08b132a8702a52f4cef3cebd14c9'),
 '320115':('nanjing-jiangning-own-source','district','c9d327ae3b65e1adfd2322bf812a9f14a315a4798f1f460e1951da89740ca7f8','9c6ccaeebb504f1a172a29b7ebb4535745013318ae3fc9f59471492b2702b5cb'),
 '320117':('nanjing-lishui-own-source','district','d59be6ffe6c8b9bb6b0ae7c471369fd506244b98949a718c6219703903581926','d0053dc3192ce52f4fc14ad4eb3c712a49b224f4ebff647294def2f08d3867c4'),
 '320118':('nanjing-gaochun-own-source','district','d84d7a25d1d42c1ede25428802ee0634dbf1f98671ddaf19ab01e4c0378d67cb','e1e92a55cc89596290f193e714e33665d9270e74aba79293e112d2ee27e6665f'),
}
EXACT_SOURCES={
    LIANYUNGANG_CODE:('连云港市','市本级',LIANYUNGANG_SOURCE_ID,{
        'bcc67aa2-7b47-4cc2-92e6-3aaf581aa901':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'eb850eb4-d57a-47e3-9fc9-45f719d582be':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320300':('徐州市','市本级','dd3ac475c600106bea879583',{
        '28a69aad-d74b-47a8-93a4-48788d60f332':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '6e67dfad-ebaa-40cf-b9ac-a15dbea3505d':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320800':('淮安市','市本级','632425a93185f0f45d827cac',{
        '5d1ce46e-2878-4454-aad3-d45e6173c871':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '1d721abe-2ab6-454e-b73b-0518bbc66cfc':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320900':('盐城市','市本级','6b119ec8140e1d3ed38c25c3',{
        '8a193295-0ccd-498b-8b0c-a461d2859c9f':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '0976ca90-3679-4634-b1e6-4ca2e21e1a35':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320205':('无锡市','锡山区',SOURCE_ID,BINDINGS),
    # Own county guide, own eight downloaded annexes; same file bytes alone
    # never authorize another locality or another annex.
    '320925':('盐城市','建湖县','ef1eb897ebf880c6f2a316f5',{
        '985f4770-1ab2-4264-9482-0f8528b16513':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '586cf49f-714b-4338-81ce-08a2956d7aa6':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    # Own Dafeng formal guide and eight independently fetched attachments.
    '320904':('盐城市','大丰区','5725c8df9cb686d0517254e8',{
        '8984153f-2c04-4676-a8fd-3a627658fb9d':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'b104e1d9-15a7-489a-ad8b-80e22e0673e7':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    # Own Haizhou formal source, separately downloaded and visually reviewed.
    '320706':('连云港市','海州区','f2208816780787a1a046b91f',{
        '50286982-5aaa-4310-b593-5767344cea86':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '2a18398d-be86-4613-a878-e17ed90f0354':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    # Own Yandu/Tinghu guides and independently downloaded blank annexes.
    # Evidence-copy and identity-copy title-only placeholders are excluded.
    '320903':('盐城市','盐都区','4abd1f31894593b284955389',{
        '73bc8138-5dba-4b3f-ae15-9f8d3f90b717':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'c99c9cba-a1f6-4107-9084-45adbb9002da':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320902':('盐城市','亭湖区','15dd894fabf31dd87c1eeff9',{
        'b2ef8a79-637b-4c49-bbbd-82f0082c2bbf':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '103d2584-4128-49dc-a177-72bb3904afa2':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    # Own Dongtai/Sheyang captures and independently fetched public originals.
    '320981':('盐城市','东台市','5e53e6d3179046433e5fdcb8',{
        'd5a8d1f0-ba28-4fa3-8e0d-0c12fb5e8120':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '5d848c02-a62a-4686-9f25-2e320b1b32ae':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320924':('盐城市','射阳县','69952614ad2cf51d91ee7460',{
        '85e7e12b-18a8-458f-90f5-5a9ea44439a1':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'c3833b5a-b6ea-40aa-a3ff-905a50e83a4d':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    # Own Binhai/Xiangshui sources; each annex was independently downloaded.
    '320922':('盐城市','滨海县','b9c51355dc6355e19cdd6c34',{
        'a0b76715-d491-4a89-8d3d-e08462f1f0f4':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '5008f178-fe89-4f89-9839-4b6b69eef95b':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320921':('盐城市','响水县','91b561d2d26a3dd2fa679983',{
        'cb2d28f4-a4d8-4633-9e89-238ebe8604ac':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '59d0356b-d251-4424-9a29-17f0491edc19':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '321000':('扬州市','市本级','8c8aaf5af507c4ae65d8b7ea',{
        'cb95bc3e-68cc-43a1-b409-da2e6f324fd3':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'e8b97aa9-2475-4fb4-bf55-99f690b725c1':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '321100':('镇江市','市本级','27626805973015340d56732b',{
        '456ed620-c6d4-45d6-838f-e086fceb814c':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '0490fd04-5659-4479-9680-57aa5ffa3349':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '321200':('泰州市','市本级','b9d1e481edaa0219e36312fa',{
        '1a094502-26db-4208-be47-11f3fce8fb58':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'd29f0a2b-dc5f-451b-99db-be8a26ff55f4':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '321300':('宿迁市','市本级','d976408fd03de4277b278053',{
        'b882276a-02d6-49cb-80f6-3b8e26c704fd':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '224056b1-b2b2-4abf-9ac4-63c1e700e0aa':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320100':('南京市','市本级','d93582141e3316c4c481ffbc',{
        '726e5815-4417-4e53-8e9e-1f68acbe748a':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '8b762eb1-770a-47f5-bba3-659ccb4b4df6':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320200':('无锡市','市本级','7ae202cc5af7b2b8db835c1d',{
        '597afb1e-1da3-4004-a863-3ce44db8ca2f':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'ac2cbf44-10a8-4424-a097-97d8aebb85aa':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320400':('常州市','市本级','9e8d445cba18341a2a84a74a',{
        '5fbef6ff-26cc-41a3-ba18-ae93a402892d':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '24b6ad01-aafd-4ce6-b6e2-cd625bad7638':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320500':('苏州市','市本级','6ee84910096097334c275d64',{
        'ff27ba51-7f54-4e23-ab80-f0037ba11367':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'f04db924-03ea-463a-918f-21c926bb23f2':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320600':('南通市','市本级','c3bef84e98a9d6ca2afe986a',{
        '5b040d4e-663b-4860-bcef-d8c12cf54741':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'c8260c13-5490-40f7-9be7-3071bb957c58':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320804':('淮安市','淮阴区','af10b6358a0cea5389de88b7',{
        'eca65f46-5178-4c29-a6f5-cea523aa5595':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '857d0650-f222-465d-9687-54459d9e3bb0':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320813':('淮安市','洪泽区','353f307d6c7fc7e41924a8cf',{
        'db154c19-9478-4644-9120-2a9bf727c70b':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '70b69cb8-9011-464c-b31c-15bc6339e391':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320871':('淮安市','经济开发区','d80293457ba981b81997c7f9',{
        'e3661b6a-1991-4fa4-9471-4f5975d7586a':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '2d24580f-7c60-4ac0-880d-fc3437ba71be':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320830':('淮安市','盱眙县','70ab0102a5469dbbfa060551',{
        '393e1c03-9727-4099-a8b9-0948596ec8e5':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '342980c8-2a11-4917-9124-d02f0bd28e60':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320703':('连云港市','连云区','43affed1b2f460165b7d11d0',{
        'd00271ab-a748-47c3-84d4-172f3c9ba531':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'c56e13df-1ad6-403b-997d-a80c51a1e8dd':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320707':('连云港市','赣榆区','2846cc27d49c263550444626',{
        'c6b17cfe-c40b-4f0b-be2b-9319b0448042':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '7c4cb9c1-016c-478d-ad15-828edecc8d60':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320722':('连云港市','东海县','2e7e7fa46c45730b32762bea',{
        'fcfd5b3f-0595-4b98-bda3-bdfaf0ea0c57':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'c1aea292-44c1-4c7b-8eb6-8d4e415eda96':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320723':('连云港市','灌云县','b329533cd5ca25e92a69f081',{
        'a49c5d14-2f99-4594-a68e-af0c524813ec':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        '8b9768fb-77c5-41e2-9a3b-0a0566596ee7':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320724':('连云港市','灌南县','89ac4e45ae810866811cf20e',{
        '526eb9d5-f756-4c3d-a2d5-50abcff3dc2b':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'c62b7731-21df-43cf-883a-907d1fa3ac68':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
    '320771':('连云港市','经济开发区','358a2d7a25da49bd5e51dea0',{
        '27a93b11-b2d2-4668-a1d3-6d43903bb787':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
        'a457b10c-74fe-4d3c-ae83-f3dedcc419f1':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'),
    }),
 '320302':('徐州市','鼓楼区','e1342562632579ac5f32aaa0',{
    'ca661200-f1f2-4b96-8ffd-599582d67bb3':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'c53b1d76-ace8-4cfb-be16-55b5c0195457':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320303':('徐州市','云龙区','343d1bc839fee96beefbe2e3',{
    '5fe62cc7-974d-4731-8a9e-6ab4cc00f549':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'e0cdb850-aea7-4189-b982-b563c08ff372':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320305':('徐州市','贾汪区','b3eb9f21c007ba0b14abef76',{
    '7c8d87a6-9978-4c1d-a9bd-c258ffc7edd7':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '24ada876-fe3a-4e29-9ea4-c6639149efd0':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320312':('徐州市','铜山区','2d647bb6acf5a4a6f1d6c81a',{
    '787e934f-1526-4081-ba1b-c787801f54f6':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '8b0ceaf3-0696-48ca-a02c-5f7345792649':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320321':('徐州市','丰县','6523327f018a58fffc5f1e5e',{
    '10a8ef9b-dff0-4fb2-8d85-902d8f42e6cf':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'bb897fd3-e822-43f5-9074-e50cbd56d12a':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320322':('徐州市','沛县','b79b5838dfd99e297b127f05',{
    '249c5be1-ddbe-4dd1-b7a3-e30a6a8e1bdf':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '1594c8ba-1c01-400b-9f0d-d5663877f61d':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320324':('徐州市','睢宁县','5d71b17ee619a49ab0b3e47a',{
    'eb891ead-804a-4718-ad78-28109de610a3':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'bd2224b9-7a18-4436-9fc1-325dfbb94e9b':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320381':('徐州市','新沂市','020c3850ed4cd886ff0d2739',{
    '4b37d83f-2bc2-4bb9-aaa3-e4fb69c76bab':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '8a03c432-a9fc-46c6-8652-3f62d9eb6dde':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320382':('徐州市','邳州市','d2a0a2956e6a022d7bef2cf7',{
    'b02a3340-4ef3-4230-84f0-39b595fd94b0':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'fd36a7f6-e516-4d36-bbab-62b09fef3538':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320902':('盐城市','亭湖区','d56231312b263cd2c5a42b96',{
    'b2ef8a79-637b-4c49-bbbd-82f0082c2bbf':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '103d2584-4128-49dc-a177-72bb3904afa2':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320903':('盐城市','盐都区','56d382f2893c03e7c7e2fbd6',{
    '73bc8138-5dba-4b3f-ae15-9f8d3f90b717':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'c99c9cba-a1f6-4107-9084-45adbb9002da':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320921':('盐城市','响水县','7d83756f2c94a39e125a20aa',{
    'cb2d28f4-a4d8-4633-9e89-238ebe8604ac':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '59d0356b-d251-4424-9a29-17f0491edc19':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320922':('盐城市','滨海县','07a281abbc4c6050825a9534',{
    'a0b76715-d491-4a89-8d3d-e08462f1f0f4':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '5008f178-fe89-4f89-9839-4b6b69eef95b':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320924':('盐城市','射阳县','cd4add4b09c7631a71b0d02f',{
    '85e7e12b-18a8-458f-90f5-5a9ea44439a1':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'c3833b5a-b6ea-40aa-a3ff-905a50e83a4d':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320981':('盐城市','东台市','0b0e7b33454afdc0221e164e',{
    'd5a8d1f0-ba28-4fa3-8e0d-0c12fb5e8120':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '5d848c02-a62a-4686-9f25-2e320b1b32ae':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320971':('盐城市','盐城开发区','cfdea0ddc6c9122dd461f617',{
    '7b18187c-ed1a-4b52-917f-d46bb1850af6':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'db8d22b6-69d6-429b-8a7e-1b6c65b8eff8':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321302':('宿迁市','宿城区','7fb7dc52dbd885bd96986222',{
    'ff3e6b45-0e9a-40a3-b3ce-d726c559b76d':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '613a5382-bee5-4fca-a3eb-d15444d222d0':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321311':('宿迁市','宿豫区','3651193e96ffa65fcbbdd653',{
    '5990c48c-6204-433d-9b10-e382b38889a3':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '32d04f5e-cf97-4ea5-9f81-3717ef74d558':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321322':('宿迁市','沭阳县','3ccf422d02539ed77d426823',{
    '08873dcb-d051-45ca-9277-f6923c2c0df0':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '5202a3a3-78af-4e85-9968-7c5994b31624':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321323':('宿迁市','泗阳县','af0c7311cc4d8d7e65d2349c',{
    '5a3a4f0b-a665-49bf-b12f-3d9ce6c08239':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'f981c5e8-237d-4eec-be77-085706efad35':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321324':('宿迁市','泗洪县','f4129dbab8e0725575533aee',{
    '85458054-1daf-41d1-86b1-acb05993c2ad':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'd0186fb3-94db-467c-b6a0-423402654089':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321325':('宿迁市','市湖滨新城','1666941b0227accabfd693bc',{
    'f7852470-a737-4c9f-be71-b237a494b7d1':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'fb30f08f-d847-4bca-a05b-013c09e77e5c':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321392':('宿迁市','苏州宿迁工业园区','99b9ee49afeb34982c4cba87',{
    'fd50790b-1455-4cf2-ae3f-6810ed58c3fb':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '3e9bf615-0fa2-4279-a43d-7d0e58419b10':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321002':('扬州市','广陵区','6de416b60f069c12cc5794c9',{
    '2af62df3-be3f-463a-81a3-b23ffb9be32b':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '2992e2e4-12a8-421d-b384-eaa22adb4a0c':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321003':('扬州市','邗江区','bbe69ce71284ba9c1c9d172f',{
    'c07338df-d292-4048-a97f-3e97641e9b10':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'e7c1e164-5ebb-4d89-a751-c222cb3ea50d':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321012':('扬州市','江都区','9247a2c6de01992d26bb57b5',{
    '688996b7-078a-43f7-ba4f-67bff2cd6426':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'e29a732c-b7e6-4324-9ba6-a6c97c61e3d0':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321023':('扬州市','宝应县','35c349b3ff699b188ad7cc46',{
    '89baa947-8627-4383-8bff-a0c045d0c827':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '156fa24b-782d-4775-aaa4-3d1371e05be5':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321084':('扬州市','高邮市','b90a43c2a0cc8c0acb5c6516',{
    '7d1c471c-2cca-4cba-a789-da6b3bee285b':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '1db32a56-164a-4f1a-90c7-2cd1397c1f5c':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320613':('南通市','崇川区','1c3e1b1b5b4841a3fc4cc60a',{
    'cb669356-efc2-48b9-895d-f449c807c17a':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'a3378d5e-a37c-4969-88b4-ca217fc71986':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320612':('南通市','通州区','b56cff9f6b1e5da25b02ec6d',{
    '583bbb1b-37f8-4cc6-b26d-438428da4072':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '4db99020-0b45-4805-bed2-79cf14e9c388':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320685':('南通市','海安市','9cfe280a096cd41035d85b91',{
    'd9f23630-2121-4f9c-96ba-8a14f1bf5138':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '61b6ae9f-1495-45bc-9db5-8ca9e9a00392':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320623':('南通市','如东县','ea97908d9e453ef904316e6f',{
    '3ed2162d-26c7-4314-b51e-998c2d5bdabf':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'c5ee786c-ee35-4166-a865-981a332aabea':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320681':('南通市','启东市','abf05466ec62053aecfe1b04',{
    '47a13e91-b667-4599-aad3-c01f3bd90417':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'fe2a393b-ee05-4197-abeb-a8d6be4f48ed':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320682':('南通市','如皋市','a629b2cb8743aeaeeb37b4e3',{
    'c3b37bd5-614e-46f4-8f43-9162d9e48419':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '289ce92c-e82f-457e-914d-634d97aef332':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320614':('南通市','海门区','b3ba940d72bebe2edaa50d97',{
    '8d82918d-9572-404c-89d6-6a7a2f296316':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'dd5c213b-0c86-45c9-a169-31e7f0a92a35':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320693':('南通市','苏锡通','2446c985a8e4028bc4729f14',{
    '92e37500-fd55-4a4b-a256-5af92a57909a':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '188616cb-8599-4c75-beca-834623fff1f5':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321102':('镇江市','京口区','cb673500cd75bfe69de5e78b',{
    '79e18b27-0e6d-4e1f-9b83-40690e6cee1e':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '66bb003d-40ff-4f4f-9946-c7e1d3cb473a':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321111':('镇江市','润州区','4223ab831f52e1afbc0bc376',{
    '58a27495-07b2-4c3b-a393-6857877c4f16':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '5ff1ef03-df01-468e-b70b-12b640f81dfb':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321112':('镇江市','丹徒区','34086ef3a9f8af8995c22fd5',{
    '8335e104-614a-42bd-804d-5198d889fde2':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '80c5cacb-31a4-4de0-96f1-1d05cdec2bec':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321181':('镇江市','丹阳市','88f8a7fab3a029da739d7759',{
    '0ddb0e56-9ebf-438c-8f4f-4aba1dd901cd':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '2b489fa8-be63-4fb6-99c7-04948b3f866f':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321182':('镇江市','扬中市','6faa24fecb0f43577eb71b76',{
    '5aa121be-5f9c-410b-ba5d-623102c98a04':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '853c7d53-dd54-4b50-863c-c23ec84baefe':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321202':('泰州市','海陵区','75350ea6969cb0b55633fffa',{
    '04cd6da4-4a0f-4963-a2c5-566646f1202e':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'f2ea5304-5dd6-481c-aca7-7b6a006c1ccd':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321203':('泰州市','高港区','4779366e0fc515afee109eb2',{
    'e1c771ad-8591-4712-8bfb-7b4b0249a319':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '32f732a0-a6c3-4b7d-a7fe-9bd810762624':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321204':('泰州市','姜堰区','0e793fcf14a99306d4a8150d',{
    '326a25a4-b666-4bb9-906d-77bda0902745':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3')}),
 '321281':('泰州市','兴化市','d60aa7fc858807793aacd5fc',{
    'eb3965fc-4b99-43b8-9468-0a6ae2dc408c':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'b20aab9e-9914-45df-a0a2-638ad8d80e46':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321282':('泰州市','靖江市','b013e0a468eedaa0271af6b3',{
    '63042073-5235-4d52-91f3-335b802508a4':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'ab85e126-a6a5-4eb1-ae0c-a1b0498a6687':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '321283':('泰州市','泰兴市','896936fec0edc7f820d3d1f8',{
    'a0509eef-f50d-411c-9760-1031f4a7a455':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '98afe763-7824-4414-9e44-1ea4750d6bcd':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320402':('常州市','天宁区','e39c9ffd79563821016f0bac',{
    'ce7347c3-9e8b-4c10-b295-97999321f710':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'd0d0588b-0586-4e9b-9bba-4291b2d9636a':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320404':('常州市','钟楼区','81386cd870bc1302c9be58b6',{
    '3cfba7f8-d1e9-4f29-a4d9-d68b0aae1470':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'ea51d49d-454c-4a75-960a-be34a3f7a9f1':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320481':('常州市','溧阳市','9c6fe7efa0a96db41d1ba41e',{
    '265ec962-29f4-4cd7-80af-728e7d339a2b':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '6ece6338-906f-420d-b401-db0082a6001e':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320413':('常州市','金坛区','73ccdcd47f33754e4fba164c',{
    '7c921ce6-43ed-43fe-8c02-ee584dfece7a':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'a5296113-81cb-438b-86f2-9e85761a39da':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320206':('无锡市','惠山区','54e5e7c2742c7957c8ffeaab',{
    'c82fa538-5ffb-4673-a362-91175e049d12':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '3afc1297-9e14-49d6-b2fb-2bfac66346d1':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320211':('无锡市','滨湖区','197d3d1aaeca692cce9d43de',{
    '6bfe76e1-90d8-4009-b6e1-df4d0491997a':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '92d30519-96ad-4a39-a3c4-6c8a87c19f40':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320213':('无锡市','梁溪区','9eadb99cc598993e8e9bc93b',{
    '9c46cc60-ede3-4d34-b818-17c6c2f7cfc0':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'cfebf172-bb48-497b-a994-6b78643f6d44':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320214':('无锡市','新吴区','e17ee662008caa98a507f07c',{
    '94e2383c-b816-4a53-a2a2-b72800d97afd':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '5ca17072-fad9-4e42-ac9d-b4d3e3691673':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320292':('无锡市','经济开发区','8b7685fe81e6e7e82758b218',{
    'c01bf318-d976-4d60-89a0-b0e87945c6b0':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '95774b46-0f4e-4b96-b0a5-1c0c841bc57a':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320585':('苏州市','太仓市','5a7d8504ff500321b04e076f',{
    '3962a0b5-9808-48fc-8c6b-a635cdd7d644':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '02c2d0d4-b08e-4071-a273-6baed007532c':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320590':('苏州市','工业园区','866205b79a0218e31aa4812d',{
    '5b8d38c4-49b6-4de8-adad-549f5c79ae7b':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '19e8b533-37a9-41f8-889b-886a4cf9781d':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320104':('南京市','秦淮区','2301e52ded0f1c2a6ff69589',{
    '13e52e45-e608-4c2a-8680-6974b5ce7240':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '6f0c5082-f09e-4c63-b2ae-cea27b617bda':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320105':('南京市','建邺区','371ce70b35260711073880bc',{
    'e70300d8-f5db-41b7-8335-7fb96dcec831':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '8c2b5f25-f760-4d58-a5dc-3513875637da':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320106':('南京市','鼓楼区','f7a64fa92a3851f56a9b89e8',{
    '22330733-e351-486e-9f4a-af67e2e04e5c':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '1d208301-c481-486d-abb9-57fed2299d89':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320102':('南京市','玄武区','61b9be6ddf4ffaa18dffa799',{
    '6213e5bb-700e-40e8-a830-947ca78aa6f9':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3')}),
 '320113':('南京市','栖霞区','b42fc4cfe005e506354b7f48',{
    'e9a6fb10-0302-4817-9538-318a739f83be':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '4dc0c076-fed7-4221-a2a3-537d39bf7f7a':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320114':('南京市','雨花台区','c07ce7c97715dd6319f2614e',{
    '0ed5fd93-b609-4add-adf0-86789ae549eb':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'f0e6b711-159c-434d-acc2-a2dc68e0ca64':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320115':('南京市','江宁区','a9703795e53724dfc0d2f860',{
    '227f4213-20bd-46dd-9f8a-881792bb48ff':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '396f76f5-38d7-488f-8911-e5118b075fd3':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320117':('南京市','溧水区','5447c1fb96d1d6594aa857e8',{
    '56d3bf6d-64a8-4b94-a2c6-6a8bd31a0f6d':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    'a8050d0e-9afa-4486-824c-2be060248008':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
 '320118':('南京市','高淳区','d1c79a2e8e0ef7eaa086b36c',{
    '289722ff-3a57-40e0-8399-ee971579425e':('application','99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'),
    '689e53e3-0538-4d72-b175-682424c9853d':('evidence','c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c')}),
}
EXACT_IDENTITIES={
    LIANYUNGANG_CODE:('连云港市人力资源和社会保障局','11320700014252938G300201430200201'),
    '320300':('徐州市人力资源和社会保障局','11320300014052557Y300201430200201'),
    '320800':('淮安市人力资源和社会保障局','113208000142899330300201430200201'),
    '320900':('盐城市人力资源和社会保障局','1132090001435503X1300201430200201'),
    '320903':('盐城市盐都区人力资源与社会保障局','11320928562941566D400201430200201'),
    '320902':('盐城市亭湖区人力资源和社会保障局','11320902014360656E400201430200201'),
    '320981':('盐城市东台市人力资源和社会保障局','11320981014396886W400201430200201'),
    '320924':('射阳县人力资源和社会保障局','11320924737070337G400201430200201'),
    '320922':('滨海县人力资源和社会保障局','11320922014374388A400201430200201'),
    '320921':('响水县人力资源和社会保障局','113209215754155300400201430200201'),
    '321000':('扬州市人力资源和社会保障局','113210000144063193300201430200201'),
    '321100':('镇江市人力资源和社会保障局','11321100014467082E300201430200201'),
    '321200':('泰州市人力资源和社会保障局','113212000144165255300201430200201'),
    '321300':('宿迁市人力资源和社会保障局','1132130055462291XB300201430200201'),
    '320100':('南京市人力资源和社会保障局','113201005555063120300201430200201'),
    '320200':('无锡市人力资源和社会保障局','11320200014008089B300201430200201'),
    '320400':('常州市人力资源社会保障局','11320400014110315K300201430200201'),
    '320500':('苏州市人力资源和社会保障局','11320500014152347F300201430200201'),
    '320600':('南通市人力资源和社会保障局','11320600014207133U300201430200201'),
    '320804':('淮安市淮阴区人力资源和社会保障局','11320821014304750B400201430200201'),
    '320813':('淮安市洪泽区人力资源和社会保障局','11320829014341463H400201430200201'),
    '320871':('淮安经济技术开发区人力资源和社会保障局','11320800K12654517X400201430200201'),
    '320830':('盱眙县人力资源和社会保障局','11320830014345835M400201430200201'),
    '320703':('连云港连云区人力资源和社会保障局','113207030142582646400201430200201'),
    '320707':('连云港市赣榆区人社局','11320707562978836D400201430200201'),
    '320722':('东海县人力资源和社会保障局','11320722570382987L400201430200201'),
    '320723':('连云港灌云县人社局','11320723014288930L400201430200201'),
    '320724':('灌南县人力资源和社会保障局','113207240143092872400201430200201'),
    '320771':('连云港经济技术开发区人力资源和社会保障局','11320708MB1A74924R400201430200201'),
 '320302':('徐州市鼓楼区人力资源和社会保障局','11320302014058019W400201430200201'),
 '320303':('徐州市云龙区人力资源和社会保障局','11320303014062499N400201430200201'),
 '320305':('徐州市贾汪区人力资源和社会保障局','113203050140711415400201430200201'),
 '320312':('徐州市铜山区人力资源和社会保障局','11320323014088744W400201430200201'),
 '320321':('丰县人力资源和社会保障局','11320321561801182G400201430200201'),
 '320322':('沛县人力资源和社会保障局','11320322014085105M400201430200201'),
 '320324':('睢宁县人力资源和社会保障局','11320324014093076G400201430200201'),
 '320381':('新沂市人力资源与社会保障局','113203810141088056400201430200201'),
 '320382':('邳州市人力资源和社会保障局','11320382014097421F400201430200201'),
 '320902':('盐城市亭湖区人力资源和社会保障局','11320902014360656E400201430200201'),
 '320903':('盐城市盐都区人力资源与社会保障局','11320928562941566D400201430200201'),
 '320921':('响水县人力资源和社会保障局','113209215754155300400201430200201'),
 '320922':('滨海县人力资源和社会保障局','11320922014374388A400201430200201'),
 '320924':('射阳县人力资源和社会保障局','11320924737070337G400201430200201'),
 '320981':('盐城市东台市人力资源和社会保障局','11320981014396886W400201430200201'),
 '320971':('盐城经济技术开发区组织部（人力资源和社会保障社局）','11320900MB03383358400201430200201'),
 '321302':('宿城区人力资源和社会保障局','11321302014320013D400201430200201'),
 '321311':('宿豫区人力资源和社会保障局','11321321014320523B400201430200201'),
 '321322':('沭阳县人力资源和社会保障局','113213220143140787400201430200201'),
 '321323':('泗阳县人社局','11321323014322932B400201430200201'),
 '321324':('泗洪县人力资源和社会保障局','11321324557085689K400201430200201'),
 '321325':('宿迁市湖滨新区政法和社会管理办公室','TE321325XXX8001032400201430200201'),
 '321392':('苏州宿迁工业园区劳动保障和社会事业局','11321300016184991A400201430200201'),
 '321002':('扬州市广陵区人力资源和社会保障局','113210020144111853400201430200201'),
 '321003':('扬州市邗江区人力资源和社会保障局','11321027014455276X400201430200201'),
 '321012':('扬州市江都区人社局','1132108801444901X4400201430200201'),
 '321023':('宝应县人力资源和社会保障局','11321023014433130R400201430200201'),
 '321084':('高邮市人力资源和社会保障局','11321084014427208M400201430200201'),
 '320613':('南通市崇川区人力资源和社会保障局','11320602014208515T400201430200201'),
 '320612':('南通市通州区人力资源和社会保障局','11320683555858940W400201430200201'),
 '320685':('海安市人力资源和社会保障局','11320621014223336G400201430200201'),
 '320623':('如东县人力资源和社会保障局','11320623014236006N400201430200201'),
 '320681':('启东市人力资源和社会保障局','113206810142471511400201430200201'),
 '320682':('如皋市人力资源和社会保障局','11320682552486117F400201430200201'),
 '320614':('南通市海门区人力资源和社会保障局','11320684014245260H400201430200201'),
 '320693':('江苏南通苏锡通科技产业园区政法和社会事业局','11320600MB1K253397400201430200201'),
 '321102':('镇江市京口区人力资源和社会保障局','113211020144727977400201430200201'),
 '321111':('镇江市润州区人力资源和社会保障局','11321111014477192T400201430200201'),
 '321112':('镇江市丹徒区人力资源和社会保障局','11321121553805554K400201430200201'),
 '321181':('丹阳市人力资源和社会保障局','113211810144872785400201430200201'),
 '321182':('扬中市人力资源和社会保障局','11321182554623867C400201430200201'),
 '321202':('海陵区人力资源和社会保障局','113212020144194353400201430200201'),
 '321203':('泰州医药高新区（高港区）社会事业和退役军人事务局','11321203014420962E400201430200201'),
 '321204':('泰州市姜堰区人力资源和社会保障局','1132128401445680X3400201430200201'),
 '321281':('兴化市人力资源和社会保障局','113212810144222044400201430200201'),
 '321282':('靖江市人力资源和社会保障局','113212825546012547400201430200201'),
 '321283':('泰兴市人力资源和社会保障局','11321283014441886R400201430200201'),
 '320402':('天宁区人力资源和社会保障局','11320402014115036Q400201430200201'),
 '320404':('常州市钟楼区人力资源和社会保障局','11320404014119504M400201430200201'),
 '320481':('常州市溧阳市人力资源和社会保障局','123204814674542847400201430200201'),
 '320413':('常州市金坛区人力资源和社会保障局','11320482014138916T400201430200201'),
 '320206':('无锡市惠山区人力资源和社会保障局','113202060140358023400201430200201'),
 '320211':('无锡市滨湖区人力资源和社会保障局','113202120140289874400201430200201'),
 '320213':('无锡市梁溪区人力资源和社会保障局','11320213MB046223X2400201430200201'),
 '320214':('无锡国家高新技术产业开发区（无锡市新吴区）人力资源和社会保障局','11320214MB0376841Y400201430200201'),
 '320292':('江苏无锡经济开发区社会事业局','11320200MB1911084Q400201430200201'),
 '320585':('苏州太仓市人社局','113205850141850345400201430200201'),
 '320590':('苏州工业园区人力资源和社会保障局','12320500X08243760H400201430200201'),
 '320104':('南京市秦淮区人力资源和社会保障局','113201045588672603400201430200201'),
 '320105':('南京市建邺区人力资源和社会保障局','11320105012989370J400201430200201'),
 '320106':('南京市鼓楼区人力资源和社会保障局','1132010601299804X7400201430200201'),
 '320102':('南京市玄武区人力资源和社会保障局','113201020129658707400201430200201'),
 '320113':('栖霞区人力资源和社会保障局','1132011301303324X3400201430200201'),
 '320114':('南京市雨花台区人力资源和社会保障局','11320114558892685X400201430200201'),
 '320115':('南京市江宁区人力资源和社会保障局','11320115558867092Y400201430200201'),
 '320117':('南京市溧水区人力资源和社会保障局','113201240130892785400201430200201'),
 '320118':('南京市高淳区人力资源和社会保障局','11320125013101345P400201430200201'),
}


def _candidate_proof(code):
    if code in MUNICIPAL_PROOFS:
        slug, guide_sha256, word_sha256 = MUNICIPAL_PROOFS[code]
        return f'{slug}-municipal-own-source', 'municipal', guide_sha256, word_sha256
    return LOCAL_PROOFS.get(code)


def _candidate_word_receipt(folder, word_sha256):
    return {'file': (CANDIDATE_BASE / folder / 'WORD-PREFLIGHT.json').as_posix(),
            'sha256': word_sha256}


def _is_jiangsu_candidate(guide, proof):
    code = guide.get('region_code')
    folder, scope, guide_sha256, word_sha256 = proof
    city, district, source_id, _ = EXACT_SOURCES[code]
    return (guide.get('province') == 'jiangsu' and guide.get('city') == city
            and guide.get('district') == district and guide.get('scope_level') == scope
            and guide.get('source_id') == source_id and guide.get('source_version') == guide_sha256
            and (guide.get('authority'), guide.get('service_code')) == EXACT_IDENTITIES[code]
            and guide.get('candidate_adapter_evidence') == _candidate_word_receipt(folder, word_sha256)
            and guide.get('published') is False)


def is_jiangsu_municipal_candidate(guide):
    code = guide.get('region_code')
    return code in MUNICIPAL_PROOFS and _is_jiangsu_candidate(guide, _candidate_proof(code))


def staged_jiangsu_locality(root, code):
    root = Path(root).resolve()
    proof = _candidate_proof(code)
    if proof is None:
        raise KeyError(code)
    folder, scope, guide_sha256, word_sha256 = proof
    word_receipt = _candidate_word_receipt(folder, word_sha256)
    guide_raw = (root / CANDIDATE_BASE / folder / 'GUIDE.json').read_bytes()
    word_raw = (root / word_receipt['file']).read_bytes()
    if (sha256(guide_raw).hexdigest(), sha256(word_raw).hexdigest()) != (guide_sha256, word_sha256):
        raise ValueError('地区指南或版式复核凭证不匹配')
    guide = json.loads(guide_raw)
    guide.update(source_version=guide_sha256, registration_status='CANDIDATE_ONLY',
                 publication_status='candidate', candidate_adapter_evidence=word_receipt)
    if guide.get('region_code') != code or not _is_jiangsu_candidate(guide, proof):
        raise ValueError('地区事项不匹配')
    area = f"{guide['city']}本级" if scope == 'municipal' else guide['district']
    for template in guide['templates']:
        kind = blank_binding(guide, template)
        if kind:
            path = root / template['file']
            if path.resolve() != path or sha256(path.read_bytes()).hexdigest() != template['sha256']:
                raise ValueError('地区原件路径或哈希不匹配')
            template.update(can_generate=True, adapter=ADAPTER, document_types=[kind],
                            content_kind='filled_official_blank',
                            generation_label=f'依据{area}官方空白表格填写')
    enabled = [t['id'] for t in guide['templates'] if t['can_generate']]
    if not enabled or sorted(enabled) != sorted(EXACT_SOURCES[code][3]):
        raise ValueError('地区空白文书适配不完整')
    guide['can_generate'] = True
    return guide


def staged_jiangsu_municipal(root, code):
    if code not in MUNICIPAL_PROOFS:
        raise KeyError(code)
    return staged_jiangsu_locality(root, code)


def staged_lianyungang_municipal(root):
    return staged_jiangsu_municipal(root, LIANYUNGANG_CODE)


def blank_binding(guide,template):
    code=guide.get('region_code');source=EXACT_SOURCES.get(code)
    if not source:return None
    city,district,source_id,bindings=source
    if (guide.get('province'),guide.get('city'),guide.get('district'))!=('jiangsu',city,district):
        return None
    proof = _candidate_proof(code)
    if proof and not _is_jiangsu_candidate(guide, proof):
        return None
    if guide.get('verification_status')!='verified' or digest(guide.get('source_url',''))[:24]!=source_id:
        return None
    if guide.get('source_id') not in {None,source_id}:return None
    if code in EXACT_IDENTITIES and (guide.get('authority'),guide.get('service_code'))!=EXACT_IDENTITIES[code]:
        return None
    binding=bindings.get(template.get('id'))
    if not binding:return None
    kind,checksum=binding
    expected={'annex_id':template['id'],'region_code':code,'sha256':checksum,'official_kind':'blank',
              'download_status':'downloaded','source_url':guide['source_url']}
    if any(template.get(k)!=v for k,v in expected.items()):return None
    if proof or code in {'320706','320903','320902','320981','320924','320922','320921'}:
        download=urlsplit(template.get('download_url',''))
        if (download.scheme!='https' or download.hostname!='sxgl.jszwfw.gov.cn' or download.port!=66
            or download.path!='/audit-qlk-web/rest/frame/pages/basic/attach/attachAction/getContent'
            or parse_qs(download.query).get('attachGuid')!=[template['id']]):return None
    path=Path(template.get('file',''))
    if path.parent.as_posix()!=f'templates/_docx/_regional/{code}' or not path.name.startswith(template['id']+'-') or path.suffix!='.docx':
        return None
    return kind


def fill_blank_document(guide,template,kind,path,data):
    if blank_binding(guide,template)!=kind:raise ValueError('空白表格与地区或文书种类不匹配')
    original=path.read_bytes()
    # The source's own bytes were independently downloaded and checked. The
    # profile selects field positions, never a province file or another region.
    data={**data}
    if kind=='evidence':
        data['evidenceList']=[{**item,'pageCount':re.sub(r'^\s*(\d+)\s*页\s*$',r'\1',str(item.get('pageCount','')))} for item in data.get('evidenceList',[])]
    elif data.get('copyCount') is None:data['copyCount']='    '
    document=(fill_application if kind=='application' else fill_evidence)(data,path,profile='JiangSuSheng')
    if kind=='application':
        for paragraph in document.paragraphs:
            match=re.search(r'相关证据(?P<slot>[\d \t]+)(?=份)',paragraph.text)
            if match:
                copies=data.get('evidenceCopyCount')
                replace_span(paragraph,match.start('slot'),match.end('slot'),str(copies) if copies is not None else '    ')
        # This own form has two empty paragraphs between addressee and signature.
        # Keep the entire closing block together without shrinking official type.
        closing=False
        for paragraph in document.paragraphs:
            compact=''.join(paragraph.text.split())
            if compact=='此致':closing=True
            if closing:
                if compact.endswith('日') and '年' in compact and '月' in compact:break
                paragraph.paragraph_format.keep_with_next=True
    return PreservedPackageDocument(document,original)
