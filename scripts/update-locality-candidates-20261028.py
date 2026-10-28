"""Increment candidate evidence and public issue outbox, without publication."""
import hashlib,json,sqlite3,sys,uuid
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest,now
from regional_adapters import with_reference_capabilities
OUT=ROOT/'reports/nationwide-localization-20261028'
def read(p):return json.loads(p.read_text('utf8'))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def run():
    rows=read(OUT/'CANDIDATES.json');indexed={(r['province'],r['city'],r['district']):r for r in rows}
    inputs=[OUT/f'jiangsu/{c}/normalized-guide.json' for c in ['320903','320902','320981','320924']]
    inputs += [OUT/f'zhejiang/staging-candidate/{c}-guide.json' for c in ['330110','330106']]
    inputs += [OUT/f'anhui/{n}/normalized-guide.json' for n in ['shushan','baohe']]
    store=RegionalStore(OUT/'acceptance/regional-guides.sqlite');sources=[];events=[]
    for path in inputs:
        g=with_reference_capabilities(read(path));own=store.put_guide(g)
        key=tuple(own[k] for k in ['province','city','district']);r=indexed.get(key,{})
        r.update({k:own[k] for k in ['province','city','district','region_code','source_id','source_url','authority','collected_at','verified_at']})
        r.update(normalized_guide=path.relative_to(ROOT).as_posix(),normalized_guide_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 published=False,can_generate=False,web_qa_status='NOT_RUN_POLICY_REFUSAL',
                 candidate_guide=f"reports/nationwide-localization-20261028/acceptance/guides/{own['source_id']}.json")
        r['offline_adapter_matches']=[{'id':t['id'],'kind':t['document_types'],'sha256':t['sha256']} for t in own['templates'] if t.get('can_generate')]
        if own['region_code'] in ['320903','320902']:r['document_visual_qa_status']='PASS_SIX_GENERATED_PAGES_REVIEWED'
        else:r['document_visual_qa_status']='NOT_RUN'
        indexed[key]=r;save(ROOT/r['candidate_guide'],own)
        files=[]
        for t in own['templates']:
            if t.get('download_status')!='downloaded':continue
            source=ROOT/t['file'];checksum=hashlib.sha256(source.read_bytes()).hexdigest();assert checksum==t['sha256']
            files.append({k:t.get(k) for k in ['id','official_kind','classification','download_url','original_name','file','sha256']})
        sources.append({**{k:own[k] for k in ['province','city','district','region_code','source_id','source_url','collected_at','verified_at']},
                        'normalized_guide':path.relative_to(ROOT).as_posix(),'files':files,'published':False})
        state=own['channel']['online_status'];kind='AUTH_REQUIRED' if state=='auth_required' else 'ONLINE_CHANNEL_UNVERIFIED'
        reason=('实际打开本区官方网上办理进入登录边界；登录后提交功能未核验，未登录或提交。' if state=='auth_required' else '本区官方指南已采集，但尚无可核验的对应网上提交入口，不据此断言不支持网办。')
        event={k:own[k] for k in ['province','city','district','region_code']}
        event.update(id=digest([own['source_id'],kind,'20261028-own-capture'])[:32],type=kind,service=own['service_name'],
                     url=own['source_url'],keyword='劳动人事争议仲裁申请',occurred_at=own['verified_at'],screenshot=None,
                     reason=reason,attempts=1,final_status='pending_manual_verification',
                     remediation='保留本区来源和认证边界；不继承其他地区渠道，不登录、不代交申请。',delivery_status='PENDING_OPENCLAW')
        events.append(event);save(OUT/'outbox'/(event['id']+'.json'),event)
    save(OUT/'CANDIDATES.json',list(indexed.values()));save(OUT/'SOURCE-INVENTORY.json',sources);save(OUT/'COLLECTION-ISSUES.json',events)
    # Only public event rows are written; no guide publication or user data access.
    source=ROOT/'backend/data/regional-guides.sqlite';backup=OUT/'outbox'/('before-events-'+uuid.uuid4().hex[:12]+'.sqlite')
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(backup)) as dst:src.backup(dst)
    public=RegionalStore(source)
    for e in events:public.record_event(e)
    save(OUT/'OUTBOX-STATUS.json',{'checked_at':now(),'openclaw_cli':'OpenClaw 2026.9.4 (3a9d69d)',
        'gateway_listening':False,'gateway_port_checked':18789,'external_sync':'NOT_ATTEMPTED_NO_CONFIRMED_GATEWAY_NO_MODEL_CALLS',
        'new_public_events':len(events),'receipt':None,'status':'PENDING_OPENCLAW','backup':backup.relative_to(ROOT).as_posix()})
    print(json.dumps({'candidates':len(indexed),'own_new_sources':len(sources),'own_originals':sum(len(x['files']) for x in sources),
                      'staged_guides':len(store.inventory()),'published_guides':len(public.inventory()),'events':len(events)},ensure_ascii=False))
if __name__=='__main__':run()
