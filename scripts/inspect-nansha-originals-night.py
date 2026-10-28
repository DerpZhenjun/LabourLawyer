"""Read-only QA of independently downloaded public Nansha originals, no authoring."""
import hashlib,importlib,json,subprocess,sys
from pypdf import PdfReader
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha'
OUT=BASE/'document-qa'
def main():
    if (OUT/'original-render.json').exists():raise ValueError('Do not overwrite completed original render')
    OUT.mkdir(exist_ok=True)
    originals=json.loads((BASE/'downloads-round23/original-files.json').read_text('utf8'))
    originals=[x for x in originals if x['official_kind']=='original_document_unclassified']
    assert len(originals)==23 and all(x['download_status']=='downloaded' for x in originals)
    references=OUT/'references';references.mkdir(exist_ok=True)
    paths=[]
    for x in originals:
        data=(ROOT/x['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==x['sha256']
        target=references/(x['id']+'.'+x['file_type'])
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data)
        paths.append(target)
    if sys.argv[1:]==['--resume-render-de136e41b219']:
        saved=OUT/'render/de136e41b219/conversion-input.json'
        tasks=json.loads(saved.read_text('utf8'))
        assert len(tasks)==23
        for task,reference in zip(tasks,paths):
            assert Path(task['source']).resolve()==reference.resolve()
            pdf=Path(task['pdf']);assert pdf.is_file() and pdf.resolve().is_relative_to(saved.parent.resolve())
            task['pages']=[p.relative_to(ROOT).as_posix() for p in sorted(pdf.parent.glob('page-*.png'))]
            assert task['pages'];task['conversion']='office_export_to_pdf'
    else:
        renderer=importlib.import_module('inspect-baiyun-originals-night');renderer.OUT=OUT
        tasks=renderer.render_originals(paths)
    for task,original in zip(tasks,originals):
        task.update(own_original=original['file'],own_sha256=original['sha256'],own_source_url=original['source_url'],own_annex_id=original['id'],original_name=original['original_name'])
        assert hashlib.sha256((ROOT/original['file']).read_bytes()).hexdigest()==original['sha256']
        text=Path(task['pdf']).parent/'text.txt'
        pdf=PdfReader(task['pdf'])
        assert len(pdf.pages)==len(task['pages'])
        text.write_text('\n\f\n'.join(p.extract_text(extraction_mode='layout') for p in pdf.pages),encoding='utf8')
        task['extracted_text']=text.relative_to(ROOT).as_posix()
    (OUT/'original-render.json').write_text(json.dumps({'authoring':False,'models':0,'originals_unchanged':True,
        'engine':'previously verified missing packaged soffice; own hidden Word read-only PDF export + bundled Poppler',
        'tasks':tasks,'visual_review':'pending','published':False,'generation_enabled':False,
        'recovery':'Original read-only23 exports and42PNGs preserved; pdftotext.exe and fitz unavailable, bundled pypdf reads existingPDF; no rerender.' if sys.argv[1:] else None},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'originals':len(tasks),'pages':[len(t['pages']) for t in tasks],'authoring':False,'models':0}))
if __name__=='__main__':main()
