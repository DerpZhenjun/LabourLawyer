"""GET-only live API verification against saved public coverage; no case/model routes."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/nationwide-localization-20261023-night'


def fetch(params):
    url = 'http://127.0.0.1:8000/api/regional-guides/lookup?' + urlencode(params)
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def main():
    expected = json.loads((OUT / 'COVERAGE-AUDIT-ROUND28.json').read_text('utf8'))
    results = []
    for row in expected['published_regions']:
        params = {k: row[k] for k in ('province', 'city', 'district')}
        actual = fetch(params)
        errors = []
        for key in ('region_code', 'source_id', 'source_url', 'verification_status'):
            if actual.get(key) != row[key]:
                errors.append(key)
        if len(actual.get('materials', [])) != row['material_count']:
            errors.append('material_count')
        if actual.get('channel', {}).get('online_status') != row['online_status']:
            errors.append('online_status')
        if any(t.get('can_generate') for t in actual.get('templates', [])) != row['can_generate']:
            errors.append('can_generate')
        results.append({**params, 'source_id': actual.get('source_id'), 'passed': not errors, 'mismatches': errors})
    missing = []
    for candidate in expected['unpublished_candidates_detail']:
        params = {k: candidate[k] for k in ('province', 'city', 'district')}
        actual = fetch(params)
        passed = (actual.get('source_id') is None and actual.get('materials') == []
                  and actual.get('templates') == [] and actual.get('verification_status') == 'unverified'
                  and not actual.get('channel', {}).get('entry_url'))
        missing.append({**params, 'passed': passed, 'actual_verification_status': actual.get('verification_status')})
    # First unavailable exact directory target from each province, no fuzzy aliases.
    probes = {}
    for d in expected['directory_regions']:
        if d['state'] == 'no_published_exact_name_match' and d['province'] not in probes:
            probes[d['province']] = d
    for d in probes.values():
        params = {k: d[k] for k in ('province', 'city', 'district')}
        actual = fetch(params)
        passed = (actual.get('source_id') is None and actual.get('materials') == []
                  and actual.get('templates') == [] and not actual.get('channel', {}).get('entry_url'))
        missing.append({**params, 'passed': passed, 'probe': 'directory_exact_unpublished'})
    result = {
        'at': datetime.now(timezone.utc).isoformat(), 'method': 'GET-only existing main backend lookup route; public metadata only.',
        'published_checks': len(results), 'unpublished_checks': len(missing),
        'failed': sum(not r['passed'] for r in results + missing),
        'published_results': results, 'unpublished_results': missing,
        'not_candidate_browser_acceptance': True, 'model_calls': 0,
    }
    target = OUT / 'LIVE-LOOKUP-AUDIT-ROUND28.json'
    if target.exists():
        raise ValueError('Preserve existing audit')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in {'published_results', 'unpublished_results'}}))
    return 1 if result['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
