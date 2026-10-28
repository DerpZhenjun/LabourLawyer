"""Recheck province windows linked by the official national navigation page."""
import argparse,hashlib,json,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from lxml import html
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from openclaw_browser_tasks import official_url,save
from province_documents import PROVINCE_DOCUMENTS
SOURCE='https://gjzwfw.www.gov.cn/col/col611/index.html'
def fetch(url,path):
    p=subprocess.run(['curl.exe','--silent','--show-error','--location','--connect-timeout','5','--max-time','25','--output',str(path),'--write-out','%{http_code} %{url_effective}',url],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    return {'url':url,'returncode':p.returncode,'result':p.stdout.decode('utf8',errors='replace'),'error':p.stderr.decode('utf8',errors='replace')[:600]}
def main(args):
    args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
    if not args.output.is_relative_to(ROOT):raise ValueError('Evidence must stay in project')
    page=args.output/'navigation.html';probe=fetch(SOURCE,page) if not (args.output/'navigation.json').exists() else {'returncode':0,'result':'200 '+SOURCE}
    if probe['returncode'] or not probe['result'].startswith('200 '):raise RuntimeError(probe)
    names={p['name']:slug for slug,p in PROVINCE_DOCUMENTS.items()};windows={}
    for link in html.fromstring(page.read_bytes()).xpath('//a[@href]'):
        name=link.text_content().strip();url=link.get('href')
        if name in names and official_url(url):windows[names[name]]=url
    previous=json.loads((args.output/'navigation.json').read_text(encoding='utf8')) if (args.output/'navigation.json').exists() else {}
    save(args.output/'navigation.json',{'source_url':SOURCE,'captured_at':previous.get('captured_at') or datetime.now().astimezone().isoformat(),'sha256':hashlib.sha256(page.read_bytes()).hexdigest(),'windows':windows})
    old_probes=json.loads((args.output/'probes.json').read_text(encoding='utf8')) if (args.output/'probes.json').exists() else []
    def one(slug):
        old=next((p for p in old_probes if p['province']==slug and p['url']==windows[slug]),None)
        if old and (args.output/(slug+'.html')).exists():return old
        record=fetch(windows[slug],args.output/(slug+'.html'));record['province']=slug;return record
    with ThreadPoolExecutor(max_workers=4) as pool:probes=list(pool.map(one,[s for s in args.provinces.split(',') if s in windows]))
    save(args.output/'probes.json',probes)
    print(json.dumps(probes,ensure_ascii=False,indent=2))
    if args.update_config:
        embedded={}
        for probe in probes:
            if probe['returncode'] or not probe['result'].startswith('200 '):continue
            urls=[urljoin(probe['url'],url) for url in html.fromstring((args.output/(probe['province']+'.html')).read_bytes()).xpath('//iframe/@src')]
            embedded[probe['province']]=[url for url in urls if official_url(url)]
        path=ROOT/'config/province_service_portals.json';data=json.loads(path.read_text(encoding='utf8'));data.update(navigation_windows=windows,navigation_embedded={**data.get('navigation_embedded',{}),**embedded},navigation_checked_at=previous.get('captured_at') or datetime.now().astimezone().isoformat(),navigation_evidence=str((args.output/'navigation.json').relative_to(ROOT)));save(path,data)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--provinces',default='hebei,heilongjiang,shandong,henan,hubei,hainan,ningxia');p.add_argument('--update-config',action='store_true');main(p.parse_args())
