"""Public release provenance for six exact own-source profiles, fail closed.

Only the supplied release root is read. Providers reconstruct canonical facts
from their already pinned SOURCE-MANIFEST/source-lock bytes. A mutable delivery
allowlist may update code entries, but cannot authorize new evidence, paths or
attachments. This grants public retention only, never generation capability.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from regional_anhui_oct29 import BASE as AH_REPORT, LOCK_SHA, SPECS as AH_SPECS, load_guide
from regional_zhejiang_oct29 import (REPORT as NB_REPORT, MANIFEST_SHA256 as NB_MANIFEST,
                                    SPECS as NB_SPECS, parse_capture as parse_ningbo)
from regional_hunan_oct29b import (REPORT as HN_REPORT, MANIFEST_SHA256 as HN_MANIFEST,
                                  DERIVED_MANIFEST_SHA256, ORIGINAL_SHAS,
                                  SPECS as HN_SPECS, parse_capture as parse_hunan)

_GUIDE_METADATA = {
    'source_id', 'version', 'content_hash', 'region_id', 'can_generate',
    'published', 'publication_status', 'candidate_web_qa', 'warnings',
}
_TEMPLATE_MARKERS = {
    'can_generate', 'document_types', 'adapter', 'content_kind', 'generation_label',
    'source_download_format', 'derived_from_format', 'classification_note',
}
_FAILURES = (ValueError, OSError, KeyError, TypeError, StopIteration, AttributeError)


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _path(root, relative):
    """Resolve only a fixed report-relative path, including symlink containment."""
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Public proof must be relative to the supplied root')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Public proof escapes supplied root')
    return path


def _json(root, relative):
    return json.loads(_path(root, relative).read_text(encoding='utf8'))


def _allowlist(root, report):
    white = _json(root, report + '/PUBLIC-WHITELIST.json')
    if isinstance(white, list):
        rows = {row['file']: row for row in white}
        if len(rows) != len(white):
            raise ValueError('Duplicate public allowlist paths')
    else:
        rows = white['files']
    if not isinstance(rows, dict) or not rows:
        raise ValueError('Missing public delivery allowlist')
    return rows


def _public_file(root, relative, checksum, white, size=None):
    """Caller allowlists cannot override the provider's independently pinned SHA."""
    row = white.get(relative)
    if not isinstance(row, dict) or row.get('sha256') != checksum:
        raise ValueError('Required own source is not approved for public delivery')
    body = _path(root, relative).read_bytes()
    if _sha(body) != checksum or (size is not None and len(body) != size):
        raise ValueError('Public source bytes differ')
    if row.get('bytes', len(body)) != len(body):
        raise ValueError('Public delivery size differs')
    return body


def _template_matches(actual, canonical, region):
    if not isinstance(actual, dict):
        return False
    if 'region_code' in actual and actual['region_code'] != region:
        return False
    ignored = _TEMPLATE_MARKERS | {'region_code'}
    if set(actual) - set(canonical) - ignored:
        return False
    return all(key in actual and actual[key] == value
               for key, value in canonical.items() if key not in _TEMPLATE_MARKERS)


def _guide_matches(guide, canonical):
    ignored = _GUIDE_METADATA | {'templates', 'evidence'}
    if set(guide) - set(canonical) - ignored:
        return False
    if any(key not in guide or guide[key] != value
           for key, value in canonical.items() if key not in ignored):
        return False
    # An omitted evidence field can be restored after export stripping. A supplied
    # field must be canonical; never echo arbitrary caller evidence into a release.
    if 'evidence' in guide and guide['evidence'] != canonical['evidence']:
        return False
    templates = guide.get('templates')
    if not isinstance(templates, list) or len(templates) != len(canonical['templates']):
        return False
    actual = {t['id']: t for t in templates}
    if len(actual) != len(templates):
        return False
    return all(_template_matches(actual.get(t['id']), t, canonical['region_code'])
               for t in canonical['templates'])


