"""Fill the verified blank evidence checklist for Shenmu workers."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated
from unicodedata import category

from docx import Document
from docx.shared import Pt
from pydantic import AfterValidator, Field

from regional_documents import PreservedPackageDocument, fill_reference_cell
from regional_guides import digest
from regional_huian_quangang_request import OwnBase
from regional_shenmu_guides import staged_guide


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_shenmu_worker_evidence_v1"
TEMPLATE_ID = "yulin-610881-worker-evidence"
LAYOUT = Path("templates/_docx/_regional/shaanxi/shenmu-610881-worker-evidence-private.docx")
ORIGINAL_SHA256 = "b11c90c11792d175fb0353edd17dac49e7fa6df6729d542f245562bd6f8e7575"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
LAYOUT_SHA256 = "a49370590b35969d37293e53ba7cf818ab1f8404b84ca754c837704859ad7b82"
MAX_ITEMS = 10
MAX_CELL_CHARS = 24
HEADERS = ("序号", "名称", "证明内容", "页数")


def _single_line(value: str) -> str:
    if any(category(ch).startswith("C") or category(ch) in {"Zl", "Zp"} for ch in value):
        raise ValueError("证据表格每栏请填写一段文字")
    return value.strip()


CellText = Annotated[str, Field(max_length=MAX_CELL_CHARS), AfterValidator(_single_line)]
RequiredCellText = Annotated[CellText, Field(min_length=1)]
PageCount = Annotated[str, Field(pattern=r"^$|^[1-9][0-9]{0,3}$", max_length=4)]


class EvidenceItem(OwnBase):
    name: RequiredCellText
    purpose: CellText = ""
    page_count: PageCount = ""


class EvidenceRequest(OwnBase):
    items: list[EvidenceItem] = Field(default_factory=list, max_length=MAX_ITEMS)


def fill_evidence(layout: bytes, values: dict) -> PreservedPackageDocument:
    if sha256(layout).hexdigest() != LAYOUT_SHA256:
        raise ValueError("神木市劳动者证据清单版式已变化")
    form = EvidenceRequest.model_validate(values)
    document = Document(BytesIO(layout))
    table, = document.tables
    if len(table.rows) != MAX_ITEMS + 1 or tuple("".join(cell.text.split()) for cell in table.rows[0].cells) != HEADERS:
        raise ValueError("神木市劳动者证据清单表格结构已变化")

    for order, (row, item) in enumerate(zip(table.rows[1:], form.items), 1):
        for cell, value in zip(row.cells, (str(order), item.name, item.purpose, item.page_count), strict=True):
            if value:
                fill_reference_cell(cell, value)
                cell.paragraphs[0].paragraph_format.line_spacing = Pt(16)
    return PreservedPackageDocument(document, layout)


def staged_worker_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root):
        raise ValueError("神木市证据清单转换件超出候选目录")
    try:
        checksum = sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("缺少神木市劳动者证据清单转换件") from exc
    if checksum != LAYOUT_SHA256:
        raise ValueError("神木市证据清单转换件字节已变化")

    worker_source = guide["role_sources"]["劳动者"]
    guide["source_version"] = digest(f'{guide["source_version"]}:{LAYOUT_SHA256}')
    guide["can_generate"] = True
    guide["templates"] = [{
        "id": TEMPLATE_ID, "original_name": "证据清单（劳动者）.doc",
        "service_object": "劳动者", "region_code": guide["region_code"],
        "guide_source_url": worker_source, "source_url": worker_source,
        "official_sha256": ORIGINAL_SHA256, "official_kind": "blank", "original_format": "DOC",
        "file_type": "doc", "download_status": "official_link_only",
        "file": LAYOUT.as_posix(), "sha256": LAYOUT_SHA256, "file_origin": "official-blank-converted-layout",
        "adapter": ADAPTER, "document_types": ["evidence"], "can_generate": True, "generation_mode": "blank",
    }]
    guide["sections"]["官网附件核验"] = (
        "两类事项使用同一份劳动者仲裁申请书样本汇编。"
        "劳动者事项在劳动（人事）关系证明材料下提供的空白证据清单可辅助填写。"
    )
    guide["warnings"] = ["可填写劳动者证据清单。下载后请在原表填写提交人和提交时间。"]
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "evidence" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配神木市劳动者证据清单")
    expected = staged_worker_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("神木市证据清单与已核验的劳动者来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    columns = (("name", "名称", MAX_CELL_CHARS), ("purpose", "证明内容", MAX_CELL_CHARS), ("page_count", "页数", 4))
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [{
            "key": "items", "label": "证据项目", "type": "object_list", "maxItems": MAX_ITEMS,
            "fields": [
                {"key": key, "label": label, "type": "text", "maxLength": length,
                 **({"required": True} if key == "name" else {}),
                 **({"format": "positive-integer"} if key == "page_count" else {})}
                for key, label, length in columns
            ],
        }],
        "defaults": EvidenceRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "xml",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }
