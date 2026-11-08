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
    if sum(t['can_generate'] for t in guide['templates']) != 2:
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
