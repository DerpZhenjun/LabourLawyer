"""Source-bound layout filling for the Hanyin county worker application."""
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Pt
from pydantic import Field

from regional_fixed_layout import display_width, fixed_line
from regional_guides import digest
from regional_huian_quangang_request import OwnBase


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = "shaanxi_hanyin_worker_application_v1"
TEMPLATE_ID = "ankang-610921-worker-application"
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-hanyin-worker/SOURCE-PROOF.json")
PROOF_SHA256 = "8eef94197ce40c293c818b5fdd835186e339d0ca796012a156b730dface2e419"
LAYOUT = Path("templates/_docx/_regional/shaanxi/hanyin-610921-private-application.docx")
IDENTITY = ("province", "city", "district", "scope_level", "region_code", "source_url", "source_id", "source_version")
CONVERTED_SHA256 = "891d211ef70c7d17d97de7d8c2b9761d9f849d59a751767dc8d17ede97421683"

FIELDS = {
    "applicant_name": ("申请人姓名", 1, 1, 9),
    "applicant_gender": ("申请人性别", 1, 3, 5),
    "applicant_birth_date": ("申请人出生年月日", 1, 5, 11),
    "applicant_address": ("申请人详细住址", 2, 2, 34),
    "applicant_id": ("申请人身份证号", 2, 5, 25),
    "applicant_employer": ("申请人工作单位", 2, 8, 34),
    "applicant_landline": ("申请人固话", 2, 11, 12),
    "applicant_mobile": ("申请人手机", 2, 14, 12),
    "respondent_name": ("被申请人企业名称", 3, 1, 32),
    "respondent_type": ("被申请人单位性质", 4, 2, 32),
    "respondent_address": ("被申请人单位地址", 4, 5, 34),
    "representative_name": ("法定代表人姓名", 4, 8, 20),
    "representative_position": ("法定代表人在单位的职务", 5, 2, 29),
    "representative_address": ("法定代表人住址", 5, 5, 28),
    "representative_age": ("法定代表人年龄", 5, 8, 5),
    "respondent_landline": ("被申请人固话", 6, 2, 12),
    "respondent_mobile": ("被申请人手机", 6, 5, 11),
    "facts_and_evidence": ("事实和理由及证据信息", 10, 2, 130),
}
REQUEST_SLOTS = ((8, 2), (8, 5), (9, 2))
REQUEST_WIDTH = 42
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"


class HanyinApplicationRequest(OwnBase):
    applicant_name: fixed_line(FIELDS["applicant_name"][3], EXTRA_WIDE) = ""
    applicant_gender: fixed_line(FIELDS["applicant_gender"][3], EXTRA_WIDE) = ""
    applicant_birth_date: fixed_line(FIELDS["applicant_birth_date"][3], EXTRA_WIDE) = ""
    applicant_address: fixed_line(FIELDS["applicant_address"][3], EXTRA_WIDE) = ""
    applicant_id: fixed_line(FIELDS["applicant_id"][3], EXTRA_WIDE) = ""
    applicant_employer: fixed_line(FIELDS["applicant_employer"][3], EXTRA_WIDE) = ""
    applicant_landline: fixed_line(FIELDS["applicant_landline"][3], EXTRA_WIDE) = ""
    applicant_mobile: fixed_line(FIELDS["applicant_mobile"][3], EXTRA_WIDE) = ""
    respondent_name: fixed_line(FIELDS["respondent_name"][3], EXTRA_WIDE) = ""
    respondent_type: fixed_line(FIELDS["respondent_type"][3], EXTRA_WIDE) = ""
    respondent_address: fixed_line(FIELDS["respondent_address"][3], EXTRA_WIDE) = ""
    representative_name: fixed_line(FIELDS["representative_name"][3], EXTRA_WIDE) = ""
    representative_position: fixed_line(FIELDS["representative_position"][3], EXTRA_WIDE) = ""
    representative_address: fixed_line(FIELDS["representative_address"][3], EXTRA_WIDE) = ""
    representative_age: fixed_line(FIELDS["representative_age"][3], EXTRA_WIDE) = ""
    respondent_landline: fixed_line(FIELDS["respondent_landline"][3], EXTRA_WIDE) = ""
    respondent_mobile: fixed_line(FIELDS["respondent_mobile"][3], EXTRA_WIDE) = ""
    facts_and_evidence: fixed_line(FIELDS["facts_and_evidence"][3], EXTRA_WIDE) = ""
    requests: list[fixed_line(REQUEST_WIDTH, EXTRA_WIDE)] = Field(default_factory=lambda: [""], max_length=len(REQUEST_SLOTS))


