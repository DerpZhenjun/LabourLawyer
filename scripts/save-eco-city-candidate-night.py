"""Persist public source issues without publishing an unaccepted guide."""
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('own_ecocity_stage',ROOT/'scripts/stage-eco-city-night.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from regional_guides import RegionalStore,digest


def main():
    guide=m.prepare();base=m.BASE;sid=digest(guide['source_url'])[:24]
    dest=base/'guide.json'
    if dest.exists():raise ValueError('Keep prior source capture intact')
    m.save(dest,guide)
    store=RegionalStore(ROOT/'backend/data/regional-guides.sqlite');events=[]
    assert store.lookup('tianjin','天津市','中新天津生态城')['source_id'] is None
    for typ,reason,state in [
        ('ONLINE_APPLICATION_UNAVAILABLE','实际点击官网在线办事栏目：此事项未开通在线受理功能。属于办理能力限制，不是技术故障。','verified_window_only'),
        ('OFFICIAL_SOURCE_CONFLICT','指南电话022-66179792与现行人社栏目022-66386789、022-66328970不同，保留双来源。','manual_confirmation_required'),
        ('SOURCE_STALE','现行目录仍链接本指南，但具体内容更新时间未公示，前往窗口前应确认。','current_catalogue_link_verified_content_date_unknown')]:
        events.append(store.record_event({'id':digest([sid,typ,guide['verified_at']])[:32],
            'province':'tianjin','city':'天津市','district':'中新天津生态城','region_code':guide['region_code'],
            'service':guide['service_name'],'type':typ,'url':guide['source_url'],'reason':reason,'final_status':state,
            'screenshot':guide['evidence']['online-channel' if typ=='ONLINE_APPLICATION_UNAVAILABLE' else 'current-service-portal'],
            'remediation':'保留自身来源及不确定性，不扩展至整个天津或滨海新区；请机构确认'}))
    m.save(base/'outbox/guide-publication-0340.json',events)
    m.save(m.OUT/'acceptance-pending.json',{'candidate_source_id':sid,'published':False,'can_generate':False,
        'blocked_step':'owned staging web services launch command rejected by execution policy; no alternate launch attempted',
        'staging_browser':'NOT_RUN','main_baseline':'5 actual MCP checks passed, not candidate publication acceptance',
        'original_render':'all four original pages visually inspected; no source file changed',
        'model_calls':0,'openclaw':'PENDING_OPENCLAW','receipt':None})
    print(json.dumps({'candidate_saved':True,'published':False,'public_events':len(events),'source_id':sid}))


if __name__=='__main__':main()
