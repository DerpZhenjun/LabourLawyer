"""Public visible Hunan own-district evidence; no session/auth/HAR persistence."""
import argparse,datetime,hashlib,json,pathlib,subprocess,urllib.request,urllib.parse,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/nationwide-verification-20261029-b/hunan'
BROWSER=r'D:\Apps\agent-browser\node_modules\agent-browser\bin\agent-browser-win32-x64.exe'
SESSION='hn-oct29b'
def browser(*args):
 p=subprocess.run([BROWSER,'--session',SESSION,*args],capture_output=True,text=True,encoding='utf8',timeout=65)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout.strip()
def evaluate(code):
 value=json.loads(browser('eval',code));return json.loads(value) if isinstance(value,str) else value
def save(path,value):
 path=REPORT/path;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def capture(name):
 p=evaluate('''JSON.stringify({url:location.href,title:document.title,text:document.body.innerText,tables:Array.from(document.querySelectorAll('table')).map(t=>Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.innerText))),materials:Array.from(document.querySelectorAll('dl[data-material-id]')).map(e=>({id:e.dataset.materialId,text:e.innerText})),links:Array.from(document.querySelectorAll('a')).map(a=>({text:a.innerText,href:a.getAttribute('href'),title:a.title,onclick:a.getAttribute('onclick')}))})''')
 if 'auth.' in p['url'] or 'login' in p['url'].lower():raise ValueError('Do not persist auth URLs or DOM')
 p['captured_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();folder=REPORT/name;folder.mkdir(parents=True,exist_ok=True)
 save(name+'/page.json',p);(folder/'page.txt').write_text(p['text'],encoding='utf8');(folder/'snapshot.txt').write_text(browser('snapshot','-i'),encoding='utf8')
 browser('screenshot','--full',str(folder/'page.png'))
 save(name+'/manifest.json',{'source_url':p['url'],'captured_at':p['captured_at'],'files':{x.name:{'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'bytes':x.stat().st_size} for x in folder.iterdir() if x.is_file() and x.name!='manifest.json'}})
 print(json.dumps({'capture':name,'url':p['url'],'chars':len(p['text'])},ensure_ascii=False))
def save_controls(name):
 p=evaluate('''JSON.stringify({source_url:location.href,public_fetches:performance.getEntriesByType('resource').filter(e=>e.name.includes('/picPathMapping?')&&/\.doc(?:&|$)/.test(decodeURIComponent(e.name))).map(e=>({url:e.name,status:e.responseStatus}))})''')
 p['captured_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save(name+'/attachment-observation.json',p)
def download_originals(name):
 catalogue=json.loads((REPORT/name/'public-catalogue.json').read_text(encoding='utf8'))['public_response']
 observation=json.loads((REPORT/name/'attachment-observation.json').read_text(encoding='utf8'));records=[]
 for material in catalogue['materialList']:
  for attachment in material.get('attachList',[]):
   role={'000002':'blank','000003':'sample'}.get(attachment.get('attachCode'))
   if not role or attachment.get('attachType')!='.doc':continue
   url='https://zwfw-new.hunan.gov.cn/picPathMapping?'+urllib.parse.urlencode({'picPath':attachment['attachPath'],'bucketName':attachment['bucketName']})
   if not any(urllib.parse.unquote(x['url'])==urllib.parse.unquote(url) for x in observation['public_fetches']):raise ValueError('Own file Fetch not observed')
   filename=attachment['attachPath'].split('/')[-1].split('$$')[0]+'.doc';relative=name+'/originals/'+role+'/'+filename;path=REPORT/relative
   metadata=path.with_suffix(path.suffix+'.source.json')
   if path.is_file() and metadata.is_file():
    existing=json.loads(metadata.read_text(encoding='utf8'))
    if existing['download_url']!=url or existing['sha256']!=hashlib.sha256(path.read_bytes()).hexdigest():raise ValueError('Retained acquisition mismatch')
    records.append(existing);continue
   with urllib.request.urlopen(url,timeout=25) as response:body=response.read();status=response.status;final=response.url
   if not body.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):raise ValueError('Official download is not a legacy Word document')
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
   record={'source_url':observation['source_url'],'approve_id':catalogue['approveId'],'area_code':catalogue['areaCode'],'material_id':material.get('materialId'),'official_annex_id':attachment['attachId'],
      'file':relative,'original_name':attachment['attachName'],'official_control':role,'attach_code':attachment['attachCode'],'download_url':url,'final_url':final,'http_status':status,
      'downloaded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'method':'cookie-free public HTTP after own native material control Fetch'}
   save(relative+'.source.json',record);records.append(record);time.sleep(1)
 save(name+'/originals.json',records);print(json.dumps({'district':name,'downloaded':len(records)}))
def save_boundary(name):
 p=evaluate('''JSON.stringify({origin:location.origin,path:location.pathname,text:document.body.innerText.slice(0,1800),passwordInputs:document.querySelectorAll('input[type=password]').length})''')
 if p['origin']!='https://auth.zwfw.hunan.gov.cn':raise ValueError('Not the own observed authentication boundary')
 p.update(captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='auth_required',submitted=False,redaction='query, headers, cookies, login DOM and all credentials not retained')
 save(name+'/online-boundary.json',p);browser('screenshot',str(REPORT/name/'online-boundary.png'))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('capture');args=parser.parse_args();capture(args.capture)
