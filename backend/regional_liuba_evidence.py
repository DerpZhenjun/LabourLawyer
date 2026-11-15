"""Fill Liuba County's verified nine-row workbook."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from re import fullmatch, sub
from typing import Annotated
from unicodedata import category
from zipfile import ZipFile

from lxml import etree
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from regional_guides import digest
from regional_hanzhong_guides import LIUBA_URL, REGIONS


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_liuba_worker_evidence_xlsx_v1"
TEMPLATE_ID = "hanzhong-610729-evidence"
LAYOUT = Path("templates/_docx/_regional/shaanxi/liuba-610729-private-source.xlsx")
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CODE = "610729"
SOURCE_ID = digest(LIUBA_URL)[:24]
IDENTITY = {
    "province": "shaanxi", "city": "汉中市", "district": "留坝县", "region_code": CODE,
    "scope_level": "district", "source_id": SOURCE_ID, "source_url": LIUBA_URL,
    "source_version": REGIONS[CODE][3],
}
SOURCE_SHA256 = "52da5de34a02c1bde6808e428fd95082d63b731b7480209385ab5010a87dd28a"
SHEET = "xl/worksheets/sheet1.xml"
CORE_METADATA = "docProps/core.xml"
CUSTOM_METADATA = "docProps/custom.xml"
MAX_ITEMS = 9
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
BOUND = {
    "file": LAYOUT.as_posix(), "sha256": SOURCE_SHA256, "adapter": ADAPTER,
    "can_generate": True, "document_types": ["evidence"], "output_format": "xlsx",
}


def plain_line(value: str) -> str:
    if any(category(char).startswith("C") or category(char) in {"Zl", "Zp"}
           or ord(char) in {0xFFFE, 0xFFFF} for char in value):
        raise ValueError("每个单元格请填写一行文字")
    return value.strip()


def positive_page_count(value: str) -> str:
    if value and not fullmatch(r"[1-9][0-9]{0,3}", value):
        raise ValueError("页数请填写 1 至 9999 的整数")
    return value


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: Annotated[str, Field(min_length=1, max_length=22), AfterValidator(plain_line), Field(min_length=1)]
    purpose: Annotated[str, Field(max_length=30), AfterValidator(plain_line)] = ""
    page_count: Annotated[str, Field(max_length=4), AfterValidator(plain_line), AfterValidator(positive_page_count)] = ""


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    items: list[EvidenceItem] = Field(default_factory=list, max_length=MAX_ITEMS)


def _xml(data: bytes):
    return etree.fromstring(data, parser=etree.XMLParser(resolve_entities=False, no_network=True))


def _xml_bytes(element) -> bytes:
    return etree.tostring(element, encoding="UTF-8", xml_declaration=True, standalone=True)


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def _set_cell(cell, value: str | int) -> None:
    if value == "":
        return
    if isinstance(value, int):
        cell.set("t", "n")
        etree.SubElement(cell, _tag("v")).text = str(value)
    else:
        cell.set("t", "inlineStr")
        axis = etree.SubElement(cell, _tag("is"))
        text = etree.SubElement(axis, _tag("t"))
        # Excel treats _xNNNN_ as an escape even in explicitly textual cells.
        text.text = sub(r"_x[0-9A-Fa-f]{4}_", lambda match: "_x005F_" + match[0][1:], value)


def _fill_sheet(worksheet: bytes, rows: list[EvidenceItem]) -> bytes:
    root = _xml(worksheet)
    cells = {cell.get("r"): cell for cell in root.iter(_tag("c"))}
    for number in range(3, 3 + MAX_ITEMS):
        if any(cells[f"{col}{number}"].find(_tag("v")) is not None or
               cells[f"{col}{number}"].find(_tag("is")) is not None or
               cells[f"{col}{number}"].find(_tag("f")) is not None for col in "BCDE"):
            raise ValueError("官方证据清单的填写区已变化")
    for index, row in enumerate(rows, 1):
        values = (index, row.name, row.purpose, int(row.page_count) if row.page_count else "")
        for column, value in zip("BCDE", values, strict=True):
            _set_cell(cells[f"{column}{index + 2}"], value)
    return _xml_bytes(root)


def _scrub_metadata(payload: bytes, remove_all: bool) -> bytes:
    root = _xml(payload)
    for field in tuple(root):
        if remove_all or etree.QName(field).localname in {"creator", "lastModifiedBy"}:
            root.remove(field)
    return _xml_bytes(root)


def fill_evidence(layout: bytes, values: dict) -> bytes:
    if sha256(layout).hexdigest() != SOURCE_SHA256:
        raise ValueError("留坝县官方证据清单原件已变化")
    rows = EvidenceRequest.model_validate(values).items
    result = BytesIO()
    with ZipFile(BytesIO(layout)) as original, ZipFile(result, mode="w") as generated:
        replacements = {
            SHEET: _fill_sheet(original.read(SHEET), rows),
            CORE_METADATA: _scrub_metadata(original.read(CORE_METADATA), remove_all=False),
            CUSTOM_METADATA: _scrub_metadata(original.read(CUSTOM_METADATA), remove_all=True),
        }
        for member in original.infolist():
            data = replacements[member.filename] if member.filename in replacements else original.read(member)
            generated.writestr(member, data)
    return result.getvalue()


def _verified_attachment(guide, template):
    return (
        guide.get("verification_status") == "verified"
        and all(guide.get(key) == value for key, value in IDENTITY.items())
        and template.get("region_code") == CODE
        and template.get("source_url") == LIUBA_URL
        and template.get("id") == TEMPLATE_ID
        and template.get("official_kind") == "blank"
        and template.get("official_sha256") == SOURCE_SHA256
        and template.get("file_type") == "xlsx"
        and template.get("download_status") == "official_link_only"
        and template.get("case_scope") is None
    )


def _approved_file(root):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root):
        return False
    try:
        return sha256(path.read_bytes()).hexdigest() == SOURCE_SHA256
    except OSError:
        return False


def with_liuba_workbook(guide, root):
    if guide.get("region_code") != CODE:
        return guide
    matches = [entry for entry in guide.get("templates", []) if entry.get("id") == TEMPLATE_ID]
    if len(matches) != 1 or not _verified_attachment(guide, matches[0]) or not _approved_file(root):
        return guide
    bound = {**matches[0], **BOUND}
    return {**guide, "can_generate": True,
            "templates": [bound if entry is matches[0] else entry for entry in guide["templates"]]}


def checked_adapter(guide, template, kind, root):
    if (kind != "evidence" or not _verified_attachment(guide, template)
            or any(template.get(key) != value for key, value in BOUND.items())
            or not _approved_file(root)):
        raise ValueError("留坝县证据清单与已核验的本地原件不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [{"key": "items", "label": "证据项目", "type": "object_list", "maxItems": MAX_ITEMS,
                    "fields": [
                        {"key": "name", "label": "名称", "type": "text", "required": True, "maxLength": 22},
                        {"key": "purpose", "label": "证明内容", "type": "text", "maxLength": 30},
                        {"key": "page_count", "label": "页数", "type": "text", "format": "positive-integer", "maxLength": 4},
                    ]}],
        "defaults": EvidenceRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }
