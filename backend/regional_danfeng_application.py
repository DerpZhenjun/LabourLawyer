"""Fill Danfeng County's official worker application in its original DOCX layout."""

from copy import deepcopy
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from docx import Document
from pydantic import Field, create_model, field_validator

from regional_fixed_layout import fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_danfeng_worker_application_v1"
TEMPLATE_ID = "shangluo-611022-worker-application"
PROOF = Path("reports/overnight-gap-closure-20261030/localities/danfeng-own-application/SOURCE-PROOF.json")
PROOF_SHA256 = "7e1e6cf8f9af59b0b58ae44b8497b8c479135005f52a1374e678a4332f0ce877"
LAYOUT = Path("templates/_docx/_regional/shaanxi/danfeng-611022-worker-application-private.docx")
ORIGINAL_SHA256 = "91600c6cfe8e4871ebd396244e8e2d26a640adee4f5db5e37c9ca905ad0f8d8b"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"

# Paragraph index, replaced range, field label and rendered width.
SLOTS = {
    "applicant_name": (1, 8, 24, "申请人姓名", 14),
    "sex": (1, 27, 34, "性别", 4),
    "ethnicity": (1, 37, 41, "民族", 6),
    "origin": (2, 41, 56, "原籍", 12),
    "home_address": (3, 16, 40, "现住址", 14),
    "phone": (3, 45, 45, "联系电话", 12),
    "mail_address": (4, 10, 34, "确认有效的通讯地址", 14),
    "postcode": (4, 39, 39, "邮政编码", 6),
    "respondent": (5, 7, 7, "被申请人", 34),
    "respondent_representative": (6, 6, 35, "被申请人法定代表人", 16),
    "respondent_position": (6, 38, 38, "被申请人法定代表人职务", 14),
    "respondent_address": (7, 9, 9, "被申请人住所", 34),
    "respondent_phone": (8, 7, 7, "被申请人联系电话", 18),
    "third_party": (9, 8, 8, "第三人", 34),
    "third_party_representative": (10, 6, 35, "第三人法定代表人", 16),
    "third_party_position": (10, 38, 38, "第三人法定代表人职务", 14),
    "third_party_address": (11, 9, 9, "第三人住所", 34),
    "third_party_phone": (12, 7, 7, "第三人联系电话", 18),
}
# Compact the original alignment spaces only on a line the user actually fills.
ALIGNMENT_SPACES = {
    2: ((0, 12, "      "), (30, 38, "  ")),
    3: ((0, 12, "    "),),
}
EMPTY_SLOT_SPACES = {
    "home_address": "      ",
    "mail_address": "      ",
    "respondent_representative": "（姓名）  ",
    "third_party_representative": "（姓名）  ",
}
BLOCKS = {"requests": (15, "仲裁请求", 36, 4), "facts": (20, "事实和理由", 40, 2)}


class DanfengBase(OwnBase):
    birth_date: str = Field("", max_length=10)
    requests: list[fixed_line(BLOCKS["requests"][2], EXTRA_WIDE)] = Field(
        default_factory=lambda: [""], max_length=BLOCKS["requests"][3],
    )
    facts: list[fixed_line(BLOCKS["facts"][2], EXTRA_WIDE)] = Field(
        default_factory=lambda: [""], max_length=BLOCKS["facts"][3],
    )

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, value):
        if value:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("出生日期须填写有效的年月日")
            date.fromisoformat(value)
        return value


DanfengWorkerRequest = create_model(
    "DanfengWorkerRequest", __base__=DanfengBase,
    **{key: (fixed_line(width, EXTRA_WIDE), "") for key, (_, _, _, _, width) in SLOTS.items()},
)


