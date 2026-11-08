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
MUNICIPAL_BASE = Path('reports/overnight-gap-closure-20261030/localities')
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
}


def _municipal_word_receipt(slug, word_sha256):
    return {'file': (MUNICIPAL_BASE / f'{slug}-municipal-own-source/WORD-PREFLIGHT.json').as_posix(),
            'sha256': word_sha256}


def is_jiangsu_municipal_candidate(guide):
    code = guide.get('region_code')
    proof = MUNICIPAL_PROOFS.get(code)
    if not proof:
        return False
    slug, guide_sha256, word_sha256 = proof
    city, district, source_id, _ = EXACT_SOURCES[code]
    return (guide.get('province') == 'jiangsu' and guide.get('city') == city
            and guide.get('district') == district and guide.get('scope_level') == 'municipal'
            and guide.get('source_id') == source_id and guide.get('source_version') == guide_sha256
            and (guide.get('authority'), guide.get('service_code')) == EXACT_IDENTITIES[code]
            and guide.get('candidate_adapter_evidence') == _municipal_word_receipt(slug, word_sha256)
            and guide.get('published') is False)


def staged_jiangsu_municipal(root, code):
    root = Path(root).resolve()
    slug, guide_sha256, word_sha256 = MUNICIPAL_PROOFS[code]
    word_receipt = _municipal_word_receipt(slug, word_sha256)
    guide_raw = (root / MUNICIPAL_BASE / f'{slug}-municipal-own-source/GUIDE.json').read_bytes()
    word_raw = (root / word_receipt['file']).read_bytes()
    if (sha256(guide_raw).hexdigest(), sha256(word_raw).hexdigest()) != (guide_sha256, word_sha256):
        raise ValueError('市本级指南或版式复核凭证不匹配')
    guide = json.loads(guide_raw)
    guide.update(source_version=guide_sha256, registration_status='CANDIDATE_ONLY',
                 publication_status='candidate', candidate_adapter_evidence=word_receipt)
    if guide.get('region_code') != code or not is_jiangsu_municipal_candidate(guide):
        raise ValueError('市本级事项不匹配')
    for template in guide['templates']:
        kind = blank_binding(guide, template)
        if kind:
            path = root / template['file']
            if path.resolve() != path or sha256(path.read_bytes()).hexdigest() != template['sha256']:
                raise ValueError('市本级原件路径或哈希不匹配')
            template.update(can_generate=True, adapter=ADAPTER, document_types=[kind],
                            content_kind='filled_official_blank',
                            generation_label=f"依据{guide['city']}本级官方空白表格填写")
    if sum(t['can_generate'] for t in guide['templates']) != 2:
        raise ValueError('市本级空白文书适配不完整')
    guide['can_generate'] = True
    return guide


def staged_lianyungang_municipal(root):
    return staged_jiangsu_municipal(root, LIANYUNGANG_CODE)


def blank_binding(guide,template):
    code=guide.get('region_code');source=EXACT_SOURCES.get(code)
    if not source:return None
    city,district,source_id,bindings=source
    if (guide.get('province'),guide.get('city'),guide.get('district'))!=('jiangsu',city,district):
        return None
    if code in MUNICIPAL_PROOFS and not is_jiangsu_municipal_candidate(guide):
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
    if code in MUNICIPAL_PROOFS or code in {'320706','320903','320902','320981','320924','320922','320921'}:
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
