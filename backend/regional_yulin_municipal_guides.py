"""Stage Yulin municipal arbitration guide links and role-specific materials."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/yulin-municipal-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "56722c97503b19a3e04d281a4926e46892433da8616de23f7dabbf98158d3e2a"


PRIMARY_SOURCE = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1114310220443&siteCode=610800000000"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "shaanxi", "榆林市", "市本级", "municipal", "610800",
        PRIMARY_SOURCE, digest(PRIMARY_SOURCE)[:24], PROOF_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("榆林市本级来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少榆林市本级官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("榆林市本级来源核验文件字节已变化")

    proof = json.loads(raw)
    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = worker["source_url"]
    region_code = proof["region_code"]
    attachment_note = (
        "两类指南共挂载七份样表，申请书及授权委托书跨角色分别为同一文件。"
        "申请书原件四页均标注样本。空白模板仍待核验。"
    )
    materials = [
        {
            "id": f'{region_code}-{role}-{item["key"]}',
            "name": f'{item["name"]}（{guide["name"]}）',
            "official_name": item["name"],
            "service_object": guide["name"],
            "source_url": guide["source_url"],
            "region_code": region_code,
            "required": item["required"],
            "original_copy": item["original_copy"],
            "format": item["format"],
            "copies": item["copies"],
        }
        for role, guide in proof["roles"].items()
        for item in guide["materials"]
    ]

    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": proof["city"],
        "district": "市本级",
        "scope_level": "municipal",
        "region_code": region_code,
        "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "榆林市本级劳动人事争议仲裁申请（劳动者、用人单位）",
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
            "办理地点": f'劳动者事项：{worker["office"]}。\n用人单位事项：{employer["office"]}。',
            "承诺办结时限": f'{proof["commitment_workdays"]} 个工作日',
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials,
        "templates": [],
        "sections": {"官网附件核验": attachment_note},
        "warnings": [attachment_note, "此页仅适用于榆林市本级事项。"],
    }
