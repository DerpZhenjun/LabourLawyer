"""Public, read-only locality reports and exact-source document generation."""
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from regional_guides import RegionalStore
from regional_documents import fill_tianfu_reference
from regional_adapters import checked_reference_adapter,HUNAN_C_ADAPTER,JIANGSU_C_ADAPTER,jiangsu_c_binding,JIANGSU_D_ADAPTER,ZHEJIANG_D_ADAPTER,JIANGSU_E_ADAPTER,ZHEJIANG_E_ADAPTER
from regional_blank_documents import fill_blank_document, ADAPTER as BLANK_ADAPTER
from regional_jiangsu_candidates import fill_candidate_document, SUPPORTED as JIANGSU_OWN_CANDIDATES
from regional_rongjiang_documents import fill_rongjiang_document, ADAPTER as RONGJIANG_ADAPTER
from regional_zhejiang_documents import fill_zhejiang_document,ADAPTER as ZHEJIANG_ADAPTER
from regional_zhejiang_oct29 import fill_document as fill_ningbo_document,blank_binding as ningbo_blank_binding,ADAPTER as NINGBO_ADAPTER
from regional_shangcheng_documents import fill_shangcheng_document,ADAPTER as SHANGCHENG_ADAPTER
from regional_jiangsu_oct29 import fill_candidate_document as fill_oct29_jiangsu_document
from regional_hunan_oct29c import fill_document as fill_hunan_c_document,blank_binding as hunan_c_binding
from regional_jiangsu_oct29c import fill_candidate_document as fill_jiangsu_c_document
from regional_jiangsu_oct29d import fill_candidate_document as fill_jiangsu_d_document
from regional_zhejiang_oct29d import fill_document as fill_zhejiang_d_document
from regional_jiangsu_oct29e import fill_candidate_document as fill_jiangsu_e_document
from regional_jiangsu_oct30f import (fill_document as fill_jiangsu_f_document, ADAPTER as JIANGSU_F_ADAPTER,
    STAGE_SHA256 as JIANGSU_F_STAGE_SHA256, PUBLICATION_SHA256 as JIANGSU_F_PUBLICATION_SHA256)
from regional_zhejiang_oct29e import fill_document as fill_zhejiang_e_document
from regional_zhejiang_chunan_oct30 import (fill_document as fill_chunan_document, ADAPTER as CHUNAN_ADAPTER,
    PUBLICATION_SHA256 as CHUNAN_PUBLICATION_SHA256)
from regional_jiangsu_request import ApplicationRequest as JiangsuEApplicationRequest,EvidenceRequest as JiangsuEEvidenceRequest
from regional_zhejiang_request import ApplicationRequest as ZhejiangDApplicationRequest,EvidenceRequest as ZhejiangDEvidenceRequest
from regional_hunan_oct29b import fill_document as fill_hunan_document, ADAPTER as HUNAN_ADAPTER
from regional_oct29_bindings import (jiangsu_binding as oct29_jiangsu_binding,feidong_canonical,fill_feidong_bound,
    JIANGSU_ADAPTER as OCT29_JIANGSU_ADAPTER,FEIDONG_ADAPTER)
from regional_directory import DirectoryStore
from regional_rollout import build_rollout_status, directory_rows, load_rollout_candidates
from routes.province_documents import ApplicationRequest, EvidenceRequest, _response
from regional_form_contracts import build_form_contract
from regional_validation import (
    RegionalValidationError, current_form_contract, select_regional_template,
    validate_generation_request, validate_guide_context,
)

ROOT=Path(__file__).resolve().parents[2]
router=APIRouter()

@router.get('/release-capabilities')
def release_capabilities():
    """Identify loaded generation code before a reviewed data-only upgrade."""
    return {'release_id':'oct30night-own-localities-v1',
            'adapters':[JIANGSU_E_ADAPTER,ZHEJIANG_E_ADAPTER,CHUNAN_ADAPTER,JIANGSU_F_ADAPTER],
            'candidate_stage_receipts':{JIANGSU_F_ADAPTER:JIANGSU_F_STAGE_SHA256},
            'publication_receipts':{CHUNAN_ADAPTER:CHUNAN_PUBLICATION_SHA256,
                                    JIANGSU_F_ADAPTER:JIANGSU_F_PUBLICATION_SHA256},
            'source_bound':True,'models_required':False,
            'regional_store':'main_default' if Path(os.getenv('LABOURLAWYER_REGIONAL_DB',ROOT/'backend/data/regional-guides.sqlite')).resolve()==(ROOT/'backend/data/regional-guides.sqlite').resolve() else 'alternate'}

