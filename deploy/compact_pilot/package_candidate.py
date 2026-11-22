"""Build a private compact pilot candidate from a reviewed source and data inventory."""

from collections import Counter
from hashlib import sha256
from io import BytesIO
from os import link
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
import argparse
import gzip
import json
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from compact_catalogue_experiment import load
from compact_proof_experiment import object_without_duplicates

FRONTEND_SUFFIXES = {'.css', '.html', '.js', '.svg', '.txt', '.webmanifest', '.woff2'}
FRONTEND_OVERLAYS = frozenset({
    'frontend/src/App.vue', 'frontend/src/api/http.ts', 'frontend/src/api/regional.ts',
    'frontend/src/components/DocumentWorkspace.vue',
    'frontend/src/router/index.ts', 'frontend/src/views/RegionalDocument.vue',
    'frontend/src/views/RegionalGuide.vue', 'deploy/compact_pilot/frontend-public/pilot-scope.html',
    'deploy/compact_pilot/frontend-public/llms.txt',
})
PILOT_SOURCES = (
    'compact_catalogue_experiment.py', 'compact_contract_experiment.py',
    'compact_http_experiment.py', 'compact_locality_experiment.py',
    'compact_proof_experiment.py', 'compact_renderer_experiment.py',
    'compact_renderer_legacy.py', 'compact_sanitized_layout_experiment.py', 'start.py',
)
DEPLOYMENT_MANIFEST = 'DEPLOYMENT-MANIFEST.json'
FRONTEND_BUILD_FLAGS = {'CI': 'true', 'VITE_LABOURLAWYER_PILOT': '1', 'VITE_API_BASE_URL': '/'}


def digest(body):
    return sha256(body).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def parse(body):
    return json.loads(body, object_pairs_hook=object_without_duplicates)


def file_bytes(root, name):
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name or str(rel) != name:
        raise ValueError('Unsafe release filename')
    path = root
    for part in rel.parts:
        path /= part
        if path.is_symlink():
            raise ValueError('Symlinks cannot enter the release')
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError('Expected release file missing')
    return path.read_bytes()


def verify_entry(data, entry):
    if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
        raise ValueError('Exact frozen input digest changed')
    return data


def git_bytes(revision, path):
    return subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT, timeout=15)


def exact_source(revision, path):
    body = git_bytes(revision, path)
    if file_bytes(ROOT, path) != body:
        raise ValueError('Working source differs from the requested Git revision')
    return body


def runtime(source_revision):
    pins = parse(exact_source(source_revision, 'deploy/compact_pilot/runtime-sources.json'))
    if pins['schema'] != 1:
        raise ValueError('Unknown runtime source inventory')
    baseline = pins['source_base_commit']
    result = {}
    for entry in pins['files']:
        name = entry['path']
        if name in result or not (name.startswith('backend/') and name.endswith('.py')
                                  or name.startswith('config/') and name.endswith('.json')
                                  or name == 'deploy/requirements.txt'):
            raise ValueError('Unsupported runtime source path')
        result[name] = verify_entry(git_bytes(baseline, name), entry)
    result['pilot/verify.py'] = exact_source(source_revision, 'deploy/verify.py')
    for name in PILOT_SOURCES:
        result['pilot/' + name] = exact_source(source_revision, 'deploy/compact_pilot/' + name)
    result['README-PILOT.md'] = exact_source(source_revision, 'deploy/compact_pilot/README.md')
    result['LICENSE'] = git_bytes(source_revision, 'LICENSE')
    return result, baseline


