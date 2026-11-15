"""Fill body slots on the independently linked Qingjian worker application form."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from re import fullmatch

from docx import Document
from pydantic import Field

from regional_documents import PreservedPackageDocument
from regional_fixed_layout import fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase
from regional_qingjian_guides import staged_guide


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_qingjian_worker_application_v1"
TEMPLATE_ID = "yulin-610830-worker-application"
LAYOUT = Path("templates/_docx/_regional/shaanxi/qingjian-610830-worker-application-private.docx")
ORIGINAL_SHA256 = "94dc67c1b0913b2e3c7f4e5f244c390d19c626fd5c109b5eab0f494caa31d1e1"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
LAYOUT_SHA256 = "3dfde2f43d6da3392359c75bb0348c5b24b218f54d335dbbf23d7cc5ff014e4e"
REQUEST_LINES = (16, 18, 20, 22)
FACT_LINES = tuple(range(24, 34))
WIDTH = 40
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"


class WorkerApplicationRequest(OwnBase):
    requests: list[fixed_line(WIDTH, EXTRA_WIDE)] = Field(default_factory=list, max_length=len(REQUEST_LINES))
    facts: list[fixed_line(WIDTH, EXTRA_WIDE)] = Field(default_factory=list, max_length=len(FACT_LINES))


def fill_application(layout: bytes, values: dict) -> PreservedPackageDocument:
    if sha256(layout).hexdigest() != LAYOUT_SHA256:
        raise ValueError("清涧县劳动者申请书版式已变化")
    data = WorkerApplicationRequest.model_validate(values)
    document = Document(BytesIO(layout))
    paragraphs = document.paragraphs
    if len(paragraphs) != 43:
        raise ValueError("清涧县劳动者申请书段落结构已变化")
    if any(not fullmatch(f"{sequence}[、.．]", paragraphs[index].text.strip())
           for sequence, index in enumerate(REQUEST_LINES, 1)):
        raise ValueError("清涧县劳动者申请书请求编号已变化")
    if any(paragraphs[index].text.strip() for index in FACT_LINES):
        raise ValueError("清涧县劳动者申请书事实栏已变化")

    for slots, lines in ((REQUEST_LINES, data.requests), (FACT_LINES, data.facts)):
        for index, value in zip(slots, lines):
            if value:
                paragraph = paragraphs[index]
                properties, = paragraph._p.xpath("./w:pPr/w:rPr")
                paragraph.add_run(value)._r.insert(0, deepcopy(properties))
    return PreservedPackageDocument(document, layout)


def staged_worker_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root):
        raise ValueError("清涧县劳动者申请书版式超出候选目录")
    try:
        checksum = sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("缺少清涧县劳动者申请书版式") from exc
    if checksum != LAYOUT_SHA256:
        raise ValueError("清涧县劳动者申请书版式已变化")

    worker_source = guide["role_sources"]["劳动者"]
    guide["source_version"] = digest(f'{guide["source_version"]}:{LAYOUT_SHA256}')
    guide["can_generate"] = True
    guide["templates"] = [{
        "id": TEMPLATE_ID, "original_name": "劳动人事争议仲裁申请书（劳动者）.docx",
        "service_object": "劳动者", "region_code": guide["region_code"],
        "guide_source_url": worker_source, "source_url": worker_source,
        "official_sha256": ORIGINAL_SHA256, "official_kind": "blank", "original_format": "DOCX",
        "file_type": "docx", "download_status": "official_link_only",
        "file": LAYOUT.as_posix(), "sha256": LAYOUT_SHA256, "file_origin": "official-blank-reflowed-layout",
        "adapter": ADAPTER, "document_types": ["application"], "can_generate": True, "generation_mode": "blank",
    }]
    guide["sections"]["官网附件核验"] += "劳动者空表仅辅助填写仲裁请求和事实理由，署名与日期保留手填。"
    guide["warnings"] = ["当前只提供劳动者申请书正文填写。用人单位申请书和授权委托书仍待验收。"]
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配清涧县劳动者申请书")
    expected = staged_worker_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("清涧县申请书与已核验的劳动者来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [
            {"key": key, "label": label, "type": "text_list", "maxLength": WIDTH, "maxItems": len(lines)}
            for key, label, lines in (("requests", "仲裁请求", REQUEST_LINES), ("facts", "事实和理由", FACT_LINES))
        ],
        "defaults": WorkerApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    return {key: {"line_widths": [WIDTH] * len(lines), "max_lines": len(lines), "no_newlines": True, "trim": True}
            for key, lines in (("requests", REQUEST_LINES), ("facts", FACT_LINES))}
