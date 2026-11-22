"""Build the compact pilot frontend from a clean, explicitly identified Git commit."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from package_candidate import (
    FRONTEND_BUILD_FLAGS, FRONTEND_OVERLAYS, ROOT, digest, exact_source, git_bytes, json_bytes,
)


def frontend_notices(frontend):
    entries = json.loads((frontend / 'package-lock.json').read_bytes())['packages']
    sections = ['Notices from installed frontend dependencies',
                'The build may omit unused dependencies. The project code license is in LICENSE.']
    for relative, entry in sorted(entries.items()):
        if not relative.startswith('node_modules/') or entry.get('dev'):
            continue
        package = frontend / relative
        if not package.is_dir():
            if entry.get('optional'):
                continue
            raise FileNotFoundError('A locked frontend dependency is missing')
        name = relative.rsplit('node_modules/', 1)[-1]
        package_meta = json.loads((package / 'package.json').read_bytes())
        if package_meta['name'] != name or package_meta['version'] != entry['version']:
            raise ValueError('An installed dependency differs from the lock')
        license_text = package_meta.get('license', entry.get('license', 'Unspecified'))
        sections.append(f'{name} {entry["version"]} — {license_text}')
        for path in sorted(package.iterdir()):
            if path.is_file() and path.name.lower().startswith(('license', 'licence', 'notice', 'copying', 'ofl')):
                sections.append(path.name + '\n' + path.read_text(encoding='utf-8-sig').strip())
    return '\n\n'.join(sections) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--offline', action='store_true', help='Use only cached locked npm artifacts')
    args = parser.parse_args()

    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, timeout=15).strip()
    if args.source_revision != head:
        raise ValueError('Use the full commit hash of the checked out candidate')
    for name in ('build_frontend.py', 'package_candidate.py'):
        exact_source(head, 'deploy/compact_pilot/' + name)
    pins = json.loads(exact_source(head, 'deploy/compact_pilot/runtime-sources.json'))
    baseline = pins['source_base_commit']
    overlays = {path: exact_source(head, path) for path in sorted(FRONTEND_OVERLAYS)}
    node = shutil.which('node')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not node or not npm:
        raise FileNotFoundError('Node and npm are required')

    output = args.output_dir.resolve()
    output.mkdir(exist_ok=False)
    stage = output / 'source'
    stage.mkdir()
    dist = output / 'dist'
    archive = output / 'baseline.tar'
    subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.eol=lf',
                    'archive', '--format=tar', '-o', str(archive), baseline, 'frontend', 'packages', 'config'],
                   cwd=ROOT, check=True, timeout=30)
    with tarfile.open(archive, 'r:') as bundle:
        bundle.extractall(stage, filter='data')
    for path, body in overlays.items():
        staged_path = path if path.startswith('frontend/') else 'frontend/public/' + Path(path).name
        (stage / staged_path).write_bytes(body)

    frontend = stage / 'frontend'
    lock_sha = digest((frontend / 'package-lock.json').read_bytes())
    if lock_sha != digest(git_bytes(baseline, 'frontend/package-lock.json')):
        raise ValueError('Baseline dependency lock changed during checkout')
    env = {**os.environ, **FRONTEND_BUILD_FLAGS}
    lock_install = [npm, 'ci', '--ignore-scripts', '--no-audit', '--no-fund']
    if args.offline:
        lock_install.append('--offline')
    subprocess.run(lock_install, cwd=frontend, env=env, check=True, timeout=240)
    subprocess.run([node, './node_modules/vue-tsc/bin/vue-tsc.js', '--noEmit'],
                   cwd=frontend, env=env, check=True, timeout=90)
    subprocess.run([node, './node_modules/vite/bin/vite.js', 'build', '--configLoader', 'native', '--outDir', str(dist)],
                   cwd=frontend, env=env, check=True, timeout=90)
    with (dist / 'third-party-notices.txt').open('x', encoding='utf-8', newline='\n') as notices:
        notices.write(frontend_notices(frontend))

    artifacts = {path.relative_to(dist).as_posix(): {'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())}
                 for path in dist.rglob('*') if path.is_file()}
    receipt = {'source_base_commit': baseline, 'source_revision': head,
               'source_files': {path: digest(body) for path, body in overlays.items()}, 'artifacts': artifacts,
               'frontend_lock_sha256': lock_sha, 'build_flags': FRONTEND_BUILD_FLAGS,
               'node_version': subprocess.check_output([node, '--version'], text=True, timeout=15).strip(),
               'npm_version': subprocess.check_output([npm, '--version'], text=True, timeout=15).strip(),
               'typecheck': 'passed', 'vite_build': 'passed'}
    body = json_bytes(receipt)
    path = output / 'FRONTEND-RECEIPT.json'
    with path.open('xb') as target:
        target.write(body)
    print(json.dumps({'receipt': str(path), 'sha256': digest(body), 'source_revision': head, 'files': len(artifacts)}))


if __name__ == '__main__':
    main()
