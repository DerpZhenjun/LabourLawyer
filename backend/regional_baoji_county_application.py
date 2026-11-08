"""Fill independently retrieved worker forms from Baoji counties."""
import json
from copy import deepcopy
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated
from unicodedata import category

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pydantic import AfterValidator, Field

from regional_documents import PreservedPackageDocument
from regional_guides import digest
from regional_huian_quangang_request import OwnBase, bounded


ROOT = Path(__file__).resolve().parents[1]
BASE_GUIDES = Path('reports/overnight-gap-closure-20261030/localities/baoji-eight-county-source/GUIDES.json')
BASE_GUIDES_SHA = 'c7539c1a883f09f49eb8aceb4b3e2a95505e2ac3b6d655d732ddcac6a9f7b883'
PROOF = Path('reports/overnight-gap-closure-20261030/localities/baoji-three-worker-applications/SOURCE-PROOF.json')
PROOF_SHA = '0c07b48554cc17a88d8eaf439d51fbb48e6ac52885c83ad35d0547fc09b9e176'
LINYOU_PROOF = Path('reports/overnight-gap-closure-20261030/localities/baoji-linyou-worker-application/SOURCE-PROOF.json')
LINYOU_PROOF_SHA = '3cddcfe9de8988b9fa05d4cf847610a387a25698a7c5693affe661e4c8cc88d1'
SHARED = 'shaanxi_baoji_qishan_long_worker_v1'
MEI = 'shaanxi_baoji_mei_worker_v1'
LINYOU = 'shaanxi_baoji_linyou_worker_v1'
ADAPTERS = {'610323': SHARED, '610326': MEI, '610327': SHARED, '610329': LINYOU}
LAYOUTS = {
    code: Path(f'templates/_docx/_regional/shaanxi/baoji-{code}-worker-application.docx') for code in ADAPTERS
}
SHARED_LAYOUT_SHA = 'a9abffd8a2714f636689727f0113f2d19f22c76ba1a7809792ac029ce64295da'
LAYOUT_HASHES = {
    '610323': SHARED_LAYOUT_SHA,
    '610326': 'd3b1d4fe23d4578a2b323cf2e7f500eadaa8b22e832f627b751e77ba6af5116f',
    '610327': SHARED_LAYOUT_SHA,
    '610329': '5c64d10d59977f133f8a38ae2ccb72fd02eba4b8e12f7f2b771dcf42845b9c69',
}


def _single_line(value):
    if any(category(char).startswith('C') or category(char) in {'Zl', 'Zp'} for char in value):
        raise ValueError('本栏请填写一行文字')
    return value.strip()


def _line(limit):
    return Annotated[str, Field(max_length=limit), AfterValidator(_single_line)]


def _iso_date(value):
    if value and date.fromisoformat(value).isoformat() != value:
        raise ValueError('出生日期须为 YYYY-MM-DD')
    return value


def _facts_lines(value):
    if value.count('\n') > 7:
        raise ValueError('事实与理由最多分八段填写')
    return value


class WorkerApplication(OwnBase):
    applicant_name: _line(20) = ''
    gender: _line(6) = ''
    address: _line(70) = ''
    id_number: _line(24) = ''
    phone: _line(24) = ''
    respondent_name: _line(60) = ''
    respondent_address: _line(75) = ''
    respondent_phone: _line(24) = ''
    representative: _line(24) = ''
    requests: list[_line(75)] = Field(default_factory=list, max_length=3)
    facts: Annotated[bounded(360), AfterValidator(_facts_lines)] = ''


class MeiApplication(WorkerApplication):
    birth_date: Annotated[str, Field(max_length=10), AfterValidator(_iso_date)] = ''


class QishanLongApplication(WorkerApplication):
    nationality: _line(12) = ''
    age: _line(3) = ''
    social_credit_code: _line(24) = ''
    representative_gender: _line(6) = ''
    representative_role: _line(20) = ''
    representative_phone: _line(24) = ''


class LinyouApplication(OwnBase):
    applicant_name: _line(20) = ''
    gender: _line(6) = ''
    birth_text: _line(20) = ''
    nationality: _line(12) = ''
    applicant_work_unit: _line(60) = ''
    address: _line(70) = ''
    phone: _line(24) = ''
    applicant_postcode: _line(12) = ''
    respondent_name: _line(60) = ''
    representative: _line(24) = ''
    representative_role: _line(20) = ''
    respondent_address: _line(75) = ''
    respondent_phone: _line(24) = ''
    respondent_postcode: _line(12) = ''
    requests: list[_line(75)] = Field(default_factory=list, max_length=3)
    facts: Annotated[bounded(360), AfterValidator(_facts_lines)] = ''


