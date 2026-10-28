"""Reproducible public-portal observations and Word evidence reports.

The browser observes public pages in a separate headless Chrome profile. A
failed automated visit never proves that a province lacks arbitration services.
Screenshots and original observations are immutable per run; conclusions cite
the specific observation instead of copying historical acquisition statuses.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit, urljoin
import uuid
from docx import Document
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from province_documents import PROVINCE_DOCUMENTS, REPOSITORY_ROOT
from terminal_progress import configure, emit

ROOT=REPOSITORY_ROOT/'templates'/'_reports'/'portal-audits'
CONFIG=REPOSITORY_ROOT/'config'/'province_service_portals.json'
MODEL='ollama/qwen3.8:27b'
MODEL_BASE_URL='http://10.66.66.1:11434'
_lock=threading.Lock()
_owner_token=uuid.uuid4().hex
KEYWORD='劳动人事争议仲裁申请'
TERMS=('劳动人事争议仲裁','劳动争议仲裁','劳动仲裁')

def now():return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
def write_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    temp.replace(path)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run_dir(run_id):
    if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[a-f0-9]{8}',run_id):raise ValueError('无效报告编号')
    return ROOT/run_id
def status(run_id):
    path=run_dir(run_id)/'status.json'
    if not path.exists():raise FileNotFoundError('报告不存在')
    result=json.loads(path.read_text(encoding='utf8'))
    if result.get('state')=='running' and result.get('owner_pid'):
        pid=result['owner_pid'];alive=True
        if pid==os.getpid():alive=result.get('owner_token')==_owner_token
        elif os.name=='nt':
            import ctypes
            handle=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
            alive=bool(handle)
            if handle:ctypes.windll.kernel32.CloseHandle(handle)
        if not alive:
            result.update(state='interrupted',error='采集进程已退出；已保存证据，需重新开始采集。',updated_at=now())
            write_json(path,result)
    return result

# Collector and report authoring are separate so browser jobs use the project
# environment and Word artifacts use the bundled document runtime.
from portal_audit_capture import collect
from portal_audit_report import build_report

def validate_capture_coverage(folder,slugs,items):
    """Reject a partial capture before it can be marked as a completed report."""
    from portal_audit_capture import KEYWORDS
    if len(items)!=len(slugs) or {x.get('slug') for x in items}!=set(slugs):
        raise RuntimeError('采集地区不完整，不能生成完成状态的报告')
    for x in items:
        searches=x.get('searches',[])
        if tuple(s.get('keyword') for s in searches)!=KEYWORDS:
            raise RuntimeError('三项检索不完整：'+x['slug'])
        for search in searches:
            picture=folder/x['slug']/search.get('screenshot','absent.png')
            if not picture.is_file() or search.get('screenshot_sha256')!=sha(picture):
                raise RuntimeError('检索截图缺失或校验不符：'+x['slug']+'/'+search.get('stage','未知'))

def execute(run_id,slugs,with_vision=False,resume=False,refine=True):
    folder=run_dir(run_id);started=now()
    previous=json.loads((folder/'status.json').read_text(encoding='utf8')) if (folder/'status.json').is_file() else {}
    configure(folder)
    def update(done=0,current='',state='running',**extra):
        write_json(folder/'status.json',{'id':run_id,'state':state,'started_at':started,'updated_at':now(),'owner_pid':os.getpid(),'owner_token':_owner_token,'completed':done,'total':len(slugs),'current':current,'report_revision':previous.get('report_revision',1),**extra})
        emit('job' if state!='running' else extra.get('phase','capture'),state,province=current,
             message=extra.get('error') or ('全国门户 / '+state),completed=done,total=len(slugs),output=str(folder),error=extra.get('error',''))
    try:
        update()
        items=asyncio.run(collect(folder,slugs,lambda n,name:update(n,name),resume=resume))
        validate_capture_coverage(folder,slugs,items)
        if refine:
            from portal_audit_refine import refine_materials
            items=asyncio.run(refine_materials(folder,items,lambda n,name:update(n,name,phase='materials')))
            from portal_audit_enrich import enrich
            items=asyncio.run(enrich(folder,items,lambda n,name:update(n,name,phase='workflows')))
            write_json(folder/'results.json',items)
            from portal_workflow_repair import repair_workflows
            items=asyncio.run(repair_workflows(folder,items,lambda n,name:update(n,name,phase='workflows')))
            from portal_material_evidence import repair_views
            items=asyncio.run(repair_views(folder,items,lambda n,name:update(n,name,phase='materials')))
        if with_vision:
            from portal_audit_vision import review
            review(folder,items,lambda n,name:update(n,name,phase='vision',model=MODEL,model_server=MODEL_BASE_URL))
            pending=[x['slug'] for x in items if x.get('ai_review',{}).get('state')!='complete']
            if pending:raise RuntimeError('AI复核尚未完成，保留断点：'+', '.join(pending))
        # The agent's document artifact runtime is authoritative when present.
        # Browser dependencies remain in the project's virtual environment.
        import subprocess,sys
        author=Path(os.getenv('DOCX_AUTHOR_PYTHON',r'C:\Users\DerpZhenjun\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'))
        if author.is_file() and Path(sys.executable).resolve()!=author.resolve():
            subprocess.run([str(author),str(REPOSITORY_ROOT/'scripts/audit_official_portals.py'),'--rebuild',run_id],check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            output=folder/'劳动仲裁政务服务门户观察报告.docx'
        else:output=build_report(folder,items)
        ai_done=sum(x.get('ai_review',{}).get('state')=='complete' for x in items)
        ai_output=folder/'劳动仲裁政务服务门户AI验证报告.docx'
        update(len(items),state='complete',report=str(output),report_sha256=sha(output),model=MODEL if with_vision else None,model_server=MODEL_BASE_URL if with_vision else None,ai_report=str(ai_output) if with_vision and ai_output.is_file() else None,ai_completed=ai_done,ai_state=('complete' if ai_done==len(items) else 'incomplete') if with_vision else 'not_requested')
        from portal_batch_index import publish_index
        publish_index(ROOT)
        return output
    except Exception as exc:
        update(state='failed',error=str(exc))
        from portal_batch_index import publish_index
        publish_index(ROOT)
        raise

def start(slugs=None,with_vision=False):
    selected=list(PROVINCE_DOCUMENTS) if slugs is None else slugs
    if not selected or any(s not in PROVINCE_DOCUMENTS for s in selected):raise ValueError('地区列表无效')
    selected=list(dict.fromkeys(selected))
    with _lock:
        for state in ROOT.glob('*/status.json'):
            existing=status(state.parent.name)
            if existing.get('state')=='running':raise RuntimeError('已有报告正在采集：'+existing['id'])
        run_id=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
        folder=run_dir(run_id);folder.mkdir(parents=True,exist_ok=True)
        write_json(folder/'status.json',{'id':run_id,'state':'running','owner_pid':os.getpid(),'owner_token':_owner_token,'completed':0,'total':len(selected),'current':'准备独立无头浏览器','started_at':now()})
        def worker():
            try:execute(run_id,selected,with_vision)
            except Exception:pass  # error already retained in status.json
        threading.Thread(target=worker,daemon=True,name='portal-audit-'+run_id).start()
    return run_id
