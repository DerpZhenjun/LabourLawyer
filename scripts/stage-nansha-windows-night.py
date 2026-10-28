"""Version own receiving-window supplement in an independent public candidate DB."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_nansha import apply_nansha_windows,WINDOW_SOURCE
from regional_guides import RegionalStore,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha'
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'staging-round24'
    if out.exists():raise ValueError('Preserve prior supplement iteration')
    old=json.loads((BASE/'guide.json').read_text('utf8'));raw=json.loads((BASE/'windows-round23/dom.json').read_text('utf8'))
    updated=apply_nansha_windows(old,raw)
    if hashlib.sha256((BASE/'windows-round23/dom.json').read_bytes()).hexdigest()!='1219eb28c72f4f77c8e0c4594754f4af136103e2a7e390fc4da7edbc265f159f':
        raise ValueError('Own already inspected source snapshot changed')
    assert old['templates']==updated['templates'] and old['materials']==updated['materials']
    out.mkdir()
    # Preserve the previous own candidate, not the users/cases database.
    with sqlite3.connect((BASE/'staging-round23/staging.sqlite').as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(out/'staging.sqlite') as dest:source.backup(dest)
    stage=RegionalStore(out/'staging.sqlite');before=stage.lookup('guangdong','广州市','南沙区');candidate=stage.put_guide(updated)
    assert before['version']!=candidate['version'] and before['source_id']==candidate['source_id']
    assert len(candidate['office_information']['labour_receiving_windows'])==10
    save(out/'before-guide.json',old);save(out/'guide.json',updated)
    save(out/'window-check.json',candidate['office_information'])
    save(out/'candidate.json',{'at':now(),'source_id':candidate['source_id'],'versions':[before['version'],candidate['version']],
        'own_window_source_url':WINDOW_SOURCE,'labour_receiving_windows':10,'own_materials':9,'own_documents':23,
        'adapters':0,'online_status':candidate['channel']['online_status'],'published':False,'candidate_browser':'NOT_RUN','models':0})
    public=RegionalStore(ROOT/'backend/data/regional-guides.sqlite')
    assert public.lookup('guangdong','广州市','南沙区')['source_id'] is None
    previous=json.loads((BASE/'outbox/own-source-round23.json').read_text('utf8'))
    original=next(e for e in previous if e['type']=='MATERIAL_INFORMATION_MISSING')
    event=public.record_event({'id':digest([WINDOW_SOURCE,'own-window-partial-resolution',raw['captured_at']])[:32],
        'province':'guangdong','city':'广州市','district':'南沙区','region_code':'440115','service':'劳动人事争议仲裁申请',
        'type':'MATERIAL_INFORMATION_MISSING','url':WINDOW_SOURCE,'occurred_at':now(),
        'reason':'已沿本区官方材料页链接核对2026-06-02机构与收件窗口公告：10个镇街劳动争议收件窗口及该栏办公时间、区院联系电话分别保留。人事争议、派出庭及涉港澳涉外场所未混用；办理形式、网办、办结时限、收费与现场次数仍未核验。',
        'attempts':1,'final_status':'partially_resolved_own_window_source','screenshot':(BASE/'windows-round23/content.png').relative_to(ROOT).as_posix(),
        'remediation':'部分补全原事件'+original['id']+'，不删除旧记录；每字段保留本次自己的来源与时钟。新数据仅在独立候选191，不宣称已发布或已支持生成。'})
    save(BASE/'outbox/own-windows-round24.json',[event]);save(BASE/'guide.json',updated)
    print(json.dumps({'source':candidate['source_id'],'before_version':before['version'],'candidate_version':candidate['version'],'own_windows':10,'published':False,'event_id':event['id'],'delivery':event['delivery_status'],'models':0}))
if __name__=='__main__':main()
