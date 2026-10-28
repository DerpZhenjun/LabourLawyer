"""Acquire each public attachment linked by Xishan's own captured guide.

No province template substitution and no automatic generator publication.
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from importlib import import_module

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from regional_jiangsu import parse_xishan_capture, official_filename
from regional_guides import now, digest
c=import_module('collect-chengdu-districts')
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-xishan'


def official(url):
    p=urlsplit(url)
    return p.scheme=='https' and (p.hostname=='jszwfw.gov.cn' or (p.hostname or '').endswith('.jszwfw.gov.cn'))


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not official(newurl):raise ValueError('附件跳转到未经核实的域名')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def run():
    capture=json.loads((OUT/'formal-guide-final.json').read_text('utf8'))
    guide=parse_xishan_capture(capture)
    entry=OUT/'online-check.json'
    if entry.is_file():
        checked=json.loads(entry.read_text('utf8'))
        guide=parse_xishan_capture(capture,checked)
        c.save(OUT/'outbox/auth-boundary.json',{'id':digest([guide['source_url'],'AUTH_REQUIRED'])[:32],
            'type':'AUTH_REQUIRED','province':'jiangsu','city':'无锡市','district':'锡山区','region_code':'320205',
            'service':guide['service_name'],'url':checked['url'],'occurred_at':checked['checked_at'],
            'screenshot':checked['screenshot'],'reason':checked['action'],'attempts':1,'final_status':'manual_authorization',
            'remediation':'由用户自行到官方渠道认证，本平台不代登录或代提交','delivery_status':'PENDING_OPENCLAW'})
    guide['evidence']={'capture_file':str((OUT/'formal-guide-final.json').relative_to(ROOT)),
                       'capture_sha256':hashlib.sha256((OUT/'formal-guide-final.json').read_bytes()).hexdigest(),
                       'screenshot':str((OUT/'formal-guide.png').relative_to(ROOT))}
    previous=json.loads((OUT/'guide.json').read_text('utf8')) if (OUT/'guide.json').exists() else {}
    old={t['id']:t for t in previous.get('templates',[])}
    opener=build_opener(OfficialRedirect())
    for template in guide['templates']:
        existing=old.get(template['id'],{})
        if existing.get('download_status')=='downloaded':
            path=ROOT/existing['file']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=existing['sha256']:raise ValueError('旧附件SHA变化，保留文件待复核')
            template.update(existing)
            template.setdefault('original_http_filename',template['original_name'])
            template['original_name']=official_filename(template['original_name'])
            continue
        try:
            if not official(template['download_url']):raise ValueError('非官方附件链接')
            with opener.open(Request(template['download_url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                body=response.read(20*1024*1024+1)
                if len(body)>20*1024*1024:raise ValueError('附件超过20MB')
                if not body.startswith((b'PK',b'\xd0\xcf',b'%PDF',b'\xff\xd8',b'\x89PNG')):raise ValueError('附件返回的不是文书或图像')
                http_filename=unquote(response.headers.get_filename() or '')
                filename=official_filename(http_filename)
                if not filename:
                    suffix='.docx' if body.startswith(b'PK') else '.doc' if body.startswith(b'\xd0\xcf') else '.pdf' if body.startswith(b'%PDF') else '.png'
                    filename=template['original_name']+suffix
                filename=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',filename)[:140]
                relative=Path('templates/_docx/_regional/320205')/(template['id']+'-'+filename)
                path=ROOT/relative;path.parent.mkdir(parents=True,exist_ok=True)
                if path.exists() and path.read_bytes()!=body:raise ValueError('相同附件ID的原文件已改变，禁止覆盖')
                if not path.exists():path.write_bytes(body)
                template.update(original_name=filename,original_http_filename=http_filename,file=relative.as_posix(),sha256=hashlib.sha256(body).hexdigest(),
                                bytes=len(body),download_status='downloaded',final_download_url=response.url,
                                file_type=path.suffix.lstrip('.').lower(),downloaded_at=now(),verified_at=now())
        except Exception as exc:
            template.update(download_status='failed',download_error=str(exc))
            event={'type':'TEMPLATE_DOWNLOAD_FAILED','province':'jiangsu','city':'无锡市','district':'锡山区',
                   'region_code':'320205','service':guide['service_name'],'url':template['download_url'],
                   'occurred_at':now(),'reason':str(exc),'attempts':1,'final_status':'pending_recheck',
                   'remediation':'保留本区县真实下载地址，不使用其他地区附件替代','delivery_status':'PENDING_OPENCLAW'}
            c.save(OUT/'outbox'/(digest([template['id'],event['type']])[:32]+'.json'),event)
        c.save(OUT/'guide.json',guide)
        print(template['id'],template['download_status'],template.get('original_name'),flush=True)
        time.sleep(1.5)
    c.save(OUT/'guide.json',guide)


if __name__=='__main__':run()
