"""Seal synthetic/public adaptation QA only. Never rewrites sealed source evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


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
    source_manifest_sha256='1b5bf8201e0dbe260fbcfa2fab4e4b9ac4abfdacdd829727ed1de93b0053f634',
    generation_adapter='jiangsu_own_blank_oct29c_v1', candidate_web_qa='NOT_RUN', published=False,
    outputs=json.loads((OUT / 'generated.json').read_text(encoding='utf8')), pages=inventory))

# Exact known file names; raw process diagnostics and reference samples are excluded.
names = ['FINAL-REPORT.md', 'artifact.md', 'inspect_sources.py', 'qa.py', 'finalize.py', 'render-isolated.ps1',
         'source-package-audit.json', 'style-summary.json', 'tests-RED.txt', 'partial-field-RED.txt', 'tests-GREEN.txt',
         'PROVENANCE-REPORT.md', 'provenance-RED.txt', 'provenance-GREEN.txt',
         'packaged-render-attempt.log', 'word-isolation-public.json', 'VISUAL-APPROVAL.json',
         'guide-320411.json', 'guide-320412.json', 'synthetic-payload.json', 'generated.json',
         'original-render-tasks.json', 'generated-render-tasks.json', 'render-inventory.json']
files = [OUT / name for name in names]
files.extend(ROOT / 'backend' / name for name in ['regional_jiangsu_oct29c.py', 'tests/test_jiangsu_oct29c.py'])
files.extend(ROOT / 'backend' / name for name in ['regional_oct29c_public_provenance.py',
             'tests/test_oct29c_public_provenance.py', 'regional_public_provenance.py'])
files.extend(OUT / 'generated' / f'{code}-{kind}.docx' for code in ['320411', '320412'] for kind in ['application', 'evidence'])
for r in inventory:
    files.append(ROOT / r['pdf'])
    files.extend(ROOT / p for p in r['pngs'])
write('PUBLIC-WHITELIST.json', dict(scope='Exact own-source provider/test and synthetic-only QA. No reference samples, SSO or process identifiers.',
    files={p.relative_to(ROOT).as_posix(): dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}))
print(f'{len(files)} exact public files; raw process diagnostics excluded')
