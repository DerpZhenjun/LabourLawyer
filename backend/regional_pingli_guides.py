"""Stage Pingli county's own role guides and publicly labelled sample entries."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-pingli-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "0da12f985eec718ea0559ee35fa742fa34131bf78271eea82e0f0f6d3f5da048"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("平利县来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少平利县官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("平利县来源核验文件字节已变化")
    proof = json.loads(raw)
    area = proof["area"]
    code = area["region_code"]
    if (area["city"], area["district"], code) != ("安康市", "平利县", "610926"):
        raise ValueError("来源地区与平利县不匹配")

    materials, templates = [], []
    for role, official in proof["roles"].items():
        service_object = official["label"]
        url = official["url"]
        for row in official["materials"]:
            key = row["key"]
            label = f'{row["name"]}（{service_object}）'
            materials.append({
                "id": f"{code}-{role}-{key}", "name": label, "official_name": row["name"],
                "service_object": service_object, "source_url": url, "region_code": code,
                "required": "必要" if row["required"] else "非必要", "instructions": row["instructions"],
            })
            if key == "identity":
                continue
            templates.append({
                "id": f"ankang-{code}-{role}-{key}-sample", "original_name": f"{label}样表",
                "service_object": service_object, "region_code": code, "source_url": url,
                "official_kind": "sample", "official_sha256": row["sample_sha256"],
                "official_attachment_entry": "material_tab", "download_status": "official_link_only",
                "file_type": "jpg", "document_types": [], "can_generate": False,
            })
    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    duplicate_notice = "劳动者指南中标为“空表”的四项下载内容与对应样表完全相同。"
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"], "district": area["district"],
        "scope_level": "district", "region_code": code, "authority": area["authority"],
        "service_name": "劳动人事争议仲裁申请", "source_title": "平利县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": worker["url"], "source_id": digest(worker["url"])[:24], "source_version": PROOF_SHA256,
        "collected_at": employer["captured_at"], "verified_at": worker["captured_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {
            "实施机关": area["authority"],
            "咨询方式": f'{proof["consultation_window"]} {proof["phone"]}',
            "承诺办结时限": f'事项指南显示 {proof["portal_commitment"]}',
            "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。',
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials, "templates": templates,
        "sections": {"官网附件核验": duplicate_notice},
        "warnings": [duplicate_notice, "请按申请人身份核对对应窗口和材料。"],
    }
