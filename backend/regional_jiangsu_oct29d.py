"""Own-source Suzhou D blank forms; no private samples or cross-region rules."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from regional_guides import digest
from regional_documents import PreservedPackageDocument
from WenShu.exact_template_fill import fill_application, fill_evidence
from WenShu.template_fill import replace_span

ROOT = Path(__file__).resolve().parents[1]
REPORT = Path('reports/nationwide-verification-20261029-d/jiangsu')
ADAPTER = 'jiangsu_own_blank_oct29d_v1'
SUPPORTED = frozenset({'320508', '320506'})
MANIFEST_SHA = '3b151169273cde16c4005035820301024a050897e7ebc5e6fb62f469f1a29ae3'
WHITELIST_SHA = '9280f4355e54f1ca500201c65ed306a0f48cf09beb6d21df7e9c9660a9314305'
SPECS = {
    '320508': dict(name='gusu', district='姑苏区',
        authority='姑苏区、保护区人力资源和社会保障局',
        task='11320508014152478Y400201430200201', webId='26',
        application='1b87480c-8cd3-4bfa-8721-7dbe5255db5b', evidence='2d48f730-b996-4ec0-9550-548ad0cd761e',
        guide_sha='10112e6c6c377bc71e24c3d29646e945a296520b0a2f4e9a7eac722e6d9d6d28'),
    '320506': dict(name='wuzhong', district='吴中区', authority='苏州市吴中区人力资源和社会保障局',
        task='11320506552548402T400201430200201', webId='27',
        application='50de5e3d-c904-45a5-b077-b2d8a9c2b88a', evidence='9f35ddb0-8c4a-4fdb-96ab-738cc09dab27',
        guide_sha='3dffd181abd146f83e3fb751a5079424b5a3d3f5d0dcf1df8714140cc4e2c24b'),
}
# Source fields are immutable; lifecycle/QA/capability annotations can evolve.
SOURCE_KEYS = ('province', 'province_name', 'city', 'district', 'region_code', 'service_name',
               'service_code', 'authority', 'source_url', 'source_title', 'source_type',
               'fields', 'materials', 'sections', 'scope_identity', 'evidence', 'channel',
               'online_boundary', 'source_issues', 'attachment_counts')
TEMPLATE_KEYS = ('id', 'annex_id', 'region_code', 'material_id', 'official_kind', 'original_name',
                 'source_url', 'download_url', 'file', 'file_type', 'sha256', 'bytes',
                 'download_status', 'public_release_status', 'content_role')


def _read_checked(path, checksum, boundary=None):
    path = Path(path).resolve()
    if boundary is not None and not path.is_relative_to(Path(boundary).resolve()):
        raise ValueError('自身公开证据路径超出给定根目录')
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('自身公开来源或原件不可用') from exc
    if hashlib.sha256(raw).hexdigest() != checksum:
        raise ValueError('自身公开来源或原件SHA不匹配')
    return raw


def _baseline(code, report_root):
    spec = SPECS.get(str(code))
    if spec is None:
        raise ValueError('不是本批姑苏或吴中自身指南')
    report_root = Path(report_root).resolve()
    manifest = json.loads(_read_checked(report_root / 'SOURCE-MANIFEST.json', MANIFEST_SHA, report_root))
    white = json.loads(_read_checked(report_root / 'PUBLIC-WHITELIST.json', WHITELIST_SHA, report_root))['files']
    guide_path = f"{spec['name']}/guide.json"
    if manifest['files'][guide_path]['sha256'] != spec['guide_sha']:
        raise ValueError('固定来源清单与指南不一致')
    if white[REPORT.as_posix() + '/' + guide_path] != manifest['files'][guide_path]:
        raise ValueError('自身指南不在冻结公开清单')
    g = json.loads(_read_checked(report_root / guide_path, spec['guide_sha'], report_root))
    expected = dict(region_code=code, district=spec['district'], city='苏州市', province='jiangsu',
                    authority=spec['authority'], service_code=spec['task'],
                    service_name='劳动人事争议仲裁申请', source_title='劳动人事争议仲裁申请')
    if any(g.get(k) != v for k, v in expected.items()):
        raise ValueError('固定指南自身身份不匹配')
    # Independently hash only public captures referenced by this exact guide.
    captures = [(g['evidence']['capture_file'], g['evidence']['capture_sha256']),
                (g['evidence']['search_capture_file'], g['evidence']['search_capture_sha256'])]
    captures.extend((m['detail_capture'], m['detail_capture_sha256']) for m in g['materials'])
    for source_file, checksum in captures:
        relative = Path(source_file).relative_to(REPORT)
        if manifest['files'][relative.as_posix()]['sha256'] != checksum:
            raise ValueError('自身控件或材料详情捕获绑定不匹配')
        if white[REPORT.as_posix() + '/' + relative.as_posix()] != manifest['files'][relative.as_posix()]:
            raise ValueError('自身控件或材料证据不在冻结公开清单')
        _read_checked(report_root / relative, checksum, report_root)
    g['source_id'] = digest(g['source_url'])[:24]
    return g


def parse_capture(code_or_name, capture_root=None):
    """Read frozen own public capture. capture_root is the sealed jiangsu directory."""
    key = str(code_or_name)
    code = next((c for c, s in SPECS.items() if key in {c, s['district'], s['name']}), None)
    return _baseline(code, Path(capture_root) if capture_root is not None else ROOT / REPORT)


def _validate_guide(guide, root=None, allow_missing_evidence=False):
    root = Path(root if root is not None else ROOT).resolve()
    if not (root / REPORT).resolve().is_relative_to(root):
        raise ValueError('自身公开来源目录超出给定根目录')
    baseline = _baseline(guide.get('region_code'), root / REPORT)
    keys = [k for k in SOURCE_KEYS if not (allow_missing_evidence and k == 'evidence' and k not in guide)]
    if guide.get('source_id') != baseline['source_id'] or any(guide.get(k) != baseline.get(k) for k in keys):
        raise ValueError('自身地区、指南字段、材料或来源控件绑定不匹配')
    if guide.get('verification_status') not in {'partial', 'verified', 'conflict'}:
        raise ValueError('自身指南尚未核验')
    actual = guide.get('templates', [])
    if len(actual) != len(baseline['templates']) or len({t.get('id') for t in actual}) != len(actual):
        raise ValueError('自身附件缺失或重复')
    for expected in baseline['templates']:
        matches = [t for t in actual if t.get('id') == expected['id']]
        if len(matches) != 1 or any(matches[0].get(k) != expected.get(k) for k in TEMPLATE_KEYS):
            raise ValueError('自身附件原始类别、材料、SHA或下载路径不匹配')
        if not _template_annotations_match(matches[0], expected, guide['region_code']):
            raise ValueError('自身附件事实或精确平台能力标记不匹配')
    return baseline, root


def _source(guide, kind, root=None):
    if kind not in {'application', 'evidence'}:
        raise ValueError('仅申请书与证据清单完成填写适配')
    baseline, root = _validate_guide(guide, root)
    annex = SPECS[guide['region_code']][kind]
    template = next(t for t in baseline['templates'] if t['id'] == annex)
    if template['official_kind'] != 'blank' or template['download_status'] != 'downloaded':
        raise ValueError('只允许自身已下载空白原件')
    path = (root / template['file']).resolve()
    if not path.is_relative_to((root / REPORT).resolve()):
        raise ValueError('自身原件超出公开来源目录')
    original = _read_checked(path, template['sha256'], root)
    return template, path, original


def blank_binding(guide, template, root=None):
    kind = next((k for k in ('application', 'evidence')
                 if SPECS.get(guide.get('region_code'), {}).get(k) == template.get('id')), None)
    if kind is None:
        raise ValueError('样例或占位材料不支持填写')
    expected, _, _ = _source(guide, kind, root)
    if any(template.get(k) != expected.get(k) for k in TEMPLATE_KEYS) or not _template_annotations_match(template, expected, guide['region_code']):
        raise ValueError('传入附件与自身空白绑定不一致')
    return _binding(expected, kind)


def _binding(template, kind):
    return {'adapter': ADAPTER, 'kind': kind, 'annex_id': template['id'],
            'source_sha256': template['sha256'], 'source_file': template['file'],
            'source_url': template['source_url']}


def _template_annotations_match(actual, canonical, code):
    if not isinstance(actual, dict):
        return False
    kind = next((k for k in ('application', 'evidence') if SPECS[code][k] == canonical['id']), None)
    markers = {'can_generate': bool(kind), 'document_types': [kind] if kind else []}
    if kind:
        markers.update(generation_adapter=ADAPTER, strict_binding=_binding(canonical, kind), generation_mode='blank',
                       content_verification_status='own_blank_and_synthetic_output_all_pages_viewed', render_status='PASS',
                       adapter=ADAPTER, content_kind='filled_official_blank', generation_label='依据本区自身官方空白表格填写')
    for key, value in canonical.items():
        if key not in actual or (actual[key] != value and (key not in markers or actual[key] != markers[key])):
            return False
    return all(key in markers and actual[key] == markers[key] for key in set(actual) - set(canonical))


def candidate_contract(guide, root=None):
    documents = {}
    for kind in ('application', 'evidence'):
        template, _, _ = _source(guide, kind, root)
        documents[kind] = blank_binding(guide, template, root)
    return {'adapter': ADAPTER, 'region_code': guide['region_code'], 'province': guide['province'],
            'city': guide['city'], 'district': guide['district'], 'source_id': guide['source_id'],
            'authority': guide['authority'], 'service_code': guide['service_code'],
            'documents': documents, 'scope': 'own_official_blank_only'}


def with_capabilities(guide, root=None):
    contract = candidate_contract(guide, root)
    result = deepcopy(guide)
    bindings = {v['annex_id']: (k, v) for k, v in contract['documents'].items()}
    for template in result['templates']:
        kind, binding = bindings.get(template['id'], (None, None))
        template['can_generate'] = bool(kind)
        template['document_types'] = [kind] if kind else []
        if kind:
            template['generation_adapter'] = ADAPTER
            template['strict_binding'] = binding
            template['generation_mode'] = 'blank'
            template['content_verification_status'] = 'own_blank_and_synthetic_output_all_pages_viewed'
            template['render_status'] = 'PASS'
            template.update(adapter=ADAPTER, content_kind='filled_official_blank', generation_label='依据本区自身官方空白表格填写')
    result['generation_adapter'] = ADAPTER
    result['can_generate'] = True
    result['warnings'] = [
        '仅支持本区自身空白申请书（劳动者、单被申请人）与六列证据清单。',
        '身份证明及证据复印件附件仅为标题占位，不支持填写生成；官方样例不分发、不作案件事实。',
        '指南申请书4份与原件副本按被申请人人数的语境分别保留；申请书副本与证据副本分别填写。',
        '在线办理已止步官方登录，未验证登录后提交；文书适配不代表已代交仲裁申请。',
    ]
    return result


def _public_proof(guide, root):
    if root is None or not isinstance(guide, dict):
        raise ValueError('必须明确给定公开根目录和本区指南')
    canonical, root = _validate_guide(guide, root, allow_missing_evidence=True)
    metadata = {'version', 'content_hash', 'region_id', 'can_generate', 'published', 'publication_status',
                'candidate_web_qa', 'warnings', 'generation_adapter'}
    if set(guide) - set(canonical) - metadata:
        raise ValueError('指南包含非本区来源事实字段')
    if guide.get('generation_adapter') not in {None, ADAPTER}:
        raise ValueError('非本区适配器标记')
    report_root = root / REPORT
    manifest = json.loads(_read_checked(report_root / 'SOURCE-MANIFEST.json', MANIFEST_SHA, root))
    white = json.loads(_read_checked(report_root / 'PUBLIC-WHITELIST.json', WHITELIST_SHA, root))['files']
    prefix = SPECS[guide['region_code']]['name'] + '/'
    for relative, pin in manifest['files'].items():
        if not relative.startswith(prefix):
            continue
        path = report_root / relative
        if white.get(REPORT.as_posix() + '/' + relative) != pin:
            raise ValueError('自身证据不在冻结公开白名单')
        raw = _read_checked(path, pin['sha256'], root)
        if len(raw) != pin['bytes']:
            raise ValueError('自身公开证据大小不匹配')
    return canonical, root, white


def public_evidence(guide, root):
    """Rebuild only canonical public evidence, requiring an explicit root."""
    try:
        canonical, _, _ = _public_proof(guide, root)
        return deepcopy(canonical['evidence'])
    except (ValueError, OSError, KeyError, TypeError, StopIteration, AttributeError):
        return None


def approved_report_attachment(guide, template, root):
    try:
        canonical, root, white = _public_proof(guide, root)
        own = next(t for t in canonical['templates'] if t['id'] == template.get('id'))
        if (own['official_kind'] not in {'blank', 'instruction'} or own['download_status'] != 'downloaded'
                or not _template_annotations_match(template, own, canonical['region_code'])):
            return False
        row = white.get(own['file'])
        if row != {'sha256': own['sha256'], 'bytes': own['bytes']}:
            return False
        return len(_read_checked(root / own['file'], own['sha256'], root)) == own['bytes']
    except (ValueError, OSError, KeyError, TypeError, StopIteration, AttributeError):
        return False


def fill_candidate_document(guide, kind, data, root=None):
    """Use each district's own fixed original; shared engine only handles OOXML slots."""
    _, path, original = _source(guide, kind, root)
    data = deepcopy(data)
    if kind == 'evidence':
        data['evidenceList'] = [{**item, 'pageCount': re.sub(r'^\s*(\d+)\s*页\s*$', r'\1', str(item.get('pageCount', '')))}
                                for item in data.get('evidenceList', [])]
    elif data.get('copyCount') is None:
        data['copyCount'] = '    '
    if kind == 'application' and not data.get('requests'):
        # The shared engine skips selection/filling for a wholly blank request.
        # A blank item selects this worker form even when only optional fields
        # were supplied; it creates no claim and prevents silent data loss.
        data['requests'] = ['']
    document = (fill_application if kind == 'application' else fill_evidence)(data, path, profile='JiangSuSheng')
    if kind == 'application':
        for paragraph in document.paragraphs:
            match = re.search(r'相关证据(?P<slot>[\d \t]+)(?=份)', paragraph.text)
            if match:
                copies = data.get('evidenceCopyCount')
                replace_span(paragraph, match.start('slot'), match.end('slot'), str(copies) if copies is not None else '    ')
        closing = False
        for paragraph in document.paragraphs:
            compact = ''.join(paragraph.text.split())
            if compact == '此致':
                closing = True
            if closing:
                if compact.endswith('日') and '年' in compact and '月' in compact:
                    break
                paragraph.paragraph_format.keep_with_next = True
    return PreservedPackageDocument(document, original)