def store():
    return RegionalStore(os.getenv('LABOURLAWYER_REGIONAL_DB',ROOT/'backend/data/regional-guides.sqlite'))

def lookup(province: str=Query(max_length=30),city: str=Query(max_length=80),district: str=Query(max_length=80)):
    return store().lookup(province,city,district)
router.add_api_route('/lookup',lookup,methods=['GET'])


def directory_store():
    return DirectoryStore(os.getenv('LABOURLAWYER_DIRECTORY_DB',ROOT/'backend/data/regional-directory.sqlite'))


@router.get('/areas')
def areas(province: str=Query(max_length=30),city: str=Query(default='',max_length=80)):
    rows=directory_store().areas(province,city)
    guides={(g['province'],g['city'],g['district']):g for g in store().inventory()}
    for row in rows:
        g=guides.get((province,city,row['district']),{}) if city else {}
        row.update(source_id=g.get('source_id'),verification_status=g.get('verification_status','unverified'),
                   can_generate=any(t.get('can_generate') for t in g.get('templates',[])))
    return {'items':rows,'scope':'官方地区目录，不等于当地指南或文书已经核验',
            'directory_is_not_guide_coverage':True}


@router.get('/directory-status')
def directory_status():
    return directory_store().summary()


@router.get('/rollout-status')
def rollout_status():
    catalog=json.loads((ROOT/'frontend/src/data/provinceCatalog.json').read_text(encoding='utf8'))
    return build_rollout_status(directory_rows(directory_store()),store().inventory(),load_rollout_candidates(ROOT),catalog)

@router.get('/inventory')
def inventory():
    guides=store().inventory()
    indexed={(g['province'],g['city'],g['district']):g for g in guides}
    targets_file=ROOT/'reports/chengdu-district-expansion-20261023/TARGETS.json'
    targets=json.loads(targets_file.read_text(encoding='utf8')) if targets_file.is_file() else []
    coverage=[]
    for target in targets:
        g=indexed.get(('sichuan','成都市',target['district']),{})
        coverage.append({'province':'sichuan','city':'成都市','district':target['district'],
                         'region_code':target['region_code'],'source_id':g.get('source_id'),
                         'verification_status':g.get('verification_status','unverified'),
                         'can_generate':any(t.get('can_generate') for t in g.get('templates',[]))})
    return {'items':[{k:v for k,v in g.items() if k not in {'sections','fields'}} for g in guides], 'coverage':coverage,
            'scope':'仅列出具体地区核验数据，不代表已覆盖全省或全国'}

def public_receipt(receipt):
    """Expose delivery facts only; runtime locations/auth remain in the DB."""
    if not isinstance(receipt,dict):return None
    public={}
    for key,allowed in (
        ('kind',{'openclaw_service_readback','workspace_persistence'}),
        ('status',{'PENDING_OPENCLAW','EXPORTED_PENDING_OPENCLAW','ACKNOWLEDGED_OPENCLAW','VERIFIED_PENDING_DATABASE'})):
        value=receipt.get(key)
        if isinstance(value,str) and value in allowed:public[key]=value
    for key in ('content_sha256','evidence_sha256'):
        value=receipt.get(key)
        if isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value):public[key]=value
    for key in ('service_acknowledged','ai_reviewed'):
        if type(receipt.get(key)) is bool:public[key]=receipt[key]
    return public


def public_event_rows(rows):
    return [{**event,'receipt':public_receipt(event.get('receipt'))} for event in rows]


def public_attempt_status(saved):
    """Old capture failures may contain private paths; retain safe metadata only."""
    if not isinstance(saved,dict):return {}
    public={}
    if saved.get('engine')=='OpenClaw':public['engine']='OpenClaw'
    attempted=saved.get('attempted_at')
    if isinstance(attempted,str) and len(attempted)<=64:
        try:datetime.fromisoformat(attempted.replace('Z','+00:00'))
        except ValueError:pass
        else:public['attempted_at']=attempted
    if type(saved.get('pending_count')) is int and saved['pending_count']>=0:
        public['pending_count']=saved['pending_count']
    return public


