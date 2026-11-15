"""Stage the two official Shangzhou District arbitration guides."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/shangzhou-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "02c83786de82e85eded235c999596b2309b7bc088e8a7d7e727804d078d1bc87"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("商州区来源核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少商州区官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("商州区官方来源核验文件字节已变化")

    proof = json.loads(raw)
    worker = proof["roles"]["worker"]
    employer = proof["roles"]["employer"]
    source_url = worker["source_url"]
    code = proof["region_code"]
    timing = "劳动者事项的承诺时限为官网原样显示，具体办结时间请向商州区人社局核实。"
    attachments = "两条官网指南共有 8 个 JPG 样表。填写前可从对应指南查阅，空白模板仍待核验。"
    return {
        "province": "shaanxi", "province_name": "陕西省", "city": proof["city"], "district": proof["district"],
        "scope_level": "district", "region_code": code, "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "商州区劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for guide in (worker, employer)},
        "collected_at": min(worker["collected_at"], employer["collected_at"]),
        "verified_at": max(worker["collected_at"], employer["collected_at"]),
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {
            "实施机关": proof["authority"], "咨询方式": worker["phone"], "办理地点": worker["venue"],
            "承诺办结时限": (
                f'劳动者事项：官网显示 {worker["commitment_workdays"]} 个工作日。'
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
        "sections": {"官网附件核验": attachments, "承诺时限说明": timing},
        "warnings": [attachments, timing],
    }