def frontend(files_root, manifest_path, manifest_pin, baseline, source_revision):
    body = manifest_path.read_bytes()
    if digest(body) != manifest_pin:
        raise ValueError('Frontend build receipt differs')
    receipt = parse(body)
    if receipt['source_base_commit'] != baseline or receipt['source_files'].keys() != FRONTEND_OVERLAYS:
        raise ValueError('Frontend build receipt is missing frozen source inputs')
    if (receipt['source_revision'] != source_revision or receipt['build_flags'] != FRONTEND_BUILD_FLAGS
            or receipt['frontend_lock_sha256'] != digest(git_bytes(baseline, 'frontend/package-lock.json'))
            or not receipt['node_version'] or not receipt['npm_version']
            or receipt['typecheck'] != 'passed' or receipt['vite_build'] != 'passed'):
        raise ValueError('Frontend build revision, dependency lock or build settings differ')
    for relative, checksum in receipt['source_files'].items():
        if not relative.startswith(('frontend/src/', 'deploy/compact_pilot/frontend-public/')):
            raise ValueError('Unexpected frontend source path')
        if digest(exact_source(source_revision, relative)) != checksum:
            raise ValueError('Frontend source differs from the build receipt')
    files = receipt['artifacts']
    if not {'index.html', 'pilot-scope.html', 'llms.txt', 'third-party-notices.txt'} <= files.keys():
        raise ValueError('Pilot frontend entry points missing')
    actual = {f.relative_to(files_root).as_posix() for f in files_root.rglob('*') if f.is_file()}
    if actual != files.keys():
        raise ValueError('Unexpected or missing frontend artifact')
    result = {}
    for name, entry in files.items():
        if PurePosixPath(name).suffix not in FRONTEND_SUFFIXES:
            raise ValueError('Unsupported frontend artifact')
        result['frontend/dist/' + name] = verify_entry(file_bytes(files_root, name), entry)
    return result


def public_data(data_root, manifest_pin):
    proof, _, _, _ = load(data_root, manifest_pin)
    if not hasattr(proof, 'derivative_sha256'):
        raise ValueError('Candidate must contain only labelled sanitized layouts')
    manifest = file_bytes(data_root, 'INVENTORY.json')
    data_files = parse(manifest)['files']
    return {'data/pilot/INVENTORY.json': manifest,
            **{'data/pilot/' + relative: file_bytes(data_root, relative) for relative in data_files}}


def archive(output, bodies):
    if output.exists():
        raise FileExistsError('The candidate archive already exists')
    with NamedTemporaryFile(prefix='.compact-', suffix='.tar.gz', dir=output.parent, delete=False) as opened:
        temporary = Path(opened.name)
    try:
        with temporary.open('wb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w') as result:
                for name, body in sorted(bodies.items()):
                    member = tarfile.TarInfo(name)
                    member.size = len(body)
                    member.mode = 0o644
                    result.addfile(member, BytesIO(body))
        link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend', required=True, type=Path)
    parser.add_argument('--frontend-receipt', required=True, type=Path)
    parser.add_argument('--frontend-receipt-sha256', required=True)
    parser.add_argument('--pilot-data', required=True, type=Path)
    parser.add_argument('--pilot-data-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source-revision', required=True)
    args = parser.parse_args()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, timeout=15).strip()
    if args.source_revision != head:
        raise ValueError('Use the full commit hash of the checked out candidate')
    exact_source(head, 'deploy/compact_pilot/package_candidate.py')
    files, baseline = runtime(head)
    files.update(frontend(args.frontend.resolve(), args.frontend_receipt, args.frontend_receipt_sha256, baseline, head))
    files.update(public_data(args.pilot_data.resolve(), args.pilot_data_sha256))
    source_paths = sorted(path for path in files if path.startswith(('backend/', 'pilot/', 'config/')))
    source_sha = digest(json_bytes({name: digest(files[name]) for name in source_paths}))
    receipt = {
        'schema_version': 1, 'scope': 'PRIVATE_LABOURLAWYER_COMPACT_CANDIDATE',
        'catalogue_inventory_sha256': args.pilot_data_sha256, 'source_sha256': source_sha,
        'source_revision': head, 'source_base_commit': baseline, 'frontend_receipt_sha256': args.frontend_receipt_sha256,
        'published': False, 'files': [{'path': name, 'bytes': len(body), 'sha256': digest(body)}
                                     for name, body in sorted(files.items())],
    }
    files[DEPLOYMENT_MANIFEST] = json_bytes(receipt)
    archive(args.output.resolve(), files)
    print(json.dumps({
        'status': 'PRIVATE_RUNNABLE_COMPACT_ARCHIVE_BUILT',
        'private_archive': {'path': str(args.output.resolve()), 'bytes': args.output.stat().st_size,
                            'sha256': digest(args.output.read_bytes())},
        'manifest_sha256': digest(files[DEPLOYMENT_MANIFEST]),
        'source_revision': head,
        'catalogue_inventory_sha256': args.pilot_data_sha256, 'file_count': len(files),
        'paths_by_top_level': dict(Counter(path.split('/')[0] for path in files)),
        'public_release': False, 'independent_public_pin_verified': False,
    }))


if __name__ == '__main__':
    main()
