"""Create a short-lived isolated TLS test CA; never install it into a trust store."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True, help='New absolute private directory; existing directories are refused')
    args = parser.parse_args()
    if not args.directory.is_absolute() or args.directory.exists() or args.directory.is_symlink():
        parser.error('Use a new absolute private directory; existing files/directories are never overwritten')
    os.umask(0o077)
    args.directory.mkdir(mode=0o700)
    def openssl(*arguments):
        subprocess.run(['openssl', *arguments], check=True, cwd=args.directory, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
    openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.crt', '-subj', '/CN=LabourLawyer Isolated Acceptance CA', '-days', '2')
    openssl('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'server.key', '-out', 'server.csr', '-subj', '/CN=TLS isolated test')
    (args.directory/'server.ext').write_text('subjectAltName=DNS:tls-test.invalid,IP:127.0.0.1\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n', encoding='ascii')
    openssl('x509', '-req', '-in', 'server.csr', '-CA', 'ca.crt', '-CAkey', 'ca.key', '-CAcreateserial', '-out', 'server.crt', '-days', '1', '-extfile', 'server.ext')
    openssl('genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048', '-out', 'other.key')
    for key in args.directory.glob('*.key'):
        key.chmod(0o600)
    print('Created private test CA and one-day loopback certificate; no OS trust store was changed')

if __name__ == '__main__':
    main()
