"""Prepare or run an application-owned Caddy TLS proxy with a supplied certificate."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import subprocess
import time
from urllib.parse import urlsplit


def hostname_value(value):
    if not value or any(ord(char) < 33 for char in value):
        raise ValueError('An explicit hostname or IP is required')
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    name = value.rstrip('.').encode('idna').decode('ascii').lower()
    if len(name) > 253 or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part) for part in name.split('.')):
        raise ValueError('Invalid hostname; wildcards, paths and schemes are not accepted')
    return name


def upstream_address(value):
    if any(ord(char) < 33 for char in value):
        raise ValueError('Invalid upstream origin')
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
        raise ValueError('Upstream must be an HTTP origin without credentials, path, query or fragment')
    host = hostname_value(parsed.hostname)
    port = parsed.port if parsed.port is not None else (443 if parsed.scheme == 'https' else 80)
    if not 1 <= port <= 65535:
        raise ValueError('Invalid upstream port')
    host = '[' + host + ']' if ':' in host else host
    return host + ':' + str(port), parsed.scheme


def private_file(path, root, *, secret=False):
    path, root = Path(path), Path(root).resolve(strict=True)
    if path.is_symlink():
        raise ValueError('Certificate/key symlink is not allowed')
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError('Certificate/key must remain within the application private root')
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Certificate/key must be a regular file')
    if os.name == 'posix':
        if info.st_uid != os.getuid():
            raise ValueError('Certificate/key owner does not match the application user')
        if secret and stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('Private key permissions must deny group and other access')
    return resolved


def certificate_check(cert, key, root, hostname, *, minimum_days=7):
    hostname = hostname_value(hostname)
    cert, key = private_file(cert, root), private_file(key, root, secret=True)
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cert), str(key), password=lambda: '')
    except (ssl.SSLError, OSError) as error:
        raise ValueError('Provided certificate and private key cannot be loaded together') from error
    try:
        details = subprocess.run(['openssl', 'x509', '-in', str(cert), '-noout', '-startdate', '-enddate', '-ext', 'subjectAltName'], check=True, capture_output=True, text=True, timeout=10).stdout
    except (subprocess.SubprocessError, OSError) as error:
        raise ValueError('OpenSSL could not inspect the supplied certificate') from error
    dates = dict(line.split('=', 1) for line in details.splitlines() if line.startswith(('notBefore=', 'notAfter=')))
    start, end = (ssl.cert_time_to_seconds(dates[name]) for name in ['notBefore', 'notAfter'])
    now = time.time()
    if now < start:
        raise ValueError('Certificate is not valid yet')
    if now >= end:
        raise ValueError('Certificate has expired')
    if end - now < minimum_days * 86400:
        raise ValueError('Certificate is within the required renewal window')
    names = re.findall(r'(DNS|IP Address):([^,\s]+)', details)
    if not any((kind == 'DNS' and hostname_value(value) == hostname) or (kind == 'IP Address' and str(ipaddress.ip_address(value)) == hostname) for kind, value in names):
        raise ValueError('Certificate SAN does not cover the exact requested hostname/IP')
    return {'hostname': hostname, 'seconds_remaining': int(end - now), 'certificate_sha256': hashlib.sha256(cert.read_bytes()).hexdigest()}


def proxy_config(hostname, listen, port, cert, key, upstream):
    hostname = hostname_value(hostname)
    listen = str(ipaddress.ip_address(listen))
    if not 1024 <= port <= 65535:
        raise ValueError('Use an unprivileged listen port')
    dial, scheme = upstream_address(upstream)
    transport = {'protocol': 'http'}
    if scheme == 'https':
        transport['tls'] = {}
    address = '[' + listen + ']' if ':' in listen else listen
    return {'admin': {'disabled': True}, 'apps': {
        'tls': {'certificates': {'load_files': [{'certificate': str(cert), 'key': str(key)}]}},
        'http': {'servers': {'application': {
            'listen': [address + ':' + str(port)], 'protocols': ['h1', 'h2'],
            'automatic_https': {'disable': True}, 'tls_connection_policies': [{}],
            'routes': [
                {'match': [{'host': [hostname]}], 'handle': [{'handler': 'reverse_proxy', 'upstreams': [{'dial': dial}], 'transport': transport}], 'terminal': True},
                {'handle': [{'handler': 'static_response', 'status_code': 421, 'body': 'Unexpected host'}], 'terminal': True}
            ]
        }}}
    }}


def check_port(listen, port):
    family = socket.AF_INET6 if ':' in listen else socket.AF_INET
    with socket.socket(family) as probe:
        if os.name == 'posix':
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((listen, port))
        except OSError as error:
            raise RuntimeError('TLS listen port is occupied or unavailable; no process was stopped') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--cert', type=Path, required=True)
    parser.add_argument('--key', type=Path, required=True)
    parser.add_argument('--hostname', required=True)
    parser.add_argument('--listen', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--minimum-days', type=int, default=7)
    parser.add_argument('--output', type=Path, required=True, help='New private JSON config file; existing files are never overwritten')
    parser.add_argument('--caddy', type=Path, help='Absolute application-owned portable Caddy executable')
    parser.add_argument('--run', action='store_true', help='Validate and run Caddy in foreground')
    args = parser.parse_args()
    root = args.private_root.resolve(strict=True)
    if os.name == 'posix' and (root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) & 0o077):
        parser.error('Private root must belong to this user and deny group/other access')
    if args.minimum_days < 0:
        parser.error('Minimum remaining days cannot be negative')
    result = certificate_check(args.cert, args.key, root, args.hostname, minimum_days=args.minimum_days)
    config = proxy_config(args.hostname, args.listen, args.port, args.cert.resolve(), args.key.resolve(), args.upstream)
    if not args.output.is_absolute() or not args.output.parent.resolve(strict=True).is_relative_to(root):
        parser.error('Output must be an absolute file within the private root')
    if args.run:
        if not args.caddy or not args.caddy.is_absolute() or not args.caddy.is_file():
            parser.error('--run requires an absolute Caddy executable')
        check_port(args.listen, args.port)
    descriptor = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        json.dump(config, output, indent=2)
        output.write('\n')
    env = dict(os.environ, XDG_DATA_HOME=str(root/'caddy-data'), XDG_CONFIG_HOME=str(root/'caddy-config'))
    if args.caddy:
        subprocess.run([str(args.caddy), 'validate', '--config', str(args.output)], check=True, env=env)
    if args.run:
        os.execve(str(args.caddy), [str(args.caddy), 'run', '--config', str(args.output)], env)
    print(json.dumps({'configuration_written': True, **result}))

if __name__ == '__main__':
    main()
