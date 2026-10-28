"""Bounded national public service candidates. Never a guide verification worker.

Default execution is a read-only queue plan. Apply backs up only the public
directory database, claims only service_discovery, and ends jobs in review states.
"""
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

ENDPOINT = 'https://gjzwfw.www.gov.cn/fwmh/item/v3/findItemList.do'
KEYWORDS = ('劳动人事争议仲裁申请', '劳动争议仲裁申请', '劳动仲裁')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def resolve_target(payload):
    """Never guess between old/new provider-qualified directory identities."""
    if not isinstance(payload, dict) or not all(isinstance(payload.get(k), str) and payload[k].strip()
                                               for k in ['province', 'city', 'district']):
        raise ValueError('Exact province/city/district identity is missing')
    identities = []
    if 'provider' in payload or 'code' in payload:
        identities.append((payload.get('provider'), payload.get('code')))
    sources = payload.get('directory_sources', [])
    if not isinstance(sources, list):
        raise ValueError('Directory sources must be an explicit list')
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError('Invalid directory source record')
        identities.append((source.get('provider'), source.get('code')))
    if not identities or any(not all(isinstance(x, str) and x for x in pair) for pair in identities):
        raise ValueError('Explicit provider and code are required')
    if len(set(identities)) != 1:
        raise ValueError('Multiple provider/code identities require manual review; none selected')
    provider, code = identities[0]
    if provider != 'national' or not re.fullmatch(r'\d{6}', code):
        raise ValueError('Unsupported provider or national directory code; no inferred conversion')
    return {**{k: payload[k].strip() for k in ['province', 'city', 'district']}, 'provider': provider, 'code': code}


