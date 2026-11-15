"""Source-bound filling for the Hanbin district worker application."""
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated
from unicodedata import category, east_asian_width

from docx import Document
from pydantic import AfterValidator, Field

from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_hanbin_worker_application_v1"
TEMPLATE_ID = "ankang-610902-worker-application"
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-hanbin-worker/SOURCE-PROOF.json")
PROOF_SHA256 = "9354dc05eb9d8fc1904bc50e34dac9186b0ad836b494206bc80abef5d88659f6"
LAYOUT = Path("templates/_docx/_regional/shaanxi/hanbin-610902-private-application.docx")
CONVERTED_SHA256 = "7c0c86dda9e36f1a8226d831899b4c421680707dec33e8e045696f997e89f0e8"
IDENTITY = ("province", "city", "district", "scope_level", "region_code", "source_url", "source_id", "source_version")
SLOTS = {
    "applicant_name": ("申请人姓名", 2, 2),
    "applicant_gender": ("申请人性别", 2, 4),
    "applicant_birth_month": ("申请人出生年月", 2, 6),
    "applicant_id": ("申请人身份证件号码", 2, 9),
    "applicant_address": ("申请人住所", 2, 11),
    "applicant_mailing_address": ("申请人通讯地址", 2, 13),
    "applicant_contact": ("申请人联系方式", 2, 15),
    "agent_first": ("委托代理人第一栏", 3, 1),
    "agent_second": ("委托代理人第二栏", 3, 3),
    "respondent_name": ("被申请人名称", 5, 2),
    "respondent_address": ("被申请人住所", 5, 4),
    "representative_name": ("法定代表人或主要负责人", 5, 8),
    "representative_position": ("法定代表人或主要负责人职务", 5, 10),
    "respondent_mailing_address": ("被申请人通讯地址", 6, 1),
    "respondent_contact": ("被申请人联系方式", 6, 3),
}
RULED = {
    "requests": ("仲裁请求", 9, 6),
    "facts": ("事实和理由", 17, 6),
    "evidence": ("证据和证据来源，证人姓名和住所", 25, 7),
}
WIDTHS = {
    "applicant_name": 14, "applicant_gender": 6, "applicant_birth_month": 17,
    "applicant_id": 23, "applicant_address": 21, "applicant_mailing_address": 26,
    "applicant_contact": 17, "agent_first": 24, "agent_second": 27,
    "respondent_name": 26, "respondent_address": 21, "representative_name": 13,
    "representative_position": 21, "respondent_mailing_address": 26, "respondent_contact": 17,
}
ROW_WIDTH = 64


def _display_width(value):
    return sum(2 if east_asian_width(char) in {"W", "F"} else 1 for char in value)


def _line(width):
    def check(value):
        if any(category(char).startswith("C") or category(char) in {"Zl", "Zp"} for char in value):
            raise ValueError("原表每栏只容纳一行文字")
        value = value.strip()
        if _display_width(value) > width:
            raise ValueError("文字超出原表栏位的填写容量")
        return value
    return Annotated[str, Field(max_length=width), AfterValidator(check)]


class HanbinApplicationRequest(OwnBase):
    applicant_name: _line(WIDTHS["applicant_name"]) = ""
    applicant_gender: _line(WIDTHS["applicant_gender"]) = ""
    applicant_birth_month: _line(WIDTHS["applicant_birth_month"]) = ""
    applicant_id: _line(WIDTHS["applicant_id"]) = ""
    applicant_address: _line(WIDTHS["applicant_address"]) = ""
    applicant_mailing_address: _line(WIDTHS["applicant_mailing_address"]) = ""
    applicant_contact: _line(WIDTHS["applicant_contact"]) = ""
    agent_first: _line(WIDTHS["agent_first"]) = ""
    agent_second: _line(WIDTHS["agent_second"]) = ""
    respondent_name: _line(WIDTHS["respondent_name"]) = ""
    respondent_address: _line(WIDTHS["respondent_address"]) = ""
    representative_name: _line(WIDTHS["representative_name"]) = ""
    representative_position: _line(WIDTHS["representative_position"]) = ""
    respondent_mailing_address: _line(WIDTHS["respondent_mailing_address"]) = ""
    respondent_contact: _line(WIDTHS["respondent_contact"]) = ""
    requests: list[_line(ROW_WIDTH)] = Field(default_factory=lambda: [""], max_length=6)
    facts: list[_line(ROW_WIDTH)] = Field(default_factory=lambda: [""], max_length=6)
    evidence: list[_line(ROW_WIDTH)] = Field(default_factory=lambda: [""], max_length=7)


