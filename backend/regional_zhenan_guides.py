"""Stage the two official Zhenan County arbitration guides."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/zhenan-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "6f27b6c4a3e766c0adcee71f8b180f8c248ff635bd21fde8fe2a9d05bbd0e7da"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("镇安县来源核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少镇安县官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("镇安县官方来源核验文件字节已变化")

    proof = json.loads(raw)
    worker = proof["roles"]["worker"]
    employer = proof["roles"]["employer"]
    source_url = worker["source_url"]
    code = proof["region_code"]
    attachments = "两条官网指南的 DOC 样表逐字节相同。请按申请人身份查看对应指南的办理地点和材料。空白模板仍待核验。"
    return {
        "province": "shaanxi", "province_name": "陕西省", "city": proof["city"], "district": proof["district"],
        "scope_level": "district", "region_code": code, "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "镇安县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for guide in (worker, employer)},
        "collected_at": min(worker["collected_at"], employer["collected_at"]),
        "verified_at": max(worker["collected_at"], employer["collected_at"]),
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {
            "实施机关": proof["authority"],
            "咨询方式": f'劳动者事项：{worker["phone"]}。用人单位事项：{employer["phone"]}。',
            "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。',
            "承诺办结时限": (
                f'劳动者事项：{worker["commitment_workdays"]} 个工作日。'
                f'用人单位事项：{employer["commitment_workdays"]} 个工作日。'
            ),
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {"id": f'{code}-{role}-{row["key"]}', "name": f'{row["name"]}（{guide["name"]}）',
             "official_name": row["name"], "service_object": guide["name"], "source_url": guide["source_url"],
             "region_code": code, "required": row["required"], "instructions": row["instructions"]}
            for role, guide in proof["roles"].items() for row in guide["materials"]
        ],
        "templates": [],
        "sections": {"官网附件核验": attachments},
        "warnings": [attachments],
    }
