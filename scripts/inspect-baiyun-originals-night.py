"""Read-only original rendering and inventory; never author/convert a Word source."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-baiyun'
OUT=BASE/'document-qa'
SKILL=Path('C:/Users/DerpZhenjun/.codex/plugins/cache/openai-primary-runtime/documents/26.1017.11052/skills/documents')
qa=importlib.import_module('verify-regional-documents')
qa.OUT=OUT


def render_originals(paths):
    probe=subprocess.run(['powershell.exe','-NoProfile','-Command','@(Get-Process WINWORD -ErrorAction SilentlyContinue).Count'],capture_output=True,text=True)
    if probe.stdout.strip()!='0':raise RuntimeError('Leave an existing Word session untouched')
    spec=importlib.util.spec_from_file_location('baiyun_read_only_renderer',ROOT/'scripts/validate_acquired_templates.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUTPUT_ROOT=OUT/'render'/uuid.uuid4().hex[:12]
    # Numbered names recur in separate official packages. Never let PDF output
    # destinations collide, even when the original basename is the same.
    tasks=[{'source':str(p),'format':'docx','province_folder':f'{i:02}-{p.parent.name}'} for i,p in enumerate(paths,1)]
    module.convert_office_files(tasks)
    for task in tasks:
        if task.get('conversion')=='failed':raise RuntimeError('Read-only export failed')
        pdf=Path(task['pdf'])
        subprocess.run([str(module.PDFTOPPM),'-scale-to','1600','-png',str(pdf),str(pdf.parent/'page')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        task['pages']=[p.relative_to(ROOT).as_posix() for p in sorted(pdf.parent.glob('page-*.png'))]
    assert len({t['pdf'] for t in tasks})==len(tasks)
    return tasks


def main():
    if (OUT/'original-render.json').exists():raise ValueError('Preserve original inspection')
    OUT.mkdir(exist_ok=True)
    packages=json.loads((BASE/'downloads-0410/original-files.json').read_text('utf8'))
    originals=[m for p in packages for m in p['members']]
    paths=[ROOT/m['file'] for m in originals]
    for p,m in zip(paths,originals):assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
    probe=subprocess.run([sys.executable,str(SKILL/'render_docx.py'),str(paths[3]),'--output_dir',str(OUT/'packaged-probe'),'--emit_pdf','--verbose'],capture_output=True,text=True,encoding='utf8',errors='replace')
    (OUT/'packaged-renderer.log').write_text(probe.stdout+'\n'+probe.stderr,encoding='utf8')
    if probe.returncode!=0:
        if 'soffice' not in probe.stderr+probe.stdout:raise RuntimeError('Unexpected packaged renderer error')
    tasks=render_originals(paths)
    assert len(tasks)==8
    for p,m in zip(paths,originals):assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
    (OUT/'original-render.json').write_text(json.dumps({'packaged_renderer_exit':probe.returncode,'authoring':False,'models':0,
        'engine':'own hidden Word read-only ExportPDF + bundled Poppler',
        'originals_unchanged':True,'tasks':tasks,'visual_review':'pending',
        'superseded_attempt':'render/7cd712a261a5 failed to save manifest and reused colliding basenames; NOT accepted'},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'originals':8,'pages':[len(t['pages']) for t in tasks],'authoring':False}))


if __name__=='__main__':main()
