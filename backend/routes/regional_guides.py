"""Public, read-only locality reports and exact-source document generation."""
import hashlib
import json
import os
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from regional_guides import RegionalStore, select_template
from regional_documents import fill_tianfu_reference
from regional_adapters import checked_reference_adapter
from regional_blank_documents import fill_blank_document, ADAPTER as BLANK_ADAPTER
from regional_jiangsu_candidates import fill_candidate_document, SUPPORTED as JIANGSU_OWN_CANDIDATES
from regional_rongjiang_documents import fill_rongjiang_document, ADAPTER as RONGJIANG_ADAPTER
from regional_zhejiang_documents import fill_zhejiang_document,ADAPTER as ZHEJIANG_ADAPTER
from regional_shangcheng_documents import fill_shangcheng_document,ADAPTER as SHANGCHENG_ADAPTER
from regional_directory import DirectoryStore
from regional_rollout import build_rollout_status, directory_rows, load_rollout_candidates
from routes.province_documents import ApplicationRequest, EvidenceRequest, _response

ROOT=Path(__file__).resolve().parents[2]
router=APIRouter()

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

@router.get('/events')
def events():
    items=store().events()
    return {'items':items,'pending':sum(e['delivery_status']=='PENDING_OPENCLAW' for e in items),
            'openclaw_status':'PENDING_OPENCLAW' if any(e['delivery_status']=='PENDING_OPENCLAW' for e in items) else 'NO_PENDING_EVENTS'}

@router.get('/report')
def report():
    status_file=ROOT/'reports/government-guide-localization/OPENCLAW-STATUS.json'
    status=json.loads(status_file.read_text(encoding='utf8')) if status_file.is_file() else {'status':'NOT_ATTEMPTED'}
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
    if status['pending_count']:status['status']='PENDING_OPENCLAW'
    cross_file=ROOT/'reports/government-guide-localization/CROSS-PROVINCE-CHECKS.json'
    cross=json.loads(cross_file.read_text(encoding='utf8')) if cross_file.is_file() else []
    return {'openclaw':status,'categories':{k:[e for e in rows if e['type'] in types] for k,types in categories.items()},'regions':inventory()['items'],'cross_province_checks':cross}

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

def checked_path(template):
    path=(ROOT/template.get('file','')).resolve()
    if not path.is_relative_to((ROOT/'templates/_docx/_regional').resolve()):
        raise HTTPException(409,'附件文件不在已核验地区目录中')
    if not path.is_file():raise HTTPException(503,'当地附件暂不可下载，请打开官方来源')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=template.get('sha256'):
        raise HTTPException(409,'附件已变化，请重新核验，不能继续生成')
    return path

@router.get('/templates/{template_id}')
def download(template_id: str,province: str=Query(max_length=30),city: str=Query(max_length=80),district: str=Query(max_length=80)):
    g=store().lookup(province,city,district)
    t=next((t for t in g['templates'] if t['id']==template_id and t['region_code']==g.get('region_code')),None)
    if not t:raise HTTPException(404,'未找到该地区的官方附件')
    return FileResponse(checked_path(t),filename=t['original_name'],headers={'Cache-Control':'no-store'})

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

class BlankApplicationRequest(ApplicationRequest):
    # These are two distinct slots in Xishan's own retained official form.
    copyCount: int | None=Field(default=None,ge=1,le=30)
    evidenceCopyCount: int | None=Field(default=None,ge=1,le=30)

    @field_validator('copyCount','evidenceCopyCount',mode='before')
    @classmethod
    def blank_copies(cls,value):return None if value=='' else value

@router.post('/generate')
def generate(payload: GenerateRequest,background_tasks: BackgroundTasks):
    # Never log the applicant payload or forward it to OpenClaw.
    g=store().lookup(payload.province,payload.city,payload.district)
    if not g.get('source_id') or g['source_id']!=payload.source_id or g['version']!=payload.version:
        raise HTTPException(409,'办理地区或来源版本已改变，请重新查看指南')
    try:t=select_template(g,payload.template_id,payload.kind,payload.mode)
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
    try:adapter=checked_reference_adapter(g,t,payload.kind)
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
    try:
        model=(BlankApplicationRequest if adapter in {BLANK_ADAPTER,ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER} else ApplicationRequest) if payload.kind=='application' else EvidenceRequest
        data=model.model_validate(payload.data)
    except ValidationError as exc:
        raise HTTPException(422,'填写内容过长或格式不正确，请缩短后重试') from exc
    if adapter in {BLANK_ADAPTER,RONGJIANG_ADAPTER,ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER} and payload.mode!='blank':raise HTTPException(409,'这是官方空白表格，请按空白表格填写模式生成')
    try:
        if adapter==SHANGCHENG_ADAPTER:
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
    suffix=('-依据官方DOC转换填写.docx' if adapter==RONGJIANG_ADAPTER else '-官方空白表格填写.docx' if adapter in {BLANK_ADAPTER,ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER} else '-参考样表辅助填写.docx')
    name=g['district']+('申请书' if payload.kind=='application' else '证据清单')+suffix
    response=_response(doc,name,background_tasks)
    response.headers['X-Document-Origin']=('official-blank-converted-filled' if adapter==RONGJIANG_ADAPTER else 'official-blank-filled' if adapter in {BLANK_ADAPTER,ZHEJIANG_ADAPTER,SHANGCHENG_ADAPTER} else 'official-sample-adaptation-not-blank')
    response.headers['X-Guide-Source-ID']=g['source_id']
    return response
