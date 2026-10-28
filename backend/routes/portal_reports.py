"""Asynchronous official-portal evidence report API."""
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from portal_audit import start,status,ROOT,run_dir
import json
router=APIRouter()
class AuditRequest(BaseModel):
    provinces:list[str]|None=Field(default=None,max_length=31)
    vision:bool=False
class OpenClawRequest(BaseModel):
    provinces:list[str]|None=Field(default=None,max_length=31)
    resume:str|None=None

@router.post('/openclaw-tasks',status_code=202)
def start_openclaw_task(payload:OpenClawRequest):
    from openclaw_task_service import start
    try:return start(payload.provinces,payload.resume)
    except ValueError as exc:raise HTTPException(400,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.get('/openclaw-tasks')
def list_openclaw_tasks():
    from openclaw_task_service import list_tasks
    return list_tasks()

@router.get('/openclaw-tasks/{identifier}')
def openclaw_task_status(identifier:str):
    from openclaw_task_service import status
    try:return status(identifier)
    except ValueError as exc:raise HTTPException(400,str(exc))
    except FileNotFoundError as exc:raise HTTPException(404,str(exc))

@router.get('/openclaw-tasks/{identifier}/{province}/evidence/{filename}')
def openclaw_task_evidence(identifier:str,province:str,filename:str):
    from openclaw_task_service import task_dir
    from province_documents import PROVINCE_DOCUMENTS
    import re
    try:folder=task_dir(identifier)
    except ValueError as exc:raise HTTPException(400,str(exc))
    if province not in PROVINCE_DOCUMENTS or not re.fullmatch(r'step-\d{2}\.png',filename):raise HTTPException(400,'Invalid evidence identifier')
    path=folder/province/filename
    if not path.is_file():raise HTTPException(404,'Screenshot not found')
    return FileResponse(path,media_type='image/png')
@router.get('')
def list_reports():
    for p in ROOT.glob('*/status.json'):status(p.parent.name)
    from portal_batch_index import publish_index
    data=publish_index(ROOT)
    data['items']=sorted(data['items'],key=lambda r:(r.get('recommended',False),r.get('updated_at','')),reverse=True)[:30]
    return data
@router.post('',status_code=202)
def create_report(payload:AuditRequest):
    try:return {'id':start(payload.provinces,payload.vision)}
    except ValueError as exc:raise HTTPException(400,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))
@router.get('/workflows/{province}')
def get_workflows(province:str,run_id:str|None=None):
    from province_documents import PROVINCE_DOCUMENTS
    if province not in PROVINCE_DOCUMENTS:raise HTTPException(404,'未知省份')
    include_live=not run_id
    if not run_id:
        latest=ROOT/'latest.json'
        if not latest.is_file():raise HTTPException(404,'还没有完整全国报告')
        run_id=json.loads(latest.read_text(encoding='utf8'))['id']
    try:path=run_dir(run_id)/province/'workflows.json'
    except ValueError as exc:raise HTTPException(400,str(exc))
    from province_experience import plain_guide,load_experiences,valid_guide
    data=json.loads(path.read_text(encoding='utf8')) if path.is_file() else {'guides':[],'province':province}
    if include_live:
        live=load_experiences();profile=(live or {}).get('provinces',{}).get(province,{})
        guide=profile.get('selected_guide')
        if profile.get('openclaw_task') and valid_guide(guide):
            guide={**guide,'evidence_experience_run':live['run_id']}
            data['guides']=[guide]+[g for g in data['guides'] if g.get('guide_url')!=guide.get('guide_url')]
    if not path.is_file() and not data['guides']:raise HTTPException(404,'本批次尚未采集地区办理流程')
    for guide in data.get('guides',[]):
        plain=plain_guide(guide,province)
        guide['plain_steps']=[{key:step[key] for key in ('title','text')} for step in plain['steps']]
        guide['plain_materials']=plain['materials']
    return data

