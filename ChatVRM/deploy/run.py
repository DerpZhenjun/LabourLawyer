"""Run one prebuilt digital release in foreground; never build or stop a listener."""
import argparse
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit


def check_port(host: str, port: int):
    with socket.socket() as probe:
        # Node permits restarting a stopped TCP server while old connections are
        # in TIME_WAIT. This does not permit sharing an active listening socket.
        if os.name != 'nt':
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError as error:
            raise RuntimeError('Digital runtime port already occupied or unavailable; no process was stopped') from error


def api_origin(value: str) -> str:
    if any(char.isspace() or ord(char) < 33 or ord(char) == 127 for char in value):
        raise ValueError('API origin cannot contain whitespace or control characters')
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.path not in {'', '/'} or '?' in value or '#' in value:
        raise ValueError('API base must be an explicit HTTP origin without credentials, query or API path')
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError('API origin has an invalid port')
    return value.rstrip('/')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path, required=True, help='Absolute path to the application-owned portable Node executable')
    parser.add_argument('--host', required=True, help='Explicit local/LAN listen address')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--api-base', type=api_origin, required=True)
    args = parser.parse_args()
    app = Path(__file__).resolve().parents[1]
    if not args.node.is_absolute() or not args.node.is_file():
        parser.error('--node must name an existing absolute executable')
    if not (app / '.next/BUILD_ID').is_file():
        parser.error('Release has no completed production build')
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged port')
    check_port(args.host, args.port)
    env = dict(os.environ, NODE_ENV='production', NEXT_TELEMETRY_DISABLED='1', LABOURLAWYER_API_BASE=args.api_base)
    os.chdir(app)
    os.execve(str(args.node), [str(args.node), str(app / 'node_modules/next/dist/bin/next'), 'start', '--hostname', args.host, '--port', str(args.port)], env)

if __name__ == '__main__':
    main()
