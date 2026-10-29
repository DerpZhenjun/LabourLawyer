"""Own-source Changzhou C blank forms; no private samples or cross-region rules."""
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
REPORT = Path('reports/nationwide-verification-20261029-c/jiangsu')
ADAPTER = 'jiangsu_own_blank_oct29c_v1'
SUPPORTED = frozenset({'320411', '320412'})
MANIFEST_SHA = '1b5bf8201e0dbe260fbcfa2fab4e4b9ac4abfdacdd829727ed1de93b0053f634'
SPECS = {
    '320411': dict(name='xinbei', district='新北区',
        authority='常州高新技术产业开发区（新北区）人力资源和社会保障局',
        task='1132040801411296X7400201430200201', webId='43',
        application='cc5fca68-4669-4fc7-8ff9-0d6668d53b68', evidence='3f808a2a-7467-4df6-82ba-da6a18a9f73b',
        guide_sha='46e32fdd3f895cc9998808869a0f9bb1ed6c096099fe74dc4fba994b23294796'),
    '320412': dict(name='wujin', district='武进区', authority='常州市武进区人社局',
        task='1132048301413435XM400201430200201', webId='44',
        application='5c41b459-d5f1-413b-af51-a502312d10e3', evidence='d52d17ae-f35a-44b2-af42-41745a39e798',
        guide_sha='157076d35ace96268ff76d91af3f3ee3b56f68ea4596d96935e3ad3dbca0bdf4'),
}
# Source fields are immutable; lifecycle/QA/capability annotations can evolve.
SOURCE_KEYS = ('province', 'province_name', 'city', 'district', 'region_code', 'service_name',
               'service_code', 'authority', 'source_url', 'source_title', 'source_type',
               'fields', 'materials', 'sections', 'scope_identity', 'evidence', 'channel',
               'online_boundary', 'source_issues', 'attachment_counts')
TEMPLATE_KEYS = ('id', 'annex_id', 'region_code', 'material_id', 'official_kind', 'original_name',
                 'source_url', 'download_url', 'file', 'file_type', 'sha256', 'bytes',
                 'download_status', 'public_release_status', 'content_role')


def _read_checked(path, checksum):
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
        raise ValueError('不是本批新北或武进自身指南')
    report_root = Path(report_root).resolve()
    manifest = json.loads(_read_checked(report_root / 'SOURCE-MANIFEST.json', MANIFEST_SHA))
    guide_path = f"{spec['name']}/guide.json"
    if manifest['files'][guide_path]['sha256'] != spec['guide_sha']:
        raise ValueError('固定来源清单与指南不一致')
    g = json.loads(_read_checked(report_root / guide_path, spec['guide_sha']))
    expected = dict(region_code=code, district=spec['district'], city='常州市', province='jiangsu',
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
        _read_checked(report_root / relative, checksum)
    g['source_id'] = digest(g['source_url'])[:24]
    return g


def parse_capture(code_or_name, capture_root=None):
    """Read frozen own public capture. capture_root is the sealed jiangsu directory."""
    key = str(code_or_name)
    code = next((c for c, s in SPECS.items() if key in {c, s['district'], s['name']}), None)
    return _baseline(code, Path(capture_root) if capture_root is not None else ROOT / REPORT)


def _validate_guide(guide, root=None):
    root = Path(root if root is not None else ROOT).resolve()
    baseline = _baseline(guide.get('region_code'), root / REPORT)
    if guide.get('source_id') != baseline['source_id'] or any(guide.get(k) != baseline.get(k) for k in SOURCE_KEYS):
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
    original = _read_checked(path, template['sha256'])
    return template, path, original


def blank_binding(guide, template, root=None):
    kind = next((k for k in ('application', 'evidence')
                 if SPECS.get(guide.get('region_code'), {}).get(k) == template.get('id')), None)
    if kind is None:
        raise ValueError('样例或占位材料不支持填写')
    expected, _, _ = _source(guide, kind, root)
    if any(template.get(k) != expected.get(k) for k in TEMPLATE_KEYS):
        raise ValueError('传入附件与自身空白绑定不一致')
    return {'adapter': ADAPTER, 'kind': kind, 'annex_id': expected['id'],
            'source_sha256': expected['sha256'], 'source_file': expected['file'],
            'source_url': expected['source_url']}


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
    result['generation_adapter'] = ADAPTER
    result['can_generate'] = True
    result['warnings'] = [
        '仅支持本区自身空白申请书（劳动者、单被申请人）与六列证据清单。',
        '身份证明及证据复印件附件仅为标题占位，不支持填写生成；官方样例不分发、不作案件事实。',
        '指南申请书4份与原件副本按被申请人人数的语境分别保留；申请书副本与证据副本分别填写。',
        '在线办理已止步官方登录，未验证登录后提交；文书适配不代表已代交仲裁申请。',
    ]
    return result


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
