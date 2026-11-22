"""Offline first-source pilot accounting. No network, services or user databases.

Coverage is a reviewed stage, never a synonym for visits or source acquisition.
Byte novelty and OOXML member identity establish reuse candidates, not authority.
"""
from collections import Counter
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import zipfile


STAGES = ('own_source_found', 'own_guide_verified', 'materials_verified',
          'blank_original_acquired', 'generation_ready', 'published')


def original_fingerprint(path):
    path = Path(path)
    body = path.read_bytes()
    raw = sha256(body).hexdigest()
    # Legacy OLE documents may contain an embedded/trailing ZIP. Ignoring the
    # OLE prefix would lose the actual Word body and create false reuse.
    if not body.startswith(b'PK\x03\x04') or not zipfile.is_zipfile(path):
        return {'sha256': raw, 'member_sha256': None, 'identity': 'raw_bytes'}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP member names are ambiguous')
        members = [(name, sha256(archive.read(name)).hexdigest())
                   for name in sorted(names)]
    digest = sha256(json.dumps(members, ensure_ascii=False,
                              separators=(',', ':')).encode('utf-8')).hexdigest()
    return {'sha256': raw, 'member_sha256': digest, 'identity': 'all_zip_members'}


def verify_files(root, evidence):
    root = Path(root).resolve()
    count = 0
    for item in evidence:
        relative = item.get('relative_path')
        digest = item.get('sha256')
        if not relative and not digest:
            continue  # Explicit access failures may have no response body.
        if not relative or not digest:
            raise ValueError('Evidence needs both relative_path and sha256')
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Evidence escaped workspace')
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Evidence SHA mismatch: ' + relative)
        count += 1
    return count


def aggregate(cohort, records, baseline_hashes, *, completed_at=None):
    expected = [str(r['code']) for r in cohort['regions']]
    actual = [str(r['region_code']) for r in records]
    if len(set(expected)) != len(expected) or len(set(actual)) != len(actual):
        raise ValueError('Frozen cohort or results contain duplicates')
    if set(actual) != set(expected):
        raise ValueError('Results must exactly match the frozen cohort')
    counts = Counter({key: 0 for key in STAGES})
    templates = []
    incomplete = []
    for row in records:
        cov, review = row.get('coverage', {}), row.get('root_review', {})
        if cov.get('own_guide_verified') and not review.get('own_scope_verified'):
            raise ValueError('Guide lacks independent own scope review')
        if cov.get('materials_verified') and not review.get('materials_roles_verified'):
            raise ValueError('Materials lack independent role review')
        if cov.get('generation_ready') and not (review.get('generation_acceptance_verified')
                and cov.get('materials_verified') and cov.get('own_guide_verified')):
            raise ValueError('Generation lacks complete acceptance')
        if cov.get('published') and not review.get('published_readback_verified'):
            raise ValueError('Publication lacks actual service readback')
        if cov.get('blank_original_acquired') and not any(
                t.get('classification') == 'blank' and t.get('root_blank_verified')
                for t in row.get('templates', [])):
            raise ValueError('Blank acquisition lacks a reviewed original')
        for key in STAGES:
            counts[key] += bool(cov.get(key))
        if row.get('timing_incomplete') or row.get('followup_timing_incomplete'):
            incomplete.append(row['region_code'])
        for t in row.get('templates', []):
            templates.append({**t, 'region_code': row['region_code']})
    qualified_urls = [t for t in templates if t.get('classification') == 'blank'
                      and t.get('root_blank_verified') and t.get('sha256')]
    # Multiple download columns can point to the same local original.
    qualified = list({(t['region_code'], t['sha256']): t for t in qualified_urls}.values())
    unique = {t['sha256'] for t in qualified}
    new = unique - set(baseline_hashes)
    start = datetime.fromisoformat(cohort['frozen_at'])
    end = datetime.fromisoformat(completed_at) if completed_at else max(
        datetime.fromisoformat(r.get('research_completed_at', r['completed_at']))
        for r in records)
    wall = (end - start).total_seconds()
    if wall <= 0:
        raise ValueError('Research end must follow freeze')
    dwell = sum(float(r.get('work_seconds', 0)) +
                float(r.get('followup_work_seconds', 0)) for r in records)
    if any(float(r.get(k, 0)) < 0 for r in records
           for k in ['work_seconds', 'followup_work_seconds']):
        raise ValueError('Negative recorded dwell time')
    return {
        'regions_attempted': len(records), 'counts': dict(counts),
        'censored_regions': sum(bool(r.get('censored', True)) for r in records),
        'research_started_at': cohort['frozen_at'], 'research_completed_at': end.isoformat(),
        'research_wall_seconds': wall,
        'recorded_region_dwell_seconds': dwell,
        'dwell_warning': 'Lower bounds and overlapping root dwell; not total effective agent hours',
        'timing_incomplete_regions': incomplete,
        'attempts_per_wall_hour': len(records) * 3600 / wall,
        'stage_output_per_wall_hour': {k: v * 3600 / wall for k, v in counts.items()},
        'full_completion_eta_seconds': None,
        'eta_reason': 'No representative end-to-end completion-time model; censored cases retained',
        'templates': {
            'reported_url_bindings': sum(bool(t.get('url') or t.get('url_present')) for t in templates),
            'acquired_url_bindings': sum(bool(t.get('sha256')) for t in templates),
            'classification_counts': dict(Counter(t.get('classification', 'unknown') for t in templates if t.get('sha256'))),
            'qualified_blank_url_bindings': len(qualified_urls),
            'qualified_blank_bindings': len(qualified),
            'regions_with_qualified_blank': len({t['region_code'] for t in qualified}),
            'unique_originals': len(unique), 'new_unique_originals': len(new),
            'previously_seen_unique_originals': len(unique) - len(new),
            'new_unique_ratio': len(new)/len(unique) if unique else None,
            'new_binding_ratio': sum(t['sha256'] in new for t in qualified)/len(qualified) if qualified else None,
            'new_sha256': sorted(new),
            'qualification_warning': 'Blank acquisition does not assert complete materials, adaptation or rendering acceptance',
        },
    }