@router.get('/events')
def events():
    items=public_event_rows(store().events())
    return {'items':items,'pending':sum(e['delivery_status']=='PENDING_OPENCLAW' for e in items),
            'openclaw_status':'PENDING_OPENCLAW' if any(e['delivery_status']=='PENDING_OPENCLAW' for e in items) else 'NO_PENDING_EVENTS'}

@router.get('/report')
def report():
    status_file=ROOT/'reports/government-guide-localization/OPENCLAW-STATUS.json'
    saved_status=json.loads(status_file.read_text(encoding='utf8')) if status_file.is_file() else {}
    status=public_attempt_status(saved_status)
    categories={
        '官方事项搜索失败':['SEARCH_NO_RESULT','WRONG_SERVICE_MATCH','SEARCH_ALIAS_REQUIRED'],
        '搜索关键词有效性':['SEARCH_ALIAS_REQUIRED','SEARCH_NO_RESULT'],
        '网上办理支持':['ONLINE_APPLICATION_UNAVAILABLE','ONLINE_CHANNEL_UNVERIFIED','OFFICIAL_SOURCE_CONFLICT'],
        '官方空白模板缺失':['OFFICIAL_TEMPLATE_NOT_FOUND','TEMPLATE_DOWNLOAD_FAILED'],
        '官方页面访问':['GUIDE_PAGE_UNAVAILABLE','REGION_SELECTION_FAILURE'],
        '需人工登录或核验':['AUTH_REQUIRED','CAPTCHA_REQUIRED','OFFICIAL_SOURCE_CONFLICT'],
        '地区间要求差异':['OFFICIAL_SOURCE_CONFLICT','SOURCE_STALE','MATERIAL_INFORMATION_MISSING']}
    rows=store().events()
    status['last_attempt_pending_count']=status.get('pending_count')
    status['pending_count']=sum(e['delivery_status']=='PENDING_OPENCLAW' for e in rows)
    receipts=[(e,e.get('receipt') if isinstance(e.get('receipt'),dict) else {}) for e in rows]
    status['total_count']=len(rows)
    status['acknowledged_count']=sum(e['delivery_status']=='ACKNOWLEDGED_OPENCLAW' and r.get('service_acknowledged') is True for e,r in receipts)
    status['exported_count']=sum(r.get('kind')=='workspace_persistence' and r.get('status')=='EXPORTED_PENDING_OPENCLAW' for _,r in receipts)
    status['ai_reviewed_count']=sum(e['delivery_status']=='ACKNOWLEDGED_OPENCLAW' and r.get('ai_reviewed') is True for e,r in receipts)
    status['status']='PENDING_OPENCLAW' if status['pending_count'] else ('ACKNOWLEDGED_OPENCLAW' if rows and status['acknowledged_count']==len(rows) else 'NO_EVENTS' if not rows else 'DELIVERY_UNVERIFIED')
    cross_file=ROOT/'reports/government-guide-localization/CROSS-PROVINCE-CHECKS.json'
    cross=json.loads(cross_file.read_text(encoding='utf8')) if cross_file.is_file() else []
    public_rows=public_event_rows(rows)
    return {'openclaw':status,'categories':{k:[e for e in public_rows if e['type'] in types] for k,types in categories.items()},'regions':inventory()['items'],'cross_province_checks':cross}

@router.get('/evidence/{filename:path}')
def evidence(filename: str):
    # Public capture screenshots only. Never serve OpenClaw config or private files.
    directories=[(ROOT/'reports/government-guide-localization').resolve(),
                 (ROOT/'reports/chengdu-district-expansion-20261023').resolve(),
                 (ROOT/'reports/nationwide-localization-20261023-night').resolve()]
    path=((ROOT if filename.startswith('reports/') else directories[0])/filename).resolve()
    if not any(path.is_relative_to(d) for d in directories) or path.suffix!='.png' or not path.is_file():raise HTTPException(404,'未找到公开截图')
    return FileResponse(path,media_type='image/png')

@router.get('/versions')
def versions(province: str=Query(max_length=30),city: str=Query(max_length=80),district: str=Query(max_length=80)):
    return {'items':store().versions(province,city,district)}

