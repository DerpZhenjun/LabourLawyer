"""Own public Jiangyin/Yixing evidence; no session state, HAR or HTML saved."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import re
import time
from email.message import Message
from urllib.parse import parse_qs, urlsplit
import requests

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'reports/nationwide-verification-20261029/jiangsu'
sys.path.insert(0, str(ROOT / 'backend'))
from regional_jiangsu import _parse_exact_capture, SECTIONS, official_filename
from regional_guides import digest

BROWSER = Path('D:/Apps/agent-browser/node_modules/agent-browser/bin/agent-browser-win32-x64.exe')
SPECS = {
    '320281': {'city':'无锡市','district':'江阴市','region_code':'320281',
               'task':'113202810140425947400201430200201', 'item':'1132028101404259474002014302002',
               'host':'wxjy.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
               'params':{'webId':'39','ql_kind':'20'}, 'authority':'江阴市人力资源和社会保障局'},
    '320282': {'city':'无锡市','district':'宜兴市','region_code':'320282',
               'task':'113202820140466759400201430200201', 'item':'1132028201404667594002014302002',
               'host':'wxyx.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
               'params':{'webId':'40','ql_kind':'20'}, 'authority':'宜兴市人力资源和社会保障局'},
}


def browser(*args):
    run = subprocess.run([str(BROWSER), '--session', 'js-oct29-verify', *args], capture_output=True,
                         encoding='utf8', timeout=45)
    if run.returncode:
        raise RuntimeError(run.stderr or run.stdout)
    return run.stdout.strip()


def evaluate(js):
    value = json.loads(browser('eval','-b',base64.b64encode(js.encode()).decode()))
    return json.loads(value) if isinstance(value,str) else value


def screenshot(folder, name):
    browser('eval','new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(true))))')
    value = browser('screenshot','--full')
    shutil.copy2(value.split('Screenshot saved to ',1)[1].strip(), folder / (name+'.png'))


def capture(code, name, formal=False):
    spec = SPECS[code]
    current = browser('get','url')
    if not current.startswith('https://'+spec['host']+'/'):
        raise ValueError('Only the own public guide host is capturable')
    folder = OUT / code
    folder.mkdir(parents=True,exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    if formal:
        # Markup is transient process memory for the strict existing parser.
        # It is restricted to public guide sections; no script/auth markup enters output.
        ids = json.dumps(list(SECTIONS.values()))
        js = f'''JSON.stringify({{url:location.href,title:document.title,text:document.body.innerText,
          html:'<html>'+document.querySelector('.area_local').outerHTML+
          {ids}.map(id=>document.getElementById(id).outerHTML).join('')+'</html>'}})'''
        transient = evaluate(js)
        transient['captured_at'] = now
        guide = _parse_exact_capture(transient, None, spec)
        guide.update(source_id=digest(guide['source_url'])[:24], published=False, can_generate=False,
                     status='candidate', web_qa_status='NOT_RUN', generation_enabled=False)
        save = folder / 'guide.json'
        save.write_text(json.dumps(guide,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        public = {'source_url':guide['source_url'],'captured_at':now,'region_code':code,
                  'title':guide['source_title'],'visible_text':transient['text'],
                  'all_sections':list(guide['sections']),'material_count':len(guide['materials']),
                  'template_count':len(guide['templates']), 'method':'Agent Browser rendered public DOM; transient section markup discarded'}
    else:
        public = evaluate('''JSON.stringify({url:location.href,title:document.title,text:document.body.innerText,
          visible_details:Array.from(document.querySelectorAll('.bszn_clxq')).filter(e=>e.getBoundingClientRect().width>0).map(e=>e.innerText)})''')
        public.update(captured_at=now,region_code=code)
    (folder/(name+'.json')).write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    screenshot(folder,name)
    print(json.dumps({'region_code':code,'name':name,'captured_at':now},ensure_ascii=False))


def download(code):
    folder=OUT/code
    guide=json.loads((folder/'guide.json').read_text(encoding='utf8'))
    logs=[]
    for template in guide['templates']:
        url=template['download_url']
        parsed=urlsplit(url)
        if (parsed.scheme!='https' or parsed.hostname!='sxgl.jszwfw.gov.cn' or parsed.port!=66
            or parsed.path!='/audit-qlk-web/rest/frame/pages/basic/attach/attachAction/getContent'
            or parse_qs(parsed.query).get('attachGuid')!=[template['id']]):
            raise ValueError('Only own guide observed annex URLs are downloadable')
        response=requests.get(url,timeout=(10,30))
        response.raise_for_status()
        message=Message();message['Content-Disposition']=response.headers.get('Content-Disposition','')
        name=official_filename(message.get_filename() or '')
        if not name or Path(name).name!=name or re.search(r'[<>:"/\\|?*]',name):
            raise ValueError('No safe original official response filename')
        target=folder/'originals'/template['id']/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(response.content)
        template.update(display_label=template['original_name'],original_name=name,
                        file=target.relative_to(ROOT).as_posix(),file_type=target.suffix.lower().lstrip('.'),
                        sha256=hashlib.sha256(response.content).hexdigest(),bytes=len(response.content),
                        downloaded_at=datetime.now(timezone.utc).isoformat(),download_status='downloaded')
        logs.append({'id':template['id'],'download_url':url,'final_url':response.url,
                     'http_status':response.status_code,'original_name':name,
                     'sha256':template['sha256'],'bytes':len(response.content),
                     'downloaded_at':template['downloaded_at'],'file':template['file']})
        print(json.dumps({'id':template['id'],'original_name':name,'bytes':len(response.content)},ensure_ascii=False))
        time.sleep(1)
    (folder/'guide.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (folder/'downloads.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def boundary(code):
    public=evaluate('''JSON.stringify({origin:location.origin,path:location.pathname,title:document.title,
       personal:document.body.innerText.includes('个人登录'),corporate:document.body.innerText.includes('法人登录')})''')
    if (public['origin'],public['path'],public['personal'],public['corporate']) != ('https://www.jszwfw.gov.cn','/jsjis/front/login.do',True,True):
        raise ValueError('Expected observed official authentication boundary')
    now=datetime.now(timezone.utc).isoformat()
    public.update(region_code=code,checked_at=now,status='auth_required',credentials_entered=False,
                  authenticated_submission_verified=False,raw_sso_url_saved=False)
    folder=OUT/code
    (folder/'online-boundary.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    screenshot(folder,'online-boundary')
    guide=json.loads((folder/'guide.json').read_text(encoding='utf8'))
    guide['channel'].update(online_status='auth_required',entry_url=guide['source_url'],
                            entry_check={'status':'auth_required','official_link':True,'url':guide['source_url'],
                                         'checked_at':now,'note':'自身指南在线办理按钮原生点击后出现个人/法人登录；登录后提交未验证。'})
    (folder/'guide.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(public,ensure_ascii=False))


def flow(code):
    guid={'320281':'25cd0bd0-80ce-4cfb-82e5-495ca600b0ee','320282':'546932a2-c869-4e10-bbe4-67e885a5c37b'}[code]
    url='https://sxgl.jszwfw.gov.cn:66/audit-qlk-web/rest/frame/pages/basic/attach/attachAction/getContent?isCommondto=true&attachGuid='+guid
    response=requests.get(url,timeout=(10,30));response.raise_for_status()
    message=Message();message['Content-Disposition']=response.headers.get('Content-Disposition','')
    name=official_filename(message.get_filename() or '')
    if not name or Path(name).name!=name:raise ValueError('Original flow filename unavailable')
    folder=OUT/code
    target=folder/'originals'/guid/name;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(response.content)
    public={'region_code':code,'annex_id':guid,'download_url':url,'final_url':response.url,
            'original_name':name,'file':target.relative_to(ROOT).as_posix(),'http_status':response.status_code,
            'downloaded_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(response.content).hexdigest(),
            'bytes':len(response.content),'kind':'official_process_diagram'}
    (folder/'flow.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(public,ensure_ascii=False))


def entry_check(code):
    folder=OUT/code;guide=json.loads((folder/'guide.json').read_text(encoding='utf8'))
    if browser('get','url')!=guide['source_url']:raise ValueError('Must remain on the own exact formal guide')
    value=evaluate('''JSON.stringify({source_url:location.href,visible_online_button_count:
      Array.from(document.querySelectorAll('a')).filter(a=>a.innerText.trim()==='在线办理'&&a.getBoundingClientRect().width>0).length})''')
    if value['visible_online_button_count']!=0:raise ValueError('Visible entry exists; inspect natively')
    value.update(region_code=code,checked_at=datetime.now(timezone.utc).isoformat(),status='unverified',
                 raw_form=guide['fields']['办理形式']['raw_value'],
                 reason='自身正式指南表内写网上办理，但本次该页没有可见在线办理按钮；未观察到提交入口。')
    (folder/'online-entry-check.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(value,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('code',choices=SPECS)
    parser.add_argument('name')
    parser.add_argument('--formal',action='store_true')
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--boundary',action='store_true')
    parser.add_argument('--flow',action='store_true')
    parser.add_argument('--entry-check',action='store_true')
    args=parser.parse_args()
    if args.entry_check:
        entry_check(args.code)
    elif args.flow:
        flow(args.code)
    elif args.boundary:
        boundary(args.code)
    elif args.download:
        download(args.code)
    else:
        capture(args.code,args.name,args.formal)
