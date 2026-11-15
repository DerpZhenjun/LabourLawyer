"""Fill only the body lines on the official Xi’an High-Tech Zone application."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from docx import Document
from pydantic import Field

from regional_documents import PreservedPackageDocument
from regional_fixed_layout import display_width, fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase
from regional_xian_high_tech_guide import staged_guide


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_xian_high_tech_application_v1"
TEMPLATE_ID = "xian-610152-application"
LAYOUT = Path("templates/_docx/_regional/shaanxi/xian-610152-application-private.docx")
ORIGINAL_SHA256 = "a1bb65264399a7c44a326670f79e78722ebc6c3bd43933f957fd850ccceea893"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
LAYOUT_SHA256 = "fcf9ca7894f8582c85c4b22e8ed74ad3277848cbbd208aeb6f906c0d5b391994"
REQUEST_LINES = tuple(range(4, 17, 2))
FACT_LINES = tuple(range(20, 47, 2))
WIDTH = 64
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"


class ApplicationRequest(OwnBase):
    requests: list[fixed_line(WIDTH, EXTRA_WIDE)] = Field(default_factory=list, max_length=len(REQUEST_LINES))
    facts: list[fixed_line(WIDTH, EXTRA_WIDE)] = Field(default_factory=list, max_length=len(FACT_LINES))


def fill_application(layout: bytes, values: dict) -> PreservedPackageDocument:
    if sha256(layout).hexdigest() != LAYOUT_SHA256:
        raise ValueError("西安高新区申请书版式已变化")
    data = ApplicationRequest.model_validate(values)
    document = Document(BytesIO(layout))
    paragraphs = document.paragraphs
    if len(paragraphs) != 61 or len(document.tables) != 1:
        raise ValueError("西安高新区申请书段落结构已变化")
    for slots, lines in ((REQUEST_LINES, data.requests), (FACT_LINES, data.facts)):
        for index, value in zip(slots, lines):
            if not value:
                continue
            paragraph = paragraphs[index]
            underlined = [run for run in paragraph.runs if run.underline]
            if len(underlined) != 1 or set(underlined[0].text) != {" "} or len(underlined[0].text) not in {70, 71}:
                raise ValueError("西安高新区申请书正文横线已变化")
            run, = underlined
            run.text = value + " " * (len(run.text) - display_width(value, EXTRA_WIDE))
    return PreservedPackageDocument(document, layout)


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root):
        raise ValueError("西安高新区申请书版式超出候选目录")
    try:
        checksum = sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("缺少西安高新区申请书版式") from exc
    if checksum != LAYOUT_SHA256:
        raise ValueError("西安高新区申请书版式已变化")

    source_url = guide["source_url"]
    guide["source_version"] = digest(f'{guide["source_version"]}:{LAYOUT_SHA256}')
    guide["can_generate"] = True
    guide["templates"] = [{
        "id": TEMPLATE_ID, "original_name": "劳动争议仲裁申请书.docx",
        "service_object": "劳动者、用人单位", "region_code": guide["region_code"],
        "guide_source_url": source_url, "source_url": source_url,
        "official_sha256": ORIGINAL_SHA256, "official_kind": "blank", "original_format": "DOCX",
        "file_type": "docx", "download_status": "official_link_only",
        "file": LAYOUT.as_posix(), "sha256": LAYOUT_SHA256, "file_origin": "official-blank-reflowed-layout",
        "adapter": ADAPTER, "document_types": ["application"], "can_generate": True, "generation_mode": "blank",
    }]
    guide["sections"]["官网附件核验"] += "申请书仅辅助填写请求事项和事实理由。双方信息、签名捺印与日期手填。"
    guide["warnings"] = ["当前仅提供申请书正文填写。送达地址确认书、证据目录等附件仍待验收。"]
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配西安高新区申请书")
    expected = staged_application_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("西安高新区申请书与已核验的西安高新区来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [
            {"key": key, "label": label, "type": "text_list", "maxLength": WIDTH, "maxItems": len(lines)}
            for key, label, lines in (("requests", "请求事项", REQUEST_LINES), ("facts", "事实和理由", FACT_LINES))
        ],
        "defaults": ApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    return {key: {"line_widths": [WIDTH] * len(lines), "max_lines": len(lines), "no_newlines": True, "trim": True}
            for key, lines in (("requests", REQUEST_LINES), ("facts", FACT_LINES))}
