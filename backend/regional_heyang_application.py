"""Fill the three verified request rows of the Heyang County worker form."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from docx import Document
from pydantic import create_model

from regional_fixed_layout import display_width, fixed_line
from regional_guides import digest
from regional_heyang_guides import staged_guide
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_heyang_worker_application_v1"
TEMPLATE_ID = "weinan-610524-worker-application"
LAYOUT = Path("templates/_docx/_regional/shaanxi/heyang-610524-worker-private.docx")
CONVERSION_SHA256 = "4dbbaf712ff531e1eaba57b1ca697657679a30ad2180dbf797026d8fd43c0d9b"
ORIGINAL_SHA256 = "57714685d0956c011f048e9705130a8e172daba2c59ee5494b2c9e97707540de"
ORIGINAL_URL = "https://zwfwxtzx.shaanxi.gov.cn/sxfw//group1/M00/18/BE/rBIxU2ChwH2ASAidAAA6AG3KLpY158.doc"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"
CAPACITY = 30
SLOTS = {
    "request_one": (7, "第一项请求"),
    "request_two": (8, "第二项请求"),
    "request_three": (9, "第三项请求"),
}
HeyangWorkerApplicationRequest = create_model(
    "HeyangWorkerApplicationRequest", __base__=OwnBase,
    **{key: (fixed_line(CAPACITY, EXTRA_WIDE), "") for key in SLOTS},
)


def fill_application(layout, values):
    if sha256(layout).hexdigest() != CONVERSION_SHA256:
        raise ValueError("合阳县劳动者申请书转换件字节已变化")
    data = HeyangWorkerApplicationRequest.model_validate(values)
    document = Document(BytesIO(layout))
    if len(document.paragraphs) != 18:
        raise ValueError("合阳县申请书段落结构已变化")
    for key, (index, _) in SLOTS.items():
        slot, = document.paragraphs[index].runs
        if slot.text != " " * CAPACITY or slot.underline is not True:
            raise ValueError("合阳县申请书请求空栏已变化")
        value = getattr(data, key)
        if value:
            slot.text = value + " " * (CAPACITY - display_width(value, EXTRA_WIDE))
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for relation_id, relation in list(part.rels.items()):
            if relation.reltype.endswith(suffix):
                del part.rels[relation_id]
    for field in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, field, "")
    return document


def staged_worker_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    path = (root / LAYOUT).resolve()
    if not path.is_relative_to(root):
        raise ValueError("合阳县申请书转换件超出候选目录")
    try:
        checksum = sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("缺少合阳县劳动者申请书转换件") from exc
    if checksum != CONVERSION_SHA256:
        raise ValueError("合阳县劳动者申请书转换件字节已变化")
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
        "劳动者申请书按自然人格式，仅开放三行请求。"
        "劳动者身份证栏与用人单位申请书栏挂载同一自然人申请书，各自附件用途仍待核验。"
    )
    guide["warnings"] = [
        "请按原表补全双方信息、事实与理由、受理机关、签名及日期。",
        "用人单位事项承诺时限按官网原样显示，请向合阳县人社局核实。",
    ]
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配合阳县劳动者申请书")
    expected = staged_worker_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("合阳县申请书与已核验的劳动者来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [{"key": key, "label": label, "type": "text", "maxLength": CAPACITY}
                   for key, (_, label) in SLOTS.items()],
        "defaults": HeyangWorkerApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    return {key: {"first_width": CAPACITY, "later_width": CAPACITY, "max_lines": 1,
                  "no_newlines": True, "trim": True} for key in SLOTS}
