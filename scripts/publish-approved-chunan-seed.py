"""Append root-reviewed Chunan to the worktree public seed; never open a DB."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_zhejiang_chunan_oct30 import prepare_candidate, with_publication_evidence, public_evidence, _same

BASE_GUIDES_SHA256 = 'f34c108b6441fe2647994965583be3b376b0621623ddf14bd373f9b3b6fe698a'
DIRECTORY_SHA256 = '913daa7dd7bcbec570945fd7cc8ed08ae55b15c50665e5f8f4d967b62fc85ba8'
REPORT = 'reports/production-readiness-20261030/localities/chunan'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf8')


def generating(guides):
    return sum(any(t.get('can_generate') is True for t in g['templates']) for g in guides)


def publish(root):
    root = Path(root).resolve()
    public = root / 'data/public-regions'
    before = {n: (public / n).read_bytes() for n in ['guides.json', 'manifest.json']}
    manifest = json.loads(before['manifest.json']); guides = json.loads(before['guides.json'])
    directory = (public / 'directory.json').read_bytes()
    if manifest['schema_version'] != 1 or any(sha256(body).hexdigest() != manifest['files'][name] for name, body in [('guides.json', before['guides.json']), ('directory.json', directory)]):
        raise ValueError('Existing public snapshot integrity differs; never rebuild it')
    if sha256(directory).hexdigest() != DIRECTORY_SHA256 or len(json.loads(directory)) != 3974:
        raise ValueError('Existing directory changed; leave it untouched')
    own = with_publication_evidence(prepare_candidate(root=root), root=root)
    if public_evidence(own, root) is None:
        raise ValueError('Complete own-source publication evidence is required')
    previous = [g for g in guides if g['region_code'] != '330127']
    if sha256(encoded(previous)).hexdigest() != BASE_GUIDES_SHA256 or (len(previous), generating(previous)) != (202, 185):
        raise ValueError('The exact previous202 guides must remain unchanged')
    current = [g for g in guides if g['region_code'] == '330127']
    if current:
        if len(guides) != 203 or len(current) != 1 or not _same(current[0], own):
            raise ValueError('Existing Chunan seed differs; never overwrite it')
        if manifest['guides'] != 203 or manifest['generatable_localities'] != 186:
            raise ValueError('Existing Chunan manifest counts differ')
        return {'status': 'already_published_exact', 'guides_after': 203, 'generatable_localities_after': 186}
    if sha256(before['guides.json']).hexdigest() != BASE_GUIDES_SHA256 or manifest['guides'] != 202 or manifest['generatable_localities'] != 185:
        raise ValueError('Unexpected baseline snapshot; no append performed')
    after_guides = guides + [own]
    after_raw = encoded(after_guides)
    next_manifest = dict(manifest, exported_at=datetime.now(timezone.utc).isoformat(), guides=203,
                         generatable_localities=186, release_id='oct30-chunan-own-locality-v1')
    next_manifest['files'] = {**manifest['files'], 'guides.json': sha256(after_raw).hexdigest()}
    backup = root / '.runtime/chunan-seed-publication-20261030'
    backup.mkdir(parents=True, exist_ok=True)
    for name, body in before.items():
        target = backup / name
        if target.exists() and target.read_bytes() != body:
            raise ValueError('Prior publication backup differs; preserve it')
        target.write_bytes(body)
    pending = {name: public / (name + '.chunan-next') for name in before}
    try:
        pending['guides.json'].write_bytes(after_raw)
        pending['manifest.json'].write_bytes(encoded(next_manifest))
        pending['guides.json'].replace(public / 'guides.json')
        pending['manifest.json'].replace(public / 'manifest.json')
    except BaseException:
        for name, body in before.items():
            (public / name).write_bytes(body)
        raise
    finally:
        for path in pending.values():
            path.unlink(missing_ok=True)
    assert after_guides[:202] == guides and (public / 'directory.json').read_bytes() == directory
    result = {'status': 'published_worktree_seed_only', 'root_review_approval': 'Root independently reviewed four actual Word pages and explicitly authorized this seed append',
              'source_id': own['source_id'], 'guides_before': 202, 'guides_after': 203,
              'generatable_localities_before': 185, 'generatable_localities_after': 186, 'directory_rows': 3974,
              'previous202_records_preserved': True, 'directory_bytes_preserved': True,
              'guides_before_sha256': BASE_GUIDES_SHA256, 'guides_after_sha256': next_manifest['files']['guides.json'],
              'directory_sha256': DIRECTORY_SHA256, 'manifest_after_sha256': sha256(encoded(next_manifest)).hexdigest(),
              'main_or_worktree_database_written': False, 'frozen_source_or_final_evidence_changed': False,
              'models_called': False, 'published_at': next_manifest['exported_at']}
    report = root / REPORT; report.mkdir(parents=True, exist_ok=True)
    (report / 'PUBLISHED-GUIDE.json').write_bytes(encoded(own))
    (report / 'PUBLICATION.json').write_bytes(encoded(result))
    return result


if __name__ == '__main__':
    if not (ROOT / '.git').is_file():
        raise RuntimeError('This operation is restricted to an isolated Git worktree')
    print(json.dumps(publish(ROOT)))
