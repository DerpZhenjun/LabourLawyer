"""Whole-byte proof before reusing layout evidence, never other locality rules."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-dongcheng'
def main():
    target=BASE/'document-qa/identical-original-render.json'
    if target.exists():raise ValueError('Preserve QA provenance')
    own=json.loads((BASE/'downloads-round28/original-files.json').read_text('utf8'))
    other=BASE.parent/'beijing-tongzhou';previous=json.loads((other/'downloads-0700/original-files.json').read_text('utf8'))
    rendered=json.loads((other/'document-qa/reference-render.json').read_text('utf8'))['tasks']
    docs=[r for r in own if r['file_type']=='docx'];old=[r for r in previous if r['file_type']=='docx'];records=[]
    assert len(docs)==3
    for item in docs:
        n=next(i for i,r in enumerate(old) if r['id']==item['id']);before=old[n]
        data=(ROOT/item['file']).read_bytes();assert data==(ROOT/before['file']).read_bytes()==Path(rendered[n]['source']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==before['sha256']==item['sha256']
        records.append({'own_source_url':item['source_url'],'own_annex_id':item['id'],'own_downloaded_file':item['file'],'own_original_sha256':item['sha256'],
            'rendered_input':rendered[n]['source'],'pages':[{'file':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in rendered[n]['pages']]})
    assert [len(r['pages']) for r in records]==[2,2,2]
    target.parent.mkdir();target.write_text(json.dumps({'records':records,'scope':'page rendering only after independently downloaded whole-byte identity; no source/rule inheritance',
        'classification':'three official samples, not blanks','authoring':False,'originals_unchanged':True,'models':0,'visual_review':'pending'},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'own_originals':3,'pages':6,'authoring':False,'models':0}))
if __name__=='__main__':main()
