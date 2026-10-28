"""Read-only own official original rendering; never invoke models or save source."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/nationwide-localization-20261023-night/cross-province/tianjin-eco-city/document-qa'


def main():
    if (OUT / 'original-render.json').exists():
        raise ValueError('Preserve existing original render evidence')
    spec = importlib.util.spec_from_file_location('own_read_only_renderer', ROOT / 'scripts/verify-regional-documents.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT
    files = [ROOT / 'templates/_docx/_regional/function-tianjin-eco-city' / n
             for n in ['110943177zze.doc', '081434099aia.docx']]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    tasks = module.render(files)
    for task in tasks:
        task['format'] = Path(task['source']).suffix[1:]
        task['render_handler'] = 'Read-only Word Documents.Open; DOC input is not converted to DOCX'
    assert before == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (OUT / 'original-render.json').write_text(json.dumps({'read_only': True, 'model_calls': 0,
        'original_sha256': before, 'tasks': tasks}, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'original_pages': [len(t['pages']) for t in tasks], 'manifest': str(OUT / 'original-render.json')}))


if __name__ == '__main__':
    main()
