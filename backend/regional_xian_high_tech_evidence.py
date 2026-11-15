"""Fill the twelve blank rows in Xi’an High-Tech Zone's evidence workbook."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated
from zipfile import ZipFile

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from regional_workbook_xml import parse_xml, plain_line, scrub_metadata, set_cell, spreadsheet_tag, xml_bytes
from regional_xian_high_tech_application import matches_guide_source


ADAPTER = "shaanxi_xian_high_tech_evidence_xlsx_v1"
TEMPLATE_ID = "xian-610152-evidence"
LAYOUT = Path("templates/_docx/_regional/shaanxi/xian-610152-evidence-private.xlsx")
SOURCE_SHA256 = "04577e50656b06bffde477959098be5ebf31ed1be191951eac16659495340c9e"
SHEET = "xl/worksheets/sheet1.xml"
FIRST_ROW = 6
LAST_ROW = 17
MAX_ITEMS = LAST_ROW - FIRST_ROW + 1


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: Annotated[str, Field(max_length=7), AfterValidator(plain_line), Field(min_length=1)]
    page_range: Annotated[str, Field(max_length=5), AfterValidator(plain_line)] = ""
    source: Annotated[str, Field(max_length=6), AfterValidator(plain_line)] = ""
    purpose: Annotated[str, Field(max_length=12), AfterValidator(plain_line)] = ""


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    items: list[EvidenceItem] = Field(default_factory=list, max_length=MAX_ITEMS)


def _fill_sheet(worksheet: bytes, rows: list[EvidenceItem]) -> bytes:
    root = parse_xml(worksheet)
    cells = {cell.get("r"): cell for cell in root.iter(spreadsheet_tag("c"))}
    for index in range(FIRST_ROW, LAST_ROW + 1):
        for col in "ABCDE":
            cell = cells.get(f"{col}{index}")
            if cell is None or any(child.tag != spreadsheet_tag("extLst") for child in cell):
                raise ValueError("西安高新区证据目录的空白行已变化")
    for index, row in enumerate(rows, 1):
        values = (index, row.name, row.page_range, row.source, row.purpose)
        for col, value in zip("ABCDE", values, strict=True):
            set_cell(cells[f"{col}{FIRST_ROW + index - 1}"], value)
    return xml_bytes(root)


def fill_evidence(layout: bytes, values: dict) -> bytes:
    if sha256(layout).hexdigest() != SOURCE_SHA256:
        raise ValueError("西安高新区证据目录原件已变化")
    rows = EvidenceRequest.model_validate(values).items
    output = BytesIO()
    with ZipFile(BytesIO(layout)) as original, ZipFile(output, mode="w") as generated:
        replacements = {
            SHEET: _fill_sheet(original.read(SHEET), rows),
            "docProps/core.xml": scrub_metadata(original.read("docProps/core.xml"), remove_all=False),
            "docProps/custom.xml": scrub_metadata(original.read("docProps/custom.xml"), remove_all=True),
        }
        for member in original.infolist():
            data = replacements[member.filename] if member.filename in replacements else original.read(member)
            generated.writestr(member, data)
    return output.getvalue()


def _verified_template(guide, root):
    if not matches_guide_source(guide, root):
        return None
    root = Path(root).resolve()
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root):
        return None
    try:
        if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
            return None
    except OSError:
        return None
    return {
        "id": TEMPLATE_ID, "original_name": "证据目录.xlsx",
        "service_object": "劳动者、用人单位", "region_code": "610152",
        "guide_source_url": guide["source_url"], "source_url": guide["source_url"],
        "official_sha256": SOURCE_SHA256, "official_kind": "blank", "original_format": "XLSX",
        "file_type": "xlsx", "download_status": "official_link_only",
        "file": LAYOUT.as_posix(), "sha256": SOURCE_SHA256,
        "file_origin": "official-blank-layout-metadata-sanitized", "output_format": "xlsx",
        "adapter": ADAPTER, "document_types": ["evidence"], "can_generate": True, "generation_mode": "blank",
    }


def with_xian_high_tech_workbook(guide, root):
    template = _verified_template(guide, root)
    if template is None or any(entry.get("id") == TEMPLATE_ID for entry in guide["templates"]):
        return guide
    return {**guide, "can_generate": True, "templates": [*guide["templates"], template]}


def checked_adapter(guide, template, kind, root):
    expected = _verified_template(guide, root)
    if kind != "evidence" or expected is None or template != expected:
        raise ValueError("西安高新区证据目录与已核验的本区原件不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = (
        ("name", "证据名称", 7), ("page_range", "页码范围", 5),
        ("source", "来源", 6), ("purpose", "证明目的", 12),
    )
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [{"key": "items", "label": "证据项目", "type": "object_list", "maxItems": MAX_ITEMS,
                    "fields": [{"key": key, "label": label, "type": "text", "maxLength": limit,
                                **({"required": True} if key == "name" else {})}
                               for key, label, limit in fields]}],
        "defaults": EvidenceRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }
