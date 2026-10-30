"""Public issue workspace export. Persistence is distinct from service ACK.

Every exported row stays PENDING_OPENCLAW: filesystem read-back proves neither
that OpenClaw has consumed the files nor that an AI reviewed the issues.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from regional_guides import EVENT_TYPES

PENDING = 'PENDING_OPENCLAW'
EXPORTED = 'EXPORTED_PENDING_OPENCLAW'
PUBLIC_FIELDS = frozenset('id type province city district region_code service keyword url occurred_at reason attempts final_status remediation'.split())
_SECRET = re.compile(r'(?i)\bbearer\s+\S+|\b(?:api[_ -]?key|token|password|cookie|authorization)\s*[:=]\s*\S+')
_PERSONAL = re.compile(r'(?<!\d)(?:\d{17}[\dXx]|1[3-9]\d{9})(?!\d)')
ISOLATED_PROFILE = 'labourlawyer-public-issues'
_FJ_GUIDE_PATH = '/person-todo/todo-fingerpost'
_JS_GUIDE_PATH = '/jszwfw/publicservice/itemlist/showDetail.do'
_UUID = r'(?:[A-Fa-f0-9]{32}|[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12})'
_LEGACY_SELECTORS = {'areaCode': r'[0-9]{6,12}', 'regionCode': r'[0-9]{6,12}', 'localInnerCode': _UUID,
                     **{key: r'[A-Za-z0-9_-]{1,128}' for key in ('itemId', 'taskCode', 'qlCode', 'qlcode', 'qlbm', 'serviceCode', 'itemCode')}}
_FJ_SELECTORS = {'unid': r'[A-Fa-f0-9]{32}', 'infoType': r'1'}
# The observed Jiangsu own-service codes are an 18-character government body
# identity (11 + Jiangsu area + ten characters), followed by 13/15 digits.
_JS_SELECTORS = {'webId': r'[1-9][0-9]{0,2}', 'ql_kind': r'[1-9][0-9]?',
                 'iddept_ql_inf': r'1132[0-9]{4}[A-Z0-9]{10}[0-9]{13}',
                 'iddept_yw_inf': r'1132[0-9]{4}[A-Z0-9]{10}[0-9]{15}'}
_URL_PRIVATE_PATH = re.compile(r'(?:^|/)(?:login|sso|oauth|passport|account|profile|private|session|upload|auth|cookie|token|signature)(?:[/.?_-]|$)', re.I)
_URL_SECRET_VALUE = re.compile(r'bearer|token|password|cookie|session|signature|credential|authorization|secret|api[_-]?key', re.I)


def _public_query(query, *, path):
    """Keep only this public path's selectors; reject ambiguous/invalid input."""
    patterns = _FJ_SELECTORS if path == _FJ_GUIDE_PATH else _JS_SELECTORS if path == _JS_GUIDE_PATH else _LEGACY_SELECTORS
    if re.search(r'%(?![A-Fa-f0-9]{2})', query): raise ValueError('Invalid public source selector encoding')
    try:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True, max_num_fields=32, errors='strict')
    except (ValueError, UnicodeError):
        raise ValueError('Invalid public source selectors') from None
    selectors = []
    seen = set()
    for key, value in pairs:
        if key.casefold() in seen: raise ValueError('Duplicate public source selectors')
        seen.add(key.casefold())
        if re.search(r'[\x00-\x1f\x7f\\]', key + value): raise ValueError('Invalid public source selector controls')
        if key not in patterns: continue  # Never forward unknown identity/credential values.
        if not re.fullmatch(patterns[key], value) or _PERSONAL.search(value) or _URL_SECRET_VALUE.search(value):
            raise ValueError('Invalid public source selector value')
        selectors.append((key, value))
    selected = dict(selectors)
    if path in {_FJ_GUIDE_PATH, _JS_GUIDE_PATH} and selected:
        if set(selected) != set(patterns): raise ValueError('Incomplete public item selectors')
    if path == _JS_GUIDE_PATH and selected and not selected['iddept_yw_inf'].startswith(selected['iddept_ql_inf']):
        raise ValueError('Public item selector identities differ')
    return urlencode(selectors)


