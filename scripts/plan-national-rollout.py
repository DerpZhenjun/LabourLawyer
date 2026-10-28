"""Dry-run by default; apply only enqueues public own-locality review work."""
import argparse
import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf8')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from regional_rollout import plan_workspace

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Back up public directory DB, then enqueue missing tasks; never start workers')
    args=parser.parse_args()
    result=plan_workspace(ROOT,apply=args.apply)
    out=ROOT/'reports/nationwide-localization-20261028/rollout';out.mkdir(parents=True,exist_ok=True)
    path=out/('applied-plan.json' if args.apply else 'dry-run-plan.json')
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'applied':result['applied'],'planned_tasks':len(result['tasks']),'enqueued':result['enqueued'],
                      'status':result['status'],'report':str(path)},ensure_ascii=False))

if __name__=='__main__':main()