def _write_underlined(run, value):
    if not value:
        return
    if run.underline is not True or not run.text or run.text.strip():
        raise ValueError("汉阴县原表的下划线填写位置已变化")
    run.text = value + " " * max(0, len(run.text) - display_width(value, EXTRA_WIDE))


def fill_application(original, values):
    if sha256(original).hexdigest() != CONVERTED_SHA256:
        raise ValueError("汉阴县核验的空表转换件已变化")
    data = HanyinApplicationRequest.model_validate(values)
    document = Document(BytesIO(original))
    paragraphs = document.paragraphs
    for key, (_, paragraph, run, _) in FIELDS.items():
        slot = paragraphs[paragraph].runs[run]
        value = getattr(data, key)
        _write_underlined(slot, value)
        if value and key in {
            "applicant_id", "applicant_landline", "applicant_mobile", "respondent_landline", "respondent_mobile",
        }:
            slot.font.size = Pt(12)
    # The original uses whitespace to wrap these four rows. Keep their starts fixed
    # after inserting proportional-width text into any of the applicant's contact slots.
    if any(getattr(data, key) for key, (_, paragraph, _, _) in FIELDS.items() if paragraph == 2):
        for run_index in (3, 6, 9):
            separator = paragraphs[2].runs[run_index]
            if separator.text != " " * 12 or separator.underline:
                raise ValueError("汉阴县原表的联系栏分隔位置已变化")
            separator.text = "\n" + " " * 8
    if any(data.requests[:2]):
        second_request = paragraphs[8].runs[3]
        if second_request.text != " " * 9 + "2":
            raise ValueError("汉阴县原表的请求栏分隔位置已变化")
        second_request.text = "\n" + " " * 8 + "2"
    for (paragraph, run), value in zip(REQUEST_SLOTS, data.requests):
        _write_underlined(paragraphs[paragraph].runs[run], value)
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
        raise ValueError("汉阴县文件路径超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少汉阴县已核验来源或转换件") from exc
    if sha256(raw).hexdigest() != checksum:
        raise ValueError("汉阴县已核验来源或转换件字节已变化")
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = json.loads(_pinned_bytes(root, PROOF, PROOF_SHA256))
    area, worker = proof["area"], proof["worker"]
    source_url = worker["guide_url"]
    code = area["region_code"]
    date = worker["blank"]["downloaded_at"]
    materials = [
        {"id": f"{code}-worker-{index}", "name": row["name"], "required": row["required"],
         "source_url": source_url, "region_code": code, "service_object": "劳动者"}
        for index, row in enumerate(worker["materials"], 1)
    ]
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"],
        "district": area["district"], "scope_level": "district", "region_code": code,
        "authority": area["authority"], "service_name": "劳动人事争议仲裁申请",
        "source_title": worker["guide_title"], "source_url": source_url,
        "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "collected_at": date, "verified_at": date, "verification_status": "partial",
        "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "法定办结时限": "5 个工作日",
                   "承诺办结时限": f'{worker["commitment_working_days"]} 个工作日',
                   "到现场次数": "1", "办理地点": worker["venue"], "咨询方式": "0915-5218720"},
        "materials": materials, "sections": {},
        "channel": {"raw_value": "该事项暂不支持在线办理", "online_status": "offline",
                    "entry_url": None, "submission_verified": False},
        "warnings": ["本页为汉阴县劳动者事项。收件机关前缀、签名盖章、日期和附件份数由申请人核对后填写。",
                     "劳动者事项的授权委托书列为样表。用人单位事项另有办理地点，申请书附件的适用角色仍待核对。"],
        "templates": [{
            "id": TEMPLATE_ID, "region_code": code, "source_url": source_url,
            "original_name": "劳动争议仲裁申请书（劳动者空表）", "official_kind": "blank",
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
        raise ValueError("仅适配汉阴县劳动者仲裁申请书")
    expected = staged_application_candidate(root)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != expected["templates"][0]:
        raise ValueError("汉阴县申请书与核验的劳动者事项来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": label, "type": "text", "maxLength": width}
              for key, (label, _, _, width) in FIELDS.items()]
    fields.insert(-1, {"key": "requests", "label": "仲裁请求", "type": "text_list",
                      "maxItems": len(REQUEST_SLOTS), "maxLength": REQUEST_WIDTH})
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version,
        "fields": fields, "defaults": HanyinApplicationRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject",
                   "text_controls": "newline_only", "trim_text": True,
                   "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    fields = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, (_, _, _, width) in FIELDS.items()}
    fields["requests"] = {"line_widths": [REQUEST_WIDTH] * len(REQUEST_SLOTS),
                          "max_lines": len(REQUEST_SLOTS), "no_newlines": True, "trim": True}
    return fields
