"""Filling rules for Xiangan's own ten-row official legacy evidence list."""
from datetime import date
from hashlib import sha256
from io import BytesIO
from typing import Annotated, Literal
from unicodedata import category, east_asian_width
from zipfile import ZipFile

from docx import Document
from docx.shared import Pt
from pydantic import AfterValidator, Field

from regional_huian_quangang_request import OwnBase


REGION_CODE = '350213'
ATTACHMENT_ID = 'A637EF6EAD573C2578CA358269DED78A'
ORIGINAL_SHA256 = '57e6ecded6e510d5adfa320c4ef82887ad5aa37d4f895f191ad78ace239b6613'
LAYOUT_SHA256 = '8bff7ad229e0b515e48f51fd97757953af6989937976ec39be6c962f771a2fae'
ADAPTER = 'fujian_xiangan_legacy_evidence_v1'
ROW_KEYS = ('name', 'source', 'pageRange', 'purpose', 'originalType')
LIMITS = {
    'caseNumber': 40, 'applicantName': 40, 'respondentName': 40, 'thirdParty': 40,
    'name': 18, 'source': 8, 'pageRange': 4, 'purpose': 18,
}
LABELS = {
    'submissionNumber': '第几次举证', 'copyType': '正本或副本', 'caseNumber': '案号',
    'applicantName': '申请人', 'respondentName': '被申请人', 'thirdParty': '第三人',
    'submitterRole': '举证方', 'submitDate': '提交日期', 'name': '证据名称',
    'source': '来源', 'pageRange': '页码', 'purpose': '证明对象', 'originalType': '原件或复印件',
}


def bounded_field(key):
    limit = LIMITS[key]

    def validate(value):
        if any(category(char).startswith('C') for char in value):
            raise ValueError('请使用单行文字，不可包含控制字符')
        value = value.strip()
        if sum(2 if east_asian_width(char) in 'AFW' else 1 for char in value) > limit:
            raise ValueError('超出本表版式容量')
        return value

    return Annotated[str, Field(max_length=limit), AfterValidator(validate)]


def optional_iso_date(value):
    if value:
        day = date.fromisoformat(value)
        if day.isoformat() != value:
            raise ValueError('须为有效的 YYYY-MM-DD 日期')
    return value


class EvidenceRow(OwnBase):
    name: bounded_field('name') = ''
    source: bounded_field('source') = ''
    pageRange: bounded_field('pageRange') = ''
    purpose: bounded_field('purpose') = ''
    originalType: Literal['', '原件', '复印件'] = ''


class XianganEvidenceRequest(OwnBase):
    submissionNumber: Annotated[str, Field(pattern=r'^$|^[1-9][0-9]?$')] = ''
    copyType: Literal['', '正本', '副本'] = ''
    caseNumber: bounded_field('caseNumber') = ''
    applicantName: bounded_field('applicantName') = ''
    respondentName: bounded_field('respondentName') = ''
    thirdParty: bounded_field('thirdParty') = ''
    submitterRole: Literal['', '申请人', '被申请人', '第三人'] = ''
    submitDate: Annotated[str, Field(max_length=10), AfterValidator(optional_iso_date)] = ''
    evidenceList: list[EvidenceRow] = Field(default_factory=lambda: [EvidenceRow()], max_length=10)


def schema_descriptor(source_version):
    schema = XianganEvidenceRequest.model_json_schema()
    props = schema['properties']
    row_props = schema['$defs']['EvidenceRow']['properties']

    def field(key, prop):
        result = {'key': key, 'label': LABELS[key], 'type': 'text'}
        if 'enum' in prop:
            result['choices'] = [value for value in prop['enum'] if value]
        if 'maxLength' in prop:
            result['maxLength'] = prop['maxLength']
        return result

    fields = [field(key, prop) for key, prop in props.items() if key != 'evidenceList']
    fields[0]['maxLength'] = 2
    next(f for f in fields if f['key'] == 'submitDate')['format'] = 'iso-date'
    fields.append({
        'key': 'evidenceList', 'label': '证据清单', 'type': 'object_list', 'maxItems': 10,
        'fields': [field(key, row_props[key]) for key in ROW_KEYS],
    })
    return {
        'schema_id': 'fujian-xiangan-legacy-evidence-v1', 'schema_version': 1,
        'source_version': source_version, 'fields': fields,
        'defaults': XianganEvidenceRequest().model_dump(),
        'policy': {
            'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
            'trim_text': True, 'capacity_is_official_requirement': False,
            'capacity_is_legal_requirement': False, 'signature_field': 'manual_only',
        },
    }


def fill_layout(layout, values):
    if sha256(layout).hexdigest() != LAYOUT_SHA256:
        raise ValueError('翔安区证据清单版式已变化')
    data = XianganEvidenceRequest.model_validate(values)
    if not any(value for key, value in data.model_dump().items() if key != 'evidenceList') and not any(
        value for row in data.evidenceList for value in row.model_dump().values()
    ):
        return layout

    doc = Document(BytesIO(layout))
    paragraphs = doc.paragraphs
    if data.submissionNumber:
        paragraphs[1].runs[1].text = data.submissionNumber
    if data.caseNumber:
        paragraphs[2].runs[1].text = data.caseNumber
        for run in paragraphs[2].runs[2:]:
            run.text = ''
    for index, value in ((3, data.applicantName), (4, data.respondentName),
                         (5, data.thirdParty), (9, data.submitDate)):
        if value:
            paragraphs[index].runs[0].text += value
    for index, choice in ((1, data.copyType), (7, data.submitterRole)):
        if choice:
            for run in paragraphs[index].runs:
                run.text = run.text.replace(f'□{choice}', f'☑{choice}')

    table, = doc.tables
    for row_index, record in enumerate(data.evidenceList, start=1):
        for column, key in enumerate(ROW_KEYS, start=1):
            value = getattr(record, key)
            if value:
                run = table.rows[row_index].cells[column].paragraphs[0].add_run(value)
                run.font.size = Pt(10)

    output = BytesIO()
    with ZipFile(BytesIO(layout)) as original, ZipFile(output, 'w') as changed:
        for entry in original.infolist():
            blob = doc.part.blob if entry.filename == 'word/document.xml' else original.read(entry)
            changed.writestr(entry, blob)
    return output.getvalue()