MODELS_BY_ADAPTER = {SHARED: QishanLongApplication, MEI: MeiApplication, LINYOU: LinyouApplication}
MODELS = {code: MODELS_BY_ADAPTER[adapter] for code, adapter in ADAPTERS.items()}


def _write_mei(paragraphs, data):
    applicant = paragraphs[2].runs
    for index, key in ((1, 'applicant_name'), (4, 'gender')):
        if data[key]:
            applicant[index].text = data[key]
    if data['birth_date']:
        for index, value in zip((8, 10, 12), data['birth_date'].split('-'), strict=True):
            applicant[index].text = value
    for index, key, suffix in ((14, 'address', ','), (18, 'id_number', ','), (21, 'phone', '。')):
        if data[key]:
            applicant[index].text = data[key] + suffix
    for index, key in ((3, 'respondent_name'), (4, 'representative'), (5, 'respondent_phone'), (6, 'respondent_address')):
        if data[key]:
            paragraphs[index].runs[1].text = data[key]
    paragraphs[8].runs[0].text = '\n'.join(f'{index}. {value}' for index, value in enumerate(data['requests'], 1) if value)
    paragraphs[10].runs[0].text = data['facts']
    paragraphs[10].runs[1].text = ''
    for index in (11, 12, 13, 14, 15):
        paragraphs[index].paragraph_format.keep_with_next = True


def _write_qishan_long(paragraphs, data):
    applicant = paragraphs[2].runs
    applicant[2].text = '，'.join(label + '：' + data[key] for key, label in (
        ('applicant_name', '姓名'), ('gender', '性别'), ('nationality', '民族'), ('age', '年龄'),
        ('address', '住所地'), ('id_number', '身份证号'), ('phone', '联系方式'),
    ) if data[key])
    for run in applicant[3:]:
        run.text = ''
    paragraphs[3].runs[1].text = data['respondent_name']
    paragraphs[4].add_run(data['social_credit_code'])
    if data['social_credit_code']:
        paragraphs[4].alignment = WD_ALIGN_PARAGRAPH.LEFT
    address = paragraphs[5].runs
    address[1].text = data['respondent_address'] + '    '
    address[3].text = '：' + data['respondent_phone']
    representative = paragraphs[6].runs
    representative[2].text = '，'.join(label + '：' + data[key] for key, label in (
        ('representative', '姓名'), ('representative_gender', '性别'),
        ('representative_role', '职务'), ('representative_phone', '电话'),
    ) if data[key])
    for run in representative[3:]:
        run.text = ''
    for i, prefix in enumerate(('仲裁请求：1：', '          2：', '3：')):
        paragraphs[7 + i].runs[0].text = prefix + (data['requests'][i] if i < len(data['requests']) else '')
    paragraphs[13].runs[1].text = data['facts']
    for index in (14, 15):
        paragraphs[index].runs[0].text = ''
    paragraphs[17].paragraph_format.keep_with_next = True
    tail = paragraphs[19]._p
    if len(tail) == 0:
        tail.getparent().remove(tail)


def _write_linyou(paragraphs, data):
    # Preserve every label and the line where the issuing county places it.
    for paragraph, index, key, prefix, gap in (
        (1, 1, 'applicant_name', '', '    '), (1, 3, 'gender', ':', ''),
        (2, 1, 'birth_text', ':', '    '), (2, 3, 'nationality', ':', ''),
        (3, 1, 'applicant_work_unit', ' ', '    '), (3, 3, 'address', ':', ''),
        (4, 1, 'phone', ':', '    '), (4, 3, 'applicant_postcode', ':', ''),
        (6, 3, 'representative', ' :', '    '), (6, 5, 'representative_role', ':', ''),
        (7, 1, 'respondent_address', ' :', '    '), (7, 3, 'respondent_phone', ':', ''),
        (8, 2, 'respondent_postcode', ':', ''),
    ):
        if data[key]:
            paragraphs[paragraph].runs[index].text = prefix + data[key] + gap
    if data['respondent_name']:
        respondent = paragraphs[5].add_run(data['respondent_name'])
        respondent._r.insert(0, deepcopy(paragraphs[1].runs[1]._r.rPr))
    for index, value in enumerate(data['requests'], 9):
        paragraphs[index].runs[-1].text += ' ' + value
    if data['facts']:
        paragraphs[12].runs[1].text = data['facts']
        for spacer in paragraphs[13:16]:
            spacer._p.getparent().remove(spacer._p)
    for paragraph in paragraphs[16:21]:
        paragraph.paragraph_format.keep_with_next = True


def fill_application(code, layout, values):
    if code not in MODELS or sha256(layout).hexdigest() != LAYOUT_HASHES[code]:
        raise ValueError('地区与已核验申请书版式不匹配')
    data = MODELS[code].model_validate(values).model_dump()
    document = Document(BytesIO(layout))
    if code == '610326':
        _write_mei(document.paragraphs, data)
    elif code == '610329':
        _write_linyou(document.paragraphs, data)
    else:
        _write_qishan_long(document.paragraphs, data)
    return PreservedPackageDocument(document, layout)


