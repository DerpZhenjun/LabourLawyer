"""Fill the reviewed body rows on Huayin's natural-person application form."""

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from docx import Document
from pydantic import Field

from regional_fixed_layout import fixed_line
from regional_guides import digest
from regional_huayin_guides import staged_guide
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_huayin_worker_application_v1"
TEMPLATE_ID = "weinan-610582-worker-application"
LAYOUT = Path("templates/_docx/_regional/shaanxi/huayin-610582-worker-private.docx")
CONVERSION_SHA256 = "be7630bbb7fd4f501f3f0e2f0d37bcd1a81285218f45c98058a7ddfbac3ca6b4"
ORIGINAL_SHA256 = "67e9fc2611a2ebf9e10e31798e96a709bfea7c42a287eb5ae3508ee3f20dcbf9"
ORIGINAL_URL = "https://zwfwxtzx.shaanxi.gov.cn/sxfw//group1/M00/06/F7/rBIxVGCiK4mAZ3CuAABiALGilko466.doc"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"
WIDTH = 40
SLOTS = {
    "requests": (17, "仲裁请求", 5),
    "facts": (24, "事实和理由", 12),
}


class HuayinWorkerApplicationRequest(OwnBase):
    requests: list[fixed_line(WIDTH, EXTRA_WIDE)] = Field(default_factory=lambda: [""], max_length=SLOTS["requests"][2])
    facts: list[fixed_line(WIDTH, EXTRA_WIDE)] = Field(default_factory=lambda: [""], max_length=SLOTS["facts"][2])


def fill_application(layout, values):
    if sha256(layout).hexdigest() != CONVERSION_SHA256:
        raise ValueError("华阴市劳动者申请书转换件字节已变化")
    data = HuayinWorkerApplicationRequest.model_validate(values)
    document = Document(BytesIO(layout))
    paragraphs = document.paragraphs
    if len(paragraphs) != 44:
        raise ValueError("华阴市申请书段落结构已变化")
    for key, (start, _, count) in SLOTS.items():
        rows = paragraphs[start:start + count]
        if any(row.text for row in rows):
            raise ValueError("华阴市申请书正文空栏已变化")
        for row, value in zip(rows, getattr(data, key)):
            if value:
                style, = row._p.xpath("./w:pPr/w:rPr")
                row.add_run(value)._r.insert(0, deepcopy(style))
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for relation_id, relation in list(part.rels.items()):
            if relation.reltype.endswith(suffix):
                del part.rels[relation_id]
    for name in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, name, "")
    return document


def staged_worker_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root):
        raise ValueError("华阴市申请书转换件超出候选目录")
    try:
        checksum = sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("缺少华阴市劳动者申请书转换件") from exc
    if checksum != CONVERSION_SHA256:
        raise ValueError("华阴市劳动者申请书转换件字节已变化")
    guide["source_version"] = digest(f'{guide["source_version"]}:{CONVERSION_SHA256}')
    guide["can_generate"] = True
    guide["templates"] = [{
        "id": TEMPLATE_ID, "original_name": "仲裁申请书（劳动者）.doc",
        "service_object": "劳动者", "region_code": guide["region_code"],
        "guide_source_url": guide["role_sources"]["劳动者"], "source_url": ORIGINAL_URL,
        "official_sha256": ORIGINAL_SHA256, "official_kind": "blank", "original_format": "DOC",
        "file_type": "doc", "download_status": "official_link_only",
        "file": LAYOUT.as_posix(), "sha256": CONVERSION_SHA256, "file_origin": "official-blank-converted-layout",
        "adapter": ADAPTER, "document_types": ["application"], "can_generate": True, "generation_mode": "blank",
    }]
    guide["sections"]["官网附件核验"] = (
        "劳动者原件是自然人格式，可填写仲裁请求以及事实和理由。"
        "单位事项链接到同一份原件，单位申请人格式仍待核验。"
    )
    guide["warnings"] = ["下载后请在原表补全双方信息、仲裁委员会名称、签名和日期。"]
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配华阴市劳动者申请书")
    expected = staged_worker_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("华阴市申请书与已核验的劳动者来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [{"key": key, "label": label, "type": "text_list", "maxLength": WIDTH, "maxItems": count}
                   for key, (_, label, count) in SLOTS.items()],
        "defaults": HuayinWorkerApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    return {key: {"line_widths": [WIDTH] * count, "max_lines": count, "no_newlines": True, "trim": True}
            for key, (_, _, count) in SLOTS.items()}
