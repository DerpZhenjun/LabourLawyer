"""Synthetic-only offline QA. Never reads reference samples or calls a model."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct29c as adapter


def originals():
    tasks = []
    for code in sorted(adapter.SUPPORTED):
        g = adapter.parse_capture(code)
        for kind, b in adapter.candidate_contract(g)['documents'].items():
            pdf = OUT / 'render' / f'{code}-original-{kind}' / 'document.pdf'
            pdf.parent.mkdir(parents=True, exist_ok=True)
            tasks.append(dict(source=str((ROOT / b['source_file']).resolve()), pdf=str(pdf)))
    (OUT / 'original-render-tasks.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf8')


def generate():
    data = dict(applicantName='虚构验收甲', respondentName='虚构验收单位', birthDate='1991-05-09',
                gender='女', idNumber='000000199105090000', phone='00000000000',
                idAddress='虚构地址一号', registeredAddress='虚构单位二号',
                committeeName='虚构仲裁委员会', requests=['请求支付虚构工资100元。', '请求支付虚构加班工资200元。'],
                factsReason='仅为软件验收，全部事实与当事人均为虚构。虚构申请人在虚构单位从事虚构工作，双方存在虚构工资争议。',
                applicationDate='2026-10-29', submitDate='2026-10-29', copyCount=3, evidenceCopyCount=2,
                evidenceList=[dict(name='虚构劳动合同', source='虚构保存', purpose='证明虚构劳动关系', originalType='复印件', pageCount='3页'),
                              dict(name='虚构工资流水', source='虚构保存', purpose='证明虚构工资支付', originalType='原件', pageCount='2页')])
    tasks = []; outputs = []
    for code in sorted(adapter.SUPPORTED):
        g = adapter.with_capabilities(adapter.parse_capture(code))
        (OUT / f'guide-{code}.json').write_text(json.dumps(g, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        for kind, b in adapter.candidate_contract(g)['documents'].items():
            path = OUT / 'generated' / f'{code}-{kind}.docx'; path.parent.mkdir(parents=True, exist_ok=True)
            adapter.fill_candidate_document(g, kind, data).save(path)
            with ZipFile(ROOT / b['source_file']) as a, ZipFile(path) as z:
                changed = [n for n in a.namelist() if a.read(n) != z.read(n)]
                assert a.namelist() == z.namelist() and changed == ['word/document.xml']
            pdf = OUT / 'render' / f'{code}-generated-{kind}' / 'document.pdf'
            pdf.parent.mkdir(parents=True, exist_ok=True)
            tasks.append(dict(source=str(path), pdf=str(pdf)))
            outputs.append(dict(file=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                source=b, changed_package_parts=changed, synthetic_only=True))
    (OUT / 'synthetic-payload.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (OUT / 'generated.json').write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (OUT / 'generated-render-tasks.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf8')


def rasterize():
    # Bundled Poppler is used after the isolated Word read-only export fallback.
    runtime = Path('C:/Users/DerpZhenjun/.cache/codex-runtimes/codex-primary-runtime/dependencies')
    poppler = next(runtime.rglob('pdftoppm.exe'))
    from pypdf import PdfReader
    result = []
    for pdf in sorted((OUT / 'render').glob('*/document.pdf')):
        subprocess.run([str(poppler), '-png', '-r', '110', str(pdf), str(pdf.parent / 'page')], check=True, capture_output=True)
        result.append(dict(pdf=str(pdf.relative_to(ROOT)), pages=len(PdfReader(pdf).pages),
                           pngs=[str(p.relative_to(ROOT)) for p in sorted(pdf.parent.glob('page-*.png'))]))
    (OUT / 'render-inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps([dict(pdf=r['pdf'], pages=r['pages']) for r in result]))


if __name__ == '__main__':
    {'originals': originals, 'generate': generate, 'rasterize': rasterize}[sys.argv[1]]()
