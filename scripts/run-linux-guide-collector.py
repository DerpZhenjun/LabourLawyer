"""Run the Linux-only official-guide worker, or administer its bounded queue."""
import argparse
import asyncio
import json
from pathlib import Path
import signal
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from linux_guide_collector import CollectorConfig,GuideQueue,run_worker

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config',required=True)
sub=parser.add_subparsers(dest='command',required=True)
worker=sub.add_parser('worker');worker.add_argument('--once',action='store_true')
submit=sub.add_parser('submit');submit.add_argument('--url',required=True)
for field in ('province','city','district','region-code'):submit.add_argument('--'+field,default='')
sub.add_parser('status')
for operation in ('retry','cancel'):
    command=sub.add_parser(operation);command.add_argument('id')
args=parser.parse_args()
config=CollectorConfig.load(args.config,ROOT)
queue=GuideQueue(config)
if args.command=='worker':
    async def main():
        stop=asyncio.Event()
        loop=asyncio.get_running_loop()
        for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
        await run_worker(config,once=args.once,stop=stop)
    asyncio.run(main())
elif args.command=='submit':print(json.dumps(queue.submit([{'url':args.url,'region':{k:getattr(args,k) for k in ('province','city','district','region_code')}}]),ensure_ascii=False))
elif args.command=='status':print(json.dumps(queue.summary(),ensure_ascii=False,indent=2))
else:print(json.dumps(getattr(queue,args.command)(args.id),ensure_ascii=False))
