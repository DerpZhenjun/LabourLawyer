"""Document adaptation for individually captured Fujian sources using the reviewed layout."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import stat

from hq_phase_proof import strict_json
from hq_word_mechanics import _layout_fill
from regional_fujian_huian_quangang_nov1 import _DocumentBytes, exact, form_fields
from regional_guides import digest, official_content, region_key
from regional_huian_quangang_request import Application, Evidence


ADAPTER = 'fujian_quanzhou_next4_own_api_v1'
PUBLICATION_SHA256 = '5099dede84960def038d59c15ed6bd71bd95e3231eb6733985d563a9713e5149'
STAGE_SHA256 = '6473592bd0f24498e499b1c94da2f224498372bd63de723cf90eb5d4684d12b3'
BROWSER_SHA256 = '71ba37232b2077ce0927f61c64809ca32c51773865424c13cfb2ed4d6d60713a'
STAGE_VERIFIED_AT = '2026-11-08T02:57:48Z'
LOCALITIES = 'reports/overnight-gap-closure-20261030/localities'
BASE = LOCALITIES + '/quanzhou-next4-own-source-projection'
REVIEW_RECEIPT = LOCALITIES + '/quanzhou-next4-word-review/WORD-REVIEW-QUEUE.json'
BROWSER_RECEIPT = LOCALITIES + '/quanzhou-next4-word-review/BROWSER-CANDIDATE.json'
PUBLICATION_RECEIPT = LOCALITIES + '/quanzhou-next4-word-review/FINAL-PUBLICATION.json'
FIXTURES = LOCALITIES + '/fujian-huian-quangang/word-qa-nov1-v1/fixtures'
DY_BASE = LOCALITIES + '/quanzhou-dehua-yongchun-own-source'
DY_STAGE_RECEIPT = DY_BASE + '/WORD-PREFLIGHT.json'
DY_STAGE_SHA256 = 'e5c0a48a53e0b4b96b30f9e8acfd7dc545654e274e9b22a5e5eefa766dc3fa40'
DY_SOURCE_FREEZE_SHA256 = '3eb5d587708c2e420bf91e7320ac4e661215ce6ab26fa7bd3fe1ad8505a57781'
DY_BROWSER_RECEIPT = DY_BASE + '/BROWSER-CANDIDATE.json'
DY_BROWSER_SHA256 = '9669479f5e1e0a7f6f3e5ffef23dbc458efc57bb13080177188b5973ef831f54'
DY_PUBLICATION_RECEIPT = DY_BASE + '/FINAL-PUBLICATION.json'
DY_PUBLICATION_SHA256 = 'c88b22b572422a4630eff6be9c1403eae6296f3daf55b1b377952c4ec18b279c'
INVESTMENT_CODE = '350599'
INVESTMENT_BASE = LOCALITIES + '/quanzhou-investment-zone-own-source'
INVESTMENT_STAGE_RECEIPT = INVESTMENT_BASE + '/WORD-PREFLIGHT.json'
INVESTMENT_STAGE_SHA256 = '60bd331d59be45e072b112a4c63785e98fd293b9e6aa962b8a3646b3c35b9990'
INVESTMENT_SOURCE_FREEZE_SHA256 = '7b752522ecfe5ca30a4ea2a81f6f266777b1f94126b9c45ceea5808fc8fcbba3'
XIANGCHENG_CODE = '350602'
XIANGCHENG_BASE = LOCALITIES + '/zhangzhou-own-source'
XIANGCHENG_STAGE_RECEIPT = XIANGCHENG_BASE + '/WORD-PREFLIGHT.json'
XIANGCHENG_STAGE_SHA256 = '2031524a853e6c2c478478c8314e3d05650778eb340577844fe18030abc85f92'
XIANGCHENG_SOURCE_FREEZE_SHA256 = '4c41d8d1717ffa7d34ba01d2ae7bf6757b169f1d48474d155121aac1a976f21a'
LONGHAI_CODE = '350681'
LONGHAI_BASE = LOCALITIES + '/zhangzhou-longhai-own-source'
LONGHAI_STAGE_RECEIPT = LONGHAI_BASE + '/WORD-PREFLIGHT.json'
LONGHAI_STAGE_SHA256 = '651c28d38274c3837b1f0573fe26143c14f438bdbb36d23decff8a92c093c2a1'
LONGHAI_SOURCE_FREEZE_SHA256 = '12d06ae95b62ae8482f905e05e79b01cf832f527d308cdaf8a2d3ff618009bac'
REGIONS = {
    '350582': {
        'district': '晋江市', 'source_id': 'd8353a4bb91532863fb03802',
        'source_manifest_sha256': '7a4b19e40bd16f66b256d7fc7d0b88d7c05289827feae7df4eb2a05a2048a503',
        'original_kinds': ('application', 'evidence'),
    },
    '350581': {
        'district': '石狮市', 'source_id': 'b954b9477907608d6cf530ed',
        'source_manifest_sha256': '8a63a89cf7048a359eb43495281378da5bd3d00885eedd1bc2e78eba95ec3e2d',
        'original_kinds': ('application',),
    },
    '350583': {
        'district': '南安市', 'source_id': '02b8e589e4891bdcbdacdc09',
        'source_manifest_sha256': '9dd8f9fdf8f88fc781301124ea58d0f67e8f4a4862b2b27bd8a6106f07630213',
        'original_kinds': ('application', 'evidence'),
    },
    '350524': {
        'district': '安溪县', 'source_id': 'ecd5bfaec46d03d4f6ae3860',
        'source_manifest_sha256': 'a3713d78625cc4267c628b5fb70ce3ecdce46005c4314d840560974449601d13',
        'original_kinds': ('application', 'evidence'),
    },
}
DY_REGIONS = {
    '350526': {
        'district': '德化县', 'source_id': '286f2f5801a4ad101b464ff7',
        'source_manifest_sha256': '983353486646af7070909393be75730aa7de42a127dec79e464695878f4605da',
        'original_kinds': ('application', 'evidence'),
    },
    '350525': {
        'district': '永春县', 'source_id': 'dce92327ed30b9ea92994e08',
        'source_manifest_sha256': 'c535d2d00bb7e8a47dfad8d0c368774e607ac4897bd20cfaf04b55d7c162fb30',
        'original_kinds': ('application', 'evidence'),
    },
}
SUPPORTED_REGIONS = {
    **REGIONS,
    **DY_REGIONS,
    INVESTMENT_CODE: {
        'district': '台商投资区', 'source_id': 'cf089c0b9ee9b764b564e269',
        'source_manifest_sha256': '297b56b936b8c43d5598c4fc115c26b881936d21fcd3da08722523ca74319fc2',
        'original_kinds': ('application', 'evidence'),
    },
    XIANGCHENG_CODE: {
        'district': '芗城区', 'source_id': 'f8e8351e86b1c41530f16dec',
        'source_manifest_sha256': 'f00f84d5e6ed1a90e7d064760966c36735950d2e734c2fa6493db2186956ab41',
        'original_kinds': ('application', 'evidence'),
    },
    LONGHAI_CODE: {
        'district': '龙海区', 'source_id': 'ed191bcdf82538767ff7bc25',
        'source_manifest_sha256': '60cb15eedb5f3d3fa70c2cd38037c93ab972e3866f530cf9fb65f6c6251bdafc',
        'original_kinds': ('application', 'evidence'),
    },
}
_CANDIDATE_PREFLIGHTS = {
    INVESTMENT_CODE: (INVESTMENT_BASE, INVESTMENT_STAGE_RECEIPT, INVESTMENT_STAGE_SHA256, INVESTMENT_SOURCE_FREEZE_SHA256),
    XIANGCHENG_CODE: (XIANGCHENG_BASE, XIANGCHENG_STAGE_RECEIPT, XIANGCHENG_STAGE_SHA256, XIANGCHENG_SOURCE_FREEZE_SHA256),
    LONGHAI_CODE: (LONGHAI_BASE, LONGHAI_STAGE_RECEIPT, LONGHAI_STAGE_SHA256, LONGHAI_SOURCE_FREEZE_SHA256),
}
_MODELS = {'application': Application, 'evidence': Evidence}
_FAILURES = (ValueError, OSError, TypeError, KeyError)


def _require(condition):
    if not condition:
        raise ValueError('本区指南或候选文书证明不匹配')


def _read(root, name):
    _require(isinstance(root, (str, Path)) and str(root).strip())
    base = Path(root).absolute()
    relative = PurePosixPath(name)
    _require(name.startswith(LOCALITIES + '/') and relative.as_posix() == name
             and not relative.is_absolute() and '\\' not in name and ':' not in name
             and all(not part.startswith('.') for part in relative.parts))
    path = base / name
    _require(path.is_file() and path.resolve() == path)
    for entry in (path, *path.parents):
        _require(not entry.is_symlink() and not getattr(entry.lstat(), 'st_file_attributes', 0)
                 & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
    return path.read_bytes()


def _source_folder(code):
    _require(type(code) is str and code in SUPPORTED_REGIONS)
    if code in _CANDIDATE_PREFLIGHTS:
        base, *_ = _CANDIDATE_PREFLIGHTS[code]
        return f'{base}/{code}'
    return f'{DY_BASE if code in DY_REGIONS else BASE}/{code}'


def _manifest_path(code):
    return f'{_source_folder(code)}/SOURCE-PROJECTION-MANIFEST.json'


def production_source(code, *, root):
    folder = _source_folder(code)
    profile = SUPPORTED_REGIONS[code]
    manifest_raw = _read(root, _manifest_path(code))
    version = profile['source_manifest_sha256']
    _require(sha256(manifest_raw).hexdigest() == version)
    manifest = strict_json(manifest_raw)
    _require(manifest['region_code'] == code and manifest['source_id'] == profile['source_id'])
    files = {}
    for name, pin in manifest['files'].items():
        raw = _read(root, f'{folder}/{name}')
        _require(len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256'])
        files[name] = raw
    guide = strict_json(files['guide.json'])
    _require(guide['region_code'] == code and guide['district'] == profile['district']
             and guide['source_id'] == profile['source_id']
             and guide['source_id'] == digest(guide['source_url'])[:24]
             and guide['source_url'] == manifest['source_url']
             and guide['published'] is False and guide['can_generate'] is False)
    guide.update(source_version=version, online_entry=None)
    guide['sections'] = {
        'apply_method_raw': strict_json(files['safe-api-getMatterBasicInfo.json'])['data']['applyMethod'],
        'flow_nodes_raw': strict_json(files['safe-api-getFlowNode.json'])['data'],
        'legal_basis_raw': strict_json(files['safe-api-getLegalBasis.json'])['data'],
        'matter_according_raw': strict_json(files['safe-api-getMatterAccording.json'])['data'],
    }
    for field in guide['fields'].values():
        field['source_version'] = version
    for material in guide['materials']:
        material.update(id=material['material_id'], official_material_id=material['material_id'])
    for template in guide['templates']:
        eligible = template['source_original_eligible'] is True
        template.update(region_code=code, original_name=template['official_label'],
                        local_original=template['file'],
                        download_status='downloaded' if eligible else 'not_downloaded')
        if eligible:
            kind = template['eligible_own_kind']
            filename = f'{kind}-format-public-retrieval.docx'
            _require(template['file'] == f'{folder}/{filename}'
                     and sha256(files[filename]).hexdigest() == template['sha256'])
            template['official_kind'] = 'blank'
    _require(sorted(t['eligible_own_kind'] for t in guide['templates'] if t['source_original_eligible'])
             == sorted(profile['original_kinds']))
    guide['channel'].update(raw_value=guide['channel']['handling_form_raw'],
                            online_depth_raw=guide['channel']['depth_raw'],
                            online_status='unverified', entry_check={'status': 'unvisited'})
    return guide


def staged_candidate(code, *, root):
    guide, _ = _staged_guide(code, root=root)
    return guide


def _staged_guide(code, *, root):
    guide = production_source(code, root=root)
    if code in DY_REGIONS:
        return _word_preflight_guide(
            guide, DY_STAGE_RECEIPT, DY_STAGE_SHA256, DY_SOURCE_FREEZE_SHA256, 12, root=root,
        )
    if code in _CANDIDATE_PREFLIGHTS:
        _, receipt, stage_sha, source_sha = _CANDIDATE_PREFLIGHTS[code]
        return _word_preflight_guide(guide, receipt, stage_sha, source_sha, 6, root=root)
    raw = _read(root, REVIEW_RECEIPT)
    _require(sha256(raw).hexdigest() == STAGE_SHA256)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'OFFLINE_PARITY_VERIFIED_REGISTRATION_PENDING'
             and receipt['published'] is False and len(receipt['records']) == 21)
    verified_forms = []
    for template in guide['templates']:
        if not template['source_original_eligible']:
            continue
        kind = template['eligible_own_kind']
        matching = [
            row for row in receipt['records']
            if row['source']['region_code'] == code and row['source']['kind'] == kind
        ]
        _require(len(matching) == 3 and {r['case'] for r in matching} == {'original', 'normal', 'stress'})
        for row in matching:
            binding = row['source']
            _require(binding['source_id'] == guide['source_id']
                     and binding['source_version'] == guide['source_version']
                     and binding['template_sha256'] == template['sha256']
                     and binding['attachment_id'] == template['id']
                     and binding['material_id'] == template['material_id']
                     and binding['public_file_unid'] == template['public_file_unid'])
        template.update(can_generate=True, adapter=ADAPTER, document_types=[kind], generation_mode='blank')
        verified_forms.append({'region_code': code, 'kind': kind, 'source_id': guide['source_id'],
                               'template_id': template['id'], 'sha256': {row['case']: row['sha256'] for row in matching}})
    _mark_candidate(guide, REVIEW_RECEIPT, STAGE_SHA256, STAGE_VERIFIED_AT)
    return guide, verified_forms


def _mark_candidate(guide, receipt, pin, verified_at):
    guide.update(registration_status='CANDIDATE_ONLY', can_generate=True, generation_adapter=ADAPTER,
                 verified_at=verified_at, publication_status='candidate',
                 candidate_adapter_evidence={'file': receipt, 'sha256': pin})


def _word_preflight_guide(guide, receipt_path, receipt_sha, source_freeze_sha, case_count, *, root):
    raw = _read(root, receipt_path)
    _require(sha256(raw).hexdigest() == receipt_sha)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'OWN_ORIGINALS_AND_TEST_LAYOUTS_BYTE_EQUIVALENT'
             and receipt['source_freeze_sha256'] == source_freeze_sha
             and receipt['published'] is False and receipt['adapter_registered'] is False
             and receipt['web_accepted'] is False and len(receipt['records']) == case_count)
    forms = []
    for template in guide['templates']:
        if not template['source_original_eligible']:
            continue
        kind = template['eligible_own_kind']
        matches = [row for row in receipt['records']
                   if row['region_code'] == guide['region_code'] and row['kind'] == kind]
        _require(len(matches) == 3 and {row['case'] for row in matches} == {'original', 'normal', 'stress'})
        _require(all(row['source_id'] == guide['source_id'] and row['attachment_id'] == template['id']
                     and row['template_sha256'] == template['sha256'] for row in matches))
        _require(next(row['sha256'] for row in matches if row['case'] == 'original') == template['sha256'])
        template.update(can_generate=True, adapter=ADAPTER, document_types=[kind], generation_mode='blank')
        forms.append({'region_code': guide['region_code'], 'kind': kind, 'source_id': guide['source_id'],
                      'template_id': template['id'], 'sha256': {row['case']: row['sha256'] for row in matches}})
    _mark_candidate(guide, receipt_path, receipt_sha, receipt['verified_at'])
    return guide, forms


def published_guide(code, *, root):
    _require(type(code) is str and (code in REGIONS or code in DY_REGIONS))
    if code in DY_REGIONS:
        return _dy_published_guide(code, root=root)
    _require(PUBLICATION_SHA256 is not None)
    raw = _read(root, PUBLICATION_RECEIPT)
    _require(sha256(raw).hexdigest() == PUBLICATION_SHA256)
    _require(sha256(_read(root, BROWSER_RECEIPT)).hexdigest() == BROWSER_SHA256)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'INDEPENDENT_NATIVE_AND_WORD_PARITY_APPROVED'
             and receipt['schema_version'] == 1 and receipt['stage_sha256'] == STAGE_SHA256
             and receipt['browser_sha256'] == BROWSER_SHA256
             and receipt['source_manifests'] == {c: p['source_manifest_sha256'] for c, p in REGIONS.items()}
             and receipt['browser_downloads'] == 14 and receipt['word_cases'] == 21
             and receipt['viewports'] == 21 and receipt['cancellations'] == 7
             and receipt['stone_evidence_enabled'] is False and len(receipt['forms']) == 7)
    return _promote_reviewed(code, receipt, PUBLICATION_RECEIPT, PUBLICATION_SHA256, root=root)


def _dy_published_guide(code, *, root):
    _require(DY_PUBLICATION_SHA256 is not None)
    raw = _read(root, DY_PUBLICATION_RECEIPT)
    _require(sha256(raw).hexdigest() == DY_PUBLICATION_SHA256)
    _require(sha256(_read(root, DY_BROWSER_RECEIPT)).hexdigest() == DY_BROWSER_SHA256)
    receipt = strict_json(raw)
    _require(receipt['state'] == 'INDEPENDENT_NATIVE_AND_WORD_PARITY_APPROVED'
             and receipt['schema_version'] == 1 and receipt['stage_sha256'] == DY_STAGE_SHA256
             and receipt['browser_sha256'] == DY_BROWSER_SHA256
             and receipt['source_manifests'] == {c: p['source_manifest_sha256'] for c, p in DY_REGIONS.items()}
             and receipt['browser_downloads'] == 8 and receipt['word_cases'] == 12
             and receipt['viewports'] == 12 and receipt['cancellations'] == 4 and len(receipt['forms']) == 4)
    return _promote_reviewed(code, receipt, DY_PUBLICATION_RECEIPT, DY_PUBLICATION_SHA256, root=root)


def _promote_reviewed(code, receipt, file, pin, *, root):
    guide, verified_forms = _staged_guide(code, root=root)
    approved_forms = [form for form in receipt['forms'] if form['region_code'] == code]
    _require(exact(sorted(approved_forms, key=lambda form: form['kind']),
                   sorted(verified_forms, key=lambda form: form['kind'])))
    guide.update(published=True, publication_status='published', registration_status='OWN_FORM_APPROVED',
                 verified_at=receipt['reviewed_at'],
                 publication_adapter_evidence={'file': file, 'sha256': pin})
    return guide


def _evidence(code):
    return {'source_projection': _manifest_path(code),
            'source_projection_sha256': SUPPORTED_REGIONS[code]['source_manifest_sha256']}


def _bound(guide, *, root, stage_required):
    _require(type(guide) is dict)
    code = guide.get('region_code')
    if stage_required:
        _require(guide.get('can_generate') is True)
    if guide.get('published') is True:
        canonical = published_guide(code, root=root)
    elif guide.get('can_generate') is True:
        canonical = staged_candidate(code, root=root)
    else:
        canonical = production_source(code, root=root)
    data = {k: v for k, v in guide.items() if k not in {'version', 'region_id', 'content_hash', 'evidence'}}
    _require(exact(data, canonical))
    if 'version' in guide:
        _require(type(guide['version']) is int and guide['version'] > 0)
    if 'region_id' in guide:
        _require(guide['region_id'] == region_key(canonical['province'], canonical['city'], canonical['district']))
    if 'content_hash' in guide:
        _require(guide['content_hash'] == digest(official_content(canonical)))
    if 'evidence' in guide:
        _require(exact(guide['evidence'], _evidence(code)))
    return canonical


def with_capabilities(guide, *, root):
    _bound(guide, root=root, stage_required=False)
    return guide


def public_evidence(guide, root):
    try:
        canonical = _bound(guide, root=root, stage_required=False)
        return _evidence(canonical['region_code'])
    except _FAILURES:
        return None


def approved_report_attachment(guide, template, root):
    try:
        canonical = _bound(guide, root=root, stage_required=False)
        return any(t['source_original_eligible'] and exact(t, template) for t in canonical['templates'])
    except _FAILURES:
        return False


def checked_adapter(guide, template, kind, *, root):
    canonical = _bound(guide, root=root, stage_required=True)
    _require(any(t['can_generate'] and t['eligible_own_kind'] == kind and exact(t, template)
                 for t in canonical['templates']))
    return ADAPTER


def production_schema_descriptor(code, kind):
    _require(type(code) is str and code in SUPPORTED_REGIONS and kind in SUPPORTED_REGIONS[code]['original_kinds'])
    # Only the independently verified geometry is shared across the official originals.
    labels = {
        'applicantName': '申请人', 'agentName': '委托代理人', 'respondentName': '被申请人',
        'requests': '仲裁请求', 'factsReason': '事实和理由', 'evidenceList': '证据清单',
        'name': '证据名称', 'pageCount': '页数', 'originalType': '原件或复印件',
        'purpose': '证明对象', 'pageRange': '页码',
    }
    fields = form_fields(kind)
    for field in fields:
        field['label'] = labels[field['key']]
        for column in field.get('fields', []):
            column['label'] = labels[column['key']]
    return {
        'schema_id': f'fujian-quanzhou-own-{code}-{kind}-v1',
        'schema_version': 1,
        'source_version': SUPPORTED_REGIONS[code]['source_manifest_sha256'],
        'fields': fields,
        'defaults': _MODELS[kind]().model_dump(),
        'policy': {
            'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
            'trim_text': True, 'capacity_is_official_requirement': False,
            'capacity_is_legal_requirement': False, 'committee_autofill_allowed': False,
            'signature_date_copies_fields': 'not_accepted',
        },
    }


def fill_document(guide, template, kind, path, data, *, root):
    checked_adapter(guide, template, kind, root=root)
    _require(Path(path).resolve() == (Path(root) / template['file']).resolve())
    raw = _read(root, template['file'])
    _require(sha256(raw).hexdigest() == template['sha256'])
    parsed = _MODELS[kind].model_validate(data, strict=True).model_dump()
    return _DocumentBytes(_layout_fill(raw, kind, parsed), root)
