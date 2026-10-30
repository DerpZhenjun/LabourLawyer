"""Create a digital-only source archive; never include a local install or user data."""
import argparse
import hashlib
import gzip
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = [
    'packages/client-contracts/generated/index.cjs',
    'packages/client-contracts/generated/index.d.cts',
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    files = subprocess.check_output(['git', '-c', 'core.quotepath=false', 'ls-files', '--', 'ChatVRM/src', 'ChatVRM/public'], cwd=ROOT, text=True, encoding="utf-8").splitlines()
    files += ['ChatVRM/deploy/' + name for name in ['prepare.py', 'run.py', 'install-node.sh', 'README.md']]
    files += ['ChatVRM/' + file for file in ['package.json', 'package-lock.json', 'next.config.js', 'next-env.d.ts', 'tsconfig.json', 'tailwind.config.js', 'postcss.config.js', '.eslintrc.json', 'LICENSE']]
    files += EXTERNAL
    manifest = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, encoding="utf-8").strip(), 'files': {}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed, tarfile.open(fileobj=compressed, mode='w') as archive:
        for name in sorted(files):
            file = ROOT / name
            if file.is_symlink():
                raise RuntimeError('Refusing symlink: ' + name)
            data = file.read_bytes()
            manifest['files'][name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(data))
        data = json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b'\n'
        info = tarfile.TarInfo('DIGITAL-SOURCE-MANIFEST.json')
        info.size = len(data)
        info.mode = 0o600
        archive.addfile(info, io.BytesIO(data))
    print(json.dumps({'files': len(files), 'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(), 'source_commit': manifest['source_commit']}))

if __name__ == '__main__':
    main()
