"""Reuse render evidence only after whole-file identity, never locality rules."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-chaoyang'
OTHER=BASE.parent/'beijing-tongzhou'
def main():
    target=BASE/'document-qa/identical-original-render.json'
    if target.exists():raise ValueError('Preserve source review evidence')
    own=json.loads((BASE/'downloads-round23/original-files.json').read_text('utf8'))
    previous=json.loads((OTHER/'downloads-0700/original-files.json').read_text('utf8'))
    previous=[f for f in previous if f['file_type']=='docx']
    rendered=json.loads((OTHER/'document-qa/reference-render.json').read_text('utf8'))['tasks']
    records=[]
    for item in own:
        if item['file_type']!='docx':continue
        n=next(i for i,f in enumerate(previous) if f['id']==item['id']);old=previous[n]
        data=(ROOT/item['file']).read_bytes();assert data==(ROOT/old['file']).read_bytes()==Path(rendered[n]['source']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['sha256']==old['sha256']
        pages=[{'file':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in rendered[n]['pages']]
        records.append({'own_source_url':item['source_url'],'own_annex_id':item['id'],'own_downloaded_file':item['file'],
            'own_original_sha256':item['sha256'],'previous_render_source':rendered[n]['source'],'pages':pages,
            'basis':'own independently downloaded whole-file bytes exactly match rendered input; page evidence reused, not rules'})
    assert len(records)==3 and [len(r['pages']) for r in records]==[2,2,2]
    target.parent.mkdir(parents=True);target.write_text(json.dumps({'records':records,'classification':'three_official_samples_not_blank',
        'authoring':False,'originals_unchanged':True,'no_model_upload':True},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'own_originals':3,'byte_identical_page_evidence':6,'authoring':False}))
if __name__=='__main__':main()
