"""Run a real public-portal audit; all evidence stays under templates/_reports."""
import argparse
from datetime import datetime
import sys
from pathlib import Path
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from portal_audit import execute,build_report,run_dir,write_json,sha
from province_documents import PROVINCE_DOCUMENTS
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--provinces',nargs='+');parser.add_argument('--vision',action='store_true');parser.add_argument('--rebuild');parser.add_argument('--resume',help='Existing run ID; retain completed regions and AI records');parser.add_argument('--skip-refine',action='store_true',help='Resume AI from saved screenshots without revisiting public guide pages');parser.add_argument('--retry-regions',nargs='+',help='Archive and recollect selected regions in a resumed run')
    args=parser.parse_args()
    if args.rebuild:
        import json
        folder=run_dir(args.rebuild)
        output=build_report(folder,json.loads((folder/'results.json').read_text(encoding='utf8')))
        state=folder/'status.json'
        if state.exists():
            payload=json.loads(state.read_text(encoding='utf8'))
            payload['report_sha256']=sha(output);write_json(state,payload)
        print(output,flush=True)
    else:
        slugs=args.provinces or list(PROVINCE_DOCUMENTS)
        if any(s not in PROVINCE_DOCUMENTS for s in slugs):parser.error('未知地区')
        run_id=args.resume or datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
        if args.retry_regions:
            if not args.resume:parser.error('--retry-regions requires --resume')
            import shutil
            base=run_dir(run_id).resolve()
            for slug in args.retry_regions:
                if slug not in slugs:parser.error('Unknown retry region: '+slug)
                source=(base/slug).resolve();target=(base/'history'/datetime.now().strftime('%Y%m%d-%H%M%S')/slug).resolve()
                if not source.is_relative_to(base) or not target.is_relative_to(base):raise ValueError('Archive path outside report workspace')
                if source.exists():
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(source),str(target))
        print('Real audit started:',run_id,flush=True)
        if args.skip_refine and not args.resume:parser.error('--skip-refine requires --resume')
        print(execute(run_id,slugs,args.vision,resume=bool(args.resume),refine=not args.skip_refine),flush=True)