def classify_response(body, target):
    """Classify metadata as candidates only, even with an explicit own-region field."""
    result = {'state': 'manual_review', 'candidates': [], 'rejected': [], 'absence_verified': False}
    try:
        response = json.loads(body)
    except (ValueError, UnicodeError, TypeError):
        return {**result, 'reason': 'Official response is not a JSON result list'}
    if not isinstance(response, dict):
        return {**result, 'reason': 'Official response has an unexpected structure'}
    result['api_code'] = str(response.get('code'))
    data = response.get('data')
    if response.get('success') is not True or str(response.get('code')) != '200' or not isinstance(data, dict) or not isinstance(data.get('list'), list):
        return {**result, 'reason': 'Official API returned failure or no valid list; this does not prove service absence',
                'api_message': response.get('message')}
    seen = set()
    for row in data['list']:
        if not isinstance(row, dict):
            result['rejected'].append({'reason': 'malformed_record'})
            continue
        title = re.sub(r'\s+', '', re.sub(r'<[^>]*>', '', str(row.get('taskName', ''))))
        if '调解' in title or not re.fullmatch(r'(劳动人事争议仲裁申请|劳动争议仲裁申请)(?:[（(][^）)]{1,60}[）)])?', title):
            result['rejected'].append({'title': row.get('taskName'), 'reason': 'wrong_or_incomplete_service'})
            continue
        task = row.get('taskBlCode') or row.get('taskCode')
        if not isinstance(task, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', task):
            result['rejected'].append({'title': row.get('taskName'), 'reason': 'missing_safe_task_identifier'})
            continue
        # Only explicit response fields count. The query's areaCode is not evidence
        # that the returned record is actually issued by this locality.
        codes = {str(row[k]) for k in ['regionCode', 'areaCode'] if row.get(k) not in (None, '')}
        if codes and codes != {target['code']}:
            result['rejected'].append({'title': row.get('taskName'), 'reason': 'response_region_mismatch', 'response_codes': sorted(codes)})
            continue
        if task in seen:
            continue
        seen.add(task)
        result['candidates'].append({'title': row['taskName'], 'task_code': task, 'record': row,
                                     'candidate_url': 'https://gjzwfw.www.gov.cn/fwmh/item/v3/item_' + task + '.do',
                                     'url_basis': 'published_national_work_js_navigation_pattern_not_browser_verified',
                                     'region_match': 'explicit_match' if codes else 'unverified',
                                     'state': 'needs_browser', 'verification_status': 'unverified',
                                     'source_id': None, 'can_generate': False})
    result.update(state='needs_browser' if result['candidates'] else 'query_miss',
                  reason='Candidates require own-locality native browser and content review' if result['candidates']
                  else 'No exact acceptable candidate in this query; no service-absence conclusion')
    return result


def fetch_public(url, form, timeout):
    """One bounded public POST, with normal TLS verification and no credentials."""
    if url != ENDPOINT:
        raise ValueError('Only the observed official national search endpoint is supported')
    request = Request(url, data=urlencode(form).encode('utf8'),
                      headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urlopen(request, timeout=timeout) as response:
            return {'status': response.status, 'body': response.read(), 'headers': dict(response.headers), 'final_url': response.url}
    except HTTPError as exc:
        return {'status': exc.code, 'body': exc.read(), 'headers': dict(exc.headers), 'final_url': exc.url}


@contextmanager
def exclusive_lock(path):
    """OS-held lock releases on process exit; file existence alone is not a lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('A service-discovery worker already owns the exclusive OS lock') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _pending(path, limit):
    if not path.is_file():
        return []
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        return [{'id': row['id'], 'payload': json.loads(row['payload'])}
                for row in db.execute("SELECT id,payload FROM discovery_jobs WHERE kind='service_discovery' AND state='pending' ORDER BY rowid LIMIT ?", (limit,))]


def _backup(path, folder):
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('regional-directory-' + uuid.uuid4().hex + '.sqlite')
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as source, closing(sqlite3.connect(backup)) as dest:
        source.backup(dest)
    return str(backup.resolve())


def _discover(target, folder, request):
    attempts = []
    candidates = []
    final_reason = 'No acceptable exact service candidate after bounded keyword fallback; not proof of absence'
    for index, keyword in enumerate(KEYWORDS, 1):
        attempt_dir = folder / ('attempt-' + str(index).zfill(2))
        attempt_dir.mkdir(parents=True, exist_ok=True)
        form = {'pageNo': 1, 'pageSize': 10, 'areaCode': target['code'], 'taskName': keyword, 'serverType': 1}
        evidence = {'url': ENDPOINT, 'method': 'POST', 'form': form, 'keyword': keyword, 'requested_at': _now()}
        classified = None
        try:
            response = request(ENDPOINT, form)
            body = response['body']
            if not isinstance(body, bytes):
                raise ValueError('Fetcher must preserve original response bytes')
            raw_path = attempt_dir / 'response.bin'
            raw_path.write_bytes(body)
            evidence.update(collected_at=_now(), http_status=response['status'], final_url=response['final_url'], response_headers=response.get('headers', {}),
                            sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), response_file=str(raw_path.resolve()))
            final_address = urlsplit(response['final_url'])
            if response['status'] != 200 or (final_address.scheme, final_address.hostname, final_address.path) != (
                    'https', 'gjzwfw.www.gov.cn', '/fwmh/item/v3/findItemList.do'):
                raise ValueError('Public endpoint HTTP status or final official origin/path differs')
            classified = classify_response(body, target)
            evidence.update(outcome=classified['state'], rejected=classified['rejected'], api_code=classified.get('api_code'))
        except Exception as exc:
            evidence.update(collected_at=_now(), error=str(exc), outcome='manual_review', no_service_absence_claim=True)
        _save(attempt_dir / 'request.json', evidence)
        attempts.append(evidence)
        if evidence.get('error'):
            final_reason = evidence['error']
            break
        if classified['state'] == 'manual_review':
            final_reason = classified['reason']
            break
        if classified['candidates']:
            candidates = [{**item, 'source_response_file': evidence['response_file'], 'source_response_sha256': evidence['sha256'],
                           'source_url': ENDPOINT, 'collected_at': evidence['collected_at']} for item in classified['candidates']]
            final_reason = classified['reason']
            break
    return {'target': target, 'state': 'needs_browser' if candidates else 'manual_review',
            'reason': final_reason, 'attempts': attempts, 'candidates': candidates,
            'alias_required': bool(candidates) and len(attempts) > 1,
            'guide_verified': False, 'can_generate': False, 'absence_verified': False}


def existing_evidence(root, payload):
    """Exact names only; retained evidence avoids repeated discovery, not review."""
    key=tuple(payload.get(k) for k in ['province','city','district'])
    if not all(isinstance(v,str) and v for v in key):return []
    result=[];dbpath=root/'backend/data/regional-guides.sqlite'
    if dbpath.is_file():
        with closing(sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            rows=db.execute('SELECT payload FROM regional_guides WHERE province=? AND city=? AND district=? AND sequence IN (SELECT sequence FROM regional_current)',key).fetchall()
        for row in rows:
            guide=json.loads(row[0])
            if guide.get('source_id') and guide.get('source_url'):
                result.append({k:guide[k] for k in ['source_id','source_url']})
    from regional_rollout import load_rollout_candidates
    for candidate in load_rollout_candidates(root):
        if tuple(candidate.get(k) for k in ['province','city','district'])==key and candidate.get('source_url'):
            result.append({k:candidate.get(k) for k in ['source_id','source_url']})
    return result


def run_discovery(root, output, *, apply=False, limit=2, delay=2.0, timeout=15.0, fetcher=fetch_public, sleeper=time.sleep):
    """Dry-run by default. Apply mutates only the fixed public queue, under one lock.

    fetcher(url, form, timeout) returns raw bytes/status/final_url/headers; it and
    sleeper are injectable for isolated tests, not alternate production providers.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
        raise ValueError('limit must be an integer from 1 to 10')
    if not 2 <= delay <= 60 or not 1 <= timeout <= 60:
        raise ValueError('delay must be at least 2 seconds; timeout must be 1..60 seconds')
    root = Path(root).resolve(); output = Path(output).resolve()
    if not output.is_relative_to((root / 'reports').resolve()):
        raise ValueError('Public discovery evidence must stay within workspace reports')
    path = root / 'backend/data/regional-directory.sqlite'
    planned = []
    for job in _pending(path, limit):
        try:
            planned.append({'id': job['id'], 'target': resolve_target(job['payload']), 'proposed_state': 'needs_browser_or_manual_review'})
        except ValueError as exc:
            planned.append({'id': job['id'], 'proposed_state': 'manual_review', 'reason': str(exc)})
    result = {'applied': apply, 'planned': planned, 'results': [], 'guide_verified': False,
              'can_generate': False, 'completion_status': 'incomplete', 'started_at': _now()}
    if not apply or not path.is_file():
        return result
    # The lock path is fixed beside the public queue, regardless of output path.
    with exclusive_lock(root / 'backend/data/regional-service-discovery.lock'):
        folder = output / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:10])
        folder.mkdir(parents=True, exist_ok=False)
        result.update(run_folder=str(folder), backup=_backup(path, folder / 'backups'))
        from regional_directory import DirectoryStore
        store = DirectoryStore(path)
        # This fixed OS lock excludes the other consumer of this exact kind.
        # Back up first; recover only our interrupted work, never other kinds.
        store.recover_interrupted('service_discovery')
        request_count = 0

        def request(url, form):
            nonlocal request_count
            if request_count:
                sleeper(delay)
            request_count += 1
            return fetcher(url, form, timeout)

        for _ in range(limit):
            job = store.claim('service_discovery')
            if job is None:
                break
            job_folder = folder / 'jobs' / job['id']
            try:
                retained=existing_evidence(root,job['payload'])
                if retained:
                    discovered={'state':'manual_review','reason':'Exact locality has retained evidence; continue its existing review/adaptation task without rediscovery',
                        'network_skipped':True,'existing_evidence':retained,'attempts':[],'candidates':[],
                        'guide_verified':False,'can_generate':False,'absence_verified':False}
                else:
                    target = resolve_target(job['payload'])
                    discovered = _discover(target, job_folder, request)
            except Exception as exc:
                discovered = {'state': 'manual_review', 'reason': str(exc), 'attempts': [], 'candidates': [],
                              'guide_verified': False, 'can_generate': False, 'absence_verified': False}
            discovered['job_id'] = job['id']
            _save(job_folder / 'result.json', discovered)
            # This public evidence outbox is not sent to any external service.
            if not discovered.get('network_skipped'):
                _save(folder / 'outbox' / (job['id'] + '.json'),
                      {**discovered, 'event': 'SERVICE_DISCOVERY_REVIEW_REQUIRED', 'scope': 'public_candidate_discovery_only',
                       'occurred_at': _now(), 'delivery_status': 'PENDING_OPENCLAW', 'not_a_verified_guide': True})
            store.finish(job['id'], discovered['state'], discovered)
            result['results'].append(discovered)
            _save(folder / 'progress.json', {**result, 'request_count': request_count})
        result.update(finished_at=_now(), request_count=request_count)
        _save(folder / 'result.json', result)
    return result
