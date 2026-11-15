"""Initial field mapping for Ziyang's reference-marked worker application."""
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
ADAPTER = "shaanxi_ziyang_worker_reference_v1"
TEMPLATE_ID = "ankang-610924-worker-reference"
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-ziyang-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "cfede06ab60528f3281b656495c57f668d3ad1da7ae6be492b64c576ba331377"
LAYOUT = Path("templates/_docx/_regional/shaanxi/ziyang-610924-private-worker-reference.docx")
IDENTITY = ("province", "city", "district", "scope_level", "region_code", "source_url", "source_id", "source_version")
ORIGINAL_SHA256 = "b6540c117e1478f18a31e4f31bf8d56f6f7922417c049f163ba68d4412e1f83f"
EXTRA_WIDE = "ABCDEFGHIJKLMNOPQRSTUVWXYZmw@%&"
FIELDS = {
    "applicant_name": (3, 1, 2, 8),
    "applicant_gender": (3, 3, 4, 4),
    "applicant_birth_date": (3, 5, 6, 14),
    "applicant_address": (4, 1, 2, 18),
    "applicant_phone": (4, 3, 5, 13),
    "applicant_id": (4, 6, 7, 25),
    "agent_name": (5, 2, 3, 8),
    "agent_gender": (5, 4, 5, 4),
    "agent_employer": (5, 6, 7, 15),
    "agent_phone": (5, 8, 9, 12),
    "agent_authority": (5, 10, 11, 24),
    "respondent_name": (6, 1, 2, 44),
    "representative_name": (7, 1, 2, 8),
    "representative_gender": (7, 3, 4, 6),
    "representative_position": (7, 5, 7, 10),
    "respondent_address": (8, 1, 2, 14),
    "respondent_phone": (8, 3, 6, 19),
}
REQUEST_ROWS = ((10, 0, 1), (11, 0, 1))
FACT_ROWS = ((13, 2, 4), (14, 0, 3))
REQUEST_WIDTH = 46
FACT_WIDTH = 44


class WorkerReferenceRequest(OwnBase):
    applicant_name: fixed_line(FIELDS["applicant_name"][3], EXTRA_WIDE) = ""
    applicant_gender: fixed_line(FIELDS["applicant_gender"][3], EXTRA_WIDE) = ""
    applicant_birth_date: fixed_line(FIELDS["applicant_birth_date"][3], EXTRA_WIDE) = ""
    applicant_address: fixed_line(FIELDS["applicant_address"][3], EXTRA_WIDE) = ""
    applicant_phone: fixed_line(FIELDS["applicant_phone"][3], EXTRA_WIDE) = ""
    applicant_id: fixed_line(FIELDS["applicant_id"][3], EXTRA_WIDE) = ""
    agent_name: fixed_line(FIELDS["agent_name"][3], EXTRA_WIDE) = ""
    agent_gender: fixed_line(FIELDS["agent_gender"][3], EXTRA_WIDE) = ""
    agent_employer: fixed_line(FIELDS["agent_employer"][3], EXTRA_WIDE) = ""
    agent_phone: fixed_line(FIELDS["agent_phone"][3], EXTRA_WIDE) = ""
    agent_authority: fixed_line(FIELDS["agent_authority"][3], EXTRA_WIDE) = ""
    respondent_name: fixed_line(FIELDS["respondent_name"][3], EXTRA_WIDE) = ""
    representative_name: fixed_line(FIELDS["representative_name"][3], EXTRA_WIDE) = ""
    representative_gender: fixed_line(FIELDS["representative_gender"][3], EXTRA_WIDE) = ""
    representative_position: fixed_line(FIELDS["representative_position"][3], EXTRA_WIDE) = ""
    respondent_address: fixed_line(FIELDS["respondent_address"][3], EXTRA_WIDE) = ""
    respondent_phone: fixed_line(FIELDS["respondent_phone"][3], EXTRA_WIDE) = ""
    requests: list[fixed_line(REQUEST_WIDTH, EXTRA_WIDE)] = Field(default_factory=lambda: [""], max_length=len(REQUEST_ROWS))
    facts: list[fixed_line(FACT_WIDTH, EXTRA_WIDE)] = Field(default_factory=lambda: [""], max_length=len(FACT_ROWS))


