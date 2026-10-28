"""Read own DOM structure and inspect an unexpected public flow-image response."""
import hashlib,json,sys
from pathlib import Path
from urllib.request import Request,urlopen
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-tongzhou'
def main():
    raw=json.loads((BASE/'sections-0650/materials-final.json').read_text('utf8'));d=html.fromstring(raw['html'])
    print('tables',[(e.get('id'),e.get('class')) for e in d.xpath('//table')])
    print('fields',[[c.text_content().strip()[:160] for c in row.xpath('./td')] for row in d.xpath('//*[@id="basic-main"]//tr')])
    print('main',[(e.tag,e.get('id'),e.get('class'),e.text_content().strip()[:220]) for e in d.xpath('//*[contains(@class,"time") or contains(@class,"task-title")]')][:25])
    u='https://banshi.beijing.gov.cn/pubtask/download/bef01726-9f33-4012-895e-909680993a3b.jpg'
    with urlopen(Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:
        b=r.read(4*1024*1024)
        evidence={'url':u,'final_url':r.url,'http_status':r.status,'content_type':r.headers.get('Content-Type'),
            'bytes':len(b),'first_16_bytes_hex':b[:16].hex(),'sha256':hashlib.sha256(b).hexdigest()}
        if b.startswith(b'\x89PNG\r\n\x1a\n'):actual='png'
        elif b.startswith(b'GIF8'):actual='gif'
        elif b.startswith(b'\xff\xd8'):actual='jpg'
        else:actual=None
        evidence['actual_file_type']=actual
        p=BASE/'downloads-0700/flow-response-inspection.json'
        if p.exists():raise ValueError('Preserve prior response inspection')
        p.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
        if actual:
            q=ROOT/'templates/_docx/_regional/110112'/('bef01726-9f33-4012-895e-909680993a3b.'+actual)
            if q.exists():assert q.read_bytes()==b
            else:q.write_bytes(b)
        print(json.dumps(evidence))
if __name__=='__main__':main()
