"""Fill the verified worker application from the Lueyang county guide."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from typing import Annotated
from unicodedata import category

from docx import Document
from pydantic import AfterValidator, Field

from regional_hanzhong_guides import NINGQIANG_LUEYANG_PROOF, staged_guide
from regional_huian_quangang_request import OwnBase

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_lueyang_worker_application_v1"
TEMPLATE_ID = "hanzhong-610727-application"
LAYOUT = Path("templates/_docx/_regional/shaanxi/lueyang-610727-private-application.docx")
CONVERTED_SHA256 = "53dee32b5a78a54a0dbd7eadc4bbff8b07bb7223bb4c1c7c62efa86f3ee4a06d"
FOLLOWUP = NINGQIANG_LUEYANG_PROOF.with_name("ATTACHMENT-FOLLOWUP.json")
FOLLOWUP_SHA256 = "9cd2f96e47aa2a606a2f052a8b8e8846a4d442a31098d8722b0663f296cef4ad"
IDENTITY = ("province", "city", "district", "scope_level", "region_code", "source_url", "source_id", "source_version")
LABELS = {
    "applicant_name": "申请人姓名",
    "applicant_gender": "申请人性别",
    "applicant_birth_date": "申请人出生日期",
    "applicant_address": "申请人住所",
    "applicant_phone": "申请人联系电话",
    "applicant_agent_name": "申请方委托代理人姓名",
    "applicant_agent_gender": "申请方委托代理人性别",
    "applicant_agent_birth_date": "申请方委托代理人出生日期",
    "applicant_agent_employer": "申请方委托代理人单位",
    "applicant_agent_phone": "申请方委托代理人联系电话",
    "respondent_name": "被申请人用人单位名称",
    "respondent_address": "被申请人住所",
    "respondent_mailing_address": "被申请人通讯地址",
    "respondent_phone": "被申请人联系电话",
    "representative_name": "法定代表人或主要负责人姓名",
    "representative_title": "法定代表人或主要负责人职务",
    "respondent_agent_name": "被申请方委托代理人姓名",
    "respondent_agent_gender": "被申请方委托代理人性别",
    "respondent_agent_birth_month": "被申请方委托代理人出生年月",
    "respondent_agent_employer": "被申请方委托代理人单位",
    "respondent_agent_phone": "被申请方委托代理人联系电话",
    "cause": "案由",
    "requests": "仲裁请求",
    "facts": "事实和理由",
    "evidence": "证据和证据来源",
    "witness_name": "证人姓名",
    "witness_address": "证人住所",
}


def _one_line(value):
    if any(category(c).startswith("C") or category(c) in {"Zl", "Zp"} for c in value):
        raise ValueError("本栏请填写一行文字")
    return value.strip()


def _line(limit):
    return Annotated[str, Field(max_length=limit), AfterValidator(_one_line)]


def _facts(value):
    rows = value.split("\n")
    if len(rows) > 3:
        raise ValueError("事实和理由最多填写三段")
    return "\n".join(_one_line(row) for row in rows).strip()


class LueyangApplicationRequest(OwnBase):
    applicant_name: _line(16) = ""
    applicant_gender: _line(4) = ""
    applicant_birth_date: _line(14) = ""
    applicant_address: _line(32) = ""
    applicant_phone: _line(20) = ""
    applicant_agent_name: _line(16) = ""
    applicant_agent_gender: _line(4) = ""
    applicant_agent_birth_date: _line(14) = ""
    applicant_agent_employer: _line(30) = ""
    applicant_agent_phone: _line(20) = ""
    respondent_name: _line(35) = ""
    respondent_address: _line(32) = ""
    respondent_mailing_address: _line(32) = ""
    respondent_phone: _line(20) = ""
    representative_name: _line(16) = ""
    representative_title: _line(16) = ""
    respondent_agent_name: _line(16) = ""
    respondent_agent_gender: _line(4) = ""
    respondent_agent_birth_month: _line(12) = ""
    respondent_agent_employer: _line(30) = ""
    respondent_agent_phone: _line(20) = ""
    cause: _line(28) = ""
    requests: list[_line(34)] = Field(default_factory=list, max_length=3)
    facts: Annotated[str, Field(max_length=110), AfterValidator(_facts)] = ""
    evidence: _line(55) = ""
    witness_name: _line(20) = ""
    witness_address: _line(32) = ""


def _labeled(labels, values):
    return [f"{label}：{value}" for label, value in zip(labels, values, strict=True) if value]


def _fill_line(paragraph, prefix, *values):
    filled = "，".join(value for value in values if value)
    paragraph.runs[0].text = prefix + filled
    for run in paragraph.runs[1:]:
        run.text = ""


def fill_application(original, values):
    if sha256(original).hexdigest() != CONVERTED_SHA256:
        raise ValueError("略阳县核验的劳动者申请书转换件已变化")
    data = LueyangApplicationRequest.model_validate(values)
    document = Document(BytesIO(original))
    p = document.paragraphs
    _fill_line(p[2], "申请人：", *_labeled(
        ("姓名", "性别", "出生日期", "住所", "联系电话"),
        (data.applicant_name, data.applicant_gender, data.applicant_birth_date,
         data.applicant_address, data.applicant_phone),
    ))
    _fill_line(p[3], "委托代理人：", *_labeled(
        ("姓名", "性别", "出生日期", "单位", "联系电话"),
        (data.applicant_agent_name, data.applicant_agent_gender, data.applicant_agent_birth_date,
         data.applicant_agent_employer, data.applicant_agent_phone),
    ))
    _fill_line(p[4], "被申请人：", *_labeled(
        ("用人单位名称", "住所", "通讯地址", "联系电话"),
        (data.respondent_name, data.respondent_address, data.respondent_mailing_address, data.respondent_phone),
    ))
    _fill_line(p[5], "法定代表人（主要负责人）：", *_labeled(
        ("姓名", "职务"), (data.representative_name, data.representative_title),
    ))
    _fill_line(p[6], "委托代理人：", *_labeled(
        ("姓名", "性别", "出生年月", "单位", "联系电话"),
        (data.respondent_agent_name, data.respondent_agent_gender, data.respondent_agent_birth_month,
         data.respondent_agent_employer, data.respondent_agent_phone),
    ))
    _fill_line(p[7], "案由：", data.cause)
    for index, request in enumerate(data.requests):
        if request:
            p[9 + index].runs[1].text += " " + request
    if len(data.requests) == 3 and data.requests[2]:
        p[11].runs[2].text = ""
        p[11].runs[3].text = "\n" + p[11].runs[3].text
    _fill_line(p[12], "事实和理由：", data.facts)
    evidence = (data.evidence, *_labeled(("证人姓名", "证人住所"), (data.witness_name, data.witness_address)))
    _fill_line(p[13], "证据和证据来源、证人姓名和住所：", *evidence)
    for paragraph in p[15:20]:
        paragraph.paragraph_format.keep_with_next = True
    p[21].paragraph_format.page_break_before = True
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for rel_id, rel in list(part.rels.items()):
            if rel.reltype.endswith(suffix):
                del part.rels[rel_id]
    for field in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, field, "")
    return document


def _checked_file(root, relative, checksum):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("略阳县申请书核验材料缺失")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("略阳县申请书核验材料已变化")
    return raw


def staged_application_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide("610727", root)
    proof = json.loads(_checked_file(root, FOLLOWUP, FOLLOWUP_SHA256))
    _checked_file(root, LAYOUT, CONVERTED_SHA256)
    sources = {entry["kind"]: entry for entry in proof["attachments"]}
    for key, template in zip(("application", "authorization"), guide["templates"], strict=True):
        source = sources[key]
        template.update(official_kind="blank", official_sha256=source["sha256"],
                        original_name=source["official_filename"])
    guide["templates"][0].update(
        adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=CONVERTED_SHA256,
        file_origin="official-blank-converted-layout", original_format="DOC",
        document_types=["application"], can_generate=True, generation_mode="blank",
    )
    guide["warnings"][1] = "略阳县官网申请书原件按劳动者申请编排。填写保留原件材料说明和手写签署区，委托书可从官网材料栏下载。"
    guide["can_generate"] = True
    guide["source_version"] = sha256(
        f"{guide['source_version']}:{FOLLOWUP_SHA256}".encode("ascii")
    ).hexdigest()
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配略阳县劳动者仲裁申请书")
    expected = staged_application_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("略阳县申请书与核验的劳动者事项来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    properties = LueyangApplicationRequest.model_json_schema()["properties"]
    fields = []
    for key, label in LABELS.items():
        prop = properties[key]
        if key == "requests":
            fields.append({"key": key, "label": label, "type": "text_list",
                           "maxItems": prop["maxItems"], "maxLength": prop["items"]["maxLength"]})
        else:
            fields.append({"key": key, "label": label, "type": "text", "maxLength": prop["maxLength"]})
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version, "fields": fields,
        "defaults": LueyangApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }
