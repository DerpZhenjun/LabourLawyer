"""Persist a real public guide navigation timeout, never claim local service absence."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest,now
from regional_directory import DirectoryStore
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian'
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'outbox/guide-target-round24.json'
    if out.exists():raise ValueError('Preserve prior actual failure event')
    failure=json.loads((BASE/'guide-target-round24/failure.json').read_text('utf8'))
    tabs=json.loads((BASE/'guide-target-round24/tabs.json').read_text('utf8'))
    target=next(t['url'] for t in tabs['tabs'] if t['url'].startswith('https://www.gdzwfw.gov.cn/portal/'))
    directory=DirectoryStore(ROOT/'backend/data/regional-directory.sqlite')
    with directory.connection() as db:
        rows=db.execute('SELECT payload FROM directory_areas WHERE id=? AND province=? AND city=? AND district=?',('national:440304','guangdong','深圳市','深圳市福田区')).fetchall()
    if len(rows)!=1:raise ValueError('Exact own directory identity ambiguous or missing')
    identity=json.loads(rows[0]['payload']);save(BASE/'directory-identity.json',identity)
    event=RegionalStore(ROOT/'backend/data/regional-guides.sqlite').record_event({
        'id':digest([target,failure['at'],'futian-index-native-follow'])[:32],
        'province':'guangdong','city':'深圳市','district':'福田区','region_code':identity['code'],
        'service':'劳动人事争议仲裁申请','type':'GUIDE_PAGE_UNAVAILABLE','url':target,'occurred_at':failure['at'],
        'reason':'实际点击福田区政府在线劳动仲裁办事指南→劳动人事争议仲裁申请→继续访问，新标签到广东政务服务网所列地址；等待事项正文25000ms超时。未获得目标正文或地区身份，不能断言该链接属于福田或不支持网上办理，也不表述为政府技术故障。',
        'attempts':1,'final_status':'pending_target_content_and_own_region_verification',
        'screenshot':(BASE/'discovery-round24/after-native-click.png').relative_to(ROOT).as_posix(),
        'remediation':'已保存目录DOM、外链提示截图、实际新标签URL及超时记录；doctor7pass0warn0fail。稍后低频核验其他自己的官方指南入口，不拿该链接或旧FAQ当已核验本区指南。'})
    save(out,[event])
    evidence={str(p.relative_to(ROOT).as_posix()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'discovery-round24/index.json',BASE/'discovery-round24/after-native-click.json',BASE/'guide-target-round24/tabs.json',BASE/'guide-target-round24/failure.json']}
    save(BASE/'DISCOVERY-STATUS.json',{'at':now(),'province':'guangdong','city':'深圳市','district':'福田区','region_code':identity['code'],'index_url':'https://www.szft.gov.cn/msfw/jyefw/ldzc/bszn/index.html','observed_target':target,'event':event['id'],'evidence_sha256':evidence,'guide_verified':False,'online_status':'unverified','published':False,'candidate':False,'models':0})
    print(json.dumps({'event':event['id'],'delivery':event['delivery_status'],'identity':identity['id'],'guide_verified':False,'models':0}))
if __name__=='__main__':main()
