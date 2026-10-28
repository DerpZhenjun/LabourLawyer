"""Bounded public-directory fallback using the national site's published JS API.
Only collect candidates; a native browser and content review must confirm guides.
"""
import argparse,concurrent.futures,hashlib,json,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from province_experience import POLICY
from openclaw_browser_tasks import TASK_ROOT,save
BASE='http://gjzwfw.www.gov.cn/fwmh'
QUERIES=('劳动仲裁','劳动人事争议仲裁','劳动人事争议调解')
def request(folder,name,path,fields):
    target=folder/(name+'.json');evidence=folder/(name+'-request.json')
    if target.exists() and evidence.exists():return json.loads(target.read_text('utf8'))
    url=BASE+path;body=urlencode(fields)
    p=subprocess.run(['curl.exe','--silent','--show-error','--connect-timeout','5','--max-time','25','--output',str(target),'--write-out','%{http_code}','--data',body,url],capture_output=True,timeout=30)
    content=target.read_bytes() if target.exists() else b''
    save(evidence,{'url':url,'fields':fields,'http_status':p.stdout.decode(),'returncode':p.returncode,'error':p.stderr.decode(errors='replace')[:600],'sha256':hashlib.sha256(content).hexdigest(),'source_js':'national-navigation/services/work.js'})
    if p.returncode or p.stdout!=b'200':raise RuntimeError('Directory request failed; see '+str(evidence))
    return json.loads(content)
def probe(slug,run,config):
    folder=run/'national-directory-recovery'/slug;folder.mkdir(parents=True,exist_ok=True)
    root=config['navigation_embedded'][slug][-1];code=parse_qs(urlsplit(root).query)['regionCode'][0]
    regions=request(folder,'cities','/ucGovRegion/findUcGovRegion.do',{'parentId':code})
    city=next((x for x in regions.get('data',[]) if x.get('regionName')==POLICY['capitals'][slug]),None)
    selected=[]
    if city:
        selected.append(city)
        districts=request(folder,'districts','/ucGovRegion/findUcGovRegion.do',{'parentId':city['regionCode']})
        if districts.get('data'):selected.append(districts['data'][0])
    candidates=[];attempts=[]
    for place in reversed(selected):
        for i,word in enumerate(QUERIES):
            name=place['regionCode']+'-'+str(i)
            data=request(folder,name,'/item/v3/findItemList.do',{'pageNo':1,'pageSize':10,'areaCode':place['regionCode'],'taskName':word,'serverType':1})
            rows=(data.get('data') or {}).get('list') or []
            attempts.append({'region':place,'query':word,'success':data.get('success'),'code':data.get('code'),'message':data.get('message'),'count':len(rows)})
            for row in rows:
                name=row.get('taskName','')
                if '劳动' not in name or not any(w in name for w in ('仲裁','调解')):continue
                task=row.get('taskBlCode') or row.get('taskCode')
                if not task or not str(task).replace('-','').isalnum():continue
                candidates.append({'url':BASE+'/item/v3/item_'+str(task)+'.do','region':place,'record':row,'source_response':str(folder/(place['regionCode']+'-'+str(i)+'.json'))})
        if candidates:break
    result={'slug':slug,'state':'candidates_require_browser_verification' if candidates else 'no_candidate_returned','selected_regions':selected,'attempts':attempts,'candidates':candidates}
    save(folder/'result.json',result);print(slug,result['state'],len(candidates),flush=True);return slug,result
def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--provinces',default='hebei,hubei,hainan,shandong,henan,heilongjiang,ningxia');a=p.parse_args();run=a.run.resolve()
    if not run.is_relative_to(TASK_ROOT.resolve()):raise ValueError('Evidence must stay in task directory')
    config=json.loads((ROOT/'config/province_service_portals.json').read_text('utf8'));results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(probe,slug,run,config):slug for slug in a.provinces.split(',')}
        for future in concurrent.futures.as_completed(futures):
            slug=futures[future]
            try:_,result=future.result();results[slug]=result
            except Exception as exc:results[slug]={'state':'failed','error':str(exc)};print(slug,str(exc),flush=True)
    save(run/'national-directory-recovery/results.json',results)
if __name__=='__main__':main()
