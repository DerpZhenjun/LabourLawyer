"""Authenticated administration for the separate Linux public-guide queue."""
import json
import os
from pathlib import Path
import re
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from auth_dependencies import require_admin
from linux_guide_collector import CollectorConfig, GuideQueue, public_url
from collector_issue_events import CollectorIssueOutbox

router=APIRouter(dependencies=[Depends(require_admin)])


def configured_queue():
    raw=os.environ.get('LABOURLAWYER_COLLECTOR_CONFIG')
    if not raw:raise HTTPException(503,'尚未配置独立的 Linux 官方指南采集环境。')
    try:return GuideQueue(CollectorConfig.load(raw,Path(__file__).resolve().parents[2]))
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError):
        raise HTTPException(503,'Linux 采集配置不可用；请由管理员检查独立运行环境。')


class Region(BaseModel):
    model_config=ConfigDict(extra='forbid')
    province:str=Field(min_length=1,max_length=80)
    city:str=Field(min_length=1,max_length=80)
    district:str=Field(min_length=1,max_length=80)
    region_code:str=Field(pattern=r'^[0-9]{6,12}$')


class Entry(BaseModel):
    model_config=ConfigDict(extra='forbid')
    url:str=Field(min_length=1,max_length=3000)
    region:Region


class Submission(BaseModel):
    model_config=ConfigDict(extra='forbid')
    items:list[Entry]=Field(min_length=1,max_length=32)


def public_job(job):
    output={k:job[k] for k in ('id','url','region','state','attempt','created_at','updated_at')}
    result=job.get('result')
    if result:
        output['result']={k:result[k] for k in ('state','requested_url','final_url','region','title','http_status',
            'started_at','observed_at','completed_at','guide_detected','review_state','attachment_template_match','auth_boundary_url') if k in result}
        output['result'].update(service_verified=False,model_used=False,review_required=True)
        output['result']['evidence']=[{k:item[k] for k in ('file','bytes','sha256')} for item in result.get('evidence',[]) if re.fullmatch(r'(?:page|failure|materials)\.(?:txt|png)|attachment-\d+\.(?:docx?|pdf|xlsx?)',item.get('file',''))]
        output['result']['attachments']=[{k:item[k] for k in ('source_url','label','state','file','sha256','bytes','observed_at','template_kind','control_evidence_url','capture_method','initial_control_result') if k in item} for item in result.get('attachments',[])]
        for key in ('requested_url','final_url','auth_boundary_url'):
            if key in output['result']:output['result'][key]=public_url(output['result'][key])
        for item in output['result']['attachments']:
            if 'source_url' in item:item['source_url']=public_url(item['source_url'])
        if result.get('error'):output['result']['error']='采集未完成，请由运行管理员检查私有日志。'
    return output


def public_issue_status(queue):
    """Read only the configured dedicated store; unavailable never means zero."""
    enabled=queue.config.issue_outbox is not None
    journal={'status':'error','observations':None,'states':None}
    outbox={'status':'disabled' if not enabled else 'error','events':None,'pending':None,'acknowledged':None}
    def count(value):
        if type(value) is not int or not 0<=value<=9007199254740991:raise ValueError('Invalid issue count')
        return value
    try:
        observed=queue.issue_event_status();states=observed['states']
        if (observed['enabled'] is not enabled or type(observed['model_calls']) is not int or observed['model_calls']!=0
                or observed['sync_performed'] is not False or type(states) is not dict
                or not set(states)<={'pending','disabled','outbox_persisted','rejected','error'}):raise ValueError('Invalid issue journal')
        states={key:count(value) for key,value in states.items()}
        observations=count(observed['observations'])
        if sum(states.values())!=observations:raise ValueError('Issue journal counts differ')
        journal={'status':'available','observations':observations,'states':states}
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):pass
    if enabled:
        try:
            path=Path(queue.config.issue_outbox)
            if path.is_symlink() or path.resolve()!=path:raise ValueError('Invalid dedicated issue path')
            if not path.exists():outbox['status']='missing'
            else:
                if not path.is_file():raise ValueError('Invalid dedicated issue file')
                before=path.stat()
                summary=CollectorIssueOutbox(path).summary()
                after=path.stat()
                if path.is_symlink() or path.resolve()!=path or (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino):raise ValueError('Dedicated issue file changed')
                if type(summary['model_calls']) is not int or summary['model_calls']!=0:raise ValueError('Invalid issue summary')
                counts={key:count(summary[key]) for key in ['events','pending','acknowledged']}
                if counts['events']!=counts['pending']+counts['acknowledged']:raise ValueError('Issue counts differ')
                outbox={'status':'available',**counts}
        except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):pass
    return {'enabled':enabled,'journal':journal,'outbox':outbox,'model_calls':0,'ai_reviewed':False}


@router.get('')
def status(queue:GuideQueue=Depends(configured_queue)):
    data=queue.summary()
    worker=data.get('worker')
    return {'counts':data['counts'],'items':[public_job(j) for j in data['items']],
            'worker':{k:worker[k] for k in ('state','alive','updated_at','job','concurrency','model_used') if k in worker} if worker else None,
            'concurrency':1,'capacity':queue.config.capacity,'model_used':False,
            'allowed_hosts':list(queue.config.allowed_hosts),'review_required':True,'issue_events':public_issue_status(queue)}


@router.post('/jobs',status_code=202)
def submit(payload:Submission,queue:GuideQueue=Depends(configured_queue)):
    try:return {'items':[public_job(j) for j in queue.submit([x.model_dump() for x in payload.items])]}
    except ValueError as exc:raise HTTPException(400,str(exc))


def call_job(queue,operation,identifier):
    try:return public_job(getattr(queue,operation)(identifier))
    except ValueError as exc:raise HTTPException(409,str(exc))
    except FileNotFoundError:raise HTTPException(404,'采集任务不存在。')


@router.get('/jobs/{identifier}')
def job(identifier:str,queue:GuideQueue=Depends(configured_queue)):
    return call_job(queue,'get',identifier)


@router.post('/jobs/{identifier}/retry',status_code=202)
def retry(identifier:str,queue:GuideQueue=Depends(configured_queue)):
    return call_job(queue,'retry',identifier)


@router.post('/jobs/{identifier}/cancel')
def cancel(identifier:str,queue:GuideQueue=Depends(configured_queue)):
    return call_job(queue,'cancel',identifier)


@router.get('/jobs/{identifier}/evidence/{filename}')
def evidence(identifier:str,filename:str,attempt:int|None=None,queue:GuideQueue=Depends(configured_queue)):
    try:record=queue.get(identifier)
    except (ValueError,FileNotFoundError):raise HTTPException(404,'采集任务不存在。')
    if not re.fullmatch(r'(?:page|failure|materials)\.(?:png|txt)|attachment-\d+\.(?:docx?|pdf|xlsx?)',filename):
        raise HTTPException(404,'证据文件不存在。')
    selected=record['attempt'] if attempt is None else attempt
    if selected<1 or selected>record['attempt']:raise HTTPException(404,'证据批次不存在。')
    directory=(queue.root/'evidence'/identifier/('attempt-'+str(selected))).resolve()
    path=(directory/filename).resolve()
    if not path.is_relative_to(directory) or not path.is_file():raise HTTPException(404,'证据文件不存在。')
    return FileResponse(path,filename=filename,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