def public_source_url(value):
    """Pure public URL projection shared by delivery and new collector DTOs.

    Return None for nonpublic/credential/private URLs. Reject malformed,
    duplicate or invalid known selectors with ValueError. Unknown query values
    are discarded. No network, persistence, service ACK or model operation.
    """
    if type(value) is not str or len(value) > 16000: raise ValueError('Invalid public source URL')
    if not value or value != value.strip() or re.search(r'[\x00-\x20\x7f\\]', value): return None
    if re.search(r'%(?![A-Fa-f0-9]{2})', value): raise ValueError('Invalid public source URL encoding')
    try:
        parts = urlsplit(value); port = parts.port
        host = parts.hostname or ''
        decoded_path = unquote(unquote(parts.path, errors='strict'), errors='strict')
    except (ValueError, UnicodeError):
        return None
    if (parts.scheme not in {'http', 'https'} or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+gov\.cn', host)
            or parts.username is not None or parts.password is not None
            or port not in {None, 443 if parts.scheme == 'https' else 80}): return None
    if (not re.fullmatch(r'[/A-Za-z0-9_.~+-]*', decoded_path) or '..' in decoded_path.split('/')
            or _URL_PRIVATE_PATH.search(decoded_path) or _PERSONAL.search(decoded_path)): return None
    query = _public_query(parts.query, path=parts.path)
    fragment = ''
    route, separator, parameters = parts.fragment.partition('?')
    if parts.path not in {_FJ_GUIDE_PATH, _JS_GUIDE_PATH} and route == '/workguide' and separator:
        public_fragment = _public_query(parameters, path=route)
        if public_fragment: fragment = route + '?' + public_fragment
    return urlunsplit((parts.scheme, host, parts.path, query, fragment))


def _json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf8')


