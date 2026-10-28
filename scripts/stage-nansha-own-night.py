"""Own Nansha candidate/public metadata outbox only; never publish or infer models."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_nansha import parse_nansha_capture,SOURCE
from regional_guides import RegionalStore,digest
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha'
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    if (BASE/'guide.json').exists():raise ValueError('Preserve completed candidate')
    raw=json.loads((BASE/'source-round23/dom.json').read_text('utf8'));files=json.loads((BASE/'downloads-round23/original-files.json').read_text('utf8'))
    qa=json.loads((BASE/'document-qa/original-render.json').read_text('utf8'))
    assert qa['reviewed_page_count']==42 and len(qa['tasks'])==23 and qa['authoring'] is False
    for task in qa['tasks']:
        assert hashlib.sha256((ROOT/task['own_original']).read_bytes()).hexdigest()==task['own_sha256']
        assert all((ROOT/p).is_file() for p in task['pages'])
    guide=parse_nansha_capture(raw,files)
    guide['evidence']={'capture_file':(BASE/'source-round23/dom.json').relative_to(ROOT).as_posix(),
        'capture_sha256':hashlib.sha256((BASE/'source-round23/dom.json').read_bytes()).hexdigest(),
        'screenshot':(BASE/'source-round23/heading.png').relative_to(ROOT).as_posix(),
        'original_review':(BASE/'document-qa/artifact.md').relative_to(ROOT).as_posix()}
    staging=BASE/'staging-round23/staging.sqlite';staging.parent.mkdir()
    main_db=ROOT/'backend/data/regional-guides.sqlite'
    with sqlite3.connect(main_db.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(staging) as dest:src.backup(dest)
    own=RegionalStore(staging).put_guide(guide);save(BASE/'guide.json',guide)
    save(BASE/'staging-round23/candidate.json',{'source_id':own['source_id'],'version':own['version'],'published':False,
        'own_material_groups':9,'own_documents':23,'own_images':2,'own_original_pages_reviewed':42,
        'online_status':'unverified','adapters':0,'candidate_browser':'NOT_RUN','models':0})
    store=RegionalStore(main_db);assert store.lookup('guangdong','广州市','南沙区')['source_id'] is None
    events=[]
    for typ,reason in [
        ('ONLINE_CHANNEL_UNVERIFIED','本区材料公告没有明确网上立案入口；申请书“南沙e受达”是文书送达选项，不把送达等同网上申请。'),
        ('MATERIAL_INFORMATION_MISSING','自身材料公告不是完整现行指南；办理形式、时限、收费、到场次数、具体当前镇街受理窗口与办公时间尚未核验。'),
        ('OFFICIAL_SOURCE_CONFLICT','自己材料清单图片推举书1份，自身原附件推举书备注一式两份；均保留待机构确认。另个案申请书本机只读渲染有信息区域重叠，原因未明，未批准生成、不判断政府源文件错误。'),
        ('SOURCE_STALE','当前网页发布日期2020-04-23，原件仍含2017/2018管辖通知和2020版本说明，虽仍置顶可下载，但现行有效性尚未完整核验；不是宣称已经失效。')]:
        events.append(store.record_event({'id':digest([SOURCE,typ,raw['captured_at']])[:32],
            'province':'guangdong','city':'广州市','district':'南沙区','region_code':'440115','service':'劳动人事争议仲裁申请',
            'type':typ,'url':SOURCE,'occurred_at':raw['captured_at'],'reason':reason,'attempts':1,
            'final_status':'manual_review','screenshot':(BASE/'source-round23/annexes.png').relative_to(ROOT).as_posix(),
            'remediation':'保留本区原图、原件及SHA，独立核验本区现行指南；不借省级/邻区要求，不启用未适配生成。'}))
    save(BASE/'outbox/own-source-round23.json',events)
    print(json.dumps({'source_id':own['source_id'],'version':own['version'],'published':False,'events_pending':len(events),'ack':0}))
if __name__=='__main__':main()
