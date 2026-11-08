"""Luohu's reviewed collective-case forms and their independent source binding."""
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from typing import Annotated
from unicodedata import category, east_asian_width

from docx import Document
from pydantic import AfterValidator, Field

from regional_documents import PreservedPackageDocument
from regional_guides import digest
from regional_huian_quangang_request import OwnBase

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = 'guangdong_luohu_collective_wps_v1'
SOURCE = 'https://www.szlh.gov.cn/lhrlzyj/gkmlpt/content/8/8598/post_8598964.html'
SOURCE_ID = digest(SOURCE)[:24]
GUIDE = Path('reports/overnight-gap-closure-20261030/localities/luohu-collective-own-source/GUIDE.json')
GUIDE_SHA = 'db45a74e0bf7cae4c7002cce975134cbd7c6699592ec7c3584cdb3ea5880807c'
LAYOUTS = {
    'application': ('templates/_docx/_regional/guangdong/luohu-collective-application.docx',
                    '0b9bd9e22c926c0c76f5dbaaf8eb2027eaef1c938ee24c2a82b2a789e4dda405'),
    'evidence': ('templates/_docx/_regional/guangdong/luohu-collective-evidence.docx',
                 '47b2d951b37cda01c02764ad810dacfd8e4e50e74f08bf0c33722a538b275f41'),
}


def _single_line(value):
    if any(category(char).startswith('C') or category(char) in {'Zl', 'Zp'} for char in value):
        raise ValueError('罗湖集体案表格须使用单行文字')
    return value.strip()


def _date(value):
    if value and date.fromisoformat(value).isoformat() != value:
        raise ValueError('日期须为 YYYY-MM-DD')
    return value


def _line(limit):
    return Annotated[str, Field(max_length=limit), AfterValidator(_single_line)]


Count = Annotated[str, Field(max_length=4, pattern=r'^$|^[1-9][0-9]{0,3}$')]
Date = Annotated[str, Field(max_length=10), AfterValidator(_date)]


class Respondent(OwnBase):
    name: _line(25) = ''
    legal_rep: _line(7) = ''
    position: _line(5) = ''
    operator: _line(23) = ''
    phone: _line(15) = ''


class ApplicationRequest(OwnBase):
    representatives: _line(22) = ''
    applicant_count: Count = ''
    respondents: list[Respondent] = Field(default_factory=list, max_length=2)
    requests: list[_line(27)] = Field(default_factory=list, max_length=7)
    total: Annotated[str, Field(max_length=10, pattern=r'^$|^[0-9]{1,7}(\.[0-9]{1,2})?$')] = ''
    fact_lines: list[_line(28)] = Field(default_factory=list, max_length=10)
    date: Date = ''


class EvidenceItem(OwnBase):
    name: _line(9) = ''
    purpose: _line(10) = ''
    sheet_count: Count = ''


class EvidenceRequest(OwnBase):
    items: list[EvidenceItem] = Field(default_factory=list, max_length=10)
    submitter: _line(12) = ''
    date: Date = ''


LABELS = {
    'representatives': '推举的员工代表', 'applicant_count': '申请人数', 'respondents': '被申请人',
    'requests': '仲裁请求（每项一行）', 'total': '合计金额', 'fact_lines': '事实与理由（每段一行）',
    'date': '填写日期', 'name': '名称', 'legal_rep': '法定代表人', 'position': '职务',
    'operator': '实际经营人', 'phone': '联系电话', 'items': '证据项目',
    'purpose': '证明内容', 'sheet_count': '张数', 'submitter': '提交人',
}
MODELS = {'application': ApplicationRequest, 'evidence': EvidenceRequest}


def schema_descriptor(kind, source_version):
    model = MODELS[kind]
    schema = model.model_json_schema()

    def descriptor(key, node):
        field = {'key': key, 'label': LABELS[key], 'type': 'text'}
        if key == 'date':
            field['format'] = 'iso-date'
        if 'maxLength' in node:
            field['maxLength'] = node['maxLength']
        if node['type'] == 'array':
            item = node['items']
            field['maxItems'] = node['maxItems']
            if '$ref' in item:
                children = schema['$defs'][item['$ref'].rsplit('/', 1)[-1]]['properties']
                field.update(type='object_list', fields=[descriptor(k, child) for k, child in children.items()])
            else:
                field.update(type='text_list', maxLength=item['maxLength'])
        return field

    return {'schema_id': ADAPTER + '_' + kind, 'schema_version': 1, 'source_version': source_version,
            'fields': [descriptor(k, prop) for k, prop in schema['properties'].items()],
            'defaults': model().model_dump(),
            'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
                       'trim_text': True, 'capacity_is_official_requirement': False, 'signature_field': 'manual_only'}}


