"""Incremental independent public-only candidate history; never publish to main."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_adapters import with_reference_capabilities
from regional_guides import RegionalStore
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang'

def main():
    output=BASE/'staging-adapted-0455';output.mkdir(exist_ok=True)
    target=output/'staging.sqlite'
    if target.exists():raise ValueError('Preserve prior independent candidate')
    approval=json.loads((BASE/'document-qa/document-approval.json').read_text(encoding='utf8'))
    if approval['status']!='approved_for_own_offline_filling_only' or approval['output_pages']!=[2,3]:raise ValueError('Own visual QA incomplete')
    for item in approval['outputs']:
        if hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Approved output changed')
        if not all((ROOT/p).is_file() for p in item['pages']):raise ValueError('Reviewed images missing')
    main=ROOT/'backend/data/regional-guides.sqlite'
    with sqlite3.connect(main.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(target) as destination:source.backup(destination)
    store=RegionalStore(target);raw=json.loads((BASE/'guide.json').read_text(encoding='utf8'))
    previous=store.put_guide(raw)
    adapted=store.put_guide(with_reference_capabilities(raw))
    assert previous['source_id']==adapted['source_id']=='9324666463f34ff63056367a'
    assert previous['version']<adapted['version']
    assert adapted['templates'][0]['document_types']==['application','evidence']
    assert RegionalStore(main).lookup('jiangxi','赣州市','蓉江新区')['source_id'] is None
    result={'source_id':adapted['source_id'],'raw_version':previous['version'],'adapted_version':adapted['version'],
        'materials':11,'official_originals':1,'offline_filling_kinds':['application','evidence'],
        'original_download_unchanged':True,'filled_outputs_origin':'official-blank-converted-filled',
        'guide_status':'partial','online_status':'unverified','candidate_browser':'NOT_RUN',
        'published':False,'models':0}
    (output/'candidate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result))

if __name__=='__main__':main()
