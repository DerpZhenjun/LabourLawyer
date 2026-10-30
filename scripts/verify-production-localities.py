"""Offline own-source recheck and Chunan QA fixtures; no DB, server or model calls."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_zhejiang_chunan_oct30 as chunan

OUT = ROOT / 'reports/production-readiness-20261030/localities'


def run():
    g = chunan.parse_capture(root=ROOT)
    out = OUT / 'chunan/fixtures'; out.mkdir(parents=True, exist_ok=True)
    data = {
        'application': {'committeeName': '淳安县劳动人事争议仲裁委员会', 'applicantName': '虚构测试劳动者',
                        'gender': '女', 'birthDate': '1990-01-01', 'phone': '虚构联系电话',
                        'respondentName': '虚构测试有限公司', 'registeredAddress': '虚构注册地址',
                        'requests': ['本文件仅供填写版式测试，不用于真实申请。'],
                        'factsReason': '全部姓名、单位、地址和事实均为虚构。' + '测试原表字段、长文字换行及手签留空。' * 24},
        'evidence': {'caseNumber': '虚构测试案号', 'submitDate': '2026-10-30',
                     'evidenceList': [{'name': '虚构测试劳动合同', 'pageCount': '2', 'source': '虚构测试来源',
                                      'purpose': '仅用于版式测试，不代表真实证据。' * 6},
                                     {'name': '虚构测试工资记录', 'pageCount': '', 'source': '', 'purpose': ''}]},
    }
    checks = []
    for kind, payload in data.items():
        template = next(t for t in g['templates'] if t['material_id'] == chunan.BLANKS[kind]['material'])
        original = (ROOT / template['file']).read_bytes()
        path = out / (kind + '-synthetic.docx')
        chunan.fill_offline_document(g, template, kind, payload, root=ROOT).save(path)
        with ZipFile(BytesIO(original)) as a, ZipFile(path) as b:
            assert set(a.namelist()) == set(b.namelist())
            assert all(a.read(n) == b.read(n) for n in a.namelist() if n != 'word/document.xml')
        assert original == (ROOT / template['file']).read_bytes()
        checks.append({'kind': kind, 'source_file': template['file'], 'source_sha256': template['sha256'],
                       'output_file': path.relative_to(ROOT).as_posix(), 'output_sha256': sha256(path.read_bytes()).hexdigest(),
                       'package_parts_except_document_xml': 'PASS', 'original_unchanged': True})
    result = {'scope': 'Chunan own-source offline adapter only', 'region_code': g['region_code'],
              'source_id': g['source_id'], 'service_code': g['service_code'], 'source_url': g['source_url'],
              'source_manifest_sha256': chunan.MANIFEST_SHA256, 'public_whitelist_sha256': chunan.WHITELIST_SHA256,
              'source_records_verified': 30, 'guide_can_generate': g['can_generate'], 'published': False,
              'models_called': False, 'database_changed': False, 'checks': checks,
              'remaining_gates': ['separate Word all-page visual review', 'candidate API/registry integration',
                                  'native candidate browser generation/download QA', 'publication approval evidence']}
    (OUT / 'chunan/OFFLINE-VERIFICATION.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    (out / 'synthetic-inputs.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'own_records': 30, 'fixtures': len(checks), 'production_generation_enabled': False}))


if __name__ == '__main__':
    run()