@router.get('/experiences/{province}')
def get_experience(province:str):
    from province_documents import PROVINCE_DOCUMENTS,REPOSITORY_ROOT
    from province_experience import load_experiences,plain_guide
    if province not in PROVINCE_DOCUMENTS:raise HTTPException(404,'未知省份')
    # The checked-in snapshot also works before a new batch is published.
    data=load_experiences() or json.loads((REPOSITORY_ROOT/'frontend/src/data/provinceExperiences.json').read_text(encoding='utf8'))
    result=dict(data['provinces'][province])
    if result.get('selected_guide'):result.update(plain_guide(result['selected_guide'],province,PROVINCE_DOCUMENTS[province].get('scope','')))
    if not result.get('steps'):result['steps']=[{'title':'先打开官方入口','text':'搜索劳动仲裁，选择实际办理地区，再查看办事指南。'}]
    result['theme']=json.loads((REPOSITORY_ROOT/'config/province_themes.json').read_text(encoding='utf8'))[province]
    result.pop('selected_guide',None);result.pop('attempts',None);result.pop('ai_review',None)
    result['templates']=[{k:t[k] for k in ('material_name','text','kind','url') if k in t} for t in result.get('templates',[])]
    return result

@router.get('/experience-reports/latest/{kind}')
def experience_report(kind:str):
    from province_experience import load_experiences,EXPERIENCE_ROOT
    names={'main':'各省劳动争议办事指南更新报告.docx','ai':'各省劳动争议办事指南AI复核报告.docx'}
    if kind not in names:raise HTTPException(404,'报告类型不存在')
    data=load_experiences()
    if not data:raise HTTPException(404,'尚未生成省份指南报告')
    path=EXPERIENCE_ROOT/data['run_id']/names[kind]
    if not path.is_file():raise HTTPException(404,'本批次报告尚未生成')
    return FileResponse(path,filename=path.name,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@router.get('/workflows/{province}/{guide_id}/evidence')
def workflow_evidence(province:str,guide_id:str,run_id:str|None=None,kind:str='materials'):
    catalog=get_workflows(province,run_id)
    if kind not in ('materials','flow'):raise HTTPException(400,'证据类型无效')
    if not run_id:run_id=json.loads((ROOT/'latest.json').read_text(encoding='utf8'))['id']
    guide=next((r for r in catalog['guides'] if r['id']==guide_id),None)
    if not guide:raise HTTPException(404,'指南不存在')
    filename=guide.get('flow_screenshot' if kind=='flow' else 'screenshot')
    if not filename:raise HTTPException(404,'该指南尚未取得此类截图')
    if guide.get('evidence_experience_run'):
        from province_experience import EXPERIENCE_ROOT
        directory=(EXPERIENCE_ROOT/guide['evidence_experience_run']/province).resolve()
        if not directory.is_relative_to(EXPERIENCE_ROOT.resolve()):raise HTTPException(404,'证据目录不存在')
    else:directory=(run_dir(run_id)/province).resolve()
    path=(directory/filename).resolve()
    if not path.is_relative_to(directory) or not path.is_file():raise HTTPException(404,'证据文件不存在')
    return FileResponse(path,media_type='image/png')
@router.get('/{run_id}')
def get_status(run_id:str):
    try:return status(run_id)
    except (ValueError,FileNotFoundError) as exc:raise HTTPException(404,str(exc))
@router.get('/{run_id}/download')
def download_report(run_id:str):
    try:
        s=status(run_id)
        if s['state']!='complete':raise HTTPException(409,'报告未完成')
        path=run_dir(run_id)/'劳动仲裁政务服务门户观察报告.docx'
        if not path.is_file():raise HTTPException(404,'报告文件不存在')
        return FileResponse(path,filename=path.name,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except (ValueError,FileNotFoundError) as exc:raise HTTPException(404,str(exc))

@router.get('/{run_id}/download-ai')
def download_ai_report(run_id:str):
    try:
        s=status(run_id)
        if s['state']!='complete':raise HTTPException(409,'报告未完成')
        path=run_dir(run_id)/'劳动仲裁政务服务门户AI验证报告.docx'
        if not path.is_file():raise HTTPException(404,'本批次尚未生成AI验证报告')
        return FileResponse(path,filename=path.name,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except (ValueError,FileNotFoundError) as exc:raise HTTPException(404,str(exc))
