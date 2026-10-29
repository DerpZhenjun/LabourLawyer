"""Public proof for exactly C4; reads only the caller's explicit release root."""
from copy import deepcopy
import json
from pathlib import Path

import regional_hunan_oct29c as hn
import regional_jiangsu_oct29c as js
from regional_public_provenance import (_allowlist, _path, _public_file, _sha, _FAILURES)

JS_WHITELIST_SHA256 = '780929cfdea33b89899bf06f43cbc51249b831fb134bafff05c8d6a4d9237f07'
GUIDE_METADATA = {'version', 'content_hash', 'region_id', 'can_generate', 'published',
                  'publication_status', 'candidate_web_qa', 'warnings'}
CAPABILITY_MARKERS = {'can_generate', 'document_types', 'adapter', 'content_kind',
                      'generation_label', 'source_download_format', 'derived_from_format',
                      'classification_note', 'generation_adapter', 'strict_binding',
                      'generation_mode', 'content_verification_status', 'render_status'}


def handles(guide):
    return isinstance(guide, dict) and isinstance(guide.get('region_code'), str) and (
        (guide.get('province') == 'jiangsu' and guide.get('region_code') in js.SUPPORTED) or
        (guide.get('province') == 'hunan' and guide.get('region_code') in {s['code'] for s in hn.SPECS.values()}))


def _template_matches(actual, canonical, capable, code, adapter):
    if not isinstance(actual, dict):
        return False
    allowed = dict(capable)
    if capable.get('can_generate'):
        allowed['generation_adapter'] = adapter
    # A store may annotate the district on templates that originally omit it.
    allowed['region_code'] = code
    for key, expected in canonical.items():
        if key not in actual:
            return False
        if actual[key] != expected and (key not in CAPABILITY_MARKERS or key not in allowed or actual[key] != allowed[key]):
            return False
    for key in set(actual) - set(canonical):
        if key not in allowed or actual[key] != allowed[key]:
            return False
    return True


def _guide_matches(guide, canonical, capable, adapter):
    ignored = GUIDE_METADATA | {'templates', 'evidence', 'generation_adapter'}
    if set(guide) - set(canonical) - ignored:
        return False
    if any(guide.get(k) != v for k, v in canonical.items() if k not in ignored):
        return False
    if 'generation_adapter' in guide and guide['generation_adapter'] not in {canonical.get('generation_adapter'), adapter}:
        return False
    if 'evidence' in guide and guide['evidence'] != canonical['evidence']:
        return False
    templates = guide.get('templates')
    if not isinstance(templates, list) or len(templates) != len(canonical['templates']):
        return False
    actual = {t['id']: t for t in templates}
    if len(actual) != len(templates):
        return False
    enhanced = {t['id']: t for t in capable['templates']}
    return all(_template_matches(actual.get(t['id']), t, enhanced[t['id']], canonical['region_code'], adapter)
               for t in canonical['templates'])


def _hunan_chain(root, name, canonical, source_white):
    """Pin the own DOC and exact public conversion before ROOT-bound providers run."""
    report = hn.ADAPTATION
    white = _allowlist(root, report)
    relative = report + '/DERIVED-MANIFEST.json'
    raw = _public_file(root, relative, hn.DERIVED_MANIFEST_SHA256, white)
    rows = json.loads(raw)['files']
    own = [r for r in rows if r['district'] == name]
    if len(own) != 1:
        raise ValueError('Missing unique C own worker conversion')
    row = own[0]
    originals = [t for t in canonical['templates'] if t['official_kind'] == 'blank' and t['sha256'] == hn.WORKER_SHA]
    if (len(originals) != 1 or row['source'] != originals[0]['file'] or row['source_sha256'] != hn.WORKER_SHA
            or row['file'] != report + '/derived/' + name + '/worker.docx'
            or row['kind'] != 'platform_conversion_of_own_official_doc_not_official_docx'):
        raise ValueError('C own DOC conversion scope differs')
    _public_file(root, row['source'], hn.WORKER_SHA, source_white, originals[0]['bytes'])
    _public_file(root, row['file'], row['sha256'], white)


def _validated(guide, root):
    if not handles(guide) or root is None:
        raise ValueError('Exact C4 profile and explicit public root required')
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Public root does not exist')
    if guide['province'] == 'jiangsu':
        name = js.SPECS[guide['region_code']]['name']; report = js.REPORT.as_posix()
        manifest_sha = js.MANIFEST_SHA; white_sha = JS_WHITELIST_SHA256; adapter = js.ADAPTER
        loader = lambda: js.parse_capture(guide['region_code'], capture_root=_path(root, report))
        def enhancer(g):
            result = js.with_capabilities(g, root=root)
            for template in result['templates']:
                if template.get('can_generate'):
                    template.update(adapter=js.ADAPTER, content_kind='filled_official_blank',
                                    generation_label='依据本区自身官方空白表格填写')
            return result
    else:
        name = next(n for n, s in hn.SPECS.items() if s['code'] == guide['region_code'])
        report = hn.REPORT; manifest_sha = hn.MANIFEST_SHA256; white_sha = hn.WHITELIST_SHA256; adapter = hn.ADAPTER
        loader = lambda: hn.parse_capture(name, capture_root=_path(root, report))
        enhancer = lambda g: hn.with_capabilities(g, root=root)
    # Fixed source allowlists cannot be expanded to distribute omitted samples.
    if _sha(_path(root, report + '/PUBLIC-WHITELIST.json').read_bytes()) != white_sha:
        raise ValueError('Sealed C source public whitelist differs')
    white = _allowlist(root, report)
    manifest_path = report + '/SOURCE-MANIFEST.json'
    raw = _public_file(root, manifest_path, manifest_sha, white)
    pins = json.loads(raw)['files']
    own = {p: pin for p, pin in pins.items() if p.startswith(name + '/')}
    if not own:
        raise ValueError('Missing C own public source pins')
    # Resolve every own file before invoking a provider, including symlinks.
    for relative, pin in own.items():
        _public_file(root, report + '/' + relative, pin['sha256'], white, pin['bytes'])
    canonical = loader()
    if guide['province'] == 'hunan':
        _hunan_chain(root, name, canonical, white)
    capable = enhancer(canonical)
    if not _guide_matches(guide, canonical, capable, adapter):
        raise ValueError('C guide facts or exact capability annotations differ')
    return root, report, name, canonical, capable, white, adapter


def public_evidence(guide, root):
    try:
        _, _, _, canonical, _, _, _ = _validated(guide, root)
        return deepcopy(canonical['evidence'])
    except _FAILURES:
        return None


def approved_report_attachment(guide, template, root):
    try:
        root, report, name, canonical, capable, white, adapter = _validated(guide, root)
        if not isinstance(template, dict):
            return False
        matches = [t for t in canonical['templates'] if t['id'] == template.get('id')]
        if len(matches) != 1:
            return False
        own = matches[0]; enhanced = next(t for t in capable['templates'] if t['id'] == own['id'])
        if not _template_matches(template, own, enhanced, canonical['region_code'], adapter):
            return False
        if canonical['province'] == 'jiangsu' and (own['official_kind'] == 'sample' or own['download_status'] == 'reference_sample_not_distributed'):
            return False
        if not own['file'].startswith(report + '/' + name + '/'):
            return False
        _public_file(root, own['file'], own['sha256'], white, own['bytes'])
        return True
    except _FAILURES:
        return False
