"""Verify an extracted deployment against its exact file manifest."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'DEPLOYMENT-MANIFEST.json').read_text(encoding='utf8'))
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('files'), list):
        raise ValueError('Invalid deployment manifest')
    expected = {'DEPLOYMENT-MANIFEST.json'}
    for row in manifest['files']:
        name = row['path']; relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name or name in expected:
            raise ValueError('Unsafe or duplicate deployment path')
        path = root
        for part in relative.parts:
            path = path / part
            if path.is_symlink(): raise ValueError('Deployment may not contain symlinks')
        if not path.resolve().is_relative_to(root) or not path.is_file(): raise ValueError('Deployment file is missing')
        body = path.read_bytes()
        if len(body) != row['bytes'] or hashlib.sha256(body).hexdigest() != row['sha256']:
            raise ValueError('Deployment file changed: ' + name)
        expected.add(name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != expected: raise ValueError('Deployment contains unexpected files; use a fresh release directory')
    return len(expected) - 1


if __name__ == '__main__':
    print('Verified', verify(Path(__file__).resolve().parents[1]), 'deployment files; no service started')
