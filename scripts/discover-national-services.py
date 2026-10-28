"""Plan public service-discovery jobs; --apply explicitly runs a small backed-up batch."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_discovery import run_discovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Back up public directory DB and claim only service_discovery jobs')
    parser.add_argument('--limit', type=int, default=2, help='Maximum jobs this run, 1..10; default 2')
    parser.add_argument('--delay', type=float, default=2.0, help='Minimum pause between all requests, at least 2 seconds')
    parser.add_argument('--timeout', type=float, default=15.0, help='Per-request timeout in seconds, 1..60')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/nationwide-localization-20261028/anhui/service-discovery')
    args = parser.parse_args()
    try:
        result = run_discovery(ROOT, args.output, apply=args.apply, limit=args.limit, delay=args.delay, timeout=args.timeout)
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
