"""Guarded two-guide public seed append. Default CLI is read-only; no DB access."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct30f as own

BASE_GUIDES_SHA256 = '58f42da0707a1a85a9923c212c36a4cc57aa0794a046ca8e3769f6801af8bc4c'
DIRECTORY_SHA256 = '913daa7dd7bcbec570945fd7cc8ed08ae55b15c50665e5f8f4d967b62fc85ba8'
FINAL_SHA256 = 'b37cabc422b4a315e22a5762553269636b821dd8d9b0b3fc46f03602af6febe6'
BACKUP = '.runtime/jiangsu-f-seed-publication-20261030'
REPORT = own.QA_REPORT


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf8')


def generating(rows):
    return sum(any(t.get('can_generate') is True for t in row['templates']) for row in rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def publish(root, *, execute=False):
    require(root is not None and not (isinstance(root, str) and not root.strip()), 'Explicit release root required')
    require(type(execute) is bool, 'Execution flag must be a boolean')
    root = Path(root).resolve()
    public = own._path(root, 'data/public-regions')
    before = {name: own._path(root, 'data/public-regions/' + name).read_bytes()
              for name in ['guides.json', 'manifest.json']}
    directory = own._path(root, 'data/public-regions/directory.json').read_bytes()
    manifest = json.loads(before['manifest.json']); guides = json.loads(before['guides.json'])
    require(type(guides) is list and type(manifest) is dict, 'Unexpected public snapshot shape')
    require(type(manifest.get('schema_version')) is int and manifest['schema_version'] == 1, 'Unexpected seed schema')
    require(set(manifest.get('files', {})) == {'guides.json', 'directory.json'}, 'Unexpected public files')
    for name, body in [('guides.json', before['guides.json']), ('directory.json', directory)]:
        require(sha256(body).hexdigest() == manifest['files'][name], 'Existing public snapshot integrity differs')
    require(sha256(directory).hexdigest() == DIRECTORY_SHA256 and len(json.loads(directory)) == 3974,
            'Exact existing directory bytes must stay unchanged')
    require(own.PUBLICATION_SHA256 == FINAL_SHA256, 'Final own browser and Word receipt pin differs')
    approved = [own.with_publication_evidence(own.prepare_candidate(code, root=root), root=root)
                for code in sorted(own.SUPPORTED)]
    require(all(own.public_evidence(row, root) is not None for row in approved), 'Complete own final evidence required')
    require(len(guides) in {203, 205}, 'Only exact baseline203 or completed205 is supported')
    previous = guides[:203]
    require(sha256(encoded(previous)).hexdigest() == BASE_GUIDES_SHA256 and generating(previous) == 186,
            'Exact previous203 encoded records must remain unchanged; never rebuild or replace them')
    expected_counts = {'guides': len(guides), 'generatable_localities': generating(guides), 'directory_rows': 3974}
    require(all(type(manifest.get(k)) is int and manifest[k] == v for k, v in expected_counts.items()),
            'Existing public manifest counts differ')
    if len(guides) == 205:
        require(own._same(guides[203:], approved) and generating(guides) == 188,
                'Existing F records differ or are out of order; never overwrite them')
        return {'status': 'already_published_exact', 'guides_after': 205, 'generatable_localities_after': 188}
    require(sha256(before['guides.json']).hexdigest() == BASE_GUIDES_SHA256, 'Unexpected baseline formatting or bytes')
    after_rows = guides + approved
    require(encoded(after_rows[:203]) == before['guides.json'], 'Baseline encoded records changed')
    after_raw = encoded(after_rows)
    next_manifest = {**manifest, 'exported_at': datetime.now(timezone.utc).isoformat(), 'guides': 205,
                     'generatable_localities': 188, 'release_id': 'oct30night-own-localities-v1',
                     'files': {**manifest['files'], 'guides.json': sha256(after_raw).hexdigest()}}
    after = {'guides.json': after_raw, 'manifest.json': encoded(next_manifest)}
    result = {'status': 'dry_run' if not execute else 'published_worktree_seed_only',
              'guides_before': 203, 'guides_after': 205, 'generatable_localities_before': 186,
              'generatable_localities_after': 188, 'directory_rows': 3974,
              'source_ids': [row['source_id'] for row in approved], 'final_evidence_sha256': FINAL_SHA256,
              'previous203_encoded_records_preserved': True, 'directory_bytes_preserved': True,
              'guides_before_sha256': BASE_GUIDES_SHA256, 'guides_after_sha256': sha256(after_raw).hexdigest(),
              'manifest_after_sha256': sha256(after['manifest.json']).hexdigest(), 'directory_sha256': DIRECTORY_SHA256,
              'main_or_worktree_database_written': False, 'frozen_source_or_evidence_changed': False,
              'model_calls': 0, 'published_at': next_manifest['exported_at'] if execute else None}
    if not execute:
        return result
    pending = {name: own._path(root, 'data/public-regions/' + name + '.jiangsu-f-next') for name in before}
    reports = {own._path(root, REPORT + '/PUBLISHED-GUIDES.json'): encoded(approved),
               own._path(root, REPORT + '/PUBLICATION.json'): encoded(result)}
    require(not any(p.exists() for p in [*pending.values(), *reports]), 'Preserve existing pending files or publication reports')
    backup = own._path(root, BACKUP); backup.mkdir(parents=True, exist_ok=True)
    for name, body in before.items():
        target = own._path(root, BACKUP + '/' + name)
        if target.exists():
            require(target.read_bytes() == body, 'Prior publication backup differs; preserve it')
        else:
            with target.open('xb') as stream:
                stream.write(body)
    owned_pending, owned_reports = [], []
    commit_started = False
    try:
        for name, path in pending.items():
            with path.open('xb') as stream:
                owned_pending.append(path); stream.write(after[name])
        require(all((public / name).read_bytes() == body for name, body in before.items())
                and (public / 'directory.json').read_bytes() == directory, 'Public snapshot changed while preparing append')
        commit_started = True
        pending['guides.json'].replace(public / 'guides.json')
        pending['manifest.json'].replace(public / 'manifest.json')
        require(all((public / name).read_bytes() == body for name, body in after.items())
                and (public / 'directory.json').read_bytes() == directory, 'Public snapshot verification failed')
        for path, body in reports.items():
            with path.open('xb') as stream:
                owned_reports.append(path); stream.write(body)
    except BaseException:
        if commit_started:
            require(all((public / name).read_bytes() in [before[name], after[name]] for name in before),
                    'Concurrent unexpected public content; preserved backups, refusing to overwrite it')
            for name, body in before.items():
                (public / name).write_bytes(body)
        for path in owned_reports:
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in owned_pending:
            path.unlink(missing_ok=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Append only after independent root review')
    args = parser.parse_args()
    if args.execute and not (ROOT / '.git').is_file():
        raise RuntimeError('Execution is restricted to an isolated Git worktree')
    print(json.dumps(publish(ROOT, execute=args.execute), ensure_ascii=False))
