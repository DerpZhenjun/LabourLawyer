from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .registry import DEFAULT_REGISTRY, select_sources
from .runner import DEFAULT_RUNTIME_ROOT, run_acquisition
from backend.terminal_progress import emit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire official arbitration document templates")
    parser.add_argument("--province", action="append", help="Province id, for example Zhejiang or Guangdong")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--no-browser", action="store_true", help="Skip the headless guide-page snapshot")
    parser.add_argument("--no-vision", action="store_true", help="Skip OpenClaw + Qwen visual review")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate and archive candidates without writing templates/_docx",
    )
    return parser


async def async_main(args) -> int:
    reports = []
    exit_code = 0
    sources=select_sources(args.province,args.registry)
    for number,source in enumerate(sources,1):
        emit('capture',province=source.province,message='开始采集官方模板',completed=number-1,total=len(sources),output=str(args.runtime_root))
        def progress(message):
            print(message,flush=True)
            emit('capture',province=source.province,message=message,output=str(args.runtime_root))
        print(f"[{source.province}] 开始采集，文件只写入：{args.runtime_root}", flush=True)
        result, report = await run_acquisition(
            source,
            runtime_root=args.runtime_root,
            capture_browser=not args.no_browser,
            use_vision=not args.no_vision,
            promote=not args.check_only,
            progress=progress,
        )
        print(f"[{source.province}] 报告：{report}", flush=True)
        reports.append({"province": source.province, "status": result.status, "report": str(report)})
        emit('capture',kind='region',province=source.province,region_state=result.status,message='模板采集：'+result.status,completed=number,total=len(sources),output=str(report.parent))
        if result.status == "failed":
            exit_code = 1
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    emit('job','failed' if exit_code else 'complete_with_gaps' if any(r['status']=='success_with_warnings' for r in reports) else 'complete',message='模板采集结束',completed=len(reports),total=len(sources))
    return exit_code


def main() -> int:
    return asyncio.run(async_main(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
