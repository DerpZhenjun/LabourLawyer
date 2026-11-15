"""Fill the reviewed Shangnan County worker DOC conversion."""

from copy import deepcopy
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from docx import Document
from pydantic import Field, create_model, field_validator

from regional_fixed_layout import display_width, fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_shangnan_worker_application_v1"
TEMPLATE_ID = "shangluo-611023-worker-application"
PROOF = Path("reports/overnight-gap-closure-20261030/localities/shangnan-own-application/SOURCE-PROOF.json")
PROOF_SHA256 = "213ec9c7e1ce82fe3a0e3221734620c54d510ce477242e010e9d11e9130ea0f7"
LAYOUT = Path("templates/_docx/_regional/shaanxi/shangnan-611023-worker-converted-private.docx")
ORIGINAL_SHA256 = "bc30ba43344b964ab605cd441e294b67a8e7be2383dc44e525fcb7abc0576e82"
CONVERSION_SHA256 = "9c167dbe521dff6cbbed82be13c9ad6849cd79e2c35421ab31dbb4828a0de960"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"

# Paragraph and padding run (None appends after the original label).
SLOTS = {
    "applicant_name": (1, 1, "申请人姓名", 12),
    "sex": (1, 3, "性别", 2),
    "applicant_id": (2, 1, "身份证号", 18),
    "ethnicity": (2, None, "民族", 8),
    "address": (3, None, "申请人住址", 38),
    "phone": (4, 1, "申请人联系电话", 16),
    "postcode": (4, None, "申请人邮政编码", 8),
    "respondent": (5, None, "被申请人", 36),
    "respondent_representative": (6, 1, "被申请人法定代表人（负责人）", 14),
    "respondent_position": (6, None, "被申请人法定代表人职务", 10),
    "respondent_address": (7, None, "被申请人通讯地址", 36),
    "respondent_phone": (8, 1, "被申请人联系电话", 16),
    "respondent_postcode": (8, None, "被申请人邮政编码", 8),
    "third_party": (9, 1, "被申请人（第三人）", 14),
    "third_party_name": (9, None, "第三人姓名", 12),
    "third_party_representative": (10, 1, "第三人法定代表人（负责人）", 14),
    "third_party_position": (10, None, "第三人法定代表人职务", 10),
    "third_party_address": (11, None, "第三人通讯地址", 36),
    "third_party_phone": (12, 1, "第三人联系电话", 16),
    "third_party_postcode": (12, None, "第三人邮政编码", 8),
    "requests": (13, None, "请求事项", 34),
}
FACT_WIDTHS = (34, 42)


class ShangnanBase(OwnBase):
    birth_date: str = Field("", max_length=10)
    facts: list[fixed_line(max(FACT_WIDTHS), EXTRA_WIDE)] = Field(default_factory=lambda: [""], max_length=2)

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, value):
        if value:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("出生时间须填写有效年月日")
            date.fromisoformat(value)
        return value

    @field_validator("facts")
    @classmethod
    def check_facts(cls, values):
        if any(display_width(value, EXTRA_WIDE) > width for value, width in zip(values, FACT_WIDTHS)):
            raise ValueError("文字超出了原件该行的填写容量")
        return values


ShangnanWorkerRequest = create_model(
    "ShangnanWorkerRequest", __base__=ShangnanBase,
    **{key: (fixed_line(width, EXTRA_WIDE), "") for key, (_, _, _, width) in SLOTS.items()},
)


def _append(paragraph, value, style):
    if value:
        run = paragraph.add_run(value)
        if style is not None:
            run._r.insert(0, deepcopy(style))


