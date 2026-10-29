"""Offline own-source Dongtai/Sheyang filling; never a publication capability."""
import hashlib
from pathlib import Path
from regional_blank_documents import blank_binding,fill_blank_document

ROOT=Path(__file__).resolve().parents[1]
SUPPORTED=frozenset({'320981','320924'})
ADAPTER='jiangsu_own_blank_candidate_v1'

def _source(guide,kind):
    code=guide.get('region_code')
    if code not in SUPPORTED or kind not in {'application','evidence'}:
        raise ValueError('不是本批自身已核验的江苏区县文书')
    matches=[t for t in guide.get('templates',[]) if blank_binding(guide,t)==kind]
    if len(matches)!=1:raise ValueError('自身指南或唯一空白附件身份不匹配')
    template=matches[0]
    path=(ROOT/template['file']).resolve()
    expected=(ROOT/'templates/_docx/_regional'/code).resolve()
    if path.parent!=expected or not path.is_relative_to(ROOT.resolve()):
        raise ValueError('自身原件canonical路径不匹配')
    try:body=path.read_bytes()
    except OSError as exc:raise ValueError('自身已下载原件不可用') from exc
    if hashlib.sha256(body).hexdigest()!=template['sha256']:
        raise ValueError('自身原件实际SHA不匹配，禁止填写')
    return template,path

def candidate_contract(guide):
    """Expose verified offline artifacts while preserving the publication gate."""
    documents={}
    for kind in ['application','evidence']:
        template,_=_source(guide,kind)
        documents[kind]={'annex_id':template['id'],'source_sha256':template['sha256'],
                         'source_file':template['file'],'source_url':guide['source_url']}
    return {'adapter':ADAPTER,'region_code':guide['region_code'],'province':guide['province'],
            'city':guide['city'],'district':guide['district'],'source_id':guide.get('source_id'),
            'authority':guide['authority'],'service_code':guide['service_code'],'documents':documents,
            'published':False,'generation_enabled':False,'web_qa_status':'NOT_RUN',
            'scope':'offline_candidate_only'}

def fill_candidate_document(guide,kind,data):
    """No caller-selected path, neighbour fallback, network, model or DB action."""
    template,path=_source(guide,kind)
    return fill_blank_document(guide,template,kind,path,data)
