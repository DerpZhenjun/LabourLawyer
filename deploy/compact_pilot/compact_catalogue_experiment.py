"""Verify a private projection from an externally supplied file inventory digest."""

from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re
from urllib.parse import parse_qsl, urlsplit

from compact_contract_experiment import LocalContractProof
from compact_proof_experiment import HEX64, object_without_duplicates

_BASE = {'CAPSULE.json', 'CONTRACTS.json', 'GUIDES.json', 'AREAS.json'}
DERIVATIVE_MANIFEST = 'LAYOUT-PROOF.json'
MANIFEST = 'INVENTORY.json'
_REQUIRED_PROVINCES = {'jiangsu': 6, 'fujian': 6, 'zhejiang': 6}
_SAFE_QUERY = {'webId', 'iddept_ql_inf', 'ql_kind', 'iddept_yw_inf', 'unid', 'infoType'}


def digest(body):
    return sha256(body).hexdigest()


def parse(body):
    return json.loads(body, object_pairs_hook=object_without_duplicates)


def public_source(value):
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not (parts.hostname or '').endswith('.gov.cn')
            or parts.username or parts.password or parts.port is not None
            or not set(k for k, _ in parse_qsl(parts.query, keep_blank_values=True)).issubset(_SAFE_QUERY)):
        raise ValueError('Unexpected official guide URL')
    if parts.fragment:
        fragment = urlsplit(parts.fragment)
        keys = parse_qsl(fragment.query, keep_blank_values=True)
        if (parts.hostname != 'www.zjzwfw.gov.cn' or parts.path != '/zjservice-fe/'
                or fragment.path != '/workguide' or fragment.fragment or len(keys) != 1
                or keys[0][0] != 'localInnerCode' or not re.fullmatch('[A-Za-z0-9_-]{1,96}', keys[0][1])):
            raise ValueError('Unexpected official guide fragment')
    return value


def load(root, manifest_pin):
    root = Path(root).resolve()
    manifest_path = root / MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('Missing pinned inventory')
    manifest_body = manifest_path.read_bytes()
    if not isinstance(manifest_pin, str) or not HEX64.fullmatch(manifest_pin) or digest(manifest_body) != manifest_pin:
        raise ValueError('Projected inventory digest differs')
    manifest = parse(manifest_body)
    if not isinstance(manifest, dict) or set(manifest) != {'scope', 'schema', 'files'}:
        raise ValueError('Unknown projection manifest shape')
    source_scope = manifest['scope']
    if source_scope not in {'PRIVATE_PILOT_DATA_ONLY', 'PRIVATE_PILOT_SANITIZED_DATA_ONLY'} or manifest['schema'] != 1:
        raise ValueError('Unknown projection manifest version')
    sanitized = source_scope == 'PRIVATE_PILOT_SANITIZED_DATA_ONLY'
    base = _BASE | {DERIVATIVE_MANIFEST} if sanitized else _BASE
    layout_directory = 'layouts' if sanitized else 'originals'
    files = manifest['files']
    if not isinstance(files, dict) or not base.issubset(files) or len(files) != len(base) + 6:
        raise ValueError('Unexpected projection inventory')
    expected_documents = files.keys() - base
    if any(not re.fullmatch(rf'{layout_directory}/[a-f0-9]{{64}}\.docx', p) for p in expected_documents):
        raise ValueError('Unexpected original file name')
    assets = {}
    found = {path.relative_to(root).as_posix() for path in root.iterdir()}
    if found != base | {MANIFEST, layout_directory}:
        raise ValueError('Unexpected projection path')
    original_root = root / layout_directory
    if original_root.is_symlink() or not original_root.is_dir() or original_root.resolve().parent != root:
        raise ValueError('Unsafe originals directory')
    found = {path.relative_to(root).as_posix() for path in original_root.iterdir()}
    if found != expected_documents:
        raise ValueError('Unexpected projection original')
    for relative, expected in files.items():
        path = root / relative
        parent = root if relative in base else original_root
        if path.is_symlink() or not path.is_file() or path.resolve().parent != parent:
            raise ValueError('Unsafe projection file')
        body = path.read_bytes()
        if expected != digest(body) or (relative not in base and path.stem != expected):
            raise ValueError('Projected file hash differs')
        if relative in base:
            assets[relative] = body
    args = (original_root, assets['CAPSULE.json'], files['CAPSULE.json'],
            assets['CONTRACTS.json'], files['CONTRACTS.json'])
    layout_hash = None
    if sanitized:
        from compact_sanitized_layout_experiment import SanitizedContractProof
        proof = SanitizedContractProof(*args, assets[DERIVATIVE_MANIFEST], files[DERIVATIVE_MANIFEST])
        layout_hash = proof.derivative_sha256
    else:
        proof = LocalContractProof(*args)
    bindings = parse(assets['CAPSULE.json'])['rows']
    source_hashes = {binding['original_sha256'] for binding in bindings}
    admitted_hashes = {layout_hash(sha) for sha in source_hashes} if sanitized else source_hashes
    if {f'{layout_directory}/{sha}.docx' for sha in admitted_hashes} != expected_documents:
        raise ValueError('Document inventory differs from the bindings')
    guides = parse(assets['GUIDES.json'])
    areas = parse(assets['AREAS.json'])
    verify_catalogue(proof, bindings, guides, areas, layout_hash=layout_hash)
    return proof, bindings, guides, areas