def fill_application(layout, values):
    if sha256(layout).hexdigest() != CONVERSION_SHA256:
        raise ValueError("商南县劳动者申请书转换件字节已变化")
    data = ShangnanWorkerRequest.model_validate(values)
    doc = Document(BytesIO(layout))
    paragraphs = doc.paragraphs
    filled_rows = {index for key, (index, _, _, _) in SLOTS.items() if getattr(data, key)}
    if data.birth_date:
        filled_rows.add(1)
    for key, (index, position, _, _) in SLOTS.items():
        if index not in filled_rows:
            continue
        paragraph = paragraphs[index]
        value = getattr(data, key)
        if position is not None:
            paragraph.runs[position].text = value + " " if value else "      "
        else:
            _append(paragraph, value, paragraph.runs[-1]._r.rPr)
    if data.birth_date:
        _append(paragraphs[1], data.birth_date, paragraphs[1].runs[-1]._r.rPr)
    for index, value in enumerate(data.facts, 14):
        _append(paragraphs[index], value, paragraphs[14].runs[0]._r.rPr)
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
        raise ValueError("商南县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少商南县核验来源或转换件") from exc
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("商南县核验来源或转换件字节已变化")
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = json.loads(_pinned_bytes(root, PROOF, PROOF_SHA256))
    area = proof["area"]
    code = area["region_code"]
    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = worker["source_url"]
    application = next(row for row in worker["materials"] if row["key"] == "application")
    blank = next(item for item in application["attachments"] if item["portal_label"] == "空表")
    return {
        "province": "shaanxi", **area, "scope_level": "district", "service_name": "劳动人事争议仲裁申请",
        "source_title": "商南县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "role_sources": {item["label"]: item["source_url"] for item in (worker, employer)},
        "collected_at": min(worker["collected_at"], employer["collected_at"]),
        "verified_at": max(worker["collected_at"], employer["collected_at"]),
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "咨询方式": worker["phone"],
                   "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。',
                   "承诺办结时限": f'{worker["commitment_workdays"]} 个工作日'},
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {"id": f'{code}-{role}-{row["key"]}', "name": f'{row["name"]}（{item["label"]}）',
             "official_name": row["name"], "service_object": item["label"], "source_url": item["source_url"],
             "region_code": code, "required": row["required"], "instructions": row["instructions"]}
            for role, item in proof["roles"].items() for row in item["materials"]
        ],
        "templates": [{
            "id": TEMPLATE_ID, "original_name": "仲裁申请书（劳动者）.docx", "service_object": "劳动者",
            "region_code": code, "source_url": blank["source_url"], "guide_source_url": source_url,
            "file_type": "doc", "original_format": "DOC", "official_kind": "blank", "official_sha256": blank["sha256"],
            "download_status": "official_link_only", "document_types": [], "can_generate": False,
        }],
        "sections": {"官网附件核验": "劳动者指南分别列有空表和样表链接，两处返回同一份未填写的自然人申请书。用人单位事项挂载相同文件，其适用格式待核验。"},
        "warnings": ["填写时请核对文末仲裁委员会名称，自行签名和填写日期。", "用人单位请查阅对应官网指南。"],
    }


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    _pinned_bytes(root, LAYOUT, CONVERSION_SHA256)
    template = guide["templates"][0]
    if template["official_sha256"] != ORIGINAL_SHA256:
        raise ValueError("商南县劳动者申请书来源摘要不匹配")
    template.update(adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=CONVERSION_SHA256,
                    file_origin="official-blank-converted-layout", document_types=["application"],
                    can_generate=True, generation_mode="blank")
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配商南县劳动者仲裁申请书")
    expected = staged_application_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("商南县申请书与已核验的劳动者来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": label, "type": "text", "maxLength": width}
              for key, (_, _, label, width) in SLOTS.items()]
    fields.insert(2, {"key": "birth_date", "label": "出生时间", "type": "text", "format": "iso-date", "maxLength": 10})
    fields.append({"key": "facts", "label": "事实与理由", "type": "text_list", "maxLength": max(FACT_WIDTHS), "maxItems": 2})
    return {"schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
            "fields": fields, "defaults": ShangnanWorkerRequest().model_dump(),
            "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                       "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"}}


def layout_fields():
    fields = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, (_, _, _, width) in SLOTS.items()}
    fields["facts"] = {"line_widths": list(FACT_WIDTHS), "max_lines": 2, "no_newlines": True, "trim": True}
    return fields
