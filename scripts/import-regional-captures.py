"""Import only actual browser captures. Download public official annexes at low rate."""
import hashlib,json,os,re,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_capture import parse_sichuan_capture
from regional_guides import RegionalStore,digest
from regional_adapters import with_reference_capabilities
REPORT=ROOT/'reports/government-guide-localization'

def public_get(url):
    host=urlsplit(url).hostname or ''
    if not (host=='www.sczwfw.gov.cn' or host.endswith('.sczwfw.gov.cn')):raise ValueError('附件下载跳转到未授权域名')
    with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as response:
        if not (urlsplit(response.url).hostname or '').endswith('sczwfw.gov.cn'):raise ValueError('非官方最终地址')
        body=response.read(20*1024*1024+1)
        if len(body)>20*1024*1024:raise ValueError('附件超过20MB限制')
        return body,response.url

def run():
    manifest=json.loads((REPORT/'CAPTURE-MANIFEST.json').read_text(encoding='utf8'))
    store=RegionalStore(os.getenv('LABOURLAWYER_REGIONAL_DB',ROOT/'backend/data/regional-guides.sqlite'))
    event=lambda data:store.record_event({'id':digest(data)[:32],**data})
    for entry in manifest['captures']:
        raw=json.loads((REPORT/entry['file']).read_text(encoding='utf-8-sig'))
        if isinstance(raw,str):raw=json.loads(raw)
        guide=parse_sichuan_capture(raw,entry['city'],entry['district'],entry.get('entry_check'))
        previous=store.lookup(guide['province'],guide['city'],guide['district'])
        guide['evidence']={'capture_file':entry['file'],'screenshot':entry['screenshot'],'capture_sha256':hashlib.sha256((REPORT/entry['file']).read_bytes()).hexdigest()}
        for t in guide['templates']:
            safe_name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',t['original_name'])[:140]
            relative=Path('templates/_docx/_regional')/guide['region_code']/(t['annex_id']+'-'+safe_name)
            path=ROOT/relative
            try:
                if path.is_file():
                    body=path.read_bytes()
                    old=next((item for item in previous.get('templates',[]) if item['id']==t['id']),{})
                    for key in ('download_url','final_download_url'):
                        if old.get(key):t[key]=old[key]
                else:
                    response=json.loads(public_get(t['download_endpoint'])[0])
                    if str(response.get('code'))!='0':raise ValueError('官方附件接口未返回下载地址')
                    download_url=response['data'];body,final_url=public_get(download_url)
                    if not body.startswith((b'PK',b'%PDF',b'\xff\xd8',b'\xd0\xcf')):raise ValueError('返回内容不是预期文书或图片')
                    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
                    t.update(download_url=download_url,final_download_url=final_url)
                    time.sleep(1)
                t.update(file=str(relative.as_posix()),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),download_status='downloaded',verified_at=raw['captured_at'])
            except Exception as exc:
                t.update(download_status='failed',download_error=str(exc))
                event({'type':'TEMPLATE_DOWNLOAD_FAILED','province':'sichuan','city':entry['city'],'district':entry['district'],'service':guide['service_name'],'url':t['download_endpoint'],'screenshot':entry['screenshot'],'reason':str(exc),'final_status':'pending','remediation':'重新访问官方材料下载控件后重试'})
        guide=store.put_guide(with_reference_capabilities(guide))
        common={'province':'sichuan','city':entry['city'],'district':entry['district'],'region_code':guide['region_code'],'service':guide['service_name'],'url':guide['source_url'],'occurred_at':guide['collected_at'],'screenshot':entry['screenshot']}
        status=guide['channel']['online_status']
        if status=='unavailable':event({**common,'type':'ONLINE_APPLICATION_UNAVAILABLE','reason':'官方办理形式为窗口办理，是否网办为否；属于办理能力限制，不是技术故障','final_status':'verified','remediation':'提供窗口地点、时间、到场要求和材料'})
        elif status=='conflict':event({**common,'type':'OFFICIAL_SOURCE_CONFLICT','reason':'办理形式/是否网办与流程、FAQ提到的线上申请不一致；窗口地址与FAQ地址也不一致','final_status':'manual_review','remediation':'保留各栏目原文，建议向机构确认，不展示可用网上申请按钮'})
        elif status=='auth_required':event({**common,'type':'AUTH_REQUIRED','reason':'真实点击在线申请进入个人登录页，未登录或提交申请','final_status':'manual_authorization','remediation':'用户自行登录官方平台办理'})
        if status in {'conflict','unverified'}:event({**common,'type':'ONLINE_CHANNEL_UNVERIFIED','reason':'线上渠道待核验；天府新区流程中的公开IP入口本次浏览器返回HTTP 502' if status=='conflict' else '尚未完成网上入口核验','screenshot':entry.get('entry_check',{}).get('screenshot',entry['screenshot']),'final_status':'pending','remediation':'保留核验状态；不要将没找到入口误判为不支持'})
        if not any(t['official_kind']=='blank' and '仲裁申请书' in t['original_name'] for t in guide['templates']):event({**common,'type':'OFFICIAL_TEMPLATE_NOT_FOUND','reason':'仲裁申请书下载被官方标注为示例样表，未发现申请书空白表格；不冒充空白模板','final_status':'documented','remediation':'明确样表来源；仅在该地区通过位置和SHA校验后提供参考填写'})
        missing=[k for k,v in guide['fields'].items() if v['verification_status']=='missing']
        if missing:event({**common,'type':'MATERIAL_INFORMATION_MISSING','reason':'未填写字段：'+','.join(missing),'final_status':'pending','remediation':'原文空白保留，界面显示待核实'})
        print(entry['district'],guide['source_id'],len(guide['materials']),len(guide['templates']),status,flush=True)
    for search in manifest['searches']:
        event({'province':'sichuan','service':'劳动人事争议仲裁申请','keyword':search['keyword'],'url':search['url'],'screenshot':search['screenshot'],'type':'SEARCH_ALIAS_REQUIRED' if search['target_found'] else 'SEARCH_NO_RESULT','reason':search['result_state'],'attempts':2,'final_status':'resolved','remediation':'改用劳动人事争议仲裁后找到准确事项'})
    inventory={'collected_at':max(g['collected_at'] for g in store.inventory()),'regions':store.inventory(),'searches':manifest['searches']}
    (REPORT/'SOURCE-INVENTORY.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf8')
    (REPORT/'COLLECTION-ISSUES.json').write_text(json.dumps(store.events(),ensure_ascii=False,indent=2),encoding='utf8')
    (REPORT/'outbox').mkdir(exist_ok=True)
    (REPORT/'outbox/pending-public-events.json').write_text(json.dumps([e for e in store.events() if e['delivery_status']=='PENDING_OPENCLAW'],ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':run()
