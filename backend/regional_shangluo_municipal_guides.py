"""Preserve the Shangluo municipal guides and their sample-file conflict."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/shangluo-municipal-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "fc98c0a477160422f85eee1c9e2e6d82400ad6cf0ed92791074d8751b1a0037e"
PRIMARY_SOURCE = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1119138246162&siteCode=611000000000"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code", "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "shaanxi", "商洛市", "市本级", "municipal", "611000", PRIMARY_SOURCE, digest(PRIMARY_SOURCE)[:24], PROOF_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("商洛市本级来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少商洛市本级官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("商洛市本级来源核验文件字节已变化")
    proof = json.loads(raw)
    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = worker["source_url"]
    code = proof["region_code"]
    duplicate_notice = (
        f'两条官网指南中有 {proof["duplicated_attachment_count"]} 个不同材料入口返回逐字节相同的 JPG。'
        "申请书、授权委托书及相关材料的独立样表待核实。"
    )
    result = {
        "province": "shaanxi", "province_name": "陕西省", "city": proof["city"], "district": "市本级",
        "scope_level": proof["region_scope"], "region_code": code, "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "商洛市本级劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for guide in (worker, employer)},
        "collected_at": worker["collected_at"], "verified_at": employer["collected_at"],
        "verification_status": "conflict", "published": False, "can_generate": False,
        "fields": {"实施机关": proof["authority"], "咨询方式": proof["phone"], "办理地点": worker["venue"],
                   "承诺办结时限": f'{worker["commitment_workdays"]} 个工作日'},
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {"id": f'{code}-{role}-{row["key"]}', "name": f'{row["name"]}（{guide["name"]}）',
             "official_name": row["name"], "service_object": guide["name"], "source_url": guide["source_url"],
             "region_code": code, "required": row["required"], "instructions": row["instructions"]}
            for role, guide in proof["roles"].items() for row in guide["materials"]
        ],
        "templates": [], "sections": {"官网附件核验": duplicate_notice},
        "warnings": [duplicate_notice, "此页仅适用于商洛市本级事项。"],
    }
    if not exact_municipal(result):
        raise ValueError("商洛市本级指南与核验来源不匹配")
    return result
