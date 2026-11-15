"""Fill the reviewed Shanyang County worker DOC conversion."""

from copy import deepcopy
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from docx import Document
from pydantic import create_model, field_validator

from regional_fixed_layout import fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_shanyang_worker_application_v1"
TEMPLATE_ID = "shangluo-611024-worker-application"
PROOF = Path("reports/overnight-gap-closure-20261030/localities/shanyang-own-application/SOURCE-PROOF.json")
PROOF_SHA256 = "fa53a2b2572ac23fca0f0106c391f75a3f7f02969a4162e3dfde1f5d24670f8c"
LAYOUT = Path("templates/_docx/_regional/shaanxi/shanyang-611024-worker-application-private.docx")
ORIGINAL_SHA256 = "6f55277834421e8247304f30ec5b68ec3d21f1e81641a73f3e80b6fb51110ba9"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"

# Paragraph index and the range of tab runs in its printable slot.
SLOTS = {
    "applicant_name": (3, 1, 4, "申请人姓名", 10),
    "sex": (3, None, None, "性别", 2),
    "applicant_id": (4, 1, 6, "身份证号", 18),
    "birth_date": (6, 1, 3, "出生时间", 10),
    "ethnicity": (7, 2, 3, "民族", 10),
    "workplace": (8, 1, 11, "申请人工作单位", 44),
    "address": (9, 2, 11, "申请人住址", 44),
    "phone": (10, 1, 6, "申请人联系电话", 18),
    "postcode": (10, 7, 12, "申请人邮政编码", 8),
    "respondent": (11, 1, 10, "被申请人", 44),
    "respondent_representative": (12, 1, 3, "被申请人法定代表人（负责人）", 16),
    "respondent_position": (12, 5, 8, "被申请人法定代表人职务", 14),
    "respondent_address": (13, 1, 10, "被申请人通讯地址", 44),
    "respondent_phone": (14, 1, 6, "被申请人联系电话", 18),
    "respondent_postcode": (14, 7, 10, "被申请人邮政编码", 8),
    "third_party": (15, 1, 6, "第三人姓名或单位名称", 38),
    "third_party_representative": (16, 1, 3, "第三人法定代表人（负责人）", 8),
    "third_party_address": (19, 1, 11, "第三人通讯地址", 44),
    "third_party_phone": (20, 1, 7, "第三人联系电话", 18),
    "third_party_postcode": (20, 8, 13, "第三人邮政编码", 8),
    "requests": (21, None, None, "请求事项", 52),
    "facts": (2, None, None, "事实与理由", 44),
}


class ShanyangBase(OwnBase):
    @field_validator("birth_date", check_fields=False)
    @classmethod
    def check_birth_date(cls, value):
        if value:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("出生时间须填写有效年月日")
            date.fromisoformat(value)
        return value


ShanyangWorkerRequest = create_model(
    "ShanyangWorkerRequest", __base__=ShanyangBase,
    **{key: (fixed_line(width, EXTRA_WIDE), "") for key, (_, _, _, _, width) in SLOTS.items()},
)


def _append(paragraph, value):
    style = paragraph.runs[-1]._r.rPr
    run = paragraph.add_run(value)
    if style is not None:
        run._r.insert(0, deepcopy(style))


def fill_application(layout, values):
    if sha256(layout).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("山阳县劳动者申请书原件字节已变化")
    data = ShanyangWorkerRequest.model_validate(values)
    doc = Document(BytesIO(layout))
    for key, (index, first, stop, _, _) in SLOTS.items():
        value = getattr(data, key)
        if not value:
            continue
        paragraph = doc.paragraphs[index]
        if first is None:
            _append(paragraph, "\n" + value if key == "facts" else value)
        else:
            runs = paragraph.runs
            slot = runs[first:stop]
            if len(slot) != stop - first or any(run.text != "\t" for run in slot):
                raise ValueError("山阳县申请书空栏位置已变化")
            has_following_label = stop < len(runs)
            slot[0].text = value + ("  " if has_following_label else "")
            for run in slot[1:]:
                run.text = ""
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
        raise ValueError("山阳县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少山阳县核验来源或原件") from exc
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("山阳县核验来源或原件字节已变化")
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
        "source_title": "山阳县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "role_sources": {item["label"]: item["source_url"] for item in (worker, employer)},
        "collected_at": min(worker["collected_at"], employer["collected_at"]),
        "verified_at": max(worker["collected_at"], employer["collected_at"]),
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "咨询方式": worker["phone"],
                   "办理地点": f'劳动者事项原文：{worker["venue"]}，请向山阳县人社局核实。\n用人单位事项原文：{employer["venue"]}。',
                   "承诺办结时限": f'两类事项官网均显示 {worker["commitment_workdays_as_displayed"]} 个工作日，请向主管机关核实。'},
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
            "file_type": "docx", "original_format": "DOCX", "official_kind": "blank", "official_sha256": blank["sha256"],
            "download_status": "official_link_only", "document_types": [], "can_generate": False,
        }],
        "sections": {"官网附件核验": "劳动者指南的 DOCX 空表和 JPG 样表是不同文件。用人单位指南挂载同一份自然人申请书，适用格式仍待核实。"},
        "warnings": ["赴现场前请核实劳动者办理地点。请核对文末机关名称、副本份数、第三人职务，并自行签名填写日期。", "用人单位请查阅对应官网指南。"],
    }


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    _pinned_bytes(root, LAYOUT, ORIGINAL_SHA256)
    template = guide["templates"][0]
    if template["official_sha256"] != ORIGINAL_SHA256:
        raise ValueError("山阳县劳动者申请书来源摘要不匹配")
    template.update(adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=ORIGINAL_SHA256,
                    file_origin="official-blank", document_types=["application"],
                    can_generate=True, generation_mode="blank")
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配山阳县劳动者仲裁申请书")
    expected = staged_application_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("山阳县申请书与已核验的劳动者来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": label, "type": "text", "maxLength": width}
              for key, (_, _, _, label, width) in SLOTS.items()]
    next(field for field in fields if field["key"] == "birth_date")["format"] = "iso-date"
    return {"schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
            "fields": fields, "defaults": ShanyangWorkerRequest().model_dump(),
            "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                       "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"}}


def layout_fields():
    fields = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, (_, _, _, _, width) in SLOTS.items()}
    return fields
