"""Record public own-source boundaries independently of candidate publication."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'


def main():
    out=BASE/'outbox/own-boundaries-0402.json'
    if out.exists():raise ValueError('Preserve existing own event evidence')
    out.parent.mkdir(exist_ok=True)
    g=json.loads((BASE/'guide.json').read_text('utf8'));entry=g['channel']['entry_check']
    raw=json.loads((BASE/'online-boundary-0345/after.json').read_text('utf8'))
    if '验证码' not in raw['text']:raise ValueError('Do not invent a captcha boundary')
    store=RegionalStore(ROOT/'backend/data/regional-guides.sqlite')
    assert store.lookup('jiangsu','盐城市','大丰区')['source_id'] is None
    events=[]
    for typ,reason,state in [
        ('AUTH_REQUIRED','实际点击自身官网在线办理到统一身份认证，停止于登录；未填写身份或提交申请。','manual_authorization'),
        ('CAPTCHA_REQUIRED','实际统一身份认证表单显示验证码；未识别、填写或绕过。','manual_authorization'),
        ('ONLINE_CHANNEL_UNVERIFIED','初次精确回跳核验不匹配；实际访问大丰自己的ycdf正式指南，独立核对机关、地区和事项编码后验证了官网别名映射。','resolved_by_own_callback_guide_capture'),
        ('MATERIAL_INFORMATION_MISSING','官网部分材料用途、适用情形及填报须知未单列填写；原文留空，不补造要求。','manual_review')]:
        events.append(store.record_event({'id':digest([g['source_url'],typ,entry['checked_at']])[:32],
            **{k:g[k] for k in ['province','city','district','region_code']},'service':g['service_name'],
            'type':typ,'url':g['source_url'] if typ=='MATERIAL_INFORMATION_MISSING' else entry['url'],
            'occurred_at':entry['checked_at'],'reason':reason,'attempts':1,'final_status':state,
            'screenshot':(BASE/('material-4.png' if typ=='MATERIAL_INFORMATION_MISSING' else 'online-boundary-0345/authentication-boundary.png')).relative_to(ROOT).as_posix(),
            'remediation':'只保留本地区公开证据；登录/验证码由用户自行处理，不代交申请、不调用模型'}))
    out.write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'public_events':len(events),'candidate_published':False,'delivery':'PENDING_OPENCLAW','receipt':None}))


if __name__=='__main__':main()
