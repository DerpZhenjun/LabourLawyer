"""Continue a saved national audit without repeating completed form searches."""
import argparse,asyncio,json,os,shutil,sys,uuid,subprocess
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from portal_audit import run_dir,write_json,now,sha,validate_capture_coverage,MODEL,MODEL_BASE_URL
from portal_audit_enrich import enrich
from portal_batch_index import publish_index

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source');parser.add_argument('--resume');parser.add_argument('--vision',action='store_true');parser.add_argument('--skip-discovery',action='store_true',help='Resume completed acquisition directly at evidence repair');parser.add_argument('--retry-material-errors',action='store_true',help='Retry only failed supplementary material visits once');args=parser.parse_args()
    if bool(args.source)==bool(args.resume):parser.error('Specify one of --source / --resume')
    if args.skip_discovery and not args.resume:parser.error('--skip-discovery requires --resume')
    if args.retry_material_errors and not args.resume:parser.error('--retry-material-errors requires --resume')
    if args.source:
        original=run_dir(args.source)
        run_id=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];folder=run_dir(run_id);folder.mkdir()
        items=json.loads((original/'results.json').read_text(encoding='utf8'))
        for item in items:shutil.copytree(original/item['slug'],folder/item['slug'])
        for name in ('results.json','manual-reviews.json','model-info.json'):
            if (original/name).is_file():shutil.copy2(original/name,folder/name)
        write_json(folder/'continuation.json',dict(source_run=args.source,reason='保留已完成检索和证据，补查地区指南、页面下方结果及文书控件',started_at=now()))
    else:
        run_id=args.resume;folder=run_dir(run_id);items=json.loads((folder/'results.json').read_text(encoding='utf8'))
        items=[json.loads((folder/x['slug']/'observations.json').read_text(encoding='utf8')) if (folder/x['slug']/'observations.json').is_file() else x for x in items]
    started=now()
    if args.retry_material_errors:
        for item in items:
            for observation in item['observations']:
                if observation.get('material_recheck_error'):
                    observation.setdefault('material_recheck_history',[]).append(dict(error=observation.pop('material_recheck_error'),attempted_at=observation.pop('material_recheck_attempted_at',None)))
            write_json(folder/item['slug']/'observations.json',item)
    def update(n=0,name='',phase='workflows',**extra):
        write_json(folder/'status.json',dict(id=run_id,state='running',owner_pid=os.getpid(),completed=n,total=len(items),current=name,phase=phase,started_at=started,updated_at=now(),report_revision=2,**extra))
    print('CONTINUE',run_id,flush=True);update()
    try:
        if not args.skip_discovery:items=asyncio.run(enrich(folder,items,update))
        validate_capture_coverage(folder,[x['slug'] for x in items],items)
        from portal_workflow_repair import repair_workflows
        items=asyncio.run(repair_workflows(folder,items,update))
        from portal_material_evidence import repair_views
        items=asyncio.run(repair_views(folder,items,lambda n,name:update(n,name,phase='materials')))
        if args.vision:
            from portal_audit_vision import review
            review(folder,items,lambda n,name:update(n,name,phase='vision',model=MODEL,model_server=MODEL_BASE_URL))
            pending=[x['slug'] for x in items if x.get('ai_review',{}).get('state')!='complete']
            if pending:raise RuntimeError('AI复核尚未完成，保留断点：'+', '.join(pending))
        author=Path(r'C:\Users\DerpZhenjun\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
        subprocess.run([str(author),str(ROOT/'scripts/audit_official_portals.py'),'--rebuild',run_id],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        output=folder/'劳动仲裁政务服务门户观察报告.docx';ai=folder/'劳动仲裁政务服务门户AI验证报告.docx'
        ai_done=sum(x.get('ai_review',{}).get('state')=='complete' for x in items)
        write_json(folder/'status.json',dict(id=run_id,state='complete',completed=len(items),total=len(items),started_at=started,updated_at=now(),report_revision=2,report=str(output),report_sha256=sha(output),ai_report=str(ai) if ai.is_file() else None,ai_completed=ai_done,ai_state='complete' if ai_done==len(items) else 'incomplete',model=MODEL,model_server=MODEL_BASE_URL))
        publish_index(folder.parent);print('REPORT',output,flush=True)
    except Exception as exc:
        update(name=str(exc));s=json.loads((folder/'status.json').read_text(encoding='utf8'));s.update(state='failed',error=str(exc));write_json(folder/'status.json',s);publish_index(folder.parent);raise

if __name__=='__main__':main()
