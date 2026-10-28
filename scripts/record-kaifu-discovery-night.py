"""Trace real scoped search recovery and a generic target without inventing own data."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-kaifu'
DISC=ROOT/'reports/nationwide-localization-20261023-night/discovery-hunan-round27'
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'outbox/discovery-round27.json'
    if out.exists():raise ValueError('Preserve actual search events')
    short=json.loads((DISC/'kaifu-search-short/dom.json').read_text('utf8'))
    full=json.loads((DISC/'kaifu-search-full/dom.json').read_text('utf8'))
    recovered=json.loads((DISC/'kaifu-all-topics/dom.json').read_text('utf8'))
    target=json.loads((BASE/'observed-generic-target-round27/dom.json').read_text('utf8'))
    assert '0 项' in short['text'] and '暂无数据' in short['text'] and '暂无数据' in full['text']
    assert '1 项' in recovered['text'] and '劳动人事争议仲裁申请' in recovered['text']
    assert '人力资源社会保障部门' in target['text'] and '开福区' not in target['text'] and 'approve_id' not in target['url']
    with sqlite3.connect((ROOT/'backend/data/regional-directory.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute('SELECT payload FROM directory_areas WHERE id=?',('national:430105',)).fetchall()
    assert len(rows)==1;identity=json.loads(rows[0][0]);assert identity['city']=='长沙市' and identity['district']=='开福区'
    save(BASE/'directory-identity.json',identity)
    store=RegionalStore(ROOT/'backend/data/regional-guides.sqlite');assert store.lookup('hunan','长沙市','开福区')['source_id'] is None
    events=[]
    observations=[
        ('SEARCH_NO_RESULT',short['url'],'劳动仲裁 → 劳动人事争议仲裁',2,'resolved_scoped_topic_filter',DISC/'kaifu-search-short/page.png',
         '开福区官网原生入口进入法人服务人力资源主题。劳动仲裁和劳动人事争议仲裁两次筛选均0项/暂无数据；切换全部主题后完整关键词找到1项。不是开福区没有仲裁服务，也不是仅换同义词即恢复。',
         '记录主题过滤与关键词的共同影响，保存原0项和恢复1项DOM/截图，不把主题内零结果当地区服务不存在。'),
        ('REGION_SELECTION_FAILURE',target['url'],'劳动人事争议仲裁',1,'pending_exact_own_guide_identity',BASE/'observed-generic-target-round27/content.png',
         '实际选择湖南省→长沙市→开福区并前往本区门户，areacode430105999000结果点击办事指南后到不含approve_id的通用事项页，办理部门仅人力资源社会保障部门，无本区机关/地址/电话。该次目标未确认具体办理地区；未标为开福区自己的正式指南。',
         '保留实际结果与跳转，不借芙蓉approve_id或材料；继续查本区正式实施机关目录。初次等待自身身份25秒超时后doctor7PASS，再按实际观察URL捕获通用正文。'),
        ('ONLINE_CHANNEL_UNVERIFIED',target['url'],'劳动人事争议仲裁',1,'pending_exact_own_channel',DISC/'kaifu-all-topics/page.png',
         '开福区筛选结果行标全程网办，但其指南跳转缺少本区实施身份；本次未点击该通用目标的在线办理，不把通用页或芙蓉认证结果当开福区网办核验。',
         '保持本区online unverified和无自身入口，等待自己的机关/材料/形式/网办链接核验；不宣称不支持网上办理。')]
    for kind,url,keyword,attempts,state,screen,reason,remediation in observations:
        assert screen.is_file()
        events.append(store.record_event({'id':digest([url,kind,'kaifu-discovery-round27'])[:32],
            'province':'hunan','city':'长沙市','district':'开福区','region_code':'430105','service':'劳动人事争议仲裁申请',
            'type':kind,'url':url,'keyword':keyword,'occurred_at':now(),'attempts':attempts,'final_status':state,
            'screenshot':screen.relative_to(ROOT).as_posix(),'reason':reason,'remediation':remediation}))
    save(out,events)
    sources=[DISC/'go-kaifu/dom.json',DISC/'kaifu-search-short/dom.json',DISC/'kaifu-search-full/dom.json',DISC/'kaifu-all-topics/dom.json',BASE/'formal-round27/tabs.json',BASE/'observed-generic-target-round27/dom.json']
    save(BASE/'DISCOVERY-STATUS.json',{'at':now(),'province':'hunan','city':'长沙市','district':'开福区','region_code':'430105',
        'state':'actual_search_recovered_but_target_generic_not_own_guide','candidate':False,'published':False,'can_generate':False,'own_templates':0,
        'evidence':[{ 'file':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],
        'public_events':[e['id'] for e in events],'source_identity_confirmed':False,'online_status':'unverified','models':0})
    print(json.dumps({'own_guide':False,'candidate':False,'events':[e['id'] for e in events],'delivery':'PENDING_OPENCLAW','models':0}))
if __name__=='__main__':main()
