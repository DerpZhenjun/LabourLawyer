"""Explicit own-source blank forms. Sharing a field layout grants no jurisdiction."""
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
EXACT_SOURCES={
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
}
EXACT_IDENTITIES={
    '320903':('盐城市盐都区人力资源与社会保障局','11320928562941566D400201430200201'),
    '320902':('盐城市亭湖区人力资源和社会保障局','11320902014360656E400201430200201'),
    '320981':('盐城市东台市人力资源和社会保障局','11320981014396886W400201430200201'),
    '320924':('射阳县人力资源和社会保障局','11320924737070337G400201430200201'),
    '320922':('滨海县人力资源和社会保障局','11320922014374388A400201430200201'),
    '320921':('响水县人力资源和社会保障局','113209215754155300400201430200201'),
}


def blank_binding(guide,template):
    code=guide.get('region_code');source=EXACT_SOURCES.get(code)
    if not source:return None
    city,district,source_id,bindings=source
    if (guide.get('province'),guide.get('city'),guide.get('district'))!=('jiangsu',city,district):
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
    if code in {'320706','320903','320902','320981','320924','320922','320921'}:
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
