"""Finish an existing audit after its owner exits, then render both reports.

This is a one-shot continuation, not a scheduler. It never terminates another
process and never writes observations while another audit owns the batch.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from portal_audit import execute,run_dir,status,write_json,now,MODEL,sha

def finish(run_id):
    folder=run_dir(run_id)
    while status(run_id).get('state')=='running':time.sleep(10)
    items=json.loads((folder/'results.json').read_text(encoding='utf8'))
    slugs=[x['slug'] for x in items]
    for attempt in range(3):
        state=status(run_id)
        items=json.loads((folder/'results.json').read_text(encoding='utf8'))
        if state.get('state')=='complete' and all(x.get('ai_review',{}).get('state')=='complete' for x in items):break
        print('CONTINUE',attempt+1,'incomplete regions:',[x['slug'] for x in items if x.get('ai_review',{}).get('state')!='complete'],flush=True)
        execute(run_id,slugs,with_vision=True,resume=True,refine=False)
    items=json.loads((folder/'results.json').read_text(encoding='utf8'))
    pending=[x['slug'] for x in items if x.get('ai_review',{}).get('state')!='complete']
    if pending:raise RuntimeError('AI review remains incomplete: '+', '.join(pending))
    # Check actual image coverage and model identity, not just a region flag.
    from portal_audit_vision import required_images
    for x in items:
        required={o['stage']:o for o in required_images(x)}
        reviews={v['stage']:v for v in x['ai_review']['images']}
        if set(required)!=set(reviews):raise RuntimeError('Missing image coverage: '+x['slug'])
        for stage,o in required.items():
            v=reviews[stage]
            if v.get('model')!=MODEL or v.get('state')!='complete' or v.get('screenshot_sha256')!=sha(folder/x['slug']/o['screenshot']):raise RuntimeError('Invalid image review: '+x['slug']+'/'+stage)
    author=Path(os.getenv('DOCX_AUTHOR_PYTHON',r'C:\Users\DerpZhenjun\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'))
    subprocess.run([str(author),str(ROOT/'scripts/audit_official_portals.py'),'--rebuild',run_id],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run([str(author),str(ROOT/'scripts/render_portal_reports.py'),str(folder)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    state=status(run_id)
    state.update(ai_state='complete',ai_completed=len(items),model=MODEL,ai_report=str(folder/'劳动仲裁政务服务门户AI验证报告.docx'),updated_at=now())
    write_json(folder/'status.json',state)
    from portal_batch_index import publish_index
    publish_index(folder.parent)
    write_json(folder/'completion-check.json',{'completed_at':now(),'regions':len(items),'searches':sum(len(x['searches']) for x in items),'ai_images':sum(len(x['ai_review']['images']) for x in items),'model':MODEL,'rendered':True})
    print('READY FOR VISUAL INSPECTION',folder,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_id');args=parser.parse_args();finish(args.run_id)
