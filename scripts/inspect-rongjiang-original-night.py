"""Render the retained binary DOC read-only; no conversion, authoring or model."""
import hashlib,importlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang'
OUT=BASE/'document-qa'
qa=importlib.import_module('verify-regional-documents');qa.OUT=OUT


def main():
    if (OUT/'original-render.json').exists():raise ValueError('Preserve completed original render')
    f=json.loads((BASE/'downloads-0425/original-file.json').read_text('utf8'))
    source=ROOT/f['file']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Own original changed')
    OUT.mkdir(exist_ok=True)
    tasks=qa.render([source])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==f['sha256']
    (OUT/'original-render.json').write_text(json.dumps({'source':f['file'],'sha256':f['sha256'],
        'original_format':'binary_DOC','tasks':tasks,'authoring':False,'model_calls':0,'original_unchanged':True,
        'packaged_docx_renderer':'not used for binary DOC; previous actual runtime probes show missing soffice.exe',
        'engine':'own hidden Word read-only ExportPDF plus bundled Poppler1600','visual_review':'pending'},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'original_pages':len(tasks[0]['pages']),'no_authoring':True}))


if __name__=='__main__':main()
