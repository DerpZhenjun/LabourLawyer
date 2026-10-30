"""Start/check only the existing isolated public receipt gateway, without models."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_issue_delivery import ISOLATED_PROFILE, _profile_cli


def validate_public_entry(entry, expected_workspace):
    workspace = Path(entry.get('workspace', '')).expanduser().resolve(strict=True)
    search = entry.get('memory', {}).get('search', {})
    tools = entry.get('tools', {})
    if (workspace != Path(expected_workspace).resolve(strict=True)
            or tools.get('allow') != ['memory_get'] or tools.get('alsoAllow')
            or tools.get('fs', {}).get('workspaceOnly') is not True
            or entry.get('heartbeat', {}).get('every') != '0m' or entry.get('contextInjection') != 'never'
            or search.get('provider') != 'none' or search.get('sources') != ['memory'] or search.get('extraPaths')
            or search.get('rememberAcrossConversations') is not False
            or search.get('experimental', {}).get('sessionMemory') is not False
            or search.get('store', {}).get('vector', {}).get('enabled') is not False):
        raise ValueError('Isolated receipt profile must remain public-only, memory_get-only, without models/heartbeats/embeddings')
    return workspace


def run(check_only=False):
    private = Path.home() / ('.openclaw-' + ISOLATED_PROFILE)
    if not (private / 'openclaw.json').is_file():
        raise FileNotFoundError('Reviewed private isolated profile is missing; startup never creates or copies credentials')
    prefix, inherited = _profile_cli(ISOLATED_PROFILE)
    os_names = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP', 'USERPROFILE',
                'APPDATA', 'LOCALAPPDATA', 'HOME', 'HOMEDRIVE', 'HOMEPATH', 'PROGRAMDATA',
                'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROCESSOR_ARCHITECTURE', 'NO_COLOR'}
    env = {key: value for key, value in inherited.items() if key.upper() in os_names}

    def cli(*args, timeout=30):
        return subprocess.run([*prefix, *args], env=env, capture_output=True, text=True, encoding='utf8',
                              errors='replace', timeout=timeout,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    def setting(path, json_value=False):
        result = cli('config', 'get', path)
        if result.returncode:
            raise ValueError('Reviewed isolated setting is unavailable: ' + path)
        return json.loads(result.stdout) if json_value else result.stdout.strip()

    entry = setting('agents.entries.' + ISOLATED_PROFILE, json_value=True)
    workspace = validate_public_entry(entry, private / 'workspace')
    if setting('gateway.bind') != 'loopback' or setting('gateway.auth.mode') != 'token':
        raise ValueError('Isolated receipt gateway requires loopback binding and private token authentication')
    port = int(setting('gateway.port'))
    if not 1024 <= port <= 65535:
        raise ValueError('Isolated gateway port is outside the permitted range')
    if cli('config', 'validate').returncode:
        raise ValueError('Isolated receipt configuration validation failed')

    def healthy():
        try:
            result = cli('health', '--json', '--timeout', '3000', timeout=15)
            return result.returncode == 0 and json.loads(result.stdout).get('ok') is True
        except (ValueError, subprocess.TimeoutExpired):
            return False

    if healthy():
        return {'status': 'healthy', 'profile': ISOLATED_PROFILE, 'started': False, 'model_calls': 0}
    if check_only:
        raise RuntimeError('Isolated receipt gateway is not healthy; no process was started in check mode')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError('Configured port is occupied; startup will not replace or stop another process')
    command = [*prefix, 'gateway', 'run', '--bind', 'loopback', '--port', str(port), '--ws-log', 'compact']
    with (private / 'receipt-gateway.log').open('ab') as log:
        process = subprocess.Popen(command, env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    # Process identity stays private; stdout never contains operator paths, PID,
    # port credentials, or the private profile's authentication token.
    (private / 'receipt-gateway-process.json').write_text(json.dumps({
        'pid': process.pid, 'port': port, 'command': command, 'workspace': str(workspace)}, indent=2), encoding='utf8')
    for _ in range(12):
        if process.poll() is not None:
            raise RuntimeError('Owned receipt gateway exited; inspect its private profile log')
        if healthy():
            return {'status': 'healthy', 'profile': ISOLATED_PROFILE, 'started': True, 'model_calls': 0}
        time.sleep(1)
    raise RuntimeError('Owned receipt gateway startup is not yet healthy; no unrelated process was stopped')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check the existing private profile/service without starting a process')
    try:
        print(json.dumps(run(parser.parse_args().check)))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'unavailable', 'profile': ISOLATED_PROFILE, 'reason': str(exc), 'model_calls': 0}))
        sys.exit(1)