LABELS = {
    'applicant_name': '申请人姓名', 'gender': '性别', 'address': '申请人住所', 'id_number': '身份证号',
    'phone': '申请人联系电话', 'respondent_name': '被申请人名称', 'respondent_address': '单位地址',
    'respondent_phone': '被申请人联系电话', 'representative': '法定代表人姓名', 'requests': '请求事项',
    'facts': '事实与理由', 'birth_date': '出生日期', 'nationality': '民族', 'age': '年龄',
    'social_credit_code': '统一社会信用代码', 'representative_gender': '法定代表人性别',
    'representative_role': '法定代表人职务', 'representative_phone': '法定代表人联系电话',
    'birth_text': '出生时间', 'applicant_work_unit': '工作单位',
    'applicant_postcode': '申请人邮政编码', 'respondent_postcode': '被申请人邮政编码',
}


def schema_descriptor(adapter, source_version):
    model = MODELS_BY_ADAPTER[adapter]
    labels = LABELS | {'respondent_address': '被申请人通信地址'} if adapter == LINYOU else LABELS
    fields = []
    for key, prop in model.model_json_schema()['properties'].items():
        field = {'key': key, 'label': labels[key], 'type': 'text'}
        if key == 'requests':
            field.update(type='text_list', maxLength=prop['items']['maxLength'], maxItems=prop['maxItems'])
        else:
            field['maxLength'] = prop['maxLength']
        if key == 'birth_date':
            field['format'] = 'iso-date'
        fields.append(field)
    return {'schema_id': adapter, 'schema_version': 1, 'source_version': source_version,
            'fields': fields, 'defaults': model().model_dump(),
            'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
                       'trim_text': True, 'capacity_is_official_requirement': False, 'signature_field': 'manual_only'}}


def _pinned_bytes(root, relative, expected):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('宝鸡区县官方来源路径无效')
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('宝鸡区县来源文件不可用') from exc
    if sha256(raw).hexdigest() != expected:
        raise ValueError('宝鸡区县来源或空白表格已变化')
    return raw


def staged_guide(code, root=None):
    if code not in MODELS:
        raise ValueError('该区县暂无通过验收的申请书')
    root = Path(ROOT if root is None else root).resolve()
    candidates = json.loads(_pinned_bytes(root, BASE_GUIDES, BASE_GUIDES_SHA))
    proof_path, proof_hash = (LINYOU_PROOF, LINYOU_PROOF_SHA) if code == '610329' else (PROOF, PROOF_SHA)
    proof = json.loads(_pinned_bytes(root, proof_path, proof_hash))
    guide = next(g for g in candidates if g['region_code'] == code)
    item = next(p for p in proof['items'] if p['region_code'] == code)
    name = guide['district'].replace('　', '')
    guide.update(source_id=digest(guide['source_url'])[:24],
                 source_version=digest(code + ':' + proof_hash + ':' + BASE_GUIDES_SHA),
                 can_generate=True, verified_at=item['fetched_at'])
    guide['warnings'][0] = '本区申请书可填写生成，签名和提交日期请由本人补填。'
    template = {
        'id': f'baoji-{code}-worker-application', 'region_code': code, 'official_kind': 'blank',
        'source_url': item['source_url'], 'official_attachment_entry': 'material_tab',
        'official_sha256': item['official_sha256'], 'official_bytes': item['official_bytes'],
        'file': LAYOUTS[code].as_posix(), 'file_type': 'docx',
        'file_origin': 'official-blank-metadata-sanitized-layout',
        'original_name': name + '劳动仲裁申请书（空白填写版）.docx',
        'download_status': 'downloaded', 'sha256': item['layout_sha256'],
        'document_types': ['application'], 'can_generate': True, 'adapter': ADAPTERS[code],
    }
    if code == '610329':
        template.update(file_origin='official-blank-converted-layout', original_format=item['original_format'])
    guide['templates'] = [template]
    return guide


def checked_adapter(guide, template, kind, root=None):
    code = guide.get('region_code')
    if kind != 'application' or code not in MODELS:
        raise ValueError('仅适配各自已核验的劳动者申请书')
    root = Path(ROOT if root is None else root).resolve()
    expected = staged_guide(code, root)
    if any(guide.get(key) != value for key, value in expected.items()) or template != expected['templates'][0]:
        raise ValueError('区县、官方来源与申请书附件不匹配')
    _pinned_bytes(root, LAYOUTS[code], LAYOUT_HASHES[code])
    return ADAPTERS[code]
