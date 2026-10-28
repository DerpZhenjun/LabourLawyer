"""Stage only the own public source; no publishing or generation enablement."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_jiangxi import parse_rongjiang_capture
from regional_guides import RegionalStore,digest
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')


def main():
    if (BASE/'guide.json').exists():raise ValueError('Preserve own candidate evidence')
    read=lambda p:json.loads((BASE/p).read_text('utf-8-sig'))
    g=parse_rongjiang_capture(read('source-0425/dom.json'),read('downloads-0425/original-file.json'),read('identity-0430/identity.json'),read('document-qa/original-slots.json'))
    if len(read('document-qa/original-render.json')['tasks'][0]['pages'])!=2:raise ValueError('Own original rendering incomplete')
    if not (BASE/'document-qa/artifact.md').is_file():raise ValueError('Original/fidelity review missing')
    g['evidence']={'capture_file':(BASE/'source-0425/dom.json').relative_to(ROOT).as_posix(),
        'capture_sha256':hashlib.sha256((BASE/'source-0425/dom.json').read_bytes()).hexdigest(),
        'screenshot':(BASE/'source-0425/source.png').relative_to(ROOT).as_posix(),
        'own_identity':(BASE/'identity-0430/identity.json').relative_to(ROOT).as_posix(),
        'original_review':(BASE/'document-qa/artifact.md').relative_to(ROOT).as_posix()}
    save(BASE/'guide.json',g)
    stage=BASE/'staging-0440/staging.sqlite';stage.parent.mkdir(exist_ok=True)
    if stage.exists():raise ValueError('Preserve own staging DB')
    main_db=ROOT/'backend/data/regional-guides.sqlite'
    with sqlite3.connect(main_db.as_uri()+'?mode=ro',uri=True) as a,sqlite3.connect(stage) as b:a.backup(b)
    candidate=RegionalStore(stage).put_guide(g)
    save(BASE/'staging-0440/candidate.json',{'source_id':candidate['source_id'],'version':candidate['version'],
        'published':False,'materials':11,'official_originals':1,'original_pages_inspected':2,'adapters':0,
        'converted_reference':'PARTIAL: own second-page layout changed, NOT approved','candidate_browser':'NOT_RUN',
        'official_service_directory_code':'360798','official_administrative_code':None,'no_model_calls':True})
    store=RegionalStore(main_db);assert store.lookup('jiangxi','赣州市','蓉江新区')['source_id'] is None
    events=[]
    for typ,reason in [('ONLINE_CHANNEL_UNVERIFIED','自身2026官方文书公告提供地址电话，但没有明确办理形式或网上申请入口；不将窗口地址推断为仅线下。'),
        ('MATERIAL_INFORMATION_MISSING','自身公告不是完整办事指南；办理时间、收费、受理时限和到场次数未提供；网页十类证据仅1-2必需，其余按实际情形，不把示例页码当要求。')]:
        events.append(store.record_event({'id':digest([g['source_url'],typ,g['verified_at']])[:32],
            **{k:g[k] for k in ['province','city','district','region_code']},'service':g['service_name'],
            'type':typ,'url':g['source_url'],'occurred_at':g['verified_at'],'attempts':1,'final_status':'manual_review',
            'reason':reason,'screenshot':g['evidence']['screenshot'],
            'remediation':'继续核验本功能区自己的正式指南与渠道；原DOC空白和网页示例分开，不借用邻区资料。'}))
    save(BASE/'outbox/own-source-0440.json',events)
    print(json.dumps({'candidate_source_id':candidate['source_id'],'stage_version':candidate['version'],
        'published':False,'adapters':0,'events':2,'delivery':'PENDING_OPENCLAW'}))


if __name__=='__main__':main()
