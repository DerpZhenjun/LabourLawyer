"""Run the Linux-only official-guide worker, or administer its bounded queue."""
import argparse
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import signal
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from linux_guide_collector import CollectorConfig,GuideQueue,run_worker

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--issue-outbox',help='Explicit separate collector issue DB; otherwise use config or remain disabled')
    sub=parser.add_subparsers(dest='command',required=True)
    worker=sub.add_parser('worker');worker.add_argument('--once',action='store_true')
    submit=sub.add_parser('submit');submit.add_argument('--url',required=True)
    for field in ('province','city','district','region-code'):submit.add_argument('--'+field,default='')
    sub.add_parser('status');sub.add_parser('replay-issues',help='Replay durable observations into configured issue DB; no network or ACK')
    for operation in ('retry','cancel'):
        command=sub.add_parser(operation);command.add_argument('id')
    for command in sub.choices.values():command.add_argument('--issue-outbox',default=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    config=CollectorConfig.load(args.config,ROOT)
    if args.issue_outbox is not None:config=replace(config,issue_outbox=Path(args.issue_outbox))
    if args.command=='worker' and sys.platform!='linux':parser.error('Official collector worker requires Linux; no Windows executor')
    queue=GuideQueue(config)
    if args.command=='worker':
        async def worker_main():
            stop=asyncio.Event();loop=asyncio.get_running_loop()
            for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
            await run_worker(config,once=args.once,stop=stop)
        asyncio.run(worker_main())
    elif args.command=='submit':print(json.dumps(queue.submit([{'url':args.url,'region':{k:getattr(args,k) for k in ('province','city','district','region_code')}}]),ensure_ascii=False))
    elif args.command=='status':
        status=queue.summary();status['issue_events']=queue.issue_event_status()
        print(json.dumps(status,ensure_ascii=False,indent=2))
    elif args.command=='replay-issues':
        report=queue.replay_issue_events();print(json.dumps(report,ensure_ascii=False))
        return 0 if report['enabled'] and not report['failed'] else 1
    else:print(json.dumps(getattr(queue,args.command)(args.id),ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
