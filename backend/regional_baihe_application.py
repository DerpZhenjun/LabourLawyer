"""Fill the role-bound Baihe employer application using its own verified DOC conversion."""

from copy import deepcopy
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from docx import Document
from pydantic import Field

from regional_fixed_layout import fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_baihe_employer_application_v1"
TEMPLATE_ID = "ankang-610929-employer-application"
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-baihe-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "1f169884dcc1cfd25d73192814cd56e3367a9be5360b9a8cde6022ddb6c8b1e8"
LAYOUT = Path("templates/_docx/_regional/shaanxi/baihe-610929-private-employer-application.docx")
CONVERTED_SHA256 = "0ae014cf63f5f3466a500295111a645551f84a1d81411348b5266b394078dc1d"
ORIGINAL_SHA256 = "aed265f01c565104ce0a4b787151595fb5b8ad1b9b0185accb27a70ec198ec20"
IDENTITY = ("province", "city", "district", "region_code", "scope_level", "source_url", "source_id", "source_version")
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"
FIELDS = {
    "applicant_company": (2, "申请人：", "申请单位名称", 36),
    "applicant_representative": (3, "法定代表人：", "申请单位法定代表人", 22),
    "applicant_address": (4, "地址：", "申请单位地址", 40),
    "applicant_contact": (5, "电话：", "申请单位电话", 24),
    "respondent": (6, "被申请人：", "被申请人", 40),
}
TEXT_BLOCKS = {
    "requests": (9, "请求事项", 44, 2),
    "facts": (11, "事实与理由", 44, 3),
}


class BaiheEmployerApplicationRequest(OwnBase):
    applicant_company: fixed_line(FIELDS["applicant_company"][3], EXTRA_WIDE) = ""
    applicant_representative: fixed_line(FIELDS["applicant_representative"][3], EXTRA_WIDE) = ""
    applicant_address: fixed_line(FIELDS["applicant_address"][3], EXTRA_WIDE) = ""
    applicant_contact: fixed_line(FIELDS["applicant_contact"][3], EXTRA_WIDE) = ""
    respondent: fixed_line(FIELDS["respondent"][3], EXTRA_WIDE) = ""
    requests: list[fixed_line(TEXT_BLOCKS["requests"][2], EXTRA_WIDE)] = Field(
        default_factory=lambda: [""], max_length=TEXT_BLOCKS["requests"][3],
    )
    facts: list[fixed_line(TEXT_BLOCKS["facts"][2], EXTRA_WIDE)] = Field(
        default_factory=lambda: [""], max_length=TEXT_BLOCKS["facts"][3],
    )


def fill_application(layout, values):
    if sha256(layout).hexdigest() != CONVERTED_SHA256:
        raise ValueError("白河县用人单位申请书转换件字节已变化")
    data = BaiheEmployerApplicationRequest.model_validate(values)
    document = Document(BytesIO(layout))
    paragraphs = document.paragraphs
    for key, (index, label, _, _) in FIELDS.items():
        paragraph = paragraphs[index]
        if paragraph.text != label:
            raise ValueError("白河县用人单位申请书字段位置已变化")
        value = getattr(data, key)
        if value:
            style = paragraph.runs[-1]._r.rPr
            run = paragraph.add_run(value)
            if style is not None:
                run._r.insert(0, deepcopy(style))
    for key, (index, _, _, _) in TEXT_BLOCKS.items():
        value = "\n".join(getattr(data, key))
        if paragraphs[index].text:
            raise ValueError("白河县用人单位申请书正文位置已变化")
        if value:
            paragraphs[index].add_run(value)
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for relation_id, relation in list(part.rels.items()):
            if relation.reltype.endswith(suffix):
                del part.rels[relation_id]
    for field in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, field, "")
    return document


def _pinned_bytes(root, relative, checksum):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("白河县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少白河县核验来源或转换件") from exc
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("白河县核验来源或转换件字节已变化")
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = json.loads(_pinned_bytes(root, PROOF, PROOF_SHA256))
    area = proof["area"]
    code = area["region_code"]
    if (area["city"], area["district"], code) != ("安康市", "白河县", "610929"):
        raise ValueError("来源地区与白河县不匹配")

    materials, templates = [], []
    for role, guide in proof["roles"].items():
        service_object = guide["label"]
        url = guide["source_url"]
        for row in guide["materials"]:
            key = row["key"]
            label = f'{row["name"]}（{service_object}）'
            materials.append({
                "id": f"{code}-{role}-{key}", "name": label, "official_name": row["name"],
                "service_object": service_object, "source_url": url, "region_code": code,
                "required": row["required"], "instructions": row["instructions"],
            })
            if row["inspection"] != "blank":
                continue
            templates.append({
                "id": f"ankang-{code}-{role}-{key}", "original_name": f"{label}空表",
                "service_object": service_object, "region_code": code, "source_url": row["blank_url"],
                "guide_source_url": url, "official_kind": "blank",
                "official_sha256": row["portal_blank_sha256"], "file_type": "doc", "original_format": "DOC",
                "download_status": "official_link_only", "document_types": [], "can_generate": False,
            })

    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = employer["source_url"]
    return {
        "province": "shaanxi", **area, "scope_level": "district", "service_name": "劳动人事争议仲裁申请",
        "source_title": "白河县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "collected_at": employer["captured_at"], "verified_at": worker["captured_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "咨询方式": proof["phone"], "办理地点": employer["venue"],
                   "承诺办结时限": f'{employer["commitment_workdays"]} 个工作日'},
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials, "templates": templates,
        "sections": {"劳动者官方指南": f'请按劳动者事项核对材料和签署要求。{worker["source_url"]}'},
        "warnings": ["本页的申请书填写仅适用于用人单位。劳动者事项的申请书附件包含法定代表人和盖章栏，签署要求待核验。"],
    }


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    _pinned_bytes(root, LAYOUT, CONVERTED_SHA256)
    template = next(entry for entry in guide["templates"] if entry["id"] == TEMPLATE_ID)
    if template["official_sha256"] != ORIGINAL_SHA256:
        raise ValueError("白河县用人单位申请书原始来源已变化")
    template.update(
        adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=CONVERTED_SHA256,
        file_origin="official-blank-converted-layout", document_types=["application"],
        can_generate=True, generation_mode="blank",
    )
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配白河县用人单位仲裁申请书")
    expected = staged_application_candidate(root)
    expected_template = next(row for row in expected["templates"] if row["id"] == TEMPLATE_ID)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected_template:
        raise ValueError("白河县申请书与已核验的用人单位事项来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": label, "type": "text", "maxLength": width}
              for key, (_, _, label, width) in FIELDS.items()]
    fields.extend({"key": key, "label": label, "type": "text_list", "maxLength": width, "maxItems": count}
                  for key, (_, label, width, count) in TEXT_BLOCKS.items())
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": fields, "defaults": BaiheEmployerApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    fields = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, (_, _, _, width) in FIELDS.items()}
    fields.update({key: {"line_widths": [width] * count, "max_lines": count, "no_newlines": True, "trim": True}
                   for key, (_, _, width, count) in TEXT_BLOCKS.items()})
    return fields
