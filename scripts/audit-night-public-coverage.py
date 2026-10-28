"""Read-only public-data audit; export coverage/gaps without publishing or inference."""
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/nationwide-localization-20261023-night'


def read_database(name):
    return sqlite3.connect((ROOT / name).as_uri() + '?mode=ro', uri=True)


def main():
    with read_database('backend/data/regional-guides.sqlite') as db:
        guides = [json.loads(r[0]) for r in db.execute(
            'SELECT g.payload FROM regional_guides g JOIN regional_current c ON g.sequence=c.sequence')]
        pending, acknowledged = db.execute(
            "SELECT SUM(delivery_status='PENDING_OPENCLAW'),SUM(receipt IS NOT NULL) FROM collection_outbox").fetchone()
    with read_database('backend/data/regional-directory.sqlite') as db:
        directory = [dict(zip(('id', 'province', 'city', 'district'), r)) for r in db.execute(
            'SELECT id,province,city,district FROM directory_areas WHERE level=4 ORDER BY province,city,district')]
    issues = []
    checked = 0
    for g in guides:
        label = '/'.join(g[k] for k in ('province', 'city', 'district'))
        if not (urlsplit(g['source_url']).hostname or '').endswith('.gov.cn'):
            issues.append({'region': label, 'type': 'NON_GOVERNMENT_SOURCE'})
        for t in g['templates']:
            if t.get('region_code') != g['region_code']:
                issues.append({'region': label, 'template': t['id'], 'type': 'REGION_MISMATCH'})
            if t.get('download_status') != 'downloaded':
                continue
            f = (ROOT / t.get('file', '')).resolve()
            if not f.is_relative_to(ROOT.resolve()) or not f.is_file():
                issues.append({'region': label, 'template': t['id'], 'type': 'MISSING_OR_UNSAFE_FILE'})
                continue
            checked += 1
            if hashlib.sha256(f.read_bytes()).hexdigest() != t.get('sha256'):
                issues.append({'region': label, 'template': t['id'], 'type': 'SHA256_MISMATCH'})
    keys = [(g['province'], g['city'], g['district']) for g in guides]
    source_ids = [g['source_id'] for g in guides]
    if len(set(keys)) != len(keys):
        issues.append({'type': 'DUPLICATE_CURRENT_LOCALITY'})
    if len(set(source_ids)) != len(source_ids):
        issues.append({'type': 'SHARED_CURRENT_SOURCE_ID'})
    key_set = set(keys)
    candidates = json.loads((OUT / 'PENDING-SOURCES.json').read_text('utf8'))
    candidate_keys = {(p['province'], p['city'], p['district']) for p in candidates}
    for d in directory:
        key = (d['province'], d['city'], d['district'])
        d['state'] = 'published_exact_name_match' if key in key_set else 'candidate_not_published' if key in candidate_keys else 'no_published_exact_name_match'
    rows = [{**{k: g[k] for k in ('province', 'city', 'district', 'region_code', 'source_id', 'source_url', 'verified_at', 'verification_status')},
             'can_generate': any(t.get('can_generate') for t in g['templates']),
             'material_count': len(g['materials']), 'handling_form': g['channel']['form'],
             'handling_form_raw': g['channel']['raw_value'], 'online_status': g['channel']['online_status'],
             'online_entry_url': g['channel'].get('entry_url')}
            for g in sorted(guides, key=lambda g: (g['province'], g['city'], g['district']))]
    result = {
        'audited_at': datetime.now(timezone.utc).isoformat(),
        'method': 'Read-only public guide/directory SQLite and current template file SHA256; no user/case DB, network, migration, publication or models.',
        'published_guides': len(guides), 'generatable_localities': sum(r['can_generate'] for r in rows),
        'unique_current_source_ids': len(set(source_ids)), 'downloaded_current_template_files_checked': checked,
        'integrity_issues': issues, 'public_pending_openclaw': pending, 'actual_openclaw_receipts': acknowledged,
        'unpublished_candidates': len(candidates), 'by_province': dict(Counter(g['province'] for g in guides)),
        'online_status_counts': dict(Counter(g['channel']['online_status'] for g in guides)),
        'handling_form_counts': dict(Counter(g['channel']['form'] for g in guides)),
        'published_regions': rows, 'directory_regions': directory, 'unpublished_candidates_detail': candidates,
        'limitations': [
            'Directory is navigation, not guide coverage or a complete functional-area census.',
            'Directory comparison uses exact names; full/short aliases are not silently normalized. Published rows establish coverage count.',
            'auth_required proves a real official login boundary, not post-login submission.',
            'Integrity audit does not replace own-source verification, document visual QA or candidate browser acceptance.']}
    target = OUT / 'COVERAGE-AUDIT-ROUND28.json'
    if target.exists():
        raise ValueError('Preserve previous audit; choose a new version')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in {
        'published_regions', 'directory_regions', 'unpublished_candidates_detail', 'limitations'}}, ensure_ascii=False))
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
