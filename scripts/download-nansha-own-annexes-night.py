"""Preserve Nansha's own public documents/images; never infer blank or currentness."""
import hashlib,json,sqlite3,time,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha'
SOURCE='https://www.gzns.gov.cn/gzjg/gzsnsq/qzfgzbm/qrlzyhshbzj/ldrszyzc/content/post_5801798.html'
class PublicAttachments(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.documents=[];self.images=[];self.active=None
    def handle_starttag(self,tag,attrs):
        value=dict(attrs);classes=value.get('class','').split()
        if tag=='a' and 'nfw-cms-attachment' in classes:
            self.active={'tag':tag,**value,'text':''};self.documents.append(self.active)
        elif tag=='img' and 'nfw-cms-img' in classes:self.images.append({'tag':tag,**value})
    def handle_data(self,text):
        if self.active is not None:self.active['text']+=text
    def handle_endtag(self,tag):
        if tag=='a':self.active=None
def verify_directory_identity():
    cached=json.loads((BASE/'downloads-round23/original-files.json').read_text('utf8'))
    assert len(cached)==25 and all(x['download_status']=='downloaded' for x in cached)
    for x in cached:assert hashlib.sha256((ROOT/x['file']).read_bytes()).hexdigest()==x['sha256']
    with sqlite3.connect((ROOT/'backend/data/regional-directory.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        found=db.execute('SELECT payload FROM directory_areas WHERE id=?',('national:440115',)).fetchall()
    assert len(found)==1;identity=json.loads(found[0][0])
    assert identity['code']=='440115' and identity['parent_code']=='440100' and identity['province']=='guangdong'
    assert identity['official_name']=='广州市南沙区' and identity['raw_record']['regionSname']=='南沙区'
    (BASE/'directory-identity.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2),encoding='utf8')
    return identity
def main():
    if sys.argv[1:]==['--verify-identity-only']:
        verify_directory_identity();print('25 cached originals SHA verified; national:440115 own full-name identity verified; no redownload');return
    out=BASE/'downloads-round23'
    if out.exists():raise ValueError('Preserve download evidence; do not overwrite')
    out.mkdir()
    raw=json.loads((BASE/'source-round23/dom.json').read_text('utf8'))
    assert raw['url']==SOURCE and '广州市南沙区劳动人事争议仲裁院' in raw['text']
    parser=PublicAttachments();parser.feed(raw['html']);nodes=parser.documents+parser.images
    assert len(nodes)==25,'Check source attachment inventory before downloading'
    results=[]
    for node in nodes:
        url=node.get('href') or node['src'];p=urlsplit(url)
        assert p.scheme=='https' and p.hostname=='www.gzns.gov.cn'
        identity=node.get('attachment-id') or node['img-id'];kind='original_document_unclassified' if node['tag']=='a' else 'official_guide_image'
        assert '/'+identity+'/' in p.path
        row={'id':identity,'source_url':SOURCE,'download_url':url,'original_name':node.get('text','').strip() or node.get('alt') or identity,
             'official_download_name':node.get('download') or node.get('alt'),'official_kind':kind,'can_generate':False,
             'collected_at':datetime.now(timezone.utc).isoformat(),'applicable_district':'南沙区','region_code':'440115'}
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:
                assert urlsplit(r.url).hostname=='www.gzns.gov.cn' and urlsplit(r.url).scheme=='https'
                data=r.read(16*1024*1024+1)
                if len(data)>16*1024*1024:raise ValueError('Oversize original')
                ext='doc' if data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')) else 'docx' if data.startswith(b'PK') else 'png' if data.startswith(b'\x89PNG\r\n\x1a\n') else None
                if ext is None or (node['tag']=='img' and ext!='png'):raise ValueError('Unexpected original signature')
                target=ROOT/'templates/_docx/_regional/440115'/(identity+'.'+ext);target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():assert target.read_bytes()==data,'Changed source: do not overwrite'
                else:target.write_bytes(data)
                row.update(file=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),file_type=ext,
                           download_status='downloaded',http_status=r.status,final_download_url=r.url,content_type=r.headers.get('Content-Type'))
        except Exception as exc:row.update(download_status='failed',download_error=str(exc))
        results.append(row);(out/'original-files.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
        print(identity,row['download_status'],flush=True);time.sleep(1)
    verify_directory_identity()
    print(json.dumps({'downloaded':sum(x['download_status']=='downloaded' for x in results),'total':len(results),'candidate':False,'models':0}))
if __name__=='__main__':main()
