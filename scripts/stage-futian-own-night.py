"""Independent public supplementary candidate; no publication, private data or models."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_futian import parse_futian_capture,SOURCES
from regional_guides import RegionalStore,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian'
PATHS={'materials':'materials-channel-round25/materials/dom.json','jurisdiction':'articles-round25/jurisdiction/dom.json','query':'articles-round25/query/dom.json','channel':'channel-recovery-round25/channel/dom.json','entry':'online-boundary-round25/public-page.json','apply':'apply-click-round25/public-page.json'}
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'staging-round25'
    if out.exists():raise ValueError('Preserve previous own candidate iteration')
    pages={k:json.loads((BASE/p).read_text('utf8')) for k,p in PATHS.items()};guide=parse_futian_capture(pages)
    identity=json.loads((BASE/'directory-identity.json').read_text('utf8'))
    assert identity['id']=='national:440304' and identity['district']=='深圳市福田区' and identity['city']=='深圳市'
    guide['directory_identity']={'id':identity['id'],'official_name':identity['district'],'source_url':identity['source_url'],'code':identity['code']}
    out.mkdir()
    with sqlite3.connect((ROOT/'backend/data/regional-guides.sqlite').as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(out/'staging.sqlite') as target:source.backup(target)
    store=RegionalStore(out/'staging.sqlite');candidate=store.put_guide(guide)
    public=RegionalStore(ROOT/'backend/data/regional-guides.sqlite')
    assert public.lookup('guangdong','深圳市','福田区')['source_id'] is None
    save(out/'guide.json',guide);save(BASE/'guide.json',guide)
    evidence={k:{'file':str((BASE/p).relative_to(ROOT).as_posix()),'sha256':hashlib.sha256((BASE/p).read_bytes()).hexdigest(),'captured_at':pages[k]['captured_at']} for k,p in PATHS.items()}
    save(out/'source-checksums.json',evidence)
    save(out/'candidate.json',{'at':now(),'source_id':candidate['source_id'],'version':candidate['version'],'own_material_groups':8,'official_annexes':0,'adapters':0,'source_type':guide['source_type'],'published':False,'candidate_browser':'NOT_RUN','online_status':'unverified','models':0})
    reasons=[
        ('SOURCE_STALE',SOURCES['materials'][0],'福田自己的材料FAQ发布日期2018-02-08；正文和日期已保存，现行受理要求尚未确认，不因仍可访问就宣称为当前标准，也不直接宣称已失效。','materials-channel-round25/materials/heading.png','向本区机构确认现行材料，保留每个来源自己的发布时间和核验时间。'),
        ('OFFICIAL_TEMPLATE_NOT_FOUND',SOURCES['materials'][0],'本次实际查看福田自己的材料FAQ、管辖FAQ、查询FAQ及明确列出福田的市级渠道FAQ，未获得本区可公开下载的空白文书附件；不代表全网不存在。','materials-channel-round25/materials/content.png','继续本区官方附件入口；不得拿广东省级或其他区模板冒充本区模板，无模板不生成。'),
        ('ONLINE_CHANNEL_UNVERIFIED',SOURCES['channel'][0],'市人社局公告明确列出福田可在平台申请。实际公开平台→我要仲裁→申请仲裁后认证站tyrz.gd.gov.cn返回ERR_EMPTY_RESPONSE；未完成认证，未提交，不能据此认定政府技术故障或不支持网办。','apply-click-round25/login-boundary.png','保留官方申请能力声明与本次访问失败两项证据，实际网办状态unverified，不显示已核验入口；不重试认证或绕过访问控制。'),
        ('MATERIAL_INFORMATION_MISSING',SOURCES['materials'][0],'自己的四份补充说明不是完整正式办事指南；办理形式、窗口地点时间电话、服务时限收费到场次数及部分材料份数未核实。页脚福民路123号1409室是网站联系地址，不能当仲裁窗口。','articles-round25/jurisdiction/heading.png','已保存8组自身旧FAQ劳动者材料及条件，单位申请仅保留原文；查询不等于申请，管辖不能按户籍自动判断。补齐正式指南后再验收发布。')]
    events=[]
    for kind,url,reason,screenshot,remediation in reasons:
        events.append(public.record_event({'id':digest([url,kind,'futian-own-round25'])[:32],'province':'guangdong','city':'深圳市','district':'福田区','region_code':'440304','service':'劳动人事争议仲裁申请','type':kind,'url':url,'occurred_at':now(),'reason':reason,'attempts':1,'final_status':'own_supplementary_candidate_pending_verification','screenshot':str((BASE/screenshot).relative_to(ROOT).as_posix()),'remediation':remediation}))
    save(BASE/'outbox/own-source-round25.json',events)
    print(json.dumps({'source':candidate['source_id'],'version':candidate['version'],'materials':8,'templates':0,'published':False,'events':[e['id'] for e in events],'delivery':'PENDING_OPENCLAW','models':0}))
if __name__=='__main__':main()