def labels(row):
    return tuple(row[field] for field in ('province', 'city', 'district'))


def verify_catalogue(proof, bindings, guides, areas, *, layout_hash=None):
    if (len(bindings) != 36 or len(guides) != 18
            or Counter(g['province'] for g in guides) != _REQUIRED_PROVINCES
            or len({labels(guide) for guide in guides}) != 18):
        raise ValueError('Unexpected locality cohort')
    scope_map = {(binding['region_code'], binding['kind']): binding for binding in bindings}
    codes = {g['region_code'] for g in guides}
    if {code for code, _ in scope_map} != codes:
        raise ValueError('Guide and proof locality cohorts differ')
    for guide in guides:
        public_source(guide['source_url'])
        if digest(json.dumps(guide['source_url'], ensure_ascii=False).encode())[:24] != guide['source_id']:
            raise ValueError('Guide URL identity differs from pinned source ID')
        if len(guide['templates']) != 2 or not guide['materials']:
            raise ValueError('Missing scoped materials or form types')
        kinds = set()
        for template in guide['templates']:
            kind, = template['document_types']
            kinds.add(kind)
            binding = scope_map[(guide['region_code'], kind)]
            contract, _ = proof.read(binding)
            official_sha = binding['original_sha256']
            expected_sha = official_sha if layout_hash is None else layout_hash(official_sha)
            if layout_hash is not None and (template.get('official_sha256') != official_sha
                    or template.get('file_origin') != 'official-blank-metadata-sanitized-layout'
                    or template.get('generation_origin') != 'official-blank-metadata-sanitized-filled'):
                raise ValueError('Guide does not distinguish the official original from its derived layout')
            if (template['id'] != binding['template_id'] or template['sha256'] != expected_sha
                    or template['source_url'] != guide['source_url']
                    or template['official_kind'] != 'blank' or template['can_generate'] is not True
                    or template['region_code'] != guide['region_code'] or template['download_status'] != 'downloaded'
                    or template['adapter'] != contract['context']['adapter']
                    or guide['source_id'] != binding['source_id'] or guide['version'] != binding['version']
                    or labels(guide) != labels(contract['context'])):
                raise ValueError('Guide-to-form contract differs')
        if kinds != {'application', 'evidence'}:
            raise ValueError('Missing verified form kind')
    if len(areas) != 29 or len({row['code'] for row in areas}) != 29:
        raise ValueError('Unexpected directory inventory')
    district_rows = [row for row in areas if row['level'] == 4]
    geographic_lookup = {(guide['region_code'], labels(guide)) for guide in guides}
    if {(row['code'], labels(row)) for row in district_rows} != geographic_lookup:
        raise ValueError('Guide locality does not match the official directory')
    area_codes = {row['code']: row for row in areas}
    for row in areas:
        if row['level'] == 2:
            continue
        parent = area_codes.get(row['parent_code'])
        if (not parent or parent['level'] != row['level'] - 1 or parent['province'] != row['province']
                or (row['level'] == 4 and parent['city'] != row['city'])):
            raise ValueError('Area has no matching parent')