def _fill_underlined(runs, value):
    if not value:
        return
    if any(run.underline is not True or run.text.strip() for run in runs):
        raise ValueError("汉滨区原表的下划线填写位置已变化")
    fill_width = sum(len(run.text) for run in runs)
    runs[0].text = value + " " * max(0, fill_width - _display_width(value))
    for run in runs[1:]:
        run.text = ""


def fill_application(original, values):
    if sha256(original).hexdigest() != CONVERTED_SHA256:
        raise ValueError("汉滨区核验的空表转换件已变化")
    data = HanbinApplicationRequest.model_validate(values)
    document = Document(BytesIO(original))
    paragraphs = document.paragraphs
    for field, (_, paragraph, index) in SLOTS.items():
        _fill_underlined(paragraphs[paragraph].runs[index:index+1], getattr(data, field))
    for field, (_, start, count) in RULED.items():
        for paragraph, value in zip(paragraphs[start:start+count], getattr(data, field)):
            _fill_underlined(paragraph.runs, value)
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for rel_id, rel in list(part.rels.items()):
            if rel.reltype.endswith(suffix):
                del part.rels[rel_id]
    for field in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, field, "")
    return document


def _pinned_bytes(root, relative, checksum):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("汉滨区文件路径超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少汉滨区已核验来源或转换件") from exc
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("汉滨区已核验来源或转换件字节已变化")
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = json.loads(_pinned_bytes(root, PROOF, PROOF_SHA256))
    area, worker = proof["area"], proof["worker"]
    source_url = worker["guide_url"]
    code = area["region_code"]
    date = worker["blank"]["downloaded_at"]
    materials = [
        {"id": f"{code}-worker-{i}", "name": row["name"], "required": row["required"],
         "source_url": source_url, "region_code": code, "service_object": "劳动者"}
        for i, row in enumerate(worker["materials"], start=1)
    ]
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"],
        "district": area["district"], "scope_level": "district", "region_code": code,
        "authority": area["authority"], "service_name": "劳动人事争议仲裁申请", "source_title": worker["guide_title"],
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "collected_at": date, "verified_at": date, "verification_status": "partial", "published": False,
        "can_generate": False,
        "fields": {"实施机关": area["authority"], "法定办结时限": "5 个工作日", "承诺办结时限": "5 个工作日",
                   "到现场次数": "1", "办理地点": "陕西省安康市汉滨区老城街道兴家仓巷42号，劳动关系与调解仲裁股",
                   "咨询方式": "0915-3214119"},
        "materials": materials, "sections": {},
        "channel": {"raw_value": "官网列在线核验", "online_status": "unverified", "entry_url": None,
                    "submission_verified": False},
        "warnings": ["申请书原件的收件机关为占位文字。请向汉滨区受理部门确认并自行填写，签名和日期留给申请人。",
                     "申请书副本说明保留原文。授权委托书在劳动者材料栏标为非必要，该入口仅列样表。"],
        "templates": [{
            "id": TEMPLATE_ID, "region_code": code, "source_url": source_url,
            "original_name": "劳动人事争议仲裁申请书（劳动者空表）", "official_kind": "blank",
            "official_sha256": worker["blank"]["sha256"], "file_type": "doc",
            "download_status": "official_link_only", "official_attachment_entry": "material_tab",
            "document_types": [], "can_generate": False,
        }],
    }


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    _pinned_bytes(root, LAYOUT, CONVERTED_SHA256)
    guide["templates"][0].update(
        adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=CONVERTED_SHA256,
        file_origin="official-blank-converted-layout", original_format="DOC",
        document_types=["application"], can_generate=True, generation_mode="blank",
    )
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配汉滨区劳动者仲裁申请书")
    expected = staged_application_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("汉滨区申请书与核验的劳动者事项来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": label, "type": "text", "maxLength": WIDTHS[key]}
              for key, (label, _, _) in SLOTS.items()]
    fields.extend({"key": key, "label": label, "type": "text_list", "maxItems": count, "maxLength": ROW_WIDTH}
                  for key, (label, _, count) in RULED.items())
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version, "fields": fields,
        "defaults": HanbinApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    result = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, width in WIDTHS.items()}
    result.update({key: {"line_widths": [ROW_WIDTH] * count, "max_lines": count, "no_newlines": True, "trim": True}
                   for key, (_, _, count) in RULED.items()})
    return result
