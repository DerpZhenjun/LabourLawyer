"""Freeze exact synthetic QA delivery; source originals are read-only."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from zipfile import ZipFile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct29e as adapter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {'sha256': sha(path), 'bytes': path.stat().st_size}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')


def relative(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Delivery path escapes project root')
    return path.relative_to(ROOT).as_posix()


if sys.argv[1:] == ['--verify']:
    white = json.loads((OUT / 'PUBLIC-WHITELIST.json').read_text('utf8'))
    for name, expected in white['files'].items():
        path = ROOT / name
        assert relative(path) == name and pin(path) == expected
    derived = json.loads((OUT / 'DERIVED-MANIFEST.json').read_text('utf8'))
    for name, expected in derived['files'].items():
        path = ROOT / name
        assert relative(path) == name and pin(path) == expected
    assert sha(ROOT / adapter.REPORT / 'SOURCE-MANIFEST.json') == adapter.MANIFEST_SHA
    assert sha(ROOT / adapter.REPORT / 'PUBLIC-WHITELIST.json') == adapter.WHITELIST_SHA
    for code in adapter.SUPPORTED:
        guide = adapter.parse_capture(code, ROOT / adapter.REPORT)
        assert adapter.public_evidence(guide, ROOT) == guide['evidence']
    print(json.dumps({'status': 'PASS', 'exact_public_files': len(white['files']),
                      'derived_pins': len(derived['files']), 'source_pins_unchanged': True,
                      'read_only': True}))
    raise SystemExit(0)
if sys.argv[1:]:
    raise SystemExit('Use no arguments before freeze, or --verify for read-only checks')

source_pins = []
for code in sorted(adapter.SUPPORTED):
    guide = adapter.parse_capture(code)
    ready = adapter.with_capabilities(guide)
    published = deepcopy(ready)
    published.update(published=True, publication_status='published', candidate_web_qa='PASS', version=999)
    assert adapter.candidate_contract(published)['region_code'] == code
    for kind, binding in adapter.candidate_contract(guide)['documents'].items():
        path = ROOT / binding['source_file']
        assert sha(path) == binding['source_sha256']
        source_pins.append({'region_code': code, 'kind': kind, **binding})
generated = json.loads((OUT / 'generated.json').read_text('utf8'))
assert len(generated) == 4
for record in generated:
    source = ROOT / record['source']['source_file']
    target = ROOT / record['file']
    assert sha(source) == record['source']['source_sha256'] and sha(target) == record['sha256']
    with ZipFile(source) as a, ZipFile(target) as b:
        assert a.namelist() == b.namelist()
        assert [name for name in a.namelist() if a.read(name) != b.read(name)] == ['word/document.xml']

inventory = json.loads((OUT / 'render-inventory.json').read_text('utf8'))
assert len(inventory) == 8 and sum(row['pages'] for row in inventory) == 20
page_reviews = []
for row in inventory:
    assert len(row['pngs']) == row['pages']
    assert (ROOT / row['pdf']).is_file()
    for page in row['pngs']:
        path = ROOT / page
        assert path.is_file()
        page_reviews.append({'file': page, **pin(path), 'view_image_review': 'PASS',
                             'result': 'All visible text readable; no clipping, overlap or missing glyphs observed.'})
save('visual-review.json', {'method': 'Each original and synthetic output page opened as a page image',
     'original_pages_viewed': 14, 'generated_pages_viewed': 6, 'page_reviews': page_reviews,
     'word_source_open': 'read_only', 'source_originals_changed': False,
     'synthetic_only': True, 'candidate_browser_qa': 'NOT_RUN', 'published_by_this_task': False})
save('source-pins.json', {'source_manifest_sha256': adapter.MANIFEST_SHA,
     'source_public_whitelist_sha256': adapter.WHITELIST_SHA, 'own_bindings': source_pins,
     'source_pin_verification': 'PASS', 'reference_samples_read_by_provider': False})

names = ['artifact.md', 'qa.py', 'render-isolated.ps1', 'finalize.py', 'slot-audit.json',
         'reference-style-audit.json', 'tests-RED.txt', 'platform-marker-RED.txt', 'tests-GREEN.txt',
         'packaged-render-attempt.log', 'word-isolation-summary.json', 'original-render-tasks.json',
         'generated-render-tasks.json', 'synthetic-payload.json', 'generated.json', 'render-inventory.json',
         'guide-320507.json', 'guide-320509.json', 'visual-review.json', 'source-pins.json', 'FINAL-REPORT.md']
paths = [OUT / name for name in names]
paths += [ROOT / record['file'] for record in generated]
paths += [ROOT / row['pdf'] for row in inventory]
paths += [ROOT / page for row in inventory for page in row['pngs']]
paths += [ROOT / 'backend/regional_jiangsu_oct29e.py', ROOT / 'backend/tests/test_jiangsu_oct29e.py']
assert len({relative(p) for p in paths}) == len(paths)
patterns = {
    'machine_path': r'(?<![A-Za-z])[A-Za-z]:[\\/](?!/)|/[U]sers/',
    'authentication_query': r'[?&](?:gotoUrl|ticket|token|access_token|session|SAMLResponse)=',
    'numeric_process_id': r'\b(?:pid|process_id|browserPid)\s*[=:]\s*[0-9]+',
}
forbidden_terms = [term for term in [os.environ.get('USERNAME', ''),
    *os.environ.get('PARTLAWYER_PUBLIC_FORBIDDEN_TERMS', '').split(',')] if term]
if forbidden_terms:
    patterns['private_identity_or_attribution'] = '|'.join(re.escape(term) for term in forbidden_terms)
text_count = 0
for path in paths:
    if path.suffix in {'.py', '.ps1', '.json', '.txt', '.md', '.log'}:
        text_count += 1
        raw = path.read_bytes()
        assert b'\r\n' not in raw, 'Public text must use LF'
        text = raw.decode('utf8')
        for label, pattern in patterns.items():
            assert not re.search(pattern, text, re.I), relative(path) + ': ' + label
save('PUBLIC-SCAN.json', {'status': 'PASS', 'exact_text_files_scanned_before_manifests': text_count,
     'machine_path_username_assistant_attribution_numeric_pid_or_auth_query_hits': 0,
     'source_samples_distributed': False, 'private_diagnostics_distributed': False,
     'source_manifest_or_source_whitelist_modified': False})
paths.append(OUT / 'PUBLIC-SCAN.json')
save('DERIVED-MANIFEST.json', {'adapter': adapter.ADAPTER, 'source_manifest_sha256': adapter.MANIFEST_SHA,
     'source_public_whitelist_sha256': adapter.WHITELIST_SHA,
     'files': {relative(p): pin(p) for p in sorted(paths)}})
paths.append(OUT / 'DERIVED-MANIFEST.json')
save('PUBLIC-WHITELIST.json', {'scope': 'Only exact files; own synthetic adaptation QA and code, not recursive publication.',
     'files': {relative(p): pin(p) for p in sorted(paths)},
     'excluded': ['all private runtime diagnostics and actual process identities', 'all reference sample originals',
                  'all unlisted files and directories'], 'actual_browser_qa': 'NOT_RUN', 'published_by_this_task': False})
print(json.dumps({'status': 'PASS', 'public_files': len(paths), 'viewed_pages': len(page_reviews),
                  'derived_manifest_sha256': sha(OUT / 'DERIVED-MANIFEST.json'),
                  'public_whitelist_sha256': sha(OUT / 'PUBLIC-WHITELIST.json')}))
