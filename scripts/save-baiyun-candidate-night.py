"""Save an independent public candidate and durable public issues, no publication."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guangdong import parse_baiyun_capture
from regional_guides import RegionalStore,digest
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-baiyun'
NIGHT=ROOT/'reports/nationwide-localization-20261023-night'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')


def main():
    if (BASE/'guide.json').exists():raise ValueError('Keep completed candidate evidence')
    raw=json.loads((BASE/'source-0405/dom.json').read_text('utf8'))
    files=json.loads((BASE/'downloads-0410/original-files.json').read_text('utf8'))
    g=parse_baiyun_capture(raw,files)
    render=json.loads((BASE/'document-qa/original-render.json').read_text('utf8'))
    if len(render['tasks'])!=8 or sum(len(t['pages']) for t in render['tasks'])!=18:raise ValueError('Own original pages incomplete')
    if not (BASE/'document-qa/visual-review.md').is_file():raise ValueError('Own original review missing')
    for task in render['tasks']:
        if any(not (ROOT/p).is_file() for p in task['pages']):raise ValueError('Missing own render page')
    g['evidence']={'capture_file':(BASE/'source-0405/dom.json').relative_to(ROOT).as_posix(),
        'capture_sha256':hashlib.sha256((BASE/'source-0405/dom.json').read_bytes()).hexdigest(),
        'screenshot':(BASE/'source-0405/source.png').relative_to(ROOT).as_posix(),
        'original_review':(BASE/'document-qa/visual-review.md').relative_to(ROOT).as_posix()}
    save(BASE/'guide.json',g)
    # Isolated copy of the public regional DB; never access users or case data.
    staging=BASE/'staging-0415/staging.sqlite';staging.parent.mkdir(exist_ok=True)
    if staging.exists():raise ValueError('Preserve prior candidate database')
    main_db=ROOT/'backend/data/regional-guides.sqlite'
    with sqlite3.connect(main_db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(staging) as dest:source.backup(dest)
    candidate=RegionalStore(staging).put_guide(g)
    store=RegionalStore(main_db)
    assert store.lookup('guangdong','广州市','白云区')['source_id'] is None
    save(BASE/'staging-0415/candidate.json',{'source_id':candidate['source_id'],'version':candidate['version'],
        'published':False,'materials':6,'original_files':8,'adapters':0,'candidate_browser':'NOT_RUN',
        'scope':'Own material notice, not full formal guide; source method and current window conditions unresolved',
        'no_staging_launch_attempt':True,'no_models':True})
    events=[]
    for typ,reason in [
        ('ONLINE_CHANNEL_UNVERIFIED','实际白云区材料公告未明确办理形式或网上提交入口；纸质材料和邮寄收件单不等于只支持窗口办理。'),
        ('OFFICIAL_SOURCE_CONFLICT','官方公告提示第4页提交人签字，但自身空白原件本次只读渲染中提交人位于第3页。按签字标签核对，不静默改写原文。'),
        ('MATERIAL_INFORMATION_MISSING','自身材料公告不是完整办事指南；窗口时间、时限、收费、现场次数及附录旧地址和受理条款现行有效性尚未独立核验。')]:
        events.append(store.record_event({'id':digest([g['source_url'],typ,g['verified_at']])[:32],
            **{k:g[k] for k in ['province','city','district','region_code']},'service':g['service_name'],
            'type':typ,'url':g['source_url'],'occurred_at':g['verified_at'],'reason':reason,
            'attempts':1,'final_status':'manual_review','screenshot':g['evidence']['screenshot'],
            'remediation':'保留本区原文、原件和差异；继续寻找本区正式指南，不借用省级或其他区县资料。'}))
    hbase=NIGHT/'cross-province/guangdong-heshan/source-0405'
    hraw=json.loads((hbase/'dom.json').read_text('utf8'))
    if 'NET::ERR_CERT_AUTHORITY_INVALID' not in hraw['text']:raise ValueError('Do not fabricate an auth/TLS failure')
    events.append(store.record_event({'id':digest(['heshan-cert',hraw['captured_at']])[:32],
        'province':'guangdong','city':'江门市','district':'鹤山市','region_code':'440784',
        'service':'劳动人事争议仲裁申请','type':'GUIDE_PAGE_UNAVAILABLE',
        'url':'https://www.heshan.gov.cn/zwgk/xxgk/hssrlzyhshbzj/qt/tzgg/content/post_3472991.html',
        'occurred_at':hraw['captured_at'],'reason':'实际浏览器停止于NET::ERR_CERT_AUTHORITY_INVALID证书警告；仅记录本次访问限制，不认定政府网站业务故障。',
        'attempts':1,'final_status':'pending_certificate_verification','screenshot':(hbase/'source.png').relative_to(ROOT).as_posix(),
        'remediation':'未点击继续访问、未忽略HTTPS错误、未采集为指南；保留截图，继续其他地区。'}))
    save(BASE/'outbox/own-source-0415.json',events)
    print(json.dumps({'candidate_source':candidate['source_id'],'staging_version':candidate['version'],
        'published':False,'adapters':0,'public_events':4,'delivery':'PENDING_OPENCLAW','receipt':None}))


if __name__=='__main__':main()
