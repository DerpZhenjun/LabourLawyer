"""Assist filling the independently reviewed Foping application sample."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated
from unicodedata import category

from docx import Document
from pydantic import AfterValidator, Field

from regional_hanzhong_guides import staged_guide
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_foping_worker_reference_v1"
TEMPLATE_ID = "hanzhong-610730-application"
LAYOUT = Path("templates/_docx/_regional/shaanxi/foping-610730-private-reference.docx")
OFFICIAL_SHA256 = "dae75fba8210fede01e8f5a22e45ff66dabfe8f081c6092037460ef6878014cd"
CONVERTED_SHA256 = "21e807daedfb1c563f391c8795a7d1da81938845aeaea8daf145a8beab424af4"
IDENTITY = ("province", "city", "district", "scope_level", "region_code", "source_url", "source_id", "source_version")
LABELS = {
    "applicant_name": "申请人姓名",
    "applicant_gender": "申请人性别",
    "applicant_ethnicity": "申请人民族",
    "applicant_age": "申请人年龄",
    "applicant_address": "申请人住所地",
    "applicant_id_number": "申请人身份证号",
    "applicant_contact": "申请人联系方式",
    "respondent_name": "被申请人登记全称",
    "respondent_credit_code": "被申请人统一社会信用代码",
    "respondent_address": "被申请人地址",
    "respondent_contact": "被申请人联系电话",
    "respondent_representative_name": "法定代表人姓名",
    "respondent_representative_gender": "法定代表人性别",
    "respondent_representative_title": "法定代表人职务",
    "respondent_representative_phone": "法定代表人电话",
    "requests": "仲裁请求",
    "facts": "事实与理由",
}


def _single_line(value):
    if any(category(c).startswith("C") or category(c) in {"Zl", "Zp"} for c in value):
        raise ValueError("本栏请填写一行文字")
    return value.strip()


def _line(limit):
    return Annotated[str, Field(max_length=limit), AfterValidator(_single_line)]


def _valid_age(value):
    if value and (not value.isascii() or not value.isdecimal() or value.startswith("0") or not 1 <= int(value) <= 120):
        raise ValueError("年龄须留空或填写 1 至 120 的整数")
    return value


def _facts(value):
    parts = value.split("\n")
    if len(parts) > 3:
        raise ValueError("事实与理由最多三段")
    return "\n".join(_single_line(part) for part in parts).strip()


class FopingReferenceRequest(OwnBase):
    applicant_name: _line(20) = ""
    applicant_gender: _line(4) = ""
    applicant_ethnicity: _line(8) = ""
    applicant_age: Annotated[str, Field(max_length=3), AfterValidator(_single_line), AfterValidator(_valid_age)] = ""
    applicant_address: _line(45) = ""
    applicant_id_number: _line(22) = ""
    applicant_contact: _line(24) = ""
    respondent_name: _line(50) = ""
    respondent_credit_code: _line(24) = ""
    respondent_address: _line(45) = ""
    respondent_contact: _line(24) = ""
    respondent_representative_name: _line(20) = ""
    respondent_representative_gender: _line(4) = ""
    respondent_representative_title: _line(18) = ""
    respondent_representative_phone: _line(24) = ""
    requests: list[_line(38)] = Field(default_factory=list, max_length=3)
    facts: Annotated[str, Field(max_length=120), AfterValidator(_facts)] = ""


def _set(paragraph, label, value=""):
    runs = paragraph.runs
    runs[0].text = label + (value if len(runs) == 1 else "")
    for run in runs[1:]:
        run.text = ""
    if len(runs) > 1:
        runs[-1].text = value


def fill_application(original, values):
    if sha256(original).hexdigest() != CONVERTED_SHA256:
        raise ValueError("佛坪县样表转换件已变化")
    data = FopingReferenceRequest.model_validate(values)
    document = Document(BytesIO(original))
    p = document.paragraphs
    if len(p) != 19 or p[0].text.strip() != "劳动人事争议仲裁申请书（模板）":
        raise ValueError("佛坪县申请书样表填写位置已变化")
    _set(p[0], "劳动人事争议仲裁申请书（参考填写）")
    _set(p[2], "申 请 人：",
         f"{data.applicant_name}  性别：{data.applicant_gender}  民族：{data.applicant_ethnicity}  年龄：{data.applicant_age}\n"
         f"住所地：{data.applicant_address}\n身份证号：{data.applicant_id_number}  联系方式：{data.applicant_contact}")
    _set(p[3], "被申请人：", data.respondent_name)
    _set(p[4], "统一社会信用代码：", data.respondent_credit_code)
    _set(p[5], "地    址：", f"{data.respondent_address}\n联系电话：{data.respondent_contact}")
    _set(p[6], "法定代表人：", f"{data.respondent_representative_name}  性别：{data.respondent_representative_gender}  "
         f"职务：{data.respondent_representative_title}  电话：{data.respondent_representative_phone}")
    request_labels = ("仲裁请求：1. ", "2. ", "3. ")
    for index, label in enumerate(request_labels):
        value = data.requests[index] if index < len(data.requests) else ""
        paragraph = p[7 + index]
        source_label = paragraph.runs[0].text
        indentation = source_label[:len(source_label) - len(source_label.lstrip())]
        _set(paragraph, indentation + label, value)
    _set(p[13], "事实与理由：", data.facts)
    _set(p[14], "")
    _set(p[15], "")
    _set(p[17], "                         申请人（手写签名）：")
    _set(p[18], "                            年    月    日")
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for rel_id, rel in list(part.rels.items()):
            if rel.reltype.endswith(suffix):
                del part.rels[rel_id]
    for key in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, key, "")
    return document


def staged_reference_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide("610730", root)
    path = (root/LAYOUT).resolve()
    if not path.is_relative_to(root) or not path.is_file() or sha256(path.read_bytes()).hexdigest() != CONVERTED_SHA256:
        raise ValueError("佛坪县核验的样表转换件缺失或字节已变化")
    choices = [entry for entry in guide["templates"] if entry["id"] == TEMPLATE_ID]
    if len(choices) != 1 or (choices[0]["official_kind"], choices[0]["official_sha256"]) != ("sample", OFFICIAL_SHA256):
        raise ValueError("佛坪县来源证明与样表不匹配")
    choices[0].update(adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=CONVERTED_SHA256,
                      can_generate=True, document_types=["application"], generation_mode="reference_adaptation")
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适配佛坪县劳动者仲裁申请样表")
    expected = staged_reference_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("佛坪县申请样表与核验来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    props = FopingReferenceRequest.model_json_schema()["properties"]
    fields = []
    for key, label in LABELS.items():
        if key == "requests":
            fields.append({"key": key, "label": label, "type": "text_list",
                           "maxItems": props[key]["maxItems"], "maxLength": props[key]["items"]["maxLength"]})
        else:
            fields.append({"key": key, "label": label, "type": "text", "maxLength": props[key]["maxLength"]})
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version, "fields": fields,
        "defaults": FopingReferenceRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }
