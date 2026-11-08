"""Fill Baoji's municipal evidence catalog without editing its source package."""
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from re import fullmatch
from typing import Annotated
from unicodedata import category

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from pydantic import AfterValidator, Field

from regional_documents import PreservedPackageDocument
from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = 'shaanxi_baoji_municipal_evidence_v1'
SOURCE = 'https://rsj.baoji.gov.cn/col9976/col1293/202305/t20230512_658694.html'
SOURCE_ID = digest(SOURCE)[:24]
GUIDE = Path('reports/overnight-gap-closure-20261030/localities/baoji-municipal-own-source/GUIDE.json')
GUIDE_SHA = '81aef3858a9bc0925c7095c2438f7064b3960c8daeedbf07a63b746e2f513850'
LAYOUT = Path('templates/_docx/_regional/shaanxi/baoji-municipal-evidence.docx')
LAYOUT_ORIGIN = 'official-blank-metadata-sanitized-layout'
LAYOUT_SHA = 'fd28374f4c2a6b6cf777df3bde5f890596bb7370b349c685a821fc0dc525695e'
MAX_ITEMS = 9
EVIDENCE_FIELDS = (('name', '证据名称', 12), ('purpose', '证明事项及证明目的', 26), ('page_range', '页码', 9))


def _single_line(value):
    if any(category(char).startswith('C') or category(char) in {'Zl', 'Zp'} for char in value):
        raise ValueError('每个单元格请填写一段文字，不手动换行')
    return value.strip()


def _page_range(value):
    if not value:
        return value
    matched = fullmatch(r'([1-9][0-9]{0,3})(?:[-\u2013\u2014]([1-9][0-9]{0,3}))?', value)
    if not matched or (matched[2] and int(matched[2]) < int(matched[1])):
        raise ValueError('请填写单个页码或按升序填写页码范围')
    return '-'.join(page for page in matched.groups() if page)


def _line(limit):
    return Annotated[str, Field(max_length=limit), AfterValidator(_single_line)]


class BaojiEvidenceItem(OwnBase):
    name: _line(12) = ''
    purpose: _line(26) = ''
    page_range: Annotated[str, Field(max_length=9), AfterValidator(_single_line), AfterValidator(_page_range)] = ''


class BaojiEvidenceRequest(OwnBase):
    items: list[BaojiEvidenceItem] = Field(default_factory=list, max_length=MAX_ITEMS)


def fill_evidence(layout, values):
    if sha256(layout).hexdigest() != LAYOUT_SHA:
        raise ValueError('宝鸡市本级证据目录空白表格已变化')
    data = BaojiEvidenceRequest.model_validate(values)
    document = Document(BytesIO(layout))
    table = document.tables[0]
    table.autofit = False
    for index, row in enumerate(table.rows[2:2 + MAX_ITEMS]):
        item = data.items[index] if index < len(data.items) else None
        fields = (str(index + 1), item.name, item.purpose, item.page_range) if item else ('', '', '', '')
        for column, (cell, value) in enumerate(zip(row.cells, fields, strict=True)):
            paragraph = cell.paragraphs[0]
            if column == 0:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif value:
                paragraph.paragraph_format.line_spacing = Pt(13)
            if paragraph.runs:
                paragraph.runs[0].text = value
            elif value:
                paragraph.add_run(value)
    signature, instruction, _ = table.rows[11].cells[0].paragraphs
    # The source explicitly instructs the filer to remove the highlighted note.
    for run in signature.runs[1:]:
        signature._p.remove(run._r)
    instruction._p.getparent().remove(instruction._p)
    return PreservedPackageDocument(document, layout)


def schema_descriptor(source_version):
    return {
        'schema_id': ADAPTER, 'schema_version': 1, 'source_version': source_version,
        'fields': [{'key': 'items', 'label': '证据项目', 'type': 'object_list', 'maxItems': MAX_ITEMS, 'fields': [
            {'key': key, 'label': label, 'type': 'text', 'maxLength': limit}
            for key, label, limit in EVIDENCE_FIELDS
        ]}],
        'defaults': BaojiEvidenceRequest().model_dump(),
        'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
                   'trim_text': True, 'capacity_is_official_requirement': False, 'signature_field': 'manual_only'},
    }


def exact_municipal(guide):
    keys = ('province', 'city', 'district', 'region_code', 'scope_level', 'source_id', 'source_url', 'source_version')
    return tuple(guide.get(key) for key in keys) == (
        'shaanxi', '宝鸡市', '市本级', '610300', 'municipal', SOURCE_ID, SOURCE, GUIDE_SHA,
    )


def _pinned_bytes(root, relative, expected):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('宝鸡市本级来源路径无效')
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('宝鸡市本级来源暂不可用') from exc
    if sha256(raw).hexdigest() != expected:
        raise ValueError('宝鸡市本级来源或空白表格已变化')
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = json.loads(_pinned_bytes(root, GUIDE, GUIDE_SHA))
    guide.update(source_id=SOURCE_ID, source_version=GUIDE_SHA)
    guide['templates'][0].update(can_generate=True, adapter=ADAPTER)
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != 'evidence' or not exact_municipal(guide):
        raise ValueError('仅适配宝鸡市本级官方证据目录')
    root = Path(ROOT if root is None else root).resolve()
    expected = staged_guide(root)
    if any(guide.get(key) != value for key, value in expected.items()) or template != expected['templates'][0]:
        raise ValueError('宝鸡市本级证据目录与已核验来源不匹配')
    _pinned_bytes(root, LAYOUT, LAYOUT_SHA)
    return ADAPTER
