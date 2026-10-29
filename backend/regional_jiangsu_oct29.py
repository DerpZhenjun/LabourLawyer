"""Fixed own-source Jiangyin/Yixing blank forms; publication is a separate gate."""
import hashlib
from pathlib import Path
import re

from regional_guides import digest
from regional_documents import PreservedPackageDocument
from WenShu.exact_template_fill import fill_application, fill_evidence
from WenShu.template_fill import replace_span

ROOT=Path(__file__).resolve().parents[1]
ADAPTER='jiangsu_own_blank_oct29_v1'
SUPPORTED=frozenset({'320281','320282'})
APPLICATION_SHA='99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'
EVIDENCE_SHA='c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'
SPECS={
    '320281': {'district':'江阴市','authority':'江阴市人力资源和社会保障局',
               'task':'113202810140425947400201430200201',
               'source_url':'https://wxjy.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=39&iddept_ql_inf=1132028101404259474002014302002&ql_kind=20&iddept_yw_inf=113202810140425947400201430200201',
               'application':'2213bd5f-676c-4db0-9a4e-d9dd8b851919',
               'evidence':'32bdbf03-606b-4da1-8c7b-96179129625a'},
    '320282': {'district':'宜兴市','authority':'宜兴市人力资源和社会保障局',
               'task':'113202820140466759400201430200201',
               'source_url':'https://wxyx.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=40&iddept_ql_inf=1132028201404667594002014302002&ql_kind=20&iddept_yw_inf=113202820140466759400201430200201',
               'application':'9949cd24-29df-4db9-af04-b4395a22aa61',
               'evidence':'6adb479a-d85d-42e9-9e77-8ec7afb3f622'},
}


def _source(guide,kind):
    code=guide.get('region_code');spec=SPECS.get(code)
    if spec is None or kind not in {'application','evidence'}:
        raise ValueError('不是本批自身已核验的江苏文书')
    expected={'province':'jiangsu','city':'无锡市','district':spec['district'],
              'service_name':'劳动人事争议仲裁申请','source_title':'劳动人事争议仲裁申请',
              'authority':spec['authority'],'service_code':spec['task'],'source_url':spec['source_url'],
              'source_id':digest(spec['source_url'])[:24],'verification_status':'verified'}
    if any(guide.get(k)!=v for k,v in expected.items()):
        raise ValueError('自身地区、正式指南、事项或实施机关不匹配')
    for label,value in [('业务办理项编码',spec['task']),('实施主体',spec['authority'])]:
        if guide.get('fields',{}).get(label,{}).get('raw_value')!=value:
            raise ValueError('自身指南栏目身份不匹配')
    annex=spec[kind]
    templates=[t for t in guide.get('templates',[]) if t.get('id')==annex]
    if len(templates)!=1:raise ValueError('自身唯一空白附件缺失或重复')
    template=templates[0]
    material='劳动人事争议仲裁申请书' if kind=='application' else '劳动人事争议仲裁案件证据清单'
    name='劳动人事争议仲裁申请书.docx' if kind=='application' else '证据清单.docx'
    checksum=APPLICATION_SHA if kind=='application' else EVIDENCE_SHA
    relative=f'reports/nationwide-verification-20261029/jiangsu/{code}/originals/{annex}/{name}'
    expected_template={'id':annex,'annex_id':annex,'region_code':code,'source_url':spec['source_url'],
                       'material_id':digest([code,material])[:20], 'official_kind':'blank',
                       'download_status':'downloaded','original_name':name,'sha256':checksum,
                       'file':relative,'file_type':'docx',
                       'download_url':'https://sxgl.jszwfw.gov.cn:66/audit-qlk-web/rest/frame/pages/basic/attach/attachAction/getContent?isCommondto=true&attachGuid='+annex}
    if any(template.get(k)!=v for k,v in expected_template.items()):
        raise ValueError('自身空白附件来源、类别、SHA或固定路径不匹配')
    path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):raise ValueError('原件超出固定工作区')
    try:original=path.read_bytes()
    except OSError as exc:raise ValueError('自身已下载原件不可用') from exc
    if hashlib.sha256(original).hexdigest()!=checksum:
        raise ValueError('自身原件实际SHA不匹配，禁止填写')
    return template,path,original


def candidate_contract(guide):
    documents={}
    for kind in ['application','evidence']:
        template,_,_=_source(guide,kind)
        documents[kind]={'annex_id':template['id'],'source_sha256':template['sha256'],
                         'source_file':template['file'],'source_url':guide['source_url']}
    return {'adapter':ADAPTER,'region_code':guide['region_code'],'province':guide['province'],
            'city':guide['city'],'district':guide['district'],'source_id':guide['source_id'],
            'authority':guide['authority'],'service_code':guide['service_code'],'documents':documents,
            'published':False,'generation_enabled':False,'web_qa_status':'NOT_RUN','scope':'offline_candidate_only'}


def fill_candidate_document(guide,kind,data):
    """Fill only the fixed own original; never recurse into routing or a registry."""
    _,path,original=_source(guide,kind)
    data={**data}
    if kind=='evidence':
        data['evidenceList']=[{**item,'pageCount':re.sub(r'^\s*(\d+)\s*页\s*$',r'\1',str(item.get('pageCount','')))}
                              for item in data.get('evidenceList',[])]
    elif data.get('copyCount') is None:data['copyCount']='    '
    document=(fill_application if kind=='application' else fill_evidence)(data,path,profile='JiangSuSheng')
    if kind=='application':
        for paragraph in document.paragraphs:
            match=re.search(r'相关证据(?P<slot>[\d \t]+)(?=份)',paragraph.text)
            if match:
                copies=data.get('evidenceCopyCount')
                replace_span(paragraph,match.start('slot'),match.end('slot'),str(copies) if copies is not None else '    ')
        closing=False
        for paragraph in document.paragraphs:
            compact=''.join(paragraph.text.split())
            if compact=='此致':closing=True
            if closing:
                if compact.endswith('日') and '年' in compact and '月' in compact:break
                paragraph.paragraph_format.keep_with_next=True
    return PreservedPackageDocument(document,original)
