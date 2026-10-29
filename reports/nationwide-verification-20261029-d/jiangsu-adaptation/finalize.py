"""Seal D-only public adaptation QA. Original source bundle is read-only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')


def pin(path):
    raw = path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


if sys.argv[1:] == ['--verify']:
    white = json.loads((OUT / 'PUBLIC-WHITELIST.json').read_text(encoding='utf8'))
    for relative, expected in white['files'].items():
        p = (ROOT / relative).resolve()
        assert p.is_relative_to(ROOT) and pin(p) == expected, relative
    print(json.dumps(dict(public_files_sha_passed=len(white['files']), read_only=True)))
    raise SystemExit(0)
if sys.argv[1:]: raise SystemExit('Only --verify or pre-freeze build is supported')

source = ROOT / 'reports/nationwide-verification-20261029-d/jiangsu/finalize.py'
check = subprocess.run([sys.executable, str(source), '--verify'], check=True, capture_output=True, text=True)
write('source-verification.json', json.loads(check.stdout))
summaries = []
for phase in ['original', 'generated']:
    raw = json.loads((OUT / f'word-{phase}-instance-isolation.json').read_text(encoding='utf-8-sig'))
    summaries.append(dict(phase=phase, completed=raw['completed'], new_instance_verified=raw['new_pid_verified'],
                         all_document_windows_verified=all(v['matches_new_instance'] for v in raw['document_window_pid_checks']),
                         macros_disabled=raw['macro_security'] == 3, link_updates_disabled=raw['link_updates_disabled'],
                         original_instances_preserved=raw['original_pids_still_alive'],
                         quit_only_distinct_own_instance=raw['quit_called_only_on_distinct_new_object']))
assert all(r['completed'] == 4 and all(v is True for k, v in r.items() if isinstance(v, bool)) for r in summaries)
write('word-isolation-public.json', summaries)
inventory = json.loads((OUT / 'render-inventory.json').read_text(encoding='utf8'))
assert sum(r['pages'] for r in inventory) == 20
write('VISUAL-APPROVAL.json', dict(status='PASS', original_pages=14, synthetic_output_pages=6,
    inspected='All 20 pages opened individually via view_image',
    checks=['Original layout retained', '1991-05-09 complete', 'Application copies 3 and evidence copies 2 independent',
            'Signatures and receiver fields blank', 'Actual date slots filled', 'Six evidence columns intact',
            'No overlap or clipping in synthetic outputs', 'Only word/document.xml changed'],
    source_manifest_sha256='3b151169273cde16c4005035820301024a050897e7ebc5e6fb62f469f1a29ae3',
    source_whitelist_sha256='9280f4355e54f1ca500201c65ed306a0f48cf09beb6d21df7e9c9660a9314305',
    generation_adapter='jiangsu_own_blank_oct29d_v1', candidate_web_qa='NOT_RUN', published=False,
    outputs=json.loads((OUT / 'generated.json').read_text(encoding='utf8')), pages=inventory))

names = ['FINAL-REPORT.md', 'artifact.md', 'inspect_sources.py', 'qa.py', 'finalize.py', 'render-isolated.ps1',
         'source-package-audit.json', 'tests-RED.txt', 'public-proof-RED.txt', 'public-proof-missing-evidence-RED.txt', 'tests-GREEN.txt',
         'packaged-render-attempt.log', 'word-isolation-public.json', 'VISUAL-APPROVAL.json', 'source-verification.json',
         'guide-320508.json', 'guide-320506.json', 'synthetic-payload.json', 'generated.json',
         'original-render-tasks.json', 'generated-render-tasks.json', 'render-inventory.json']
files = [OUT / name for name in names]
files.extend(ROOT / 'backend' / name for name in ['regional_jiangsu_oct29d.py', 'tests/test_jiangsu_oct29d.py'])
files.extend(OUT / 'generated' / f'{code}-{kind}.docx' for code in ['320506', '320508'] for kind in ['application', 'evidence'])
for r in inventory:
    files.append(ROOT / r['pdf'])
    files.extend(ROOT / p for p in r['pngs'])
for p in files:
    if p.suffix in {'.py', '.ps1', '.md'}:
        assert b'\r\n' not in p.read_bytes(), 'New product code must be LF: ' + str(p)
write('PUBLIC-WHITELIST.json', dict(scope='Exact own D provider/test and synthetic-only QA. No reference samples, SSO or process identifiers.',
    files={p.relative_to(ROOT).as_posix(): pin(p) for p in files}))
print(json.dumps(dict(public_files=len(files), source_manifest_sha256='3b151169273cde16c4005035820301024a050897e7ebc5e6fb62f469f1a29ae3',
                     module=pin(ROOT / 'backend/regional_jiangsu_oct29d.py'), tests=pin(ROOT / 'backend/tests/test_jiangsu_oct29d.py'))))
