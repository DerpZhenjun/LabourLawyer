"""Build a public-only tarball from exact source and verified web build inputs."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PARTS = {'.git', '.runtime', '.venv', '__pycache__', 'node_modules', 'uploads', 'runtime', 'private', 'tests'}
PUBLIC_PREFIXES = ('templates/_docx/', 'reports/', 'data/public-regions/', 'config/', 'frontend/src/data/')
DEPLOY_EXTENSIONS = {'.py', '.sh', '.txt', '.in', '.json', '.md'}


def bounded(root, relative):
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('Bundle paths must be forward-slash relative paths')
    name = PurePosixPath(relative)
    if name.is_absolute() or '..' in name.parts or ':' in relative or not name.parts:
        raise ValueError('Bundle path escapes release root')
    if any(part in PRIVATE_PARTS or part.startswith('.') for part in name.parts):
        raise ValueError('Private/runtime path is not distributable: ' + relative)
    if name.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.env', '.gguf', '.pt', '.pth', '.bin', '.safetensors', '.pyc'}:
        raise ValueError('Private database, credentials or model file is not distributable')
    current = root
    for part in name.parts:
        current = current / part
        if current.is_symlink(): raise ValueError('Symlinks are not distributable')
    full = (root / relative).resolve()
    if not full.is_relative_to(root) or not full.is_file():
        raise ValueError('Missing or out-of-bounds distributable file: ' + relative)
    return full


def digest(body): return hashlib.sha256(body).hexdigest()


def checked_body(root, row):
    body = bounded(root, row['path']).read_bytes()
    if row.get('newline') is not None:
        if row['newline'] != 'lf' or not row['path'].startswith(('config/', 'frontend/src/data/')):
            raise ValueError('Only portable public JSON may normalize checkout line endings')
        body = body.replace(b'\r\n', b'\n')
    if len(body) != row.get('bytes') or digest(body) != row.get('sha256'):
        raise ValueError('Approved file bytes changed: ' + row['path'])
    return body


def verify_build(root, receipt_path):
    receipt_path = Path(receipt_path).resolve()
    if not receipt_path.is_relative_to(root): raise ValueError('Build receipt must be inside the source workspace')
    receipt = json.loads(receipt_path.read_text(encoding='utf8'))
    if receipt.get('status') != 'passed' or receipt.get('action') != 'build' or 'web' not in receipt.get('targets', []):
        raise ValueError('Deployment requires a passing real web build receipt')
    subprocess.run(['node', str(root / 'scripts/client-pipeline.mjs'), 'artifact', '--receipt', receipt_path.relative_to(root).as_posix()], cwd=root, check=True)
    return receipt


def build_bundle(root, output, policy_path, receipt_path):
    root = Path(root).resolve(); output = Path(output).resolve()
    if output.exists(): raise FileExistsError('Refusing to overwrite an existing deployment bundle')
    receipt = verify_build(root, receipt_path)
    policy_path = Path(policy_path).resolve()
    if not policy_path.is_relative_to(root / 'deploy'): raise ValueError('Public policy must be inside deploy/')
    policy = json.loads(policy_path.read_text(encoding='utf8'))
    if policy.get('schema_version') != 1 or not isinstance(policy.get('files'), list): raise ValueError('Invalid deployment public-file policy')
    bodies = {}
    for row in policy['files']:
        relative = row['path']
        if not relative.startswith(PUBLIC_PREFIXES): raise ValueError('Public policy may not authorize source-private paths')
        if relative in bodies: raise ValueError('Duplicate public policy path')
        bodies[relative] = checked_body(root, row)
    source_policy = json.loads((root / 'deploy/source-files.json').read_text(encoding='utf8'))
    if source_policy.get('schema_version') != 1 or not isinstance(source_policy.get('files'), list):
        raise ValueError('An explicit deployment source allowlist is required')
    for relative in source_policy['files']:
        allowed = ((relative.startswith(('backend/', 'llm_service/')) and PurePosixPath(relative).suffix == '.py'
                    and not relative.startswith('backend/data/'))
                   or (relative.startswith('deploy/') and PurePosixPath(relative).suffix in DEPLOY_EXTENSIONS)
                   or relative in {'scripts/manage-users.py', 'scripts/claim-legacy-case.py',
                                   'scripts/run-linux-guide-collector.py', 'scripts/create-tls-test-ca.py',
                                   'scripts/test-tls-proxy.py', 'docs/ubuntu-deployment.md',
                                   'docs/linux-guide-collector.md'})
        if not allowed: raise ValueError('Unsupported deployment source path: ' + relative)
        bodies[relative] = bounded(root, relative).read_bytes()
    for row in receipt.get('artifacts', []):
        relative = row['path']
        if relative.startswith('frontend/dist/'):
            bodies[relative] = checked_body(root, row)
    if 'frontend/dist/index.html' not in bodies: raise ValueError('Verified frontend index is missing')
    manifest = {'schema_version': 1, 'scope': 'public source, official proofs and locally verified frontend build',
                'source_sha256': receipt.get('sourceSha256'), 'published': False,
                'files': [{'path': name, 'bytes': len(body), 'sha256': digest(body)} for name, body in sorted(bodies.items())]}
    bodies['DEPLOYMENT-MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf8')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.deployment-', suffix='.tar.gz', delete=False) as file:
            temporary = Path(file.name)
        with tarfile.open(temporary, 'w:gz') as archive:
            for name, body in sorted(bodies.items()):
                info = tarfile.TarInfo(name); info.size = len(body); info.mtime = 0
                info.mode = 0o755 if name.endswith('.sh') else 0o644
                archive.addfile(info, io.BytesIO(body))
        temporary.rename(output)
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--public-policy', type=Path)
    args = parser.parse_args(); root = args.root.resolve()
    output = build_bundle(root, args.output, args.public_policy or root / 'deploy/public-files.json', args.receipt)
    print(json.dumps({'bundle': str(output), 'bytes': output.stat().st_size, 'sha256': digest(output.read_bytes()), 'published': False}))


if __name__ == '__main__': main()
