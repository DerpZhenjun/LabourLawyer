"""Fill the independently reviewed Xixiang worker application reference."""
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated
from unicodedata import category

from docx import Document
from pydantic import AfterValidator, Field

from regional_huian_quangang_request import OwnBase, bounded
from regional_hanzhong_guides import staged_guide


REFERENCE_SHA256 = 'eb9641450cd2e7d39ab1bc7bc47ff10e61cd38192e508855613a0d1688778882'
COMMITTEE = '西乡县劳动人事争议仲裁委员会'
ADAPTER = 'shaanxi_xixiang_worker_reference_v1'
ROOT = Path(__file__).resolve().parents[1]
LAYOUT = Path('templates/_docx/_regional/shaanxi/xixiang-610724-private-reference.docx')
TEMPLATE_ID = 'hanzhong-610724-application'
IDENTITY = ('province', 'city', 'district', 'scope_level', 'region_code', 'source_url', 'source_id', 'source_version')
LABELS = {
    'applicant_name': '申请人姓名', 'gender': '性别', 'birth_date': '出生日期', 'ethnicity': '民族',
    'household_or_nationality': '户籍所在地或国籍', 'current_address': '现住址', 'applicant_phone': '申请人联系电话',
    'mailing_address': '有效的通讯地址', 'postcode': '邮政编码', 'respondent_name': '被申请人',
    'respondent_representative': '被申请人法定代表人或负责人', 'respondent_position': '被申请人代表职务',
    'respondent_address': '被申请人住所', 'respondent_phone': '被申请人联系电话', 'third_party_name': '第三人',
    'third_party_representative': '第三人法定代表人或负责人', 'third_party_position': '第三人代表职务',
    'third_party_address': '第三人住所', 'third_party_phone': '第三人联系电话', 'requests': '仲裁请求',
    'facts': '事实和理由', 'application_copies': '申请书副本份数', 'evidence_copies': '证据材料份数',
}


def _single_line(value):
    if any(category(c).startswith('C') or category(c) in {'Zl', 'Zp'} for c in value):
        raise ValueError('本栏请填写一行文字')
    return value.strip()


def _line(limit):
    return Annotated[str, Field(max_length=limit), AfterValidator(_single_line)]


def _birth_date(value):
    if value and date.fromisoformat(value).isoformat() != value:
        raise ValueError('出生日期须为 YYYY-MM-DD')
    return value


def _facts_lines(value):
    if value.count('\n') > 5:
        raise ValueError('事实和理由最多分六段填写')
    return value


CopyCount = Annotated[str, Field(pattern=r'^(|[1-9][0-9]?)$')]


class XixiangReferenceRequest(OwnBase):
    applicant_name: _line(20) = ''
    gender: _line(6) = ''
    birth_date: Annotated[str, Field(max_length=10), AfterValidator(_birth_date)] = ''
    ethnicity: _line(12) = ''
    household_or_nationality: _line(60) = ''
    current_address: _line(75) = ''
    applicant_phone: _line(25) = ''
    mailing_address: _line(75) = ''
    postcode: _line(12) = ''
    respondent_name: _line(60) = ''
    respondent_representative: _line(24) = ''
    respondent_position: _line(24) = ''
    respondent_address: _line(75) = ''
    respondent_phone: _line(25) = ''
    third_party_name: _line(60) = ''
    third_party_representative: _line(24) = ''
    third_party_position: _line(24) = ''
    third_party_address: _line(75) = ''
    third_party_phone: _line(25) = ''
    requests: list[_line(100)] = Field(default_factory=list, max_length=4)
    facts: Annotated[bounded(480), AfterValidator(_facts_lines)] = ''
    application_copies: CopyCount = ''
    evidence_copies: CopyCount = ''


def fill_application(original, values):
    if sha256(original).hexdigest() != REFERENCE_SHA256:
        raise ValueError('西乡县申请书样表已变化')
    data = XixiangReferenceRequest.model_validate(values)
    document = Document(BytesIO(original))
    paragraphs = document.paragraphs
    if len(paragraphs) != 29 or paragraphs[0].text != '劳动仲裁申请书' or paragraphs[24].text != COMMITTEE:
        raise ValueError('西乡县申请书样表填写位置已变化')

    date_text = '    年   月   日'
    if data.birth_date:
        birthday = date.fromisoformat(data.birth_date)
        date_text = f'{birthday.year}年{birthday.month}月{birthday.day}日'
    replacements = {
        1: f'申 请 人：{data.applicant_name}    性别：{data.gender}',
        2: f'出生时间：{date_text}    民族：{data.ethnicity}',
        3: f'户籍所在地（或外国人注明国籍）：{data.household_or_nationality}',
        4: f'现住址：{data.current_address}',
        5: f'联系电话：{data.applicant_phone}',
        6: f'确认有效的通讯地址：{data.mailing_address}',
        7: f'邮政编码：{data.postcode}',
        8: f'被申请人：{data.respondent_name}',
        9: f'法定代表人（主要负责人）：{data.respondent_representative}',
        10: f'职务：{data.respondent_position}',
        11: f'住所：{data.respondent_address}',
        12: f'联系电话：{data.respondent_phone}',
        13: f'第三人：{data.third_party_name}',
        14: f'法定代表人（主要负责人）：{data.third_party_representative}',
        15: f'职务：{data.third_party_position}',
        16: f'住所：{data.third_party_address}    联系电话：{data.third_party_phone}',
        22: f'事实和理由：{data.facts}',
        25: f'附件：1.《仲裁申请书》副本 {data.application_copies} 份；',
        26: f'2.证据清单及有关证据材料 {data.evidence_copies} 份。',
    }
    requests = [request for request in data.requests if request]
    for index in range(4):
        text = requests[index] if index < len(requests) else ''
        replacements[18 + index] = f'{index + 1}. {text}'.rstrip()
    for index, text in replacements.items():
        paragraphs[index].runs[0].text = text

    for part, suffix in ((document.part, '/customXml'), (document.part.package, '/custom-properties')):
        for key, rel in list(part.rels.items()):
            if rel.reltype.endswith(suffix):
                del part.rels[key]
    for key in ('author', 'last_modified_by', 'comments', 'keywords', 'subject', 'identifier'):
        setattr(document.core_properties, key, '')
    return document


def staged_reference_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide('610724', root)
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root) or not path.is_file() or sha256(path.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise ValueError('西乡县核验的本地样表缺失或字节已变化')
    template = next(t for t in guide['templates'] if t['id'] == TEMPLATE_ID)
    if (template['official_kind'], template['official_sha256']) != ('sample', REFERENCE_SHA256):
        raise ValueError('西乡县来源证明与样表不匹配')
    template.update(
        adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=REFERENCE_SHA256,
        can_generate=True, document_types=['application'], generation_mode='reference_adaptation',
    )
    guide['can_generate'] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != 'application' or template.get('id') != TEMPLATE_ID:
        return None
    try:
        expected = staged_reference_candidate(root)
    except (OSError, ValueError):
        return None
    if any(guide.get(key) != expected[key] for key in IDENTITY):
        return None
    return ADAPTER if template == expected['templates'][0] else None


def schema_descriptor(source_version):
    props = XixiangReferenceRequest.model_json_schema()['properties']
    fields = []
    for key, label in LABELS.items():
        field = {'key': key, 'label': label, 'type': 'text'}
        if key == 'requests':
            field.update(type='text_list', maxItems=props[key]['maxItems'], maxLength=props[key]['items']['maxLength'])
        elif key in {'application_copies', 'evidence_copies'}:
            field.update(maxLength=2)
        else:
            field['maxLength'] = props[key]['maxLength']
        if key == 'birth_date':
            field['format'] = 'iso-date'
        fields.append(field)
    return {
        'schema_id': ADAPTER, 'schema_version': 1, 'source_version': source_version,
        'fields': fields, 'defaults': XixiangReferenceRequest().model_dump(),
        'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
                   'trim_text': True, 'capacity_is_official_requirement': False, 'signature_field': 'manual_only'},
    }