@contextmanager
def _database(path, writable=False):
    path = Path(path).resolve(strict=True)
    db = sqlite3.connect(path.as_uri() + ('?mode=rw' if writable else '?mode=ro'), uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def _public_event(payload, identifier):
    event = json.loads(payload)
    if not isinstance(event, dict) or event.get('id') != identifier:
        raise ValueError('Outbox identity does not match payload')
    if event.get('type') not in EVENT_TYPES:
        raise ValueError('Only known public collection issue types may be exported')
    if not isinstance(identifier, str) or not re.fullmatch(r'[\w.-]{1,256}', identifier):
        raise ValueError('Invalid public issue identifier')
    public = {}
    for field in sorted(PUBLIC_FIELDS & event.keys()):
        value = event[field]
        if value is None:
            continue
        if field == 'attempts':
            if type(value) is not int or not 0 <= value <= 1000000:
                raise ValueError('Invalid public collection attempt count')
        else:
            if not isinstance(value, str) or len(value) > 16000:
                raise ValueError('Public collection fields must be bounded scalar text')
            if field == 'url':
                value = public_source_url(value)
                if value is None: continue
            else:
                value = _PERSONAL.sub('[REDACTED]', _SECRET.sub('[REDACTED]', value))
        public[field] = value
    return public


def _immutable_write(path, content, workspace):
    if path.is_symlink() or not path.resolve().is_relative_to(workspace):
        raise ValueError('Export path must remain in the configured workspace')
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError('Existing export evidence conflicts; preserved without overwrite')
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.writing-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _persist(workspace, public):
    content = _json({'schema': 'partlawyer-public-issues/v1', 'scope': 'public_government_collection_only', 'events': [public]})
    checksum = hashlib.sha256(content).hexdigest()
    directory = workspace / 'partlawyer-public-issues' / 'v1' / checksum
    if not directory.resolve().is_relative_to(workspace):
        raise ValueError('Export directory escapes configured workspace')
    directory.mkdir(parents=True, exist_ok=True)
    content_file = directory / 'events.json'
    receipt_file = directory / 'receipt.json'
    receipt = {'schema': 'partlawyer-workspace-export/v1', 'kind': 'workspace_persistence',
               'status': EXPORTED, 'persisted_event_ids': [public['id']],
               'content_file': content_file.relative_to(workspace).as_posix(),
               'receipt_file': receipt_file.relative_to(workspace).as_posix(),
               'content_sha256': checksum, 'service_acknowledged': False, 'ai_reviewed': False}
    _immutable_write(content_file, content, workspace)
    _immutable_write(receipt_file, _json(receipt), workspace)
    if content_file.read_bytes() != content or receipt_file.read_bytes() != _json(receipt):
        raise ValueError('Workspace export read-back verification failed')
    return {**receipt, 'workspace': str(workspace)}


def _record_export(database, identifier, expected_payload, receipt):
    with _database(database, writable=True) as db:
        updated = db.execute('UPDATE collection_outbox SET receipt=? WHERE id=? AND payload=? AND delivery_status=?',
                             (json.dumps(receipt, ensure_ascii=False), identifier, expected_payload, PENDING))
        if updated.rowcount != 1:
            raise ValueError('Outbox changed during export; retry the current payload')


def delivery_summary(database):
    """Read-only counts; workspace export never contributes to service ACK."""
    with _database(database) as db:
        rows = db.execute('SELECT delivery_status,receipt FROM collection_outbox').fetchall()
    counts = {'total': len(rows), 'pending': 0, 'workspace_exported': 0, 'acknowledged': 0, 'ai_reviewed': 0}
    for row in rows:
        counts['pending'] += row['delivery_status'] == PENDING
        receipt = json.loads(row['receipt']) if row['receipt'] else {}
        counts['workspace_exported'] += receipt.get('kind') == 'workspace_persistence' and receipt.get('status') == EXPORTED
        counts['acknowledged'] += row['delivery_status'] == 'ACKNOWLEDGED_OPENCLAW'
        counts['ai_reviewed'] += row['delivery_status'] == 'ACKNOWLEDGED_OPENCLAW' and receipt.get('ai_reviewed') is True
    return counts


def deliver_pending(database, workspace, *, record_receipts=False, limit=1000):
    """Export rows independently. Default is DB read-only; rows stay pending."""
    if type(limit) is not int or not 1 <= limit <= 10000:
        raise ValueError('Export limit must be between 1 and 10000')
    with _database(database) as db:
        rows = db.execute('SELECT id,payload FROM collection_outbox WHERE delivery_status=? ORDER BY created_at,id LIMIT ?',
                          (PENDING, limit)).fetchall()
    result = {'attempted_at': datetime.now(timezone.utc).isoformat(), 'status': EXPORTED,
              'transport': 'openclaw_workspace_files', 'attempted': len(rows), 'workspace_exported': 0,
              'acknowledged': 0, 'ai_reviewed': 0, 'failed': 0, 'failures': [], 'receipts': [],
              'database_receipts_written': bool(record_receipts), 'model_calls': 0}
    try:
        workspace = Path(workspace).expanduser().resolve(strict=True)
        if not workspace.is_dir():
            raise NotADirectoryError('Configured OpenClaw workspace is unavailable')
    except (OSError, RuntimeError) as exc:
        result.update(status=PENDING, failed=len(rows), failures=[{'error_type': type(exc).__name__, 'error': str(exc)}])
        result['pending'] = delivery_summary(database)['pending']
        return result
    result['workspace'] = str(workspace)
    for row in rows:
        try:
            public = _public_event(row['payload'], row['id'])
            receipt = _persist(workspace, public)
            if record_receipts:
                _record_export(database, row['id'], row['payload'], receipt)
            result['receipts'].append(receipt)
            result['workspace_exported'] += 1
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            result['failed'] += 1
            result['failures'].append({'event_id': row['id'], 'error_type': type(exc).__name__, 'error': str(exc)})
    result['pending'] = delivery_summary(database)['pending']
    if result['failed']:
        result['status'] = 'PARTIAL_EXPORT' if result['workspace_exported'] else PENDING
    return result


def discover_workspace(timeout=30):
    """Ask the real installed CLI for this one nonsecret config property."""
    executable = shutil.which('openclaw') or shutil.which('openclaw.cmd')
    if not executable:
        raise FileNotFoundError('OpenClaw CLI is not installed or on PATH')
    launcher = Path(executable).parent / 'node_modules' / 'openclaw' / 'openclaw.mjs'
    node = shutil.which('node')
    prefix = [node, str(launcher)] if node and launcher.is_file() else [executable]
    completed = subprocess.run([*prefix, 'config', 'get', 'agents.defaults.workspace'],
                               capture_output=True, text=True, encoding='utf8', errors='replace',
                               timeout=timeout, check=False,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if completed.returncode:
        raise RuntimeError('OpenClaw CLI could not resolve the configured workspace')
    value = completed.stdout.strip()
    if not value or '\n' in value:
        raise ValueError('OpenClaw returned an ambiguous workspace path')
    workspace = Path(value).expanduser().resolve(strict=True)
    if not workspace.is_dir():
        raise NotADirectoryError('Configured OpenClaw workspace is unavailable')
    return workspace


def _profile_cli(profile):
    if profile != ISOLATED_PROFILE:
        raise ValueError('Service verification requires the named isolated public issue profile')
    executable = shutil.which('openclaw') or shutil.which('openclaw.cmd')
    if not executable:
        raise FileNotFoundError('OpenClaw CLI is not installed or on PATH')
    launcher = Path(executable).parent / 'node_modules' / 'openclaw' / 'openclaw.mjs'
    node = shutil.which('node')
    prefix = [node, str(launcher)] if node and launcher.is_file() else [executable]
    # Profile selection must not be redirected into the global configuration or
    # gateway by inherited environment overrides, including main auth tokens.
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith('OPENCLAW_')}
    return [*prefix, '--profile', profile], env


def _configured_profile_workspace(profile):
    prefix, env = _profile_cli(profile)
    completed = subprocess.run([*prefix, 'config', 'get', f'agents.entries.{ISOLATED_PROFILE}.workspace'],
                               env=env, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=30,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if completed.returncode or not completed.stdout.strip() or '\n' in completed.stdout.strip():
        raise ValueError('Isolated profile does not configure the dedicated public issue agent workspace')
    return Path(completed.stdout.strip()).expanduser().resolve(strict=True)


def _gateway_memory_read(agent, workspace, relative_path, timeout, *, profile=None):
    """Invoke the installed, supported isolated RPC without an agent/model turn."""
    prefix, env = _profile_cli(profile)
    params = {'name': 'memory_get', 'agentId': agent, 'sessionKey': f'agent:{agent}:main',
              'args': {'path': relative_path, 'corpus': 'memory', 'from': 1, 'lines': 1000}}
    completed = subprocess.run([*prefix, 'gateway', 'call', 'tools.invoke', '--json', '--timeout', str(timeout * 1000),
                                '--params', json.dumps(params)], capture_output=True, text=True, encoding='utf8',
                               errors='replace', timeout=timeout + 15, check=False, env=env,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if completed.returncode:
        raise RuntimeError('OpenClaw gateway RPC failed: ' + _SECRET.sub('[REDACTED]', completed.stderr[-2000:]))
    return json.loads(completed.stdout)


def _service_acknowledge(database, rows, receipt):
    with _database(database, writable=True) as db:
        for row in rows:
            result = db.execute('UPDATE collection_outbox SET delivery_status=?,receipt=? WHERE id=? AND payload=? AND delivery_status=?',
                                ('ACKNOWLEDGED_OPENCLAW', json.dumps(receipt, ensure_ascii=False), row['id'], row['payload'], PENDING))
            if result.rowcount != 1:
                raise ValueError('Outbox changed during service read-back; batch left pending for retry')


def verify_pending_with_openclaw(database, workspace, agent, *, profile=None, record_receipts=False, limit=1000, timeout=15):
    """Exact scoped service reads; explicit record_receipts publishes DB ACK.

    Requires a separately reviewed public-only agent. Chunking stays below the
    installed memory_get 12000-character cap. This proves service file receipt,
    never AI review. Default leaves the database read-only and pending.
    """
    if agent != 'labourlawyer-public-issues':
        raise ValueError('Service receipt verification requires the dedicated public-only agent')
    if profile != ISOLATED_PROFILE:
        raise ValueError('Service receipt verification requires the named isolated profile')
    if type(limit) is not int or not 1 <= limit <= 10000 or type(timeout) is not int or not 1 <= timeout <= 60:
        raise ValueError('Invalid service receipt limit or timeout')
    workspace = Path(workspace).expanduser().resolve(strict=True)
    if workspace != _configured_profile_workspace(profile):
        raise ValueError('Workspace does not match the dedicated agent in the isolated profile')
    if not workspace.is_dir():
        raise NotADirectoryError('Dedicated public-only agent workspace is unavailable')
    with _database(database) as db:
        rows = db.execute('SELECT id,payload FROM collection_outbox WHERE delivery_status=? ORDER BY created_at,id LIMIT ?',
                          (PENDING, limit)).fetchall()
    result = {'status': 'VERIFIED_PENDING_DATABASE', 'transport': 'openclaw_gateway_tools_invoke_memory_get',
              'agent': agent, 'profile': profile, 'workspace': str(workspace), 'attempted': len(rows), 'workspace_exported': 0,
              'service_verified': 0, 'acknowledged': 0, 'ai_reviewed': 0, 'model_calls': 0,
              'failed': 0, 'failures': [], 'receipts': [], 'database_receipts_written': bool(record_receipts)}
    prepared = []
    for row in rows:
        try:
            public = _public_event(row['payload'], row['id'])
            export = _persist(workspace, public)
            prepared.append((row, public, export['content_sha256']))
            result['workspace_exported'] += 1
        except (ValueError, OSError) as exc:
            result['failed'] += 1
            result['failures'].append({'event_id': row['id'], 'error_type': type(exc).__name__, 'error': str(exc)})

    def bundle(items):
        return _json({'schema': 'partlawyer-service-receipt/v1', 'scope': 'public_government_collection_only',
                      'events': [item[1] for item in items],
                      'content_sha256s': {item[0]['id']: item[2] for item in items}})

    batches, current = [], []
    for item in prepared:
        candidate = bundle([*current, item])
        if len(candidate.decode('utf8').encode('utf-16-le')) // 2 > 9000:
            if current:
                batches.append(current)
                current = []
            if len(bundle([item]).decode('utf8').encode('utf-16-le')) // 2 > 9000:
                result['failed'] += 1
                result['failures'].append({'event_id': item[0]['id'], 'error_type': 'ValueError', 'error': 'Public event exceeds scoped service read budget'})
                continue
        current.append(item)
    if current:
        batches.append(current)
    for batch in batches:
        content = bundle(batch)
        checksum = hashlib.sha256(content).hexdigest()
        relative = f'memory/partlawyer-public-issues/{checksum}.md'
        path = workspace / relative
        try:
            if not path.parent.resolve().is_relative_to(workspace):
                raise ValueError('Service read-back path escapes public workspace')
            path.parent.mkdir(parents=True, exist_ok=True)
            _immutable_write(path, content, workspace)
            response = _gateway_memory_read(agent, workspace, relative, timeout, profile=profile)
            if not isinstance(response, dict) or not isinstance(response.get('output'), dict):
                raise ValueError('OpenClaw returned a malformed tool response')
            details = response['output'].get('details')
            if not isinstance(details, dict):
                raise ValueError('OpenClaw returned malformed read-back details')
            if (response.get('ok') is not True or response.get('toolName') != 'memory_get'
                    or details.get('status') != 'ok' or details.get('disabled') or details.get('error')
                    or details.get('truncated') or details.get('path') != relative or details.get('from') != 1
                    or details.get('text') != content.decode('utf8').removesuffix('\n')):
                raise ValueError('OpenClaw did not return the exact complete public issue bundle: ' +
                                 str(response.get('error') or details.get('error') or 'content/path/truncation mismatch'))
            evidence = {'schema': 'partlawyer-openclaw-service-proof/v2', 'method': 'tools.invoke', 'tool': 'memory_get', 'agent': agent, 'profile': profile,
                        'path': relative, 'content_sha256': checksum, 'response': response}
            evidence_bytes = _json(evidence)
            proof_relative = f'partlawyer-public-issues/service-readbacks/v2/{profile}/{checksum}.json'
            proof = workspace / proof_relative
            proof.parent.mkdir(parents=True, exist_ok=True)
            _immutable_write(proof, evidence_bytes, workspace)
            if proof.read_bytes() != evidence_bytes:
                raise ValueError('Service read-back evidence could not be persisted exactly')
            receipt = {'kind': 'openclaw_service_readback', 'ok': True,
                       'accepted_event_ids': [item[0]['id'] for item in batch], 'agent': agent, 'profile': profile,
                       'service_acknowledged': True, 'ai_reviewed': False, 'workspace': str(workspace),
                       'content_file': relative, 'content_sha256': checksum,
                       'evidence_file': proof_relative, 'evidence_sha256': hashlib.sha256(evidence_bytes).hexdigest()}
            if record_receipts:
                _service_acknowledge(database, [item[0] for item in batch], receipt)
                result['acknowledged'] += len(batch)
            result['service_verified'] += len(batch)
            result['receipts'].append(receipt)
        except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError) as exc:
            result['failed'] += len(batch)
            result['failures'].append({'event_ids': [item[0]['id'] for item in batch], 'error_type': type(exc).__name__, 'error': str(exc)})
            # Do not repeatedly hammer an unavailable service. Exported rows and
            # earlier proof files remain durable; the next command retries.
            break
    result['pending'] = delivery_summary(database)['pending']
    if result['failed']:
        result['status'] = 'PARTIAL_SERVICE_READBACK'
    elif record_receipts:
        result['status'] = 'ACKNOWLEDGED_OPENCLAW'
    return result
