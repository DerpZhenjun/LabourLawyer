"""Stage Weinan municipal arbitration guide links and role-specific materials."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/weinan-municipal-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "a3562cf3db1a5bb88209e539396e6ee315d9c4a7efb5e35d33a7e179c0dbfd35"


PRIMARY_SOURCE = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1113560176120&siteCode=610500000000"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "shaanxi", "渭南市", "市本级", "municipal", "610500",
        PRIMARY_SOURCE, digest(PRIMARY_SOURCE)[:24], PROOF_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("渭南市本级来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少渭南市本级官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("渭南市本级来源核验文件字节已变化")

    proof = json.loads(raw)
    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = worker["source_url"]
    region_code = proof["region_code"]
    attachment_note = "两条官网指南各有一份申请书样表。请按申请人身份查看对应指南，空白模板仍待核验。"
    materials = []
    for role, guide in proof["roles"].items():
        material = guide["material"]
        materials.append({
            "id": f"{region_code}-{role}-application",
            "name": f'{material["name"]}（{guide["name"]}）',
            "official_name": material["name"],
            "service_object": guide["name"],
            "source_url": guide["source_url"],
            "region_code": region_code,
            "required": material["required"],
            "instructions": material["instructions"],
        })

    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": proof["city"],
        "district": "市本级",
        "scope_level": "municipal",
        "region_code": region_code,
        "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "渭南市本级劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url,
        "source_id": digest(source_url)[:24],
        "source_version": PROOF_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for guide in (worker, employer)},
        "collected_at": min(worker["collected_at"], employer["collected_at"]),
        "verified_at": max(worker["collected_at"], employer["collected_at"]),
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": proof["authority"],
            "咨询方式": proof["consultation_phone"],
            "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。',
            "承诺办结时限": f'{proof["commitment_workdays"]} 个工作日',
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials,
        "templates": [],
        "sections": {"官网附件核验": attachment_note},
        "warnings": [attachment_note, "此页仅适用于渭南市本级事项。"],
    }
