"""Read-only evidence of an owned OpenClaw tab when font waiting fails."""
import argparse,base64
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,required=True);parser.add_argument('--target',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
output=args.output.resolve()
if not output.is_relative_to(ROOT):raise ValueError('Evidence must stay in project')
with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp(f'http://127.0.0.1:{args.port}',timeout=10000)
    for context in browser.contexts:
        for page in context.pages:
            session=context.new_cdp_session(page)
            try:
                if session.send('Target.getTargetInfo')['targetInfo']['targetId']!=args.target:continue
                result=session.send('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False,'fromSurface':True})
                output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(base64.b64decode(result['data']));break
            finally:session.detach()
        else:continue
        break
    else:raise ValueError('Owned native browser target no longer exists')