def _validated(guide, root):
    if not isinstance(guide, dict) or root is None:
        raise ValueError('An explicit public root and guide are required')
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Public root does not exist')
    province, code = guide.get('province'), guide.get('region_code')
    if province == 'anhui' and code in {s[1] for s in AH_SPECS.values()}:
        name = next(n for n, s in AH_SPECS.items() if s[1] == code)
        report = AH_REPORT.as_posix(); manifest = report + '/source-lock.json'; checksum = LOCK_SHA
        loader = lambda: load_guide(name, root=root)
    elif province == 'zhejiang' and code in {s['code'] for s in NB_SPECS.values()}:
        name = next(n for n, s in NB_SPECS.items() if s['code'] == code)
        report = NB_REPORT; manifest = report + '/SOURCE-MANIFEST.json'; checksum = NB_MANIFEST
        loader = lambda: parse_ningbo(name, capture_root=_path(root, report))
    elif province == 'hunan' and code in {s['code'] for s in HN_SPECS.values()}:
        name = next(n for n, s in HN_SPECS.items() if s['code'] == code)
        report = HN_REPORT; manifest = report + '/SOURCE-MANIFEST.json'; checksum = HN_MANIFEST
        loader = lambda: parse_hunan(name, capture_root=_path(root, report))
    else:
        raise ValueError('No public report contract for this exact profile')
    # Check fixed manifest path containment before a provider can read any bytes.
    white = _allowlist(root, report)
    _public_file(root, manifest, checksum, white)
    canonical = loader()
    if not _guide_matches(guide, canonical):
        raise ValueError('Guide facts, locality or attachment scope differ')
    pins = _json(root, manifest)
    if province != 'anhui':
        pins = {report + '/' + p: value for p, value in pins['files'].items()}
    own_prefix = report + '/' + name + '/'
    own = {p: value for p, value in pins.items() if p.startswith(own_prefix)}
    if not own:
        raise ValueError('Missing own locality proof')
    for relative, pin in own.items():
        expected = pin if isinstance(pin, str) else pin['sha256']
        size = None if isinstance(pin, str) else pin['bytes']
        _public_file(root, relative, expected, white, size)
    return root, report, name, canonical, white


def _hunan_worker_chain(root, report, name, template, white):
    """Verify the public conversion independently; never call ROOT-bound _derived."""
    relative = report + '/DERIVED-MANIFEST.json'
    raw = _public_file(root, relative, DERIVED_MANIFEST_SHA256, white)
    rows = json.loads(raw)['files']
    derived = 'derived/' + name + '/1624951667887.docx'
    own = [row for row in rows if row['district'] == name and row['file'] == derived]
    if len(own) != 1:
        raise ValueError('Missing unique own worker conversion')
    row = own[0]
    source = name + '/originals/blank/1624951667887.doc'
    if (row['source'] != source or template['file'] != report + '/' + source
        or row['source_sha256'] != ORIGINAL_SHAS['1624951667887']
        or row['kind'] != 'platform_conversion_of_own_official_doc_not_official_docx'):
        raise ValueError('Own DOC to platform DOCX conversion chain differs')
    _public_file(root, report + '/' + source, row['source_sha256'], white)
    _public_file(root, report + '/' + derived, row['sha256'], white, row['bytes'])


def public_evidence(guide, root):
    """Return a deep copy of rebuilt safe evidence, or None, using only root.

    Store metadata and capability markers are ignored. Facts, authority,
    materials, sections, source identity, own scope and original bytes must match.
    Legacy/other profiles have no report-path authorization through this helper.
    """
    try:
        _, _, _, canonical, _ = _validated(guide, root)
        return deepcopy(canonical['evidence'])
    except _FAILURES:
        return None


def approved_report_attachment(guide, template, root):
    """Allow an exact own canonical report original, with validated public proof.

    This includes retained official samples for these six profiles only; they
    never gain generation permission. Hunan's supported worker blank additionally
    requires its fixed, public, own-DOC conversion chain. Arbitrary derived paths
    or templates are not accepted as official originals.
    """
    try:
        root, report, name, canonical, white = _validated(guide, root)
        if not isinstance(template, dict):
            return False
        matches = [t for t in canonical['templates'] if t['id'] == template.get('id')]
        if len(matches) != 1 or not _template_matches(template, matches[0], canonical['region_code']):
            return False
        own = matches[0]
        if not own['file'].startswith(report + '/' + name + '/'):
            return False
        _public_file(root, own['file'], own['sha256'], white, own['bytes'])
        if (report == HN_REPORT and own['official_kind'] == 'blank'
            and Path(own['file']).stem == '1624951667887'):
            _hunan_worker_chain(root, report, name, own, white)
        return True
    except _FAILURES:
        return False
