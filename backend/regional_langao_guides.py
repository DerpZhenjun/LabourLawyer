"""Project the two verified Langao county guides and their official sample links."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-langao-own-guides/SOURCE-PROOF.json")
NOTES = PROOF.with_name("SOURCE-NOTES.json")
PROOF_SHA256 = "12195122753096c1ba01daf998e5855cbc1fd39f5265031590b30f0d0dac71a0"
NOTES_SHA256 = "017acd8fde66169fcc0f2f61e6bbc807578edbe223518e5984c6d93bd1322706"
MATERIAL_KEYS = {
    "劳动人事争议仲裁申请书": "application",
    "主体资格证明材料": "qualification",
    "授权委托书": "authorization",
}


def _pinned_json(root, path, expected):
    path = (root / path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("岚皋县来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少岚皋县官方来源核验文件") from exc
    if sha256(raw).hexdigest() != expected:
        raise ValueError("岚皋县来源核验文件字节已变化")
    return json.loads(raw)


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    proof = _pinned_json(root, PROOF, PROOF_SHA256)
    notes = _pinned_json(root, NOTES, NOTES_SHA256)
    area = proof["area"]
    code = area["region_code"]
    if (area["city"], area["district"], code) != ("安康市", "岚皋县", "610925"):
        raise ValueError("来源地区与岚皋县不匹配")
    if notes["region_code"] != code or notes["application_sha256"] != proof["application"]["sha256"]:
        raise ValueError("岚皋县原件填写说明与来源不匹配")
    materials, templates = [], []
    for role in ("worker", "employer"):
        official = proof[role]
        for index, row in enumerate(official["materials"], 1):
            label = f'{row["name"]}（{official["role"]}）'
            kind = MATERIAL_KEYS[row["name"]]
            attachment = proof[kind]
            materials.append({
                "id": f"{code}-{role}-{index}", "name": label, "official_name": row["name"],
                "service_object": official["role"], "source_url": official["url"], "region_code": code,
                "required": row["required"], "instructions": notes["applicant_role_notes"][role][row["name"]],
            })
            templates.append({
                "id": f"ankang-{code}-{role}-{kind}-sample", "original_name": f'{label}样表',
                "service_object": official["role"], "region_code": code, "source_url": official["url"],
                "official_kind": attachment["official_kind"], "official_sha256": attachment["sha256"],
                "official_attachment_entry": "material_tab", "download_status": "official_link_only",
                "file_type": attachment.get("format", "docx"), "document_types": [], "can_generate": False,
            })
    worker, employer = proof["worker"], proof["employer"]
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"], "district": area["district"],
        "scope_level": "district", "region_code": code, "authority": area["authority"],
        "service_name": "劳动人事争议仲裁申请", "source_title": "岚皋县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": worker["url"], "source_id": digest(worker["url"])[:24],
        "source_version": digest(PROOF_SHA256 + ":" + NOTES_SHA256),
        "collected_at": worker["observed_at"], "verified_at": employer["observed_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "咨询方式": notes["official_phone"], "承诺办结时限": notes["commitment"],
                   "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。'},
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials, "templates": templates,
        "sections": {"申请书填写说明": notes["application_note"]},
        "warnings": ["请按申请人身份核对对应窗口和材料。两条事项当前展示本县官网样表。", notes["application_note"]],
    }
