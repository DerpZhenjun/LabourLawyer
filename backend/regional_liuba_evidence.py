"""Fill Liuba County's verified nine-row workbook."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from re import fullmatch
from typing import Annotated
from zipfile import ZipFile

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from regional_guides import digest
from regional_workbook_xml import parse_xml, plain_line, scrub_metadata, set_cell, spreadsheet_tag, xml_bytes
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
BOUND = {
    "file": LAYOUT.as_posix(), "sha256": SOURCE_SHA256, "adapter": ADAPTER,
    "can_generate": True, "document_types": ["evidence"], "output_format": "xlsx",
}


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


def _fill_sheet(worksheet: bytes, rows: list[EvidenceItem]) -> bytes:
    root = parse_xml(worksheet)
    cells = {cell.get("r"): cell for cell in root.iter(spreadsheet_tag("c"))}
    for number in range(3, 3 + MAX_ITEMS):
        if any(cells[f"{col}{number}"].find(spreadsheet_tag("v")) is not None or
               cells[f"{col}{number}"].find(spreadsheet_tag("is")) is not None or
               cells[f"{col}{number}"].find(spreadsheet_tag("f")) is not None for col in "BCDE"):
            raise ValueError("官方证据清单的填写区已变化")
    for index, row in enumerate(rows, 1):
        values = (index, row.name, row.purpose, int(row.page_count) if row.page_count else "")
        for column, value in zip("BCDE", values, strict=True):
            set_cell(cells[f"{column}{index + 2}"], value)
    return xml_bytes(root)


def fill_evidence(layout: bytes, values: dict) -> bytes:
    if sha256(layout).hexdigest() != SOURCE_SHA256:
        raise ValueError("留坝县官方证据清单原件已变化")
    rows = EvidenceRequest.model_validate(values).items
    result = BytesIO()
    with ZipFile(BytesIO(layout)) as original, ZipFile(result, mode="w") as generated:
        replacements = {
            SHEET: _fill_sheet(original.read(SHEET), rows),
            CORE_METADATA: scrub_metadata(original.read(CORE_METADATA), remove_all=False),
            CUSTOM_METADATA: scrub_metadata(original.read(CUSTOM_METADATA), remove_all=True),
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
