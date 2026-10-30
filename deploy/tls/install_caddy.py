"""Install the pinned official Linux amd64 Caddy binary in a private user directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import tarfile
from urllib.request import urlopen

VERSION = '2.11.7'
ARCHIVE = f'caddy_{VERSION}_linux_amd64.tar.gz'
URL = f'https://github.com/caddyserver/caddy/releases/download/v{VERSION}/{ARCHIVE}'
# Official caddy_2.11.7_checksums.txt publishes SHA512, not SHA256.
SHA512 = 'a7a433a1b133efc3c8d10eb0b99d52a24b5ef5c322dc77f5282182b1c0402139ab83f3a99f0c52409df77d20123fb0b523edad8a66d8f5e49136197bf61ef0e7'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() not in {'x86_64', 'amd64'}:
        parser.error('This pinned installer supports Linux amd64 only')
    if not args.directory.is_absolute() or args.directory.is_symlink():
        parser.error('Use an absolute application-owned directory, not a symlink')
    os.umask(0o077)
    args.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    root = args.directory.resolve()
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        parser.error('Install directory must belong to this user and deny group/other access')
    archive = root / ARCHIVE
    if not archive.exists():
        # A failed download remains visibly invalid and is never executed.
        with urlopen(URL, timeout=120) as response, archive.open('xb') as output:
            while block := response.read(1024 * 1024):
                output.write(block)
    data = archive.read_bytes()
    if hashlib.sha512(data).hexdigest() != SHA512:
        raise ValueError('Official Caddy archive checksum mismatch; refusing extraction/execution')
    with tarfile.open(archive) as package:
        member = package.getmember('caddy')
        if not member.isfile():
            raise ValueError('Expected a regular Caddy archive member')
        binary_data = package.extractfile(member).read()
    binary = root / f'caddy-{VERSION}'
    if binary.exists():
        if binary.is_symlink() or binary.read_bytes() != binary_data:
            raise ValueError('Existing portable Caddy differs from the pinned release; no file overwritten')
    else:
        with binary.open('xb') as output:
            output.write(binary_data)
        binary.chmod(0o700)
    print(json.dumps({'version': VERSION, 'archive_sha512': SHA512, 'archive_sha256': hashlib.sha256(data).hexdigest(), 'binary_sha256': hashlib.sha256(binary_data).hexdigest(), 'official_checksum_verified': True}))

if __name__ == '__main__':
    main()