def _write_slot(paragraphs, slot, value, font_size=None):
    if not value:
        return
    paragraph, begin, end = slot
    runs = paragraphs[paragraph].runs[begin:end]
    if not runs or any(run.underline is not True or run.text.strip() or not run.text for run in runs):
        raise ValueError("紫阳县参考原表的填写位置已变化")
    padding = max(0, sum(len(run.text) for run in runs) - display_width(value, EXTRA_WIDE))
    runs[0].text = value + " " * padding
    if font_size is not None:
        runs[0].font.size = Pt(font_size)
    for run in runs[1:]:
        run.text = ""


def fill_reference(original, values):
    if sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("紫阳县劳动者原件字节已变化")
    data = WorkerReferenceRequest.model_validate(values)
    document = Document(BytesIO(original))
    paragraphs = document.paragraphs
    for field, (paragraph, begin, end, _) in FIELDS.items():
        size = 12 if field.endswith(("_phone", "_name")) or field in {"agent_authority", "representative_position"} else None
        _write_slot(paragraphs, (paragraph, begin, end), getattr(data, field), size)
    for rows, values in ((REQUEST_ROWS, data.requests), (FACT_ROWS, data.facts)):
        for slot, value in zip(rows, values):
            _write_slot(paragraphs, slot, value)
    for part, suffix in ((document.part, "/customXml"), (document.part.package, "/custom-properties")):
        for key, relation in list(part.rels.items()):
            if relation.reltype.endswith(suffix):
                del part.rels[key]
    for key in ("author", "last_modified_by", "comments", "keywords", "subject", "identifier"):
        setattr(document.core_properties, key, "")
    return document


LABELS = {
    "applicant_name": "申请人姓名", "applicant_gender": "申请人性别",
    "applicant_birth_date": "申请人出生日期", "applicant_address": "申请人住址",
    "applicant_phone": "申请人联系电话", "applicant_id": "申请人公民身份号码",
    "agent_name": "委托代理人姓名", "agent_gender": "委托代理人性别",
    "agent_employer": "委托代理人工作单位", "agent_phone": "委托代理人联系电话",
    "agent_authority": "代理权限", "respondent_name": "被申请人名称",
    "representative_name": "法定代表人或负责人姓名", "representative_gender": "法定代表人或负责人性别",
    "representative_position": "法定代表人或负责人职务", "respondent_address": "被申请人住址",
    "respondent_phone": "被申请人联系电话",
}


