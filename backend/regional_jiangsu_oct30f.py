"""Own-source Changshu and Zhangjiagang worker forms; explicit roots never use private fallback."""
from copy import deepcopy
from datetime import date
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from docx import Document
from docx.oxml.ns import qn
from docx.table import _Row
from regional_guides import digest
from regional_documents import PreservedPackageDocument
from WenShu.exact_template_fill import keep_body, fill_sections, fill_footer, remove_empty_edges
from WenShu.template_fill import replace_span, fill_label_slots, set_cell_text

ROOT = Path(__file__).resolve().parents[1]
REPORT = Path('reports/nationwide-verification-20261029-f/jiangsu')
ADAPTER = 'jiangsu_own_blank_oct30f_v1'
SUPPORTED = frozenset({'320581', '320582'})
MANIFEST_SHA = 'c594c7bc7b352e934e5ea7f71137f9bc22031acee522d7b4eeff82ca7f8445ea'
WHITELIST_SHA = '5ca19bb495971d97e832f3468f577654a730ed99fe5b8e2435254cbaee3eddf6'
SPECS = {
    '320581': dict(name='changshu', district='常熟市', authority='常熟市人力资源和社会保障局',
        task='11320581014173412K400201430200201', webId='30',
        application='9992a58d-12a7-4131-8317-82e2358af86f', evidence='0671a152-24d1-4c00-bf92-f281dc2451c0',
        guide_sha='b3f8cd1e64a1c03b0808d869b5daa03a788f3343e0f237f6a1cf23d57b14f529'),
    '320582': dict(name='zhangjiagang', district='张家港市', authority='张家港市人力资源和社会保障局',
        task='11320582551232000Y400201430200201', webId='31',
        application='e7792a1a-fbf0-461d-9574-67196dec0d6b', evidence='fb67c9e4-1f9f-4e6c-bdb0-cc6c04f0966a',
        guide_sha='f389a9f16651cd64db3b37b897ea049dd670ba21680c83a6d315a44fa42c4efd'),
}

APPLICATION_FIELDS = frozenset({'committeeName', 'applicantName', 'birthDate', 'gender', 'idNumber', 'idAddress',
    'otherDocumentType', 'otherDocumentNumber', 'applicantMailingAddress', 'phone', 'acceptMediation', 'legalAid',
    'respondentName', 'respondentType', 'registeredAddress', 'socialCreditCode', 'legalRepName', 'legalRepPosition',
    'departmentHead', 'departmentHeadPosition', 'mailingAddress', 'companyContact', 'companyContactPhone',
    'requests', 'factsReason', 'applicationDate', 'copyCount', 'evidenceCopyCount'})
EVIDENCE_FIELDS = frozenset({'committeeName', 'caseNumber', 'submitDate', 'evidenceList'})
EVIDENCE_ITEM_FIELDS = frozenset({'name', 'source', 'purpose', 'originalType', 'pageCount'})
DATA_FIELDS = {'application': APPLICATION_FIELDS, 'evidence': EVIDENCE_FIELDS, 'evidence_item': EVIDENCE_ITEM_FIELDS}
LIMITS = {'ordinary': 300, 'factsReason': 12000, 'requests': 4, 'request': 1200, 'evidenceList': 40,
          'evidence_name': 300, 'evidence_source': 300, 'evidence_originalType': 300,
          'evidence_pageCount': 300, 'evidence_purpose': 1200, 'copyCount_min': 1, 'copyCount_max': 30}
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
        raise ValueError('不是本批常熟或张家港自身指南')
    report_root = Path(report_root).resolve()
    manifest = json.loads(_read_checked(report_root / 'SOURCE-MANIFEST.json', MANIFEST_SHA, report_root))
    white = json.loads(_read_checked(report_root / 'PUBLIC-WHITELIST.json', WHITELIST_SHA, report_root))['files']
    for relative, pin in manifest['files'].items():
        if relative.startswith(spec['name'] + '/'):
            if white.get((REPORT / relative).as_posix()) != pin:
                raise ValueError('自身来源文件不在冻结公开清单')
            if len(_read_checked(report_root / relative, pin['sha256'], report_root)) != pin['bytes']:
                raise ValueError('自身来源文件大小不匹配')
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


QA_REPORT = 'reports/overnight-gap-closure-20261030/localities/jiangsu-f'
STAGE_RECEIPT = QA_REPORT + '/STAGE-APPROVAL.json'
STAGE_SHA256 = '1c9bcc069f4b659f55225a988852f81e7888ab66b6e0c46ad4d0a78fbdf38c88'  # Pinned only after independent root review of own Word proof.
PUBLICATION_RECEIPT = QA_REPORT + '/FINAL-BROWSER-QA.json'
PUBLICATION_SHA256 = 'b37cabc422b4a315e22a5762553269636b821dd8d9b0b3fc46f03602af6febe6'  # Separate root-reviewed native download and Word proof.
_STORE_METADATA = frozenset({'version', 'content_hash', 'region_id'})
_FAILURES = (ValueError, OSError, KeyError, TypeError, StopIteration, AttributeError)


