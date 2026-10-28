"""Bounded aliases for the observed Sichuan public search, exact match unchanged."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlsplit

from chengdu_collection import select_service
from regional_directory import clock

KEYWORDS=('劳动人事争议仲裁申请','劳动人事争议仲裁','劳动仲裁','劳动人事')
ENDPOINT='https://www.sczwfw.gov.cn/jsearchfront/interfaces/searchMatterUrl.do?'


class SearchResponseError(ValueError):
    def __init__(self,url,keyword):
        super().__init__('官网检索未返回结果列表，不能认定为无结果')
        self.url=url
        self.keyword=keyword


def discover_service(code, folder, request, pause):
    folder=Path(folder)
    attempts=[]
    for index,keyword in enumerate(KEYWORDS):
        # Reuse the original full-keyword evidence, never replace its clock.
        path=folder/(code+'.json') if index==0 else folder/'aliases'/(code+'-'+hashlib.sha256(keyword.encode()).hexdigest()[:12]+'.json')
        url=ENDPOINT+urlencode({'title':keyword,'websiteid':code+'000'})
        if path.is_file():
            record=json.loads(path.read_text('utf8'))
            if record.get('url')!=url:raise ValueError('缓存检索链接与地区或关键词不匹配')
        else:
            raw=request(url)
            response=json.loads(raw)
            if not isinstance(response.get('data'),list):
                errors=folder/'errors';errors.mkdir(parents=True,exist_ok=True)
                evidence={'url':url,'keyword':keyword,'region_code':code,'collected_at':clock(),
                          'response':response,'response_sha256':hashlib.sha256(raw).hexdigest(),
                          'status':'invalid_response_not_no_result'}
                # Append by response digest, never erase an earlier response.
                (errors/(code+'-'+hashlib.sha256(raw+url.encode()).hexdigest()[:20]+'.json')).write_text(
                    json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
                raise SearchResponseError(url,keyword)
            record={'url':url,'keyword':keyword,'collected_at':clock(),'response':response,
                    'response_sha256':hashlib.sha256(raw).hexdigest()}
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
            pause(1.5)
        if not isinstance(record.get('response',{}).get('data'),list):
            raise ValueError('官网检索未返回结果列表，不能认定为无结果')
        service=select_service(record['response'],code)
        attempts.append({'keyword':keyword,'url':url,'collected_at':record['collected_at'],
                         'returned_rows':len(record['response']['data']),'target_found':service is not None,
                         'capture_file':str(path),'matching_rule':'exact_service_name_and_own_region_and_official_formal_guide'})
        if service:return {'service':service,'attempts':attempts,'alias_required':index>0}
        # Some exact matches use the province's newer public portal. They must
        # be clicked through in a browser; never fabricate the formal URL.
        summaries={}
        for row in record['response']['data']:
            item=row.get('data',{});address=urlsplit(item.get('url',''))
            if (item.get('title')=='劳动人事争议仲裁申请' and item.get('areacode')==code
                    and address.hostname=='www.sczwfw.gov.cn'
                    and address.path=='/jiq4/front/transition/ywTransToDetail_summary'
                    and parse_qs(address.query).get('areaCode')==[code]):
                summaries[item['url']]=item
        if len(summaries)>1:raise ValueError('多个不同新版概览候选，需人工核验')
        if summaries:
            attempts[-1]['outcome']='exact_v4_summary_requires_browser_navigation'
            return {'service':None,'summary_candidate':next(iter(summaries.values())),
                    'attempts':attempts,'alias_required':index>0}
    return {'service':None,'attempts':attempts,'alias_required':False}


def requeue_search_misses(store):
    """Call only under the collector's OS lock and on an explicit retry run."""
    with store.connection() as db:
        rows=db.execute("SELECT id,result FROM discovery_jobs WHERE kind='sichuan_capture' AND state='manual_review'").fetchall()
        ids=[r['id'] for r in rows if json.loads(r['result'] or '{}').get('type')=='SEARCH_NO_RESULT'
             and not json.loads(r['result'] or '{}').get('alias_attempts_completed')]
        for identity in ids:
            db.execute("UPDATE discovery_jobs SET state='pending',updated_at=? WHERE id=?",(clock(),identity))
    return ids