def _verified_bytes(root, filename, expected):
    path = (root / filename).resolve()
    if not path.is_relative_to(root):
        raise ValueError('罗湖集体案来源路径无效')
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('罗湖集体案来源文件暂不可用') from exc
    if sha256(raw).hexdigest() != expected:
        raise ValueError('罗湖集体案来源文件已变化')
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = json.loads(_verified_bytes(root, GUIDE, GUIDE_SHA))
    guide.update(source_id=SOURCE_ID, source_version=GUIDE_SHA)
    for template in guide['templates']:
        template.update(can_generate=True, adapter=ADAPTER)
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind not in MODELS or guide.get('case_scope') != 'collective':
        raise ValueError('仅适配罗湖区自己的集体案文书')
    root = Path(ROOT if root is None else root).resolve()
    expected = staged_guide(root)
    # The API may project the selected subset. Check the same pinned source,
    # template, identity and all substantive guide fields.
    if any(guide.get(k) != value for k, value in expected.items() if k != 'templates'):
        raise ValueError('罗湖区集体案来源不匹配')
    matching = [t for t in expected['templates'] if t['document_types'] == [kind]]
    if matching != [template] or sum(t.get('id') == template['id'] for t in guide['templates']) != 1:
        raise ValueError('罗湖区集体案附件不匹配')
    _verified_bytes(root, *LAYOUTS[kind])
    return ADAPTER


def width(value):
    return sum(2 if east_asian_width(c) in 'FW' else 1 for c in value)


def line(value, maximum):
    if type(value) is not str or any(category(c).startswith('C') for c in value):
        raise ValueError('填写内容须为单行文本')
    value = value.strip()
    if width(value) > maximum:
        raise ValueError('超出当前模板单行的实测容量')
    return value


def slot(p, indexes, value, maximum=None):
    runs = [p.runs[i] for i in indexes]
    original = ''.join(r.text for r in runs)
    if not all(r.underline for r in runs) or not original or original.strip():
        raise ValueError('原件下划线槽位不匹配')
    capacity = len(original) if maximum is None else min(len(original), maximum)
    value = line(value, capacity)
    if value:
        runs[0].text = value + ' ' * (len(original) - width(value))
        for run in runs[1:]:
            run.text = ''


def apply_date(p, indexes, value):
    if value == '':
        return
    if type(value) is not str:
        raise ValueError('日期须为 YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('日期须为 YYYY-MM-DD')
    for index, part in zip(indexes, value.split('-'), strict=True):
        slot(p, (index,), part)


def application(doc, data):
    paragraphs = doc.paragraphs
    if (len(paragraphs) != 48 or paragraphs[1].text != '（集体案用）'
            or paragraphs[39].text != '深圳市罗湖区劳动人事争议仲裁委员会'):
        raise ValueError('与罗湖集体案原件版式不匹配')
    count = data.get('applicant_count', '')
    total = data.get('total', '')
    slot(paragraphs[3], (2,), data.get('representatives', ''), 44)
    slot(paragraphs[4], (1,), count)
    for i, party in enumerate(data['respondents']):
        offset = 6+5*i
        for field, delta, indexes, capacity in (
            ('name', 0, (2,), 50), ('legal_rep', 1, (1,), 14 if i == 0 else 24),
            ('position', 1, (4,), 20 if i == 0 else 10), ('operator', 2, (1,) if i == 0 else (1, 2), 46),
            ('phone', 3, (1,), 30),
        ):
            slot(paragraphs[offset+delta], indexes, party.get(field, ''), capacity)
    for i, request in enumerate(data['requests']):
        slot(paragraphs[17+i], (2, 3) if i == 6 else (2,), request, 55)
    slot(paragraphs[24], (1,), total)
    for i, fact in enumerate(data['fact_lines']):
        slot(paragraphs[27+i], (0, 1) if i == 6 else (0,), fact, 56)
    apply_date(paragraphs[42], (1, 3, 5), data.get('date', ''))


def evidence(doc, data):
    table, = doc.tables
    header = [''.join(c.text.split()) for c in table.rows[0].cells]
    if len(table.rows) != 11 or header != ['序号', '名称', '证明内容', '张数']:
        raise ValueError('与罗湖证据清单原件版式不匹配')
    for i, item in enumerate(data['items'], 1):
        values = [item[key] for key in ('name', 'purpose', 'sheet_count')]
        for cell, value in zip(table.rows[i].cells, [str(i) if any(values) else '', *values], strict=True):
            if cell.text:
                raise ValueError('证据行已包含原件内容')
            if value:
                p = cell.paragraphs[0]
                if p.runs:
                    p.runs[0].text = value
                else:
                    p.add_run(value)
    slot(doc.paragraphs[3], (1, 2, 3), data.get('submitter', ''), 24)
    apply_date(doc.paragraphs[3], (6, 8, 10), data.get('date', ''))


def fill_document(kind, path, values):
    if kind not in MODELS:
        raise ValueError('仅适配罗湖区自己的集体案文书')
    layout = path.read_bytes()
    if sha256(layout).hexdigest() != LAYOUTS[kind][1]:
        raise ValueError('罗湖区集体案转换版已变化')
    data = MODELS[kind].model_validate(values).model_dump()
    document = Document(BytesIO(layout))
    (application if kind == 'application' else evidence)(document, data)
    return PreservedPackageDocument(document, layout)
