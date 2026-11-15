"""Fill the reference-marked employer application from Ziyang's own original."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from docx import Document
from pydantic import Field

from regional_fixed_layout import fixed_line
from regional_huian_quangang_request import OwnBase
from regional_ziyang_worker_reference import (
    EXTRA_WIDE, IDENTITY, PROOF, ROOT, _pinned_bytes, _write_slot, staged_guide, staged_reference_candidate,
)


ADAPTER = "shaanxi_ziyang_employer_reference_v1"
TEMPLATE_ID = "ankang-610924-employer-reference"
LAYOUT = Path("templates/_docx/_regional/shaanxi/ziyang-610924-private-employer-reference.docx")
ORIGINAL_SHA256 = "3f313454a14bca271bc550ac18fb5156e4b703cdb34df694ced423b5aba5691c"
FIELDS = {
    "applicant_company": ("申请单位名称", 3, 1, 2, 42),
    "representative_name": ("申请单位法定代表人或负责人姓名", 4, 1, 2, 8),
    "representative_gender": ("申请单位法定代表人或负责人性别", 4, 3, 4, 6),
    "representative_position": ("申请单位法定代表人或负责人职务", 4, 5, 7, 12),
    "applicant_address": ("申请单位住址", 5, 1, 2, 14),
    "applicant_phone": ("申请单位联系电话", 5, 3, 6, 16),
    "agent_name": ("委托代理人姓名", 6, 2, 3, 8),
    "agent_gender": ("委托代理人性别", 6, 4, 5, 4),
    "agent_employer": ("委托代理人工作单位", 6, 6, 7, 14),
    "agent_phone": ("委托代理人联系电话", 6, 8, 9, 12),
    "agent_authority": ("代理权限", 6, 10, 11, 22),
    "respondent_name": ("被申请人姓名", 7, 1, 2, 8),
    "respondent_gender": ("被申请人性别", 7, 3, 4, 4),
    "respondent_birth_date": ("被申请人出生日期", 7, 5, 6, 14),
    "respondent_address": ("被申请人住址", 8, 1, 2, 14),
    "respondent_phone": ("被申请人联系电话", 8, 3, 4, 12),
    "respondent_id": ("被申请人公民身份号码", 8, 5, 6, 25),
}
REQUEST_ROWS = ((10, 0, 1), (11, 0, 1))
FACT_ROWS = ((13, 2, 4), (14, 0, 3))
REQUEST_WIDTH = 46
FACT_WIDTH = 44


class EmployerReferenceRequest(OwnBase):
    applicant_company: fixed_line(FIELDS["applicant_company"][4], EXTRA_WIDE) = ""
    representative_name: fixed_line(FIELDS["representative_name"][4], EXTRA_WIDE) = ""
    representative_gender: fixed_line(FIELDS["representative_gender"][4], EXTRA_WIDE) = ""
    representative_position: fixed_line(FIELDS["representative_position"][4], EXTRA_WIDE) = ""
    applicant_address: fixed_line(FIELDS["applicant_address"][4], EXTRA_WIDE) = ""
    applicant_phone: fixed_line(FIELDS["applicant_phone"][4], EXTRA_WIDE) = ""
    agent_name: fixed_line(FIELDS["agent_name"][4], EXTRA_WIDE) = ""
    agent_gender: fixed_line(FIELDS["agent_gender"][4], EXTRA_WIDE) = ""
    agent_employer: fixed_line(FIELDS["agent_employer"][4], EXTRA_WIDE) = ""
    agent_phone: fixed_line(FIELDS["agent_phone"][4], EXTRA_WIDE) = ""
    agent_authority: fixed_line(FIELDS["agent_authority"][4], EXTRA_WIDE) = ""
    respondent_name: fixed_line(FIELDS["respondent_name"][4], EXTRA_WIDE) = ""
    respondent_gender: fixed_line(FIELDS["respondent_gender"][4], EXTRA_WIDE) = ""
    respondent_birth_date: fixed_line(FIELDS["respondent_birth_date"][4], EXTRA_WIDE) = ""
    respondent_address: fixed_line(FIELDS["respondent_address"][4], EXTRA_WIDE) = ""
    respondent_phone: fixed_line(FIELDS["respondent_phone"][4], EXTRA_WIDE) = ""
    respondent_id: fixed_line(FIELDS["respondent_id"][4], EXTRA_WIDE) = ""
    requests: list[fixed_line(REQUEST_WIDTH, EXTRA_WIDE)] = Field(
        default_factory=lambda: [""], max_length=len(REQUEST_ROWS),
    )
    facts: list[fixed_line(FACT_WIDTH, EXTRA_WIDE)] = Field(
        default_factory=lambda: [""], max_length=len(FACT_ROWS),
    )


def fill_reference(original, values):
    if sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("紫阳县用人单位参考原件字节已变化")
    data = EmployerReferenceRequest.model_validate(values)
    document = Document(BytesIO(original))
    paragraphs = document.paragraphs
    for key, (_, paragraph, begin, end, _) in FIELDS.items():
        _write_slot(paragraphs, (paragraph, begin, end), getattr(data, key), 12)
    for rows, values in ((REQUEST_ROWS, data.requests), (FACT_ROWS, data.facts)):
        for slot, value in zip(rows, values):
            _write_slot(paragraphs, slot, value)
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for relation_id, relation in list(part.rels.items()):
            if relation.reltype.endswith(suffix):
                del part.rels[relation_id]
    for field in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, field, "")
    return document


def _enable_employer(guide, root):
    _pinned_bytes(root, LAYOUT, ORIGINAL_SHA256)
    template = next(entry for entry in guide["templates"] if entry["id"] == TEMPLATE_ID)
    if (template["official_kind"], template["official_sha256"], template.get("reference_marking")) != (
        "sample", ORIGINAL_SHA256, "供当事人参考",
    ):
        raise ValueError("紫阳县用人单位参考原件的来源或标记已变化")
    template.update(
        adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=ORIGINAL_SHA256, service_object="用人单位",
        manual_signing="signature_fingerprint", can_generate=True, document_types=["application"],
        generation_mode="reference_adaptation",
    )
    guide["can_generate"] = True
    guide["warnings"][1] = "请选择与申请人身份对应的申请书。授权委托书与负责人身份证明可查看各自的官网空表。"
    return guide


def staged_dual_role_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    return _enable_employer(staged_reference_candidate(root), root)


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅适用紫阳县用人单位参考稿")
    root = Path(ROOT if root is None else root).resolve()
    expected = _enable_employer(staged_guide(root), root)
    own_template = next(entry for entry in expected["templates"] if entry["id"] == TEMPLATE_ID)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != own_template:
        raise ValueError("紫阳县用人单位参考稿与核验来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": label, "type": "text", "maxLength": width}
              for key, (label, _, _, _, width) in FIELDS.items()]
    fields.extend([
        {"key": "requests", "label": "仲裁请求", "type": "text_list", "maxItems": len(REQUEST_ROWS), "maxLength": REQUEST_WIDTH},
        {"key": "facts", "label": "事实和理由", "type": "text_list", "maxItems": len(FACT_ROWS), "maxLength": FACT_WIDTH},
    ])
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version, "fields": fields,
        "defaults": EmployerReferenceRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    fields = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, (_, _, _, _, width) in FIELDS.items()}
    fields.update({
        key: {"line_widths": [width] * count, "max_lines": count, "no_newlines": True, "trim": True}
        for key, width, count in (("requests", REQUEST_WIDTH, len(REQUEST_ROWS)), ("facts", FACT_WIDTH, len(FACT_ROWS)))
    })
    return fields
