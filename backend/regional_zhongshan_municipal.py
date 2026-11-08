"""Zhongshan's municipal-only application, filled from its verified DOC conversion."""
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated
from unicodedata import category, east_asian_width

from docx import Document
from pydantic import AfterValidator, Field, create_model

from regional_documents import PreservedPackageDocument
from regional_guides import digest
from regional_huian_quangang_request import OwnBase

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = 'guangdong_zhongshan_municipal_legacy_application_v1'
SOURCE = 'https://hrss.zs.gov.cn/zcy/zczn/sqzc/content/post_1899769.html'
SOURCE_ID = digest(SOURCE)[:24]
GUIDE = Path('reports/overnight-gap-closure-20261030/localities/zhongshan-municipal-own-source/GUIDE.json')
GUIDE_SHA = 'f2ba477f85474ce3ffee413bb4b03b6cc3ec5b63acc841eb786f29f7670c59a6'
LAYOUT = Path('templates/_docx/_regional/guangdong/zhongshan-municipal-application.docx')
LAYOUT_SHA = 'de465523e521717b8f072c4783dbe69fc7954170015bd6fb77c6e9cf3a3a3d45'
CONVERTED_ORIGIN = 'official-blank-converted-layout'
SLOTS = {
    'applicant_name': (0, 3, 6, '申请人姓名'), 'id_number': (0, 7, 18, '身份证明号码'),
    'gender': (1, 3, 4, '性别'), 'phone': (1, 7, 18, '申请人电话'), 'address': (2, 3, 26, '申请人地址'),
    'respondent_name': (3, 3, 21, '被申请人名称'), 'registered_address': (4, 3, 24, '被申请人登记地址'),
    'company_contact': (7, 3, 6, '被申请人联系人'), 'company_phone': (7, 7, 18, '被申请人联系电话'),
    'employment_start': (10, 5, 13, '入职时间'), 'job': (10, 9, 7, '工种'),
    'wage': (11, 5, 24, '工资'), 'insurance': (12, 5, 24, '社会保险'),
    'contract': (13, 5, 24, '劳动合同情况'), 'agreed_hours': (14, 5, 8, '约定工作时间'),
    'actual_hours': (14, 9, 6, '实际工作时间'), 'departure': (15, 5, 26, '离职情况'),
    'paid_amounts': (16, 5, 24, '离职时已支付款项'),
}
REASONS = {f'reason_{index}': row for index, row in enumerate((0, 4, 8, 13, 17), 1)}
NARROW = {'id_number', 'phone', 'company_phone'}


def _single_line(value):
    if any(category(char).startswith('C') or category(char) in {'Zl', 'Zp'} for char in value):
        raise ValueError('中山市表格填写须为单行文本')
    return value.strip()


def _narrow(value):
    if any(east_asian_width(char) in 'FW' for char in value):
        raise ValueError('证件和联系方式超出当前栏位可接受字符宽度')
    return value


def _bounded(limit, narrow=False):
    if narrow:
        return Annotated[str, Field(max_length=limit), AfterValidator(_single_line), AfterValidator(_narrow)]
    return Annotated[str, Field(max_length=limit), AfterValidator(_single_line)]


ZhongshanApplicationRequest = create_model(
    'ZhongshanApplicationRequest', __base__=OwnBase,
    **{key: (_bounded(capacity, key in NARROW), '') for key, (_, _, capacity, _) in SLOTS.items()},
    requests=(list[_bounded(20)], Field(default_factory=list, max_length=9)),
    **{key: (list[_bounded(22)], Field(default_factory=list, max_length=4)) for key in REASONS},
)


def schema_descriptor(source_version):
    fields = [{'key': key, 'label': label, 'type': 'text', 'maxLength': limit}
              for key, (_, _, limit, label) in SLOTS.items()]
    fields.append({'key': 'requests', 'label': '仲裁请求（每项一行）', 'type': 'text_list',
                   'maxLength': 20, 'maxItems': 9})
    fields.extend({'key': key, 'label': f'第 {index} 项事实与理由（每项最多四行）',
                   'type': 'text_list', 'maxLength': 22, 'maxItems': 4}
                  for index, key in enumerate(REASONS, 1))
    return {
        'schema_id': ADAPTER, 'schema_version': 1, 'source_version': source_version, 'fields': fields,
        'defaults': ZhongshanApplicationRequest().model_dump(),
        'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
                   'trim_text': True, 'capacity_is_official_requirement': False, 'signature_field': 'manual_only'},
    }


def exact_municipal(guide):
    keys = ('province', 'city', 'district', 'region_code', 'scope_level', 'source_id', 'source_url', 'source_version')
    return tuple(guide.get(key) for key in keys) == (
        'guangdong', '中山市', '市本级', '442000', 'municipal', SOURCE_ID, SOURCE, GUIDE_SHA,
    )


def _pinned_bytes(root, relative, expected):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('中山市本级来源路径无效')
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('中山市本级来源文件暂不可用') from exc
    if sha256(raw).hexdigest() != expected:
        raise ValueError('中山市本级来源或转换版已变化')
    return raw


def staged_guide(root=None):
    """Build an isolated candidate from the reviewed, pinned source."""
    root = Path(ROOT if root is None else root).resolve()
    guide = json.loads(_pinned_bytes(root, GUIDE, GUIDE_SHA))
    guide.update(source_id=SOURCE_ID, source_version=GUIDE_SHA)
    template, = guide['templates']
    template.update(can_generate=True, adapter=ADAPTER)
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != 'application' or not exact_municipal(guide):
        raise ValueError('仅适配中山市本级自己的申请书')
    root = Path(ROOT if root is None else root).resolve()
    expected = staged_guide(root)
    if any(guide.get(key) != value for key, value in expected.items()) or template != expected['templates'][0]:
        raise ValueError('中山市本级附件与已核验来源不匹配')
    _pinned_bytes(root, LAYOUT, LAYOUT_SHA)
    return ADAPTER


def _fill_cell(cell, value):
    if cell.text.strip() or len(cell.paragraphs) != 1:
        raise ValueError('中山市申请书没有预期的空白栏位')
    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = value
    else:
        p.add_run(value)


def _fill_line(p, value):
    if not value:
        return
    after = max((i for i, run in enumerate(p.runs) if run.text.strip()), default=-1) + 1
    runs = [run for run in p.runs[after:] if run.text and not run.text.strip()]
    if not runs:
        raise ValueError('中山市申请书没有预期的空白行')
    runs[0].text = value
    for run in runs[1:]:
        run.text = ''


def fill_application(path, data):
    layout = path.read_bytes()
    if sha256(layout).hexdigest() != LAYOUT_SHA:
        raise ValueError('中山市申请书转换版已变化')
    values = ZhongshanApplicationRequest.model_validate(data).model_dump()
    doc = Document(BytesIO(layout))
    table, = doc.tables
    if len(table.rows) != 18 or doc.paragraphs[0].text != '劳动人事争议仲裁申请书':
        raise ValueError('中山市申请书版式不符')
    for field, (row, column, _, _) in SLOTS.items():
        if values[field]:
            _fill_cell(table.rows[row].cells[column], values[field])
    requests = table.rows[8].cells[2].paragraphs
    for i, value in enumerate(values['requests']):
        _fill_line(requests[i], value)
    reasons = table.rows[17].cells[2].paragraphs
    for field, start in REASONS.items():
        for index, value in enumerate(values[field], start):
            _fill_line(reasons[index], value)
    return PreservedPackageDocument(doc, layout)
