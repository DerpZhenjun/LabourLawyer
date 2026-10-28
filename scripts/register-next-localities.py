"""Register independently captured candidates; never publish unaccepted guides."""
import hashlib,json,sys,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import digest,now
from regional_adapters import with_reference_capabilities
public_guide=runpy.run_path(str(ROOT/'scripts/export-public-data.py'))['public_guide']

def main():
    root=ROOT/'reports/nationwide-localization-20261028-next'
    previous=ROOT/'reports/nationwide-localization-20261028/CANDIDATES.json'
    rows=json.loads(previous.read_text('utf8'));indexed={tuple(c[k] for k in ['province','city','district']):c for c in rows}
    paths=[root/f'jiangsu/{code}/normalized-guide.json' for code in ['320922','320921']]
    paths += [root/f'zhejiang/staging-candidate/{code}-guide.json' for code in ['330108','330102']]
    sources=[];events=[]
    for path in paths:
        g=with_reference_capabilities(json.loads(path.read_text('utf8')))
        row={k:g[k] for k in ['province','city','district','region_code','source_id','source_url','authority','collected_at','verified_at']}
        row.update(published=False,can_generate=False,normalized_guide=path.relative_to(ROOT).as_posix(),
            normalized_guide_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            web_qa_status='NOT_RUN_POLICY_REFUSAL',document_visual_qa_status='NOT_RUN',
            offline_adapter_matches=[{'id':t['id'],'kind':t['document_types'],'sha256':t['sha256']} for t in g['templates'] if t.get('can_generate')])
        indexed[tuple(g[k] for k in ['province','city','district'])]=row
        sources.append(public_guide(g))
        kind='OFFICIAL_SOURCE_CONFLICT' if g['verification_status']=='conflict' else 'AUTH_REQUIRED' if g['channel'].get('online_status')=='auth_required' else 'ONLINE_CHANNEL_UNVERIFIED'
        event={k:g[k] for k in ['province','city','district','region_code']}
        event.update(id=digest([g['source_id'],kind,'next-own-capture'])[:32],type=kind,
            service=g['service_name'],keyword='劳动人事争议仲裁申请',url=g['source_url'],occurred_at=g['verified_at'],
            screenshot=None,attempts=1,final_status='pending_manual_verification',delivery_status='PENDING_OPENCLAW',
            reason='材料栏与办理流程存在冲突。' if kind=='OFFICIAL_SOURCE_CONFLICT' else '尚未核实登录后的实际网上提交能力。',
            remediation='保留自身来源；不登录、不代交、不推断其他地区规则。')
        events.append(event)
    def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    save(previous,list(indexed.values()))
    compact=[{k:c[k] for k in ['province','city','district','region_code','source_id','source_url','published','can_generate'] if k in c} for c in indexed.values()]
    save(ROOT/'config/regional_candidates.json',compact)
    save(root/'PUBLIC-SOURCES.json',sources)
    for e in events:save(root/'outbox'/(e['id']+'.json'),e)
    save(root/'RESUME-CHECKPOINT.json',{'updated_at':now(),'new_candidates':4,'total_candidates':len(indexed),
        'published_guides_unchanged':181,'generatable_localities_unchanged':166,'new_publication':False,
        'blocked_stage':'Candidate web acceptance launch rejected; no bypass attempted.',
        'next':'Run permitted candidate browser acceptance and document visual QA before publication.',
        'openclaw_delivery':'PENDING_OPENCLAW_NO_ACK','ollama_started':False})
    print(json.dumps({'new_candidates':4,'candidates':len(indexed),'published_guides':181},ensure_ascii=False))
if __name__=='__main__':main()
