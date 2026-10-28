"""Retain actual official archive files; never enable or publish a generator."""
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit,unquote
from urllib.request import HTTPRedirectHandler,Request,build_opener
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import now,digest
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city'
OUT=BASE/'own-annexes-0305'


class OwnOfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname!='www.eco-city.gov.cn':raise ValueError('Not this own official archive host')
        return super().redirect_request(req,fp,code,msg,headers,url)


def main():
    if OUT.exists():raise ValueError('Preserve existing files and evidence')
    OUT.mkdir(parents=True)
    rawfile=BASE/'discovery-0303/official-page.json';raw=json.loads(rawfile.read_text('utf8'))
    if raw['url']!='https://www.eco-city.gov.cn/p1/sqldzc/20171010/461.html' or '中新天津生态城内注册' not in raw['text']:
        raise ValueError('Own function-area source required')
    links=json.loads((BASE/'discovery-0303/public-links.json').read_text('utf8'))
    if len(links)!=5:raise ValueError('Own archive changed; review actual controls')
    result={'source_url':raw['url'],'source_title':raw['title'],'collected_at':raw['captured_at'],
            'raw_capture_sha256':hashlib.sha256(rawfile.read_bytes()).hexdigest(),
            'province':'tianjin','city':'天津市','district':'中新天津生态城',
            'platform_region_key':'function:tianjin-eco-city','official_region_code':None,
            'region_code_note':'内部候选功能区标识，不是已核实的官方行政区划编码，不等同整个滨海新区',
            'verification_status':'pending_archive_currency_and_form_review','published':False,'can_generate':False,
            'files':[],'warnings':['路径含2017，页面未显示当前更新日期；本轮仅核实公开可访问，现行要求待进一步确认。',
                                    '申请书名为样式，不据此断言官方空白；法律附件不是申请表格。']}
    opener=build_opener(OwnOfficialRedirect())
    for link in links:
        address=urlsplit(link['url'])
        if address.scheme!='https' or address.hostname!='www.eco-city.gov.cn' or not address.path.startswith('/u/cms/www/'):
            raise ValueError('Not this captured own public attachment')
        record={'source_url':raw['url'],'download_url':link['url'],'official_display_name':link['text'],
                'official_kind':'unverified_form_style' if '申请书' in link['text'] else 'unverified_evidence_form' if '证据清单' in link['text'] else 'legal_basis_document',
                'collected_at':now(),'can_generate':False}
        try:
            with opener.open(Request(link['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                body=response.read(20*1024*1024+1)
                if len(body)>20*1024*1024 or not body.startswith((b'PK',b'\xd0\xcf',b'%PDF')):raise ValueError('Not a supported original office file')
                name=unquote(response.headers.get_filename() or Path(address.path).name)
                name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name)
                dest=ROOT/'templates/_docx/_regional/function-tianjin-eco-city'/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.exists():raise ValueError('Original already exists; never overwrite')
                dest.write_bytes(body)
                record.update(original_name=name,filename_source='http_header' if response.headers.get_filename() else 'official_url_basename',
                              file=dest.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(body).hexdigest(),
                              bytes=len(body),download_status='downloaded',downloaded_at=now(),final_download_url=response.url)
        except Exception as exc:record.update(download_status='failed',reason=str(exc))
        result['files'].append(record);c.save(OUT/'original-files.json',result)
        print(record['official_kind'],record['download_status'],flush=True);time.sleep(1)
    c.save(BASE/'outbox/archive-currency-0305.json',{'id':digest([raw['url'],'SOURCE_STALE'])[:32],
        'type':'SOURCE_STALE','province':'tianjin','city':'天津市','district':'中新天津生态城',
        'region_code':'function:tianjin-eco-city','service':'劳动争议仲裁申请','url':raw['url'],'occurred_at':now(),
        'screenshot':(BASE/'discovery-0303/official-page.png').relative_to(ROOT).as_posix(),
        'reason':'页面路径2017、未明示当前更新日期，现行要求需复核；内部候选功能区key并非官方行政编码',
        'attempts':1,'final_status':'pending_current_guide_and_official_region_identity',
        'remediation':'保留原文及原附件，进一步核实自身现行指南和文书；不扩大至整个滨海新区或天津全市',
        'delivery_status':'PENDING_OPENCLAW'})


if __name__=='__main__':main()
