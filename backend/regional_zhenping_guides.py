"""Stage only the guides and official sample links verified for Zhenping county."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-zhenping-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "602da4ec0929522c0d9863cd6be383331f084ce957692fd2faf950f4ceee54ef"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("镇坪县来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少镇坪县官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("镇坪县来源核验文件字节已变化")
    proof = json.loads(raw)
    area = proof["area"]
    code = area["region_code"]
    if (area["city"], area["district"], code) != ("安康市", "镇坪县", "610927"):
        raise ValueError("来源地区与镇坪县不匹配")

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
                "required": row["required"], "instructions": row["instructions"],
            })
            if row["classification"] != "sample":
                continue
            name = f"劳动仲裁申请书提纲（{service_object}事项官网附件）" if key == "application" else f"{label}样表"
            templates.append({
                "id": f"ankang-{code}-{role}-{key}-sample", "original_name": name,
                "service_object": service_object, "region_code": code, "source_url": url,
                "official_kind": "sample", "official_sha256": row["sample_sha256"],
                "official_attachment_entry": "material_tab", "download_status": "official_link_only",
                "file_type": row["format"], "original_format": row["format"].upper(),
                "document_types": [], "can_generate": False,
            })

    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    commitment = "\n".join(
        f'{guide["label"]}事项：{guide["commitment_workdays"]} 个工作日' for guide in (worker, employer)
    )
    duplicate_notice = "两条指南中标作“空表”的 8 个下载与各自对应的样表逐字节相同。"
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"], "district": area["district"],
        "scope_level": "district", "region_code": code, "authority": area["authority"],
        "service_name": "劳动人事争议仲裁申请", "source_title": "镇坪县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": worker["url"], "source_id": digest(worker["url"])[:24], "source_version": PROOF_SHA256,
        "collected_at": worker["captured_at"], "verified_at": employer["captured_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {
            "实施机关": area["authority"], "咨询方式": proof["phone"],
            "承诺办结时限": commitment,
            "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。',
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials, "templates": templates,
        "sections": {"官网附件核验": duplicate_notice},
        "warnings": [duplicate_notice, "请按申请人身份核对对应材料和申请书格式。"],
    }
