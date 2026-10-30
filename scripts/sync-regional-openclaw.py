"""Export public issues durably; never substitute filesystem export for ACK."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_issue_delivery import deliver_pending, delivery_summary, discover_workspace, verify_pending_with_openclaw


def run(args):
    database = Path(args.database).resolve(strict=True)
    report = Path(args.report).resolve()
    report.mkdir(parents=True, exist_ok=True)
    try:
        workspace = Path(args.workspace) if args.workspace else discover_workspace(args.timeout)
        if args.verify_service:
            status = verify_pending_with_openclaw(database, workspace, args.agent, record_receipts=args.record_receipts,
                                                 profile=args.profile, limit=args.limit, timeout=args.timeout)
        else:
            status = deliver_pending(database, workspace, record_receipts=args.record_receipts, limit=args.limit)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        status = {'status': 'PENDING_OPENCLAW', 'attempted_at': datetime.now(timezone.utc).isoformat(),
                  'workspace_exported': 0, 'acknowledged': 0, 'ai_reviewed': 0, 'model_calls': 0,
                  'error_type': type(exc).__name__, 'reason': str(exc), 'pending': delivery_summary(database)['pending']}
    status['database'] = str(database)
    filename = datetime.now(timezone.utc).strftime('workspace-export-%Y%m%dT%H%M%S%fZ.json')
    (report / filename).write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in status.items() if k != 'receipts'}, ensure_ascii=True))
    return 1 if status.get('failed', 0) or status.get('error_type') else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=os.getenv('LABOURLAWYER_REGIONAL_DB', ROOT / 'backend/data/regional-guides.sqlite'))
    parser.add_argument('--workspace', help='Existing OpenClaw agent workspace; omitted asks the real CLI')
    parser.add_argument('--report', default=ROOT / 'reports/production-readiness-20261030/openclaw')
    parser.add_argument('--record-receipts', action='store_true', help='Persist evidence; service mode publishes ACK only after exact complete service read-back')
    parser.add_argument('--verify-service', action='store_true', help='Verify exact bundle via the dedicated public-only OpenClaw agent; --workspace required')
    parser.add_argument('--agent', default='labourlawyer-public-issues')
    parser.add_argument('--profile', help='Required isolated OpenClaw profile for --verify-service')
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--timeout', type=int, default=30, help='CLI config lookup timeout; no model is called')
    args = parser.parse_args()
    if args.verify_service and (not args.workspace or args.profile != 'labourlawyer-public-issues'):
        parser.error('--verify-service requires --profile labourlawyer-public-issues and its reviewed --workspace')
    sys.exit(run(args))
