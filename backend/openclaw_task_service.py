"""Launch and inspect durable, private OpenClaw acquisition jobs."""
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime
import uuid
import os
import threading
from openclaw_browser_tasks import ROOT,TASK_ROOT,save,HIDDEN
from province_documents import PROVINCE_DOCUMENTS

PROCESSES={}
START_LOCK=threading.Lock()
def task_dir(identifier):
    import re
    if not re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}',identifier):raise ValueError('Invalid task identifier')
    return TASK_ROOT/identifier

def start(provinces=None,resume=None):
    with START_LOCK:return _start(provinces,resume)

def _start(provinces=None,resume=None):
    if provinces is not None and (not provinces or len(provinces)>31 or len(set(provinces))!=len(provinces) or any(p not in PROVINCE_DOCUMENTS for p in provinces)):raise ValueError('Invalid provinces')
    if any(p.poll() is None for p in PROCESSES.values()):raise RuntimeError('An OpenClaw acquisition job is already running')
    from openclaw_job_lock import acquisition_lock
    with acquisition_lock():pass
    identifier=resume or datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
    folder=task_dir(identifier)
    if resume and not (folder/'status.json').is_file():raise ValueError('Resume task does not exist')
    folder.mkdir(parents=True,exist_ok=True)
    prior=json.loads((folder/'status.json').read_text(encoding='utf8')) if resume else {}
    provinces=provinces or prior.get('requested_provinces')
    if resume and not provinces:
        old_launch=folder/'launch.json'
        if old_launch.exists():provinces=json.loads(old_launch.read_text(encoding='utf8')).get('provinces')
        if not provinces:provinces=[p.name for p in folder.iterdir() if p.is_dir() and p.name in PROVINCE_DOCUMENTS]
    save(folder/'status.json',{**prior,'state':'queued','total':len(provinces) if provinces else None,'requested_provinces':provinces,'completed':prior.get('completed',0)})
    command=[sys.executable,str(ROOT/'scripts/openclaw-acquire-guides.py'),'--resume',str(folder)]
    if provinces:command+=['--provinces',','.join(provinces)]
    output=(folder/('worker-'+uuid.uuid4().hex[:6]+'.log')).open('wb')
    try:
        env=dict(os.environ,PYTHONUTF8='1',PYTHONUNBUFFERED='1',LABOURLAWYER_PROGRESS_FILE=str(folder/'progress.jsonl'))
        process=subprocess.Popen(command,cwd=ROOT,stdout=output,stderr=output,creationflags=HIDDEN,env=env)
    finally:output.close()
    PROCESSES[identifier]=process
    save(folder/'launch.json',{'owner_pid':process.pid,'provinces':provinces,'resumed':bool(resume),'started_at':datetime.now().astimezone().isoformat()})
    return {'id':identifier,'state':'queued'}

def status(identifier):
    folder=task_dir(identifier)
    if not folder.is_dir():raise FileNotFoundError('Task not found')
    path=folder/'status.json';result=json.loads(path.read_text(encoding='utf8')) if path.exists() else {'state':'queued'}
    result['id']=identifier
    process=PROCESSES.get(identifier)
    if process and process.poll() is not None and result['state'] in ('queued','running','reviewing'):
        result.update(state='failed',exit_code=process.returncode)
    if not process and result['state'] in ('queued','running','reviewing'):
        launch=folder/'launch.json'
        if launch.exists() and not worker_alive(json.loads(launch.read_text(encoding='utf8'))):
            result.update(state='interrupted',error='Worker exited; saved evidence can be resumed.')
            save(path,result)
    current=result.get('current');detail=folder/str(current)/'task.json' if current in PROVINCE_DOCUMENTS else None
    if detail and detail.is_file():result['current_task']=json.loads(detail.read_text(encoding='utf8'))
    completed=folder/'results.json'
    if completed.is_file():result['provinces']=json.loads(completed.read_text(encoding='utf8'))
    return result

def worker_alive(launch):
    pid=launch.get('owner_pid')
    if not isinstance(pid,int) or pid<=0:return False
    if os.name!='nt':
        try:os.kill(pid,0);return True
        except OSError:return False
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=wintypes.DWORD();times=[wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value!=259:return False
        if not kernel.GetProcessTimes(handle,*[ctypes.byref(t) for t in times]):return False
        created=((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)/1e7-11644473600
        started=datetime.fromisoformat(launch['started_at']).timestamp()
        return abs(created-started)<20  # reject a PID reused by another process
    finally:kernel.CloseHandle(handle)

def list_tasks():
    identifiers=sorted((p.parent.name for p in TASK_ROOT.glob('*/status.json')),reverse=True)[:30]
    items=[]
    for identifier in identifiers:
        item=status(identifier)
        def compact(result):
            summary={key:result[key] for key in ('state','status','error','updated_at') if key in result}
            last=result.get('evidence') or (result.get('actions') or [{}])[-1]
            summary['screenshot']=last.get('screenshot',{}).get('filename')
            summary['last_action']=last.get('plan',{}).get('reason','')
            return summary
        if 'current_task' in item:item['current_task']=compact(item['current_task'])
        if 'provinces' in item:item['provinces']={slug:compact(result) for slug,result in item['provinces'].items()}
        items.append(item)
    return {'items':items}