def checked_path(template,guide=None):
    from regional_public_provenance import approved_report_attachment
    filename=template.get('file') if isinstance(template,dict) else None
    if not isinstance(filename,str) or not filename:raise HTTPException(409,'附件路径无效')
    root=ROOT.resolve();path=(root/filename).resolve()
    # New reviewed blanks retain their original own-source evidence directory.
    # This exception requires the entire pinned guide and template contract, not
    # an arbitrary report path or a claimed adapter flag.
    own_checked=guide is not None and (hunan_c_binding(guide,template)=='application' or jiangsu_c_binding(guide,template) in {'application','evidence'} or approved_report_attachment(guide,template,root)
        or oct29_jiangsu_binding(guide,template) in {'application','evidence'})
    if not path.is_relative_to(root) or (not path.is_relative_to((root/'templates/_docx/_regional').resolve()) and not own_checked):
        raise HTTPException(409,'附件文件不在已核验地区目录中')
    if not path.is_file():raise HTTPException(503,'当地附件暂不可下载，请打开官方来源')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=template.get('sha256'):
        raise HTTPException(409,'附件已变化，请重新核验，不能继续生成')
    return path

@router.get('/templates/{template_id}')
def download(template_id: str,province: str=Query(max_length=30),city: str=Query(max_length=80),district: str=Query(max_length=80),
             source_id: Annotated[str | None,Query(max_length=64)]=None,version: int | None=None):
    g=store().lookup(province,city,district)
    if source_id is not None or version is not None:
        if source_id is None or version is None or source_id!=g.get('source_id') or type(version) is not int or version!=g.get('version'):
            raise HTTPException(409,'办理地区或来源版本已改变，请重新查看指南')
    t=next((t for t in g['templates'] if t.get('id')==template_id),None)
    if not t:raise HTTPException(404,'未找到该地区的官方附件')
    if 'region_code' not in t:
        from regional_public_provenance import public_evidence,approved_report_attachment
        if public_evidence(g,ROOT) is None or not approved_report_attachment(g,t,ROOT):
            raise HTTPException(404,'未找到本区完整来源证明的官方附件')
        # A response-local projection, never a store/captured-guide mutation.
        t={**t,'region_code':g['region_code']}
    elif t.get('region_code')!=g.get('region_code'):
        raise HTTPException(404,'未找到该地区的官方附件')
    return FileResponse(checked_path(t,g),filename=t['original_name'],headers={'Cache-Control':'no-store',
        'X-Guide-Source-ID':g.get('source_id',''),'X-Guide-Version':str(g.get('version','')),'X-Template-SHA256':t['sha256']})

class GenerateRequest(BaseModel):
    province: str=Field(max_length=30)
    city: str=Field(max_length=80)
    district: str=Field(max_length=80)
    source_id: str=Field(max_length=64)
    version: int
    template_id: str=Field(max_length=64)
    kind: Literal['application','evidence']
    mode: Literal['blank','reference_adaptation']
    data: dict
    contract_id: str | None=Field(default=None,min_length=64,max_length=64,pattern=r'^[0-9a-f]{64}$')

class BlankApplicationRequest(ApplicationRequest):
    # These are two distinct slots in Xishan's own retained official form.
    copyCount: int | None=Field(default=None,ge=1,le=30)
    evidenceCopyCount: int | None=Field(default=None,ge=1,le=30)

    @field_validator('copyCount','evidenceCopyCount',mode='before')
    @classmethod
    def blank_copies(cls,value):return None if value=='' else value

class FeidongApplicationRequest(BaseModel):
    model_config={'extra':'forbid'}
    applicant_lines: list[str]=Field(default_factory=list,max_length=2)
    agent_lines: list[str]=Field(default_factory=list,max_length=2)
    respondent_lines: list[str]=Field(default_factory=list,max_length=2)
    representative_lines: list[str]=Field(default_factory=list,max_length=2)
    requests: list[str]=Field(default_factory=list,max_length=40)
    facts: str=Field(default='',max_length=2000)

class HunanEmbeddedEvidence(BaseModel):
    model_config={'extra':'forbid'}
    name: str=Field(default='',max_length=300)
    source: str=Field(default='',max_length=300)
    purpose: str=Field(default='',max_length=300)