def fill_application(source, values):
    if sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("丹凤县劳动者申请书原件字节已变化")
    data = DanfengWorkerRequest.model_validate(values)
    doc = Document(BytesIO(source))
    paragraphs = doc.paragraphs
    replacements = {}
    for key, (index, start, stop, _, _) in SLOTS.items():
        value = getattr(data, key)
        if value:
            # Separate adjacent labeled fields while keeping the original run formatting.
            if start != stop and stop < len(paragraphs[index].text):
                value += "  "
            replacements.setdefault(index, []).append((start, stop, value))
    if data.birth_date:
        replacements.setdefault(2, []).extend(
            (start, stop, component) for (start, stop), component in zip(
                ((15, 20), (21, 24), (25, 29)), data.birth_date.split("-"), strict=True,
            )
        )
    for key, substitute in EMPTY_SLOT_SPACES.items():
        index, start, stop, _, _ = SLOTS[key]
        if index in replacements and not getattr(data, key):
            replacements[index].append((start, stop, substitute))
    for index, edits in replacements.items():
        edits.extend(ALIGNMENT_SPACES.get(index, ()))
        run = paragraphs[index].runs[0]
        text = run.text
        for start, stop, value in sorted(edits, reverse=True):
            text = text[:start] + value + text[stop:]
        run.text = text

    for key, (first, _, _, _) in BLOCKS.items():
        style = paragraphs[first - 1].runs[-1]._r.rPr
        for offset, line in enumerate(getattr(data, key)):
            if line:
                run = paragraphs[first + offset].add_run(line)
                if style is not None:
                    run._r.insert(0, deepcopy(style))
    for part, suffix in ((doc.part, "/customXml"), (doc.part.package, "/custom-properties")):
        for relation_id, relation in list(part.rels.items()):
            if relation.reltype.endswith(suffix):
                del part.rels[relation_id]
    for field in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(doc.core_properties, field, "")
    return doc


def _pinned_bytes(root, relative, checksum):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("丹凤县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少丹凤县核验来源或申请书原件") from exc
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("丹凤县核验来源或申请书原件字节已变化")
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = json.loads(_pinned_bytes(root, PROOF, PROOF_SHA256))
    area = proof["area"]
    code = area["region_code"]
    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = worker["source_url"]
    blank = next(item for item in worker["materials"][0]["attachments"] if item["portal_label"] == "空表")
    return {
        "province": "shaanxi", **area, "scope_level": "district", "service_name": "劳动人事争议仲裁申请",
        "source_title": "丹凤县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "role_sources": {item["label"]: item["source_url"] for item in (worker, employer)},
        "collected_at": min(worker["collected_at"], employer["collected_at"]),
        "verified_at": max(worker["collected_at"], employer["collected_at"]),
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "咨询方式": worker["phone"], "办理地点": worker["venue"],
                   "承诺办结时限": f'{worker["commitment_workdays"]} 个工作日'},
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {"id": f'{code}-{role}-{row["key"]}', "name": f'{row["name"]}（{item["label"]}）',
             "official_name": row["name"], "service_object": item["label"], "source_url": item["source_url"],
             "region_code": code, "required": row["required"], "instructions": row["instructions"]}
            for role, item in proof["roles"].items() for row in item["materials"]
        ],
        "templates": [{
            "id": TEMPLATE_ID, "original_name": "劳动仲裁申请书（劳动者）.docx", "service_object": "劳动者",
            "region_code": code, "source_url": blank["source_url"], "guide_source_url": source_url,
            "file_type": "docx", "official_kind": "blank", "official_sha256": blank["sha256"],
            "download_status": "official_link_only", "document_types": [], "can_generate": False,
        }],
        "sections": {"官网附件核验": "两类事项的申请书空表字节相同。原件的申请人栏为自然人格式，用人单位填写版待核验。"},
        "warnings": ["填写后请核对文末仲裁委员会名称，并手写签名和日期。", "用人单位请查阅对应官网指南。"],
    }


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    _pinned_bytes(root, LAYOUT, ORIGINAL_SHA256)
    template = guide["templates"][0]
    if template["official_sha256"] != ORIGINAL_SHA256:
        raise ValueError("丹凤县劳动者申请书来源摘要不匹配")
    template.update(adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=ORIGINAL_SHA256,
                    file_origin="official-blank", document_types=["application"], can_generate=True, generation_mode="blank")
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配丹凤县劳动者仲裁申请书")
    expected = staged_application_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("丹凤县申请书与已核验的劳动者来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": label, "type": "text", "maxLength": width}
              for key, (_, _, _, label, width) in SLOTS.items()]
    fields.insert(3, {"key": "birth_date", "label": "出生日期", "type": "text", "format": "iso-date", "maxLength": 10})
    fields.extend({"key": key, "label": label, "type": "text_list", "maxLength": width, "maxItems": count}
                  for key, (_, label, width, count) in BLOCKS.items())
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": fields, "defaults": DanfengWorkerRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    fields = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, (_, _, _, _, width) in SLOTS.items()}
    fields.update({key: {"line_widths": [width] * count, "max_lines": count, "no_newlines": True, "trim": True}
                   for key, (_, _, width, count) in BLOCKS.items()})
    return fields
