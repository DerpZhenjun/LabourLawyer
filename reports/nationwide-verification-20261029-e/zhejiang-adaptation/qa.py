"""Synthetic-only offline package QA; never changes frozen source files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
import regional_zhejiang_oct29e as provider


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def generate():
    tasks = []
    records = []
    app = dict(applicantName='虚构验收劳动者', birthDate='1990-01-02', gender='女', nationality='汉族',
               idNumber='000000199001020000', phone='00000000000', householdType='本省非农业户口',
               idAddress='虚构住所一号', respondentName='虚构星禾有限公司', socialCreditCode='000000000000000000',
               registeredAddress='虚构单位注册地址二号', mailingAddress='虚构单位通讯地址三号', workAddress='虚构履行地四号',
               legalRepName='虚构负责人', legalRepPhone='00000000000', legalRepPosition='虚构经理',
               companyContact='虚构联系人', companyContactPhone='00000000000', committeeName='虚构验收仲裁委员会',
               requests=['请求支付虚构工资1000元。', '请求支付虚构加班工资200元。'],
               factsReason='本申请全部为软件验收虚构内容。虚构验收劳动者于2025年3月1日进入虚构星禾有限公司从事虚构文员工作，约定每月工资3000元。虚构单位尚未支付虚构工资，双方协商未果。以上当事人、地址、金额与事件全部为虚构，不能直接用于提交。',
               applicationDate='2026-10-29', copyCount=3)
    evidence = dict(committeeName='虚构验收仲裁委员会', caseNumber='虚构案号2026号', copyCount=3, submitDate='2026-10-29',
                    evidenceList=[dict(name='虚构劳动合同', pageCount='2页', source='虚构申请人保存', purpose='说明虚构劳动关系及约定工资。'),
                                  dict(name='虚构工资记录', pageCount='3', source='虚构单位提供', purpose='说明虚构工资支付情况。')])
    save(OUT / 'synthetic-payload.json', {'application': app, 'evidence': evidence})
    for name in ['fuyang', 'jiande']:
        guide = provider.with_capabilities(provider.parse_capture(name))
        save(OUT / ('guide-' + guide['region_code'] + '.json'), guide)
        for template in guide['templates']:
            if not template.get('can_generate'):
                continue
            kind = template['document_types'][0]
            original = ROOT / template['file']
            generated = OUT / 'generated' / (guide['region_code'] + '-' + kind + '.docx')
            generated.parent.mkdir(parents=True, exist_ok=True)
            data = app if kind == 'application' else evidence
            provider.fill_document(guide, template, kind, original, data).save(generated)
            with ZipFile(original) as before, ZipFile(generated) as after:
                assert before.namelist() == after.namelist()
                changed = [n for n in before.namelist() if before.read(n) != after.read(n)]
                assert changed == ['word/document.xml']
                assert after.testzip() is None
            records.append(dict(region_code=guide['region_code'], kind=kind, source_id=guide['source_id'],
                                source_file=template['file'], source_sha256=template['sha256'],
                                file=generated.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(generated.read_bytes()).hexdigest(),
                                changed_package_parts=changed, synthetic_only=True, visual_qa='NOT_RUN'))
            for stage, file in [('original', original), ('generated', generated)]:
                folder = OUT / 'render' / f'{guide["region_code"]}-{stage}-{kind}'
                folder.mkdir(parents=True, exist_ok=True)
                tasks.append({'source': file.resolve().relative_to(ROOT).as_posix(),
                              'pdf': (folder / 'document.pdf').resolve().relative_to(ROOT).as_posix()})
    save(OUT / 'generated.json', records)
    save(OUT / 'word-render-tasks.json', tasks)
    print('Generated four own-bound synthetic copies; only word/document.xml changed.')


def rasterize():
    configured = os.environ.get('ZJE_PDFTOPPM')
    if not configured or not Path(configured).is_file():
        raise ValueError('Set ZJE_PDFTOPPM to the existing PDF rasterizer executable.')
    binary = Path(configured).resolve()
    from pypdf import PdfReader
    rows = []
    inventory = OUT / 'render-inventory.json'
    previous = {row['pdf']: row.get('sha256') for row in json.loads(inventory.read_text('utf8'))} if inventory.exists() else {}
    for pdf in sorted((OUT / 'render').glob('*/document.pdf')):
        checksum = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if previous.get(pdf.relative_to(ROOT).as_posix()) != checksum:
            subprocess.run([str(binary), '-png', '-r', '110', str(pdf), str(pdf.parent / 'page')], check=True, capture_output=True)
        rows.append({'pdf': pdf.relative_to(ROOT).as_posix(), 'sha256': checksum, 'pages': len(PdfReader(pdf).pages),
                     'pngs': [p.relative_to(ROOT).as_posix() for p in sorted(pdf.parent.glob('page-*.png'))]})
    save(OUT / 'render-inventory.json', rows)
    print(json.dumps([{'pdf': row['pdf'], 'pages': row['pages']} for row in rows]))


if __name__ == '__main__':
    configured = os.environ.get('ZJE_PYTHON')
    if not configured or Path(configured).resolve() != Path(sys.executable).resolve():
        raise ValueError('Set ZJE_PYTHON to the existing dependency-equipped Python and invoke that executable.')
    {'generate': generate, 'rasterize': rasterize}[sys.argv[1]]()
