"""Synthetic-only offline QA. Never reads reference samples or calls a model."""
import hashlib
import os
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct29e as adapter


def _configured_tool(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError('Set ' + name + ' to the required local executable before running QA')
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(name + ' must identify an existing executable')
    return path


def _configured_python():
    if _configured_tool('PARTLAWYER_QA_PYTHON') != Path(sys.executable).resolve():
        raise ValueError('Run this script with the interpreter configured in PARTLAWYER_QA_PYTHON')


def check_config():
    _configured_python()
    _configured_tool('PARTLAWYER_QA_POPPLER')
    print(json.dumps(dict(python_configured=True, poppler_configured=True)))


def originals():
    tasks = []
    for code in sorted(adapter.SUPPORTED):
        g = adapter.parse_capture(code)
        for kind, b in adapter.candidate_contract(g)['documents'].items():
            pdf = OUT / 'render' / f'{code}-original-{kind}' / 'document.pdf'
            pdf.parent.mkdir(parents=True, exist_ok=True)
            tasks.append(dict(source=b['source_file'], pdf=pdf.relative_to(ROOT).as_posix()))
    (OUT / 'original-render-tasks.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf8', newline='\n')


def generate():
    data = dict(applicantName='虚构验收甲', respondentName='虚构验收单位', birthDate='1991-05-09',
                gender='女', idNumber='000000199105090000', phone='00000000000',
                idAddress='虚构地址一号', registeredAddress='虚构单位二号',
                committeeName='虚构仲裁委员会', requests=['请求支付虚构工资100元。', '请求支付虚构加班工资200元。'],
                factsReason='仅为软件验收，全部事实与当事人均为虚构。虚构申请人在虚构单位从事虚构工作，双方存在虚构工资争议。',
                applicationDate='2026-10-29', submitDate='2026-10-29', copyCount=3, evidenceCopyCount=2,
                evidenceList=[dict(name='虚构劳动合同', source='虚构保存', purpose='证明虚构劳动关系', originalType='复印件', pageCount='3页'),
                              dict(name='虚构工资流水', source='虚构保存', purpose='证明虚构工资支付', originalType='原件', pageCount='2页')])
    data.update(otherDocumentType='虚构其他证件', otherDocumentNumber='虚构证件号',
                applicantMailingAddress='虚构通讯地址', acceptMediation='是', legalAid='否',
                respondentType='虚构单位类型', socialCreditCode='虚构信用代码',
                legalRepName='虚构负责人', legalRepPosition='虚构职务',
                departmentHead='虚构主管', departmentHeadPosition='虚构主管职务',
                mailingAddress='虚构单位通讯地址', companyContact='虚构联系人', companyContactPhone='00000000000',
                caseNumber='虚构验收案号')
    data['evidenceList'][0]['purpose'] = '虚构证据用途，仅供软件版式验收。' * 15
    data['evidenceList'].append(dict(source='虚构仅填写来源', purpose='虚构部分字段也须保留'))
    payloads = {kind: {k: v for k, v in data.items() if k in adapter.DATA_FIELDS[kind]} for kind in ['application', 'evidence']}
    tasks = []; outputs = []
    for code in sorted(adapter.SUPPORTED):
        g = adapter.with_capabilities(adapter.parse_capture(code))
        (OUT / f'guide-{code}.json').write_text(json.dumps(g, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
        for kind, b in adapter.candidate_contract(g)['documents'].items():
            path = OUT / 'generated' / f'{code}-{kind}.docx'; path.parent.mkdir(parents=True, exist_ok=True)
            adapter.fill_candidate_document(g, kind, payloads[kind]).save(path)
            with ZipFile(ROOT / b['source_file']) as a, ZipFile(path) as z:
                changed = [n for n in a.namelist() if a.read(n) != z.read(n)]
                assert a.namelist() == z.namelist() and changed == ['word/document.xml']
            pdf = OUT / 'render' / f'{code}-generated-{kind}' / 'document.pdf'
            pdf.parent.mkdir(parents=True, exist_ok=True)
            tasks.append(dict(source=path.relative_to(ROOT).as_posix(), pdf=pdf.relative_to(ROOT).as_posix()))
            outputs.append(dict(file=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                source=b, changed_package_parts=changed, synthetic_only=True))
    (OUT / 'synthetic-payload.json').write_text(json.dumps(payloads, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
    (OUT / 'generated.json').write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
    (OUT / 'generated-render-tasks.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf8', newline='\n')


def rasterize():
    # Bundled Poppler is used after the isolated Word read-only export fallback.
    poppler = _configured_tool('PARTLAWYER_QA_POPPLER')
    from pypdf import PdfReader
    result = []
    for pdf in sorted((OUT / 'render').glob('*/document.pdf')):
        subprocess.run([str(poppler), '-png', '-r', '110', str(pdf), str(pdf.parent / 'page')], check=True, capture_output=True)
        result.append(dict(pdf=pdf.relative_to(ROOT).as_posix(), pages=len(PdfReader(pdf).pages),
                           pngs=[p.relative_to(ROOT).as_posix() for p in sorted(pdf.parent.glob('page-*.png'))]))
    (OUT / 'render-inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
    print(json.dumps([dict(pdf=r['pdf'], pages=r['pages']) for r in result]))


if __name__ == '__main__':
    _configured_python()
    {'originals': originals, 'generate': generate, 'rasterize': rasterize, 'check-config': check_config}[sys.argv[1]]()
