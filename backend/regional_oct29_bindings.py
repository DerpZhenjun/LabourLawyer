"""Shared-route bindings for newly reviewed candidates; never publishes a guide."""
from copy import deepcopy
from pathlib import Path
from regional_guides import digest
from regional_jiangsu_oct29 import candidate_contract,ADAPTER as JIANGSU_ADAPTER,SUPPORTED as JIANGSU_CODES
from regional_anhui_oct29 import load_guide,fill_feidong_application,FEIDONG_ADAPTER_KEY as FEIDONG_ADAPTER


def jiangsu_binding(guide,template):
    try:
        contract=candidate_contract(guide)
        for kind,source in contract['documents'].items():
            expected={'id':source['annex_id'],'source_url':source['source_url'],'sha256':source['source_sha256'],
                      'file':source['source_file'],'region_code':contract['region_code'],'official_kind':'blank'}
            if all(template.get(k)==v for k,v in expected.items()):return kind
    except (ValueError,OSError,KeyError,TypeError):pass
    return None


def feidong_canonical(guide,template):
    try:
        canonical=load_guide('feidong')
        if any(guide.get(k)!=v for k,v in canonical.items() if k not in {'templates','warnings'}):return None
        if guide.get('source_id') not in {None,digest(canonical['source_url'])[:24]}:return None
        original=next(t for t in canonical['templates'] if t['official_kind']=='blank')
        if any(template.get(k)!=v for k,v in original.items() if k not in {'document_types','can_generate'}):return None
        if template.get('region_code')!=canonical['region_code']:return None
        return canonical
    except (ValueError,OSError,KeyError,TypeError,StopIteration):return None


def with_capabilities(guide):
    result=deepcopy(guide)
    js=result.get('province')=='jiangsu' and result.get('region_code') in JIANGSU_CODES
    feidong=result.get('province')=='anhui' and result.get('region_code')=='340122'
    if not js and not feidong:return result
    for template in result.get('templates',[]):
        if feidong:template['region_code']=result['region_code']
        kind=jiangsu_binding(result,template) if js else 'application' if feidong_canonical(result,template) else None
        template.update(can_generate=bool(kind),document_types=[kind] if kind else [])
        if kind:
            template.update(adapter=JIANGSU_ADAPTER if js else FEIDONG_ADAPTER,content_kind='filled_official_blank',
                            generation_label='依据'+result['district']+'自身官方空白表格填写')
    return result


class FilledBytes:
    def __init__(self,body):self.body=body
    def save(self,target):
        if hasattr(target,'write'):target.write(self.body)
        else:Path(target).write_bytes(self.body)


def fill_feidong_bound(guide,template,data):
    canonical=feidong_canonical(guide,template)
    if canonical is None:raise ValueError('肥东县自身来源或官方空白表格未通过绑定核验')
    try:return FilledBytes(fill_feidong_application(canonical,data))
    except ValueError as exc:
        raise ValueError('填写超过肥东县原表行数、每行字数或格式限制，请按提示修改；不会裁掉超出内容。') from exc
