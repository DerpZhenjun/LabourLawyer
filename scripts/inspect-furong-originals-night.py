"""Read-only visual QA of four own guide originals; no document authoring."""
import hashlib, importlib, json, sys
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong'
OUT=BASE/'document-qa'

def main():
    if OUT.exists(): raise ValueError('Preserve existing original QA')
    OUT.mkdir()
    rows=json.loads((BASE/'downloads-round26/original-files.json').read_text('utf8'))
    docs=[r for r in rows if r['file_type']=='doc'];assert len(docs)==4
    paths=[ROOT/r['file'] for r in docs]
    for p,r in zip(paths,docs): assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    renderer=importlib.import_module('inspect-baiyun-originals-night');renderer.OUT=OUT
    tasks=renderer.render_originals(paths)
    for task,r in zip(tasks,docs):
        pdf=PdfReader(task['pdf']);assert len(pdf.pages)==len(task['pages'])
        target=Path(task['pdf']).with_name('text.txt')
        target.write_text('\n\f\n'.join(p.extract_text(extraction_mode='layout') for p in pdf.pages),encoding='utf8')
        task.update(own_original=r['file'],own_sha256=r['sha256'],own_source_url=r['source_url'],own_annex_id=r['id'],
                    original_name=r['original_name'],control_role=r['official_kind'],extracted_text=target.relative_to(ROOT).as_posix())
        assert hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['sha256']
    (OUT/'original-render.json').write_text(json.dumps({'authoring':False,'models':0,'originals_unchanged':True,
        'engine':'previously diagnosed missing packaged soffice; hidden Word read-only PDF export + bundled Poppler',
        'tasks':tasks,'visual_review':'pending','generation_enabled':False,'published':False},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'originals':len(tasks),'pages':[len(t['pages']) for t in tasks],'authoring':False,'models':0}))

if __name__=='__main__':main()