class HunanApplicationRequest(BaseModel):
    """Only fields that have a slot in these two own worker forms."""
    model_config={'extra':'forbid'}
    applicantName: str=Field(default='',max_length=160)
    gender: str=Field(default='',max_length=160)
    birthDate: str=Field(default='',max_length=160)
    occupation: str=Field(default='',max_length=160)
    nationality: str=Field(default='',max_length=160)
    idAddress: str=Field(default='',max_length=160)
    postalCode: str=Field(default='',max_length=160)
    phone: str=Field(default='',max_length=160)
    workUnit: str=Field(default='',max_length=160)
    workUnitPostalCode: str=Field(default='',max_length=160)
    workUnitPhone: str=Field(default='',max_length=160)
    respondentName: str=Field(default='',max_length=160)
    registeredAddress: str=Field(default='',max_length=160)
    respondentPostalCode: str=Field(default='',max_length=160)
    legalRepName: str=Field(default='',max_length=160)
    legalRepPosition: str=Field(default='',max_length=160)
    legalRepPhone: str=Field(default='',max_length=160)
    hrContactName: str=Field(default='',max_length=160)
    hrContactPosition: str=Field(default='',max_length=160)
    hrContactPhone: str=Field(default='',max_length=160)
    thirdParty: str=Field(default='',max_length=160)
    committeeName: str=Field(default='',max_length=160)
    applicationDate: str=Field(default='',max_length=160)
    copyCount: Annotated[str,Field(max_length=160)] | int | float=''
    requests: list[str]=Field(default_factory=list,max_length=8)
    factsReason: str=Field(default='',max_length=1800)
    evidenceList: list[HunanEmbeddedEvidence]=Field(default_factory=list,max_length=10)

def generation_request_model(adapter,kind):
    """Preserve the existing adapter-specific request-model selection."""
    model=(BlankApplicationRequest if adapter in {BLANK_ADAPTER,ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER,NINGBO_ADAPTER,OCT29_JIANGSU_ADAPTER,JIANGSU_C_ADAPTER,JIANGSU_D_ADAPTER} else ApplicationRequest) if kind=='application' else EvidenceRequest
    if adapter==FEIDONG_ADAPTER:model=FeidongApplicationRequest
    if adapter in {HUNAN_ADAPTER,HUNAN_C_ADAPTER}:model=HunanApplicationRequest
    if adapter in {ZHEJIANG_D_ADAPTER,ZHEJIANG_E_ADAPTER,CHUNAN_ADAPTER}:model=ZhejiangDApplicationRequest if kind=='application' else ZhejiangDEvidenceRequest
    if adapter in {JIANGSU_E_ADAPTER,JIANGSU_F_ADAPTER}:model=JiangsuEApplicationRequest if kind=='application' else JiangsuEEvidenceRequest
    return model


@router.get('/form-contract')
def form_contract(province: str=Query(max_length=30),city: str=Query(max_length=80),district: str=Query(max_length=80),
                  source_id: str=Query(max_length=64),version: int=Query(ge=1),template_id: str=Query(max_length=64),
                  kind: Literal['application','evidence']=Query()):
    g=store().lookup(province,city,district)
    try:
        validate_guide_context(
            g, province=province, city=city, district=district,
            source_id=source_id, version=version, missing_source_status=404)
        template = select_regional_template(g, template_id, kind)
        return current_form_contract(
            g, template, kind, root=ROOT, contract_builder=build_form_contract)
    except RegionalValidationError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.post('/generate')
