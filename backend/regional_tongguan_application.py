"""Fill only the reviewed body fields of Tongguan County's two application forms."""

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from docx import Document
from pydantic import create_model

from regional_fixed_layout import fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_tongguan_role_application_v1"
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/weinan-tongguan-own-sources/SOURCE-OBSERVATIONS.json")
SOURCE_SHA256 = "f980f496e98114ea5945963ff79ae22f47af86233826f0c433fcbf17fe757ed2"
ORIGINAL_LINKS = {
    "worker": "https://zwfwxtzx.shaanxi.gov.cn/sxfw//group1/M00/17/28/rBIxVGEnTZ2Ab1QbAAAwAOLcvyk661.doc",
    "employer": "https://zwfwxtzx.shaanxi.gov.cn/sxfw//group1/M00/2A/CC/rBIxU2EnTBGAYHLxAAAwAIu14s0210.doc",
}
CONVERSION_HASHES = {
    "worker": "fd175ceb24c66ec39656a63b111d391dc3a8129da3f53b056fe859e512ffa90b",
    "employer": "eb0bcbe2d0df71802b2be79f38ec85d0319a350e947cc38e910e5f69fabd9e9c",
}
LAYOUTS = {
    role: Path(f"templates/_docx/_regional/shaanxi/tongguan-610522-{role}-private.docx")
    for role in CONVERSION_HASHES
}
TEMPLATE_ROLES = {f"weinan-610522-{role}-application": role for role in LAYOUTS}
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"

# Target paragraph, user-facing label, and verified line capacity.
SLOTS = {
    "request_one": (5, "第一项请求", 30),
    "request_two": (6, "第二项请求", 24),
    "facts": (9, "事实和理由", 44),
    "evidence_one": (11, "证据和证据来源（第一行）", 44),
    "evidence_two": (12, "证据和证据来源（第二行）", 44),
}
BODY_ANCHORS = {
    5: "一、请求事项：1、",
    6: "2、",
    8: "二、事实和理由：",
    9: "",
    10: "三、证据和证据来源",
    11: "",
    12: "",
}
TongguanApplicationRequest = create_model(
    "TongguanApplicationRequest", __base__=OwnBase,
    **{field: (fixed_line(width, EXTRA_WIDE), "") for field, (_, _, width) in SLOTS.items()},
)


def fill_application(role, layout, values):
    if sha256(layout).hexdigest() != CONVERSION_HASHES.get(role):
        raise ValueError("潼关县对应申请人身份的申请书转换件不匹配")
    data = TongguanApplicationRequest.model_validate(values)
    document = Document(BytesIO(layout))
    if len(document.paragraphs) != 19 or any(
        document.paragraphs[index].text.strip() != text for index, text in BODY_ANCHORS.items()
    ):
        raise ValueError("潼关县申请书正文位置已变化")
    for key, (target, _, _) in SLOTS.items():
        value = getattr(data, key)
        if value:
            paragraph = document.paragraphs[target]
            style, = paragraph._p.xpath("./w:pPr/w:rPr")
            paragraph.add_run(value)._r.insert(0, deepcopy(style))
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for relation_id, relation in list(part.rels.items()):
            if relation.reltype.endswith(suffix):
                del part.rels[relation_id]
    for name in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, name, "")
    return document


def _read_pinned(root, relative, checksum):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("潼关县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少潼关县核验来源或转换件") from exc
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("潼关县核验文件字节已变化")
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = json.loads(_read_pinned(root, SOURCE, SOURCE_SHA256))
    code = proof["region_code"]
    roles = tuple(proof["roles"].items())
    templates = []
    for role, receipt in roles:
        application = next(item for item in receipt["materials"] if item["key"] == "application")
        blank = next(item for item in application["attachments"] if item["portal_label"] == "空表")
        templates.append({
            "id": f"weinan-{code}-{role}-application",
            "original_name": f'仲裁申请书（{receipt["name"]}）.doc',
            "service_object": receipt["name"],
            "region_code": code,
            "guide_source_url": receipt["source_url"],
            "source_url": ORIGINAL_LINKS[role],
            "official_sha256": blank["sha256"],
            "official_kind": "blank",
            "file_type": "doc",
            "original_format": "DOC",
            "download_status": "official_link_only",
            "document_types": [],
            "can_generate": False,
        })
    source_url = proof["roles"]["worker"]["source_url"]
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": proof["city"],
        "district": proof["district"],
        "region_code": code,
        "scope_level": "district",
        "authority": proof["authority"],
        "source_title": "潼关县劳动人事争议仲裁申请（劳动者、用人单位）",
        "service_name": "劳动人事争议仲裁申请",
        "source_url": source_url,
        "source_id": digest(source_url)[:24],
        "source_version": SOURCE_SHA256,
        "role_sources": {receipt["name"]: receipt["source_url"] for _, receipt in roles},
        "collected_at": roles[0][1]["collected_at"],
        "verified_at": roles[1][1]["collected_at"],
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": proof["authority"],
            "咨询方式": proof["consultation_phone"],
            "办理地点": "\n".join(f'{v["name"]}事项：{v["venue"]}。' for _, v in roles),
            "承诺办结时限": "劳动者及用人单位事项均显示 0 个工作日，请向潼关县人社局核实。",
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {
                "id": f'{code}-{role}-{item["key"]}',
                "name": f'{item["name"]}（{receipt["name"]}）',
                "official_name": item["name"],
                "region_code": code,
                "service_object": receipt["name"],
                "source_url": receipt["source_url"],
                "required": item["required"],
            }
            for role, receipt in roles for item in receipt["materials"]
        ],
        "templates": templates,
        "sections": {"官网附件核验": "两类申请书各有独立的官方空表。原件均为两页，第二页是日期栏。"},
        "warnings": ["请选择对应申请人身份的文书，并按原表补全双方信息、受理机关、签名或盖章及日期。"],
    }


def _with_layout(root, template):
    role = TEMPLATE_ROLES[template["id"]]
    layout = LAYOUTS[role]
    checksum = CONVERSION_HASHES[role]
    _read_pinned(root, layout, checksum)
    return {
        **template, "adapter": ADAPTER, "file": layout.as_posix(), "sha256": checksum,
        "file_origin": "official-blank-converted-layout", "document_types": ["application"],
        "can_generate": True, "generation_mode": "blank",
    }


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    guide["templates"] = [_with_layout(root, template) for template in guide["templates"]]
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    template_id = template.get("id")
    if kind != "application" or template_id not in TEMPLATE_ROLES:
        raise ValueError("仅适配潼关县已核验申请书")
    root = Path(ROOT if root is None else root).resolve()
    expected = staged_guide(root)
    bound = next(item for item in expected["templates"] if item["id"] == template_id)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != _with_layout(root, bound):
        raise ValueError("潼关县申请书与已核验的本区角色来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": [{"key": key, "label": label, "type": "text", "maxLength": width}
                   for key, (_, label, width) in SLOTS.items()],
        "defaults": TongguanApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    return {key: {"first_width": width, "later_width": width, "max_lines": 1, "no_newlines": True, "trim": True}
            for key, (_, _, width) in SLOTS.items()}