def _same(actual, expected):
    """Require the canonical JSON type at every nested source/lifecycle slot."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def _matches(guide, canonical):
    return (type(guide) is dict and not (set(guide) - set(canonical) - _STORE_METADATA)
            and all(k in guide and _same(guide[k], v) for k, v in canonical.items()))


def _path(root, relative):
    if root is None or isinstance(root, str) and not root.strip():
        raise ValueError('必须明确提供自身公开根目录')
    root = Path(root).resolve(); relative = Path(relative)
    if relative.is_absolute() or relative.drive or '..' in relative.parts:
        raise ValueError('自身公开证据路径越界')
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root) or resolved.relative_to(root).as_posix() != relative.as_posix():
        raise ValueError('自身公开证据路径越界或被符号链接替换')
    return resolved


def _raw(code, root):
    return parse_capture(code, _path(root, REPORT))


def _receipt(root, path, checksum, stage=True):
    if not isinstance(checksum, str) or len(checksum) != 64:
        raise ValueError('自身验收收据尚未由独立发布负责人审核固定')
    receipt = json.loads(_read_checked(_path(root, path), checksum, root))
    sources = [_raw(code, root) for code in sorted(SUPPORTED)]
    identities = [{k: source[k] for k in ('region_code', 'source_id', 'service_code')} for source in sources]
    expected = {'identities': identities, 'source_manifest_sha256': MANIFEST_SHA,
                'public_whitelist_sha256': WHITELIST_SHA, 'model_calls': 0,
                'visual_review': 'PASS', 'can_publish': not stage}
    if any(k not in receipt or not _same(receipt[k], v) for k, v in expected.items()):
        raise ValueError('自身验收收据范围或来源链不匹配')
    if not stage and (receipt.get('stage_receipt_sha256') != STAGE_SHA256
                      or receipt.get('native_confirmation_download_four_forms') is not True):
        raise ValueError('最终验收缺少自身四份文书真实网页下载证明')
    files = receipt.get('files')
    if type(files) is not list or not files or len({f['path'] for f in files}) != len(files):
        raise ValueError('自身验收证据清单缺失或重复')
    for row in files:
        if not row['path'].startswith(QA_REPORT + '/'):
            raise ValueError('自身验收证据路径超出本批目录')
        body = _path(root, row['path']).read_bytes()
        if type(row['bytes']) is not int or row['bytes'] != len(body) or hashlib.sha256(body).hexdigest() != row['sha256']:
            raise ValueError('自身验收证据文件已变化')
    return {'receipt': path, 'sha256': checksum}


def _binding(template, kind):
    return {'adapter': ADAPTER, 'kind': kind, 'annex_id': template['id'],
            'source_sha256': template['sha256'], 'source_file': template['file'],
            'source_url': template['source_url']}


def prepare_candidate(code, *, root):
    """Derive an explicit attested QA candidate without any DB/source write."""
    result = _raw(str(code), root)
    result['candidate_adapter_evidence'] = _receipt(root, STAGE_RECEIPT, STAGE_SHA256)
    result.update(can_generate=True, generation_adapter=ADAPTER, published=False,
                  publication_status='staged_own_word_qa')
    for template in result['templates']:
        kind = next((k for k in ('application', 'evidence') if SPECS[str(code)][k] == template['id']), None)
        if kind:
            template.update(can_generate=True, document_types=[kind], generation_adapter=ADAPTER,
                strict_binding=_binding(template, kind), generation_mode='blank', adapter=ADAPTER,
                content_kind='filled_official_blank', applicant_scope='worker' if kind == 'application' else 'evidence_list',
                generation_label='依据本区自身官方空白表格填写', render_status='PASS',
                content_verification_status='own_blank_and_synthetic_output_all_pages_viewed')
    obsolete = {'本批仅采集自身指南与公开来源，未做新适配或候选网页验收，未发布。',
                'DOCX只读结构与文本检查不等于逐页版式验收，render_status仍为NOT_RUN。'}
    result['warnings'] = [w for w in result['warnings'] if w not in obsolete]
    result['warnings'].extend([
        '仅适配本区自身空白申请书劳动者区段、单被申请人，以及六列证据清单。',
        '身份证明与证据复印件为标题占位，不支持填写生成；官方样例不作为案件事实。',
        '申请书4份与证据清单2份材料要求保留；原件中申请书副本与证据副本分别填写。',
        '调解、法律援助及原件或复印件栏不自动代选；签名、提交人及接收人留空。',
        '本区原件及虚构填写副本已经逐页Word检查；仍为候选，尚未完成网页验收和发布。',
        '网上办理止步官方登录，未验证登录后提交，文书生成不代表已代交申请。'])
    return result


def _publication_projection(code, root):
    result = prepare_candidate(code, root=root)
    result['publication_adapter_evidence'] = _receipt(root, PUBLICATION_RECEIPT, PUBLICATION_SHA256, stage=False)
    result.update(published=True, publication_status='published', candidate_web_qa='PASS')
    result['warnings'] = [w for w in result['warnings'] if not w.startswith('本区原件及虚构填写副本')]
    result['warnings'].append('本区自身两份空白文书已经真实网页填写下载及下载件逐页Word检查；仍须本人核对和手写签名。')
    return result


def _bound_guide(guide, root, allow_source=False):
    if type(guide) is not dict:
        raise ValueError('自身指南格式不匹配')
    source = _raw(guide.get('region_code'), root)
    if allow_source and _matches(guide, source):
        return source
    published = guide.get('published') is True or 'publication_adapter_evidence' in guide
    canonical = _publication_projection(source['region_code'], root) if published else prepare_candidate(source['region_code'], root=root)
    if not _matches(guide, canonical):
        raise ValueError('自身来源、字段、附件、能力或固定验收收据不匹配')
    return canonical


def with_capabilities(guide, root=None):
    root = ROOT if root is None else root
    _bound_guide(guide, root, allow_source=True)
    return deepcopy(guide)


def with_publication_evidence(guide, *, root):
    candidate = prepare_candidate(guide.get('region_code'), root=root)
    if not _matches(guide, candidate):
        raise ValueError('必须从已验收的本区候选生成发布投影')
    result = _publication_projection(guide['region_code'], root)
    for key in _STORE_METADATA & set(guide):
        result[key] = deepcopy(guide[key])
    return result


def _source(guide, kind, root=None):
    if type(kind) is not str or kind not in {'application', 'evidence'}:
        raise ValueError('仅适配本区劳动者申请书与证据清单')
    root = ROOT if root is None else root
    canonical = _bound_guide(guide, root, allow_source=True)
    raw = _raw(canonical['region_code'], root)
    template = next(t for t in raw['templates'] if t['id'] == SPECS[raw['region_code']][kind])
    path = _path(root, template['file'])
    original = _read_checked(path, template['sha256'], _path(root, REPORT))
    return template, path, original


def blank_binding(guide, template, root=None):
    root = ROOT if root is None else root
    canonical = _bound_guide(guide, root, allow_source=True)
    kind = next((k for k in ('application', 'evidence') if SPECS[canonical['region_code']][k] == template.get('id')), None)
    own = next((t for t in canonical['templates'] if t['id'] == template.get('id')), None)
    if kind is None or not _same(template, own):
        raise ValueError('传入附件不是本区自身已适配空白原件')
    return _binding(template, kind)


def candidate_contract(guide, root=None):
    documents = {}
    for kind in ('application', 'evidence'):
        template, _, _ = _source(guide, kind, root)
        documents[kind] = _binding(template, kind)
    return {'adapter': ADAPTER, 'region_code': guide['region_code'], 'province': guide['province'],
            'city': guide['city'], 'district': guide['district'], 'source_id': guide['source_id'],
            'authority': guide['authority'], 'service_code': guide['service_code'],
            'documents': documents, 'scope': 'own_official_blank_only'}


def checked_adapter(guide, template, kind, root=None):
    canonical = _bound_guide(guide, ROOT if root is None else root)
    if type(kind) is not str or kind not in {'application', 'evidence'}:
        raise ValueError('自身文书种类不匹配')
    if template.get('id') != SPECS[canonical['region_code']][kind]:
        raise ValueError('自身附件与请求种类不匹配')
    blank_binding(canonical, template, root)
    return ADAPTER


def public_evidence(guide, root):
    try:
        return deepcopy(_bound_guide(guide, root, allow_source=True)['evidence'])
    except _FAILURES:
        return None


def approved_report_attachment(guide, template, root):
    try:
        canonical = _bound_guide(guide, root, allow_source=True)
        return any(_same(template, t) and t['official_kind'] in {'blank', 'instruction'}
                   and t.get('download_status') == 'downloaded' for t in canonical['templates'])
    except _FAILURES:
        return False


# Only locality-free slot operations are shared. Both F own originals were
# independently inspected (118 paragraphs, worker/employer split,13x6 table).
from regional_jiangsu_oct29e import _application, _evidence, _validate_data


def fill_candidate_document(guide, kind, data, root=None):
    """Offline QA copy; never enables source-only capabilities."""
    _, _, original = _source(guide, kind, root)
    validated = _validate_data(kind, data)
    document = Document(BytesIO(original))
    (_application if kind == 'application' else _evidence)(document, validated)
    return PreservedPackageDocument(document, original)


def fill_document(guide, template, kind, path, data, *, root):
    """Route entry requires attested candidate/publication and exact own path."""
    checked_adapter(guide, template, kind, root=root)
    _, own_path, _ = _source(guide, kind, root)
    if Path(path).resolve() != own_path:
        raise ValueError('原件路径不是本区自身附件，禁止同SHA跨区借用')
    return fill_candidate_document(guide, kind, data, root)