def generate(payload: GenerateRequest,background_tasks: BackgroundTasks):
    # Never log the applicant payload or forward it to OpenClaw.
    g=store().lookup(payload.province,payload.city,payload.district)
    try:
        validate_guide_context(
            g, province=payload.province, city=payload.city, district=payload.district,
            source_id=payload.source_id, version=payload.version)
        t = select_regional_template(g, payload.template_id, payload.kind, mode=payload.mode)
        adapter, data, validated_contract_id = validate_generation_request(
            g, t, payload.kind, payload.data, payload.contract_id, root=ROOT,
            adapter_checker=checked_reference_adapter, contract_builder=build_form_contract,
            request_model_factory=generation_request_model)
    except RegionalValidationError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    blank_adapters={BLANK_ADAPTER,ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER,NINGBO_ADAPTER,OCT29_JIANGSU_ADAPTER,FEIDONG_ADAPTER,JIANGSU_C_ADAPTER,JIANGSU_D_ADAPTER,ZHEJIANG_D_ADAPTER,JIANGSU_E_ADAPTER,ZHEJIANG_E_ADAPTER,CHUNAN_ADAPTER,JIANGSU_F_ADAPTER}
    if adapter in blank_adapters|{RONGJIANG_ADAPTER,HUNAN_ADAPTER,HUNAN_C_ADAPTER} and payload.mode!='blank':raise HTTPException(409,'这是官方空白表格，请按空白表格填写模式生成')
    try:
        if adapter==CHUNAN_ADAPTER:
            doc=fill_chunan_document(g,t,payload.kind,checked_path(t,g),data.model_dump(),root=ROOT)
        elif adapter==JIANGSU_F_ADAPTER:
            doc=fill_jiangsu_f_document(g,t,payload.kind,checked_path(t,g),data.model_dump(),root=ROOT)
        elif adapter==JIANGSU_E_ADAPTER:
            doc=fill_jiangsu_e_document(g,payload.kind,data.model_dump())
        elif adapter==ZHEJIANG_E_ADAPTER:
            doc=fill_zhejiang_e_document(g,t,payload.kind,checked_path(t,g),data.model_dump())
        elif adapter==JIANGSU_D_ADAPTER:
            doc=fill_jiangsu_d_document(g,payload.kind,data.model_dump())
        elif adapter==ZHEJIANG_D_ADAPTER:
            doc=fill_zhejiang_d_document(g,t,payload.kind,checked_path(t,g),data.model_dump())
        elif adapter==HUNAN_C_ADAPTER:
            doc=fill_hunan_c_document(g,t,payload.kind,checked_path(t,g),data.model_dump())
        elif adapter==JIANGSU_C_ADAPTER:
            doc=fill_jiangsu_c_document(g,payload.kind,data.model_dump())
        elif adapter==HUNAN_ADAPTER:
            doc=fill_hunan_document(g,t,payload.kind,checked_path(t,g),data.model_dump())
        elif adapter==OCT29_JIANGSU_ADAPTER:
            doc=fill_oct29_jiangsu_document(g,payload.kind,data.model_dump())
        elif adapter==FEIDONG_ADAPTER:
            doc=fill_feidong_bound(g,t,data.model_dump())
        elif adapter==NINGBO_ADAPTER:
            doc=fill_ningbo_document(g,t,payload.kind,checked_path(t,g),data.model_dump())
        elif adapter==SHANGCHENG_ADAPTER:
            doc=fill_shangcheng_document(g,t,payload.kind,checked_path(t),data.model_dump())
        elif adapter==ZHEJIANG_ADAPTER:
            doc=fill_zhejiang_document(g,t,payload.kind,checked_path(t),data.model_dump())
        elif adapter==RONGJIANG_ADAPTER:
            doc=fill_rongjiang_document(g,t,payload.kind,checked_path(t),data.model_dump())
        elif adapter==BLANK_ADAPTER:
            if g.get('region_code') in JIANGSU_OWN_CANDIDATES:
                doc=fill_candidate_document(g,payload.kind,data.model_dump())
            else:
                doc=fill_blank_document(g,t,payload.kind,checked_path(t),data.model_dump())
        else:doc=fill_tianfu_reference(checked_path(t),payload.kind,data.model_dump())
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
    suffix=('-依据官方DOC转换填写.docx' if adapter in {RONGJIANG_ADAPTER,HUNAN_ADAPTER,HUNAN_C_ADAPTER} else '-官方空白表格填写.docx' if adapter in blank_adapters else '-参考样表辅助填写.docx')
    name=g['district']+('申请书' if payload.kind=='application' else '证据清单')+suffix
    response=_response(doc,name,background_tasks)
    response.headers['X-Document-Origin']=('official-blank-converted-filled' if adapter in {RONGJIANG_ADAPTER,HUNAN_ADAPTER,HUNAN_C_ADAPTER} else 'official-blank-filled' if adapter in blank_adapters else 'official-sample-adaptation-not-blank')
    response.headers['X-Guide-Source-ID']=g['source_id']
    response.headers['X-Guide-Version']=str(g['version'])
    if validated_contract_id is not None:response.headers['X-Form-Contract-ID']=validated_contract_id
    return response