def _pinned_bytes(root, relative, expected_sha):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("紫阳县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少紫阳县核验原件或来源证明") from exc
    if sha256(raw).hexdigest() != expected_sha:
        raise ValueError("紫阳县核验文件字节已变化")
    return raw


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = json.loads(_pinned_bytes(root, PROOF, PROOF_SHA256))
    area = proof["area"]
    code = area["region_code"]
    worker, employer = proof["worker"], proof["employer"]
    source_url = worker["source_url"]
    attachments = {(entry["role"], entry["material"]): entry for entry in proof["attachments"]}
    materials = [
        {"id": f"{code}-{role}-{index}", "name": f'{row["name"]}（{guide["role"]}）',
         "official_name": row["name"], "required": row["required"], "instructions": row["instructions"],
         "source_url": guide["source_url"], "region_code": code, "service_object": guide["role"]}
        for role, guide in (("worker", worker), ("employer", employer))
        for index, row in enumerate(guide["materials"], 1)
    ]
    templates = []
    for role, kind, suffix, title, official_kind in (
        ("worker", "application", "worker-reference", "紫阳县劳动者仲裁申请书（参考格式）", "sample"),
        ("employer", "application", "employer-reference", "紫阳县用人单位仲裁申请书（参考格式）", "sample"),
        ("worker", "authorization", "authorization", "紫阳县授权委托书（两类事项官网空表）", "blank"),
        ("employer", "representative-proof", "representative-proof", "紫阳县法定代表人或负责人身份证明书（官网空表）", "blank"),
    ):
        entry = attachments[role, kind]
        templates.append({
            "id": f"ankang-{code}-{suffix}", "region_code": code, "source_url": entry["url"], "original_name": title,
            "guide_source_url": proof[role]["source_url"], "official_kind": official_kind,
            "official_sha256": entry["sha256"], "official_bytes": entry["bytes"], "file_type": "docx",
            "download_status": "official_link_only", "document_types": [], "can_generate": False,
            **({"reference_marking": "供当事人参考"} if entry.get("reference_wording_present") else {}),
        })
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"],
        "district": area["district"], "region_code": code, "scope_level": "district", "authority": area["authority"],
        "service_name": "劳动人事争议仲裁申请", "source_title": "紫阳县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "collected_at": worker["observed_at"], "verified_at": worker["observed_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "办理地点": proof["venue"]},
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials, "templates": templates, "sections": {},
        "warnings": ["劳动者和用人单位使用各自原件。申请书保留供当事人参考标记，签名、手印和日期由本人填写。",
                     "用人单位申请书、授权委托书和负责人身份证明书提供对应的官网入口。"],
    }


def staged_reference_candidate(root=None):
    root = Path(ROOT if root is None else root).resolve()
    guide = staged_guide(root)
    _pinned_bytes(root, LAYOUT, ORIGINAL_SHA256)
    template = next(entry for entry in guide["templates"] if entry["id"] == TEMPLATE_ID)
    if template["official_kind"] != "sample" or template["official_sha256"] != ORIGINAL_SHA256:
        raise ValueError("紫阳县参考标记或官方原件绑定已变化")
    template.update(adapter=ADAPTER, file=LAYOUT.as_posix(), sha256=ORIGINAL_SHA256,
                    can_generate=True, document_types=["application"], generation_mode="reference_adaptation")
    guide["can_generate"] = True
    return guide


def checked_adapter(guide, template, kind, root=None):
    if kind != "application" or template.get("id") != TEMPLATE_ID:
        raise ValueError("仅支持紫阳县劳动者参考稿")
    expected = staged_reference_candidate(root)
    exact = next(entry for entry in expected["templates"] if entry["id"] == TEMPLATE_ID)
    if any(guide.get(key) != expected[key] for key in IDENTITY) or template != exact:
        raise ValueError("紫阳县参考稿与核验来源不匹配")
    return ADAPTER


def schema_descriptor(source_version):
    fields = [{"key": key, "label": LABELS[key], "type": "text", "maxLength": width}
              for key, (_, _, _, width) in FIELDS.items()]
    fields.extend([
        {"key": "requests", "label": "仲裁请求", "type": "text_list", "maxItems": 2, "maxLength": REQUEST_WIDTH},
        {"key": "facts", "label": "事实和理由", "type": "text_list", "maxItems": 2, "maxLength": FACT_WIDTH},
    ])
    return {
        "schema_id": ADAPTER, "schema_version": 1, "source_version": source_version, "fields": fields,
        "defaults": WorkerReferenceRequest().model_dump(),
        "policy": {"unknown_fields": "reject", "invalid_xml": "reject", "text_controls": "newline_only",
                   "trim_text": True, "capacity_is_official_requirement": False, "signature_field": "manual_only"},
    }


def layout_fields():
    fields = {key: {"first_width": width, "later_width": width, "max_lines": 1, "trim": True}
              for key, (_, _, _, width) in FIELDS.items()}
    fields.update({key: {"line_widths": [width, width], "max_lines": 2, "no_newlines": True, "trim": True}
                   for key, width in (("requests", REQUEST_WIDTH), ("facts", FACT_WIDTH))})
    return fields
