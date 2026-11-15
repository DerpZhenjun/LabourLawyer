"""Project Ankang's own municipal role guides and verified sample entries."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-municipal-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "555d930c0440ad3a269add0d313ae9289d5d5e6159c3d020cdd556c2f92549a3"
PRIMARY_SOURCE = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1117911280248&siteCode=610900000000"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code", "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "shaanxi", "安康市", "市本级", "municipal", "610900", PRIMARY_SOURCE, digest(PRIMARY_SOURCE)[:24], PROOF_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("安康市本级来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少安康市本级官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("安康市本级来源核验文件字节已变化")
    proof = json.loads(raw)
    area = proof["area"]
    code = area["region_code"]
    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = worker["source_url"]
    result = {
        "province": "shaanxi", **area, "scope_level": "municipal", "service_name": "劳动人事争议仲裁申请",
        "source_title": "安康市本级劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "collected_at": worker["captured_at"], "verified_at": employer["captured_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {
            "实施机关": area["authority"], "咨询方式": proof["phone"],
            "承诺办结时限": f'{worker["commitment_workdays"]} 个工作日',
            "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。',
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [], "templates": [], "sections": {},
        "warnings": [
            "办理窗口设在高新区数字化创业中心。此页指南与样表适用范围为安康市本级事项。",
            "两类申请书的原件各不相同。授权委托书为一页静态 PDF，请从对应事项查看。",
        ],
    }
    if not exact_municipal(result):
        raise ValueError("安康市本级指南与核验来源不匹配")

    for role, guide in proof["roles"].items():
        service_object = guide["label"]
        for row in guide["materials"]:
            key = row["key"]
            label = f'{row["name"]}（{service_object}）'
            result["materials"].append({
                "id": f"{code}-{role}-{key}", "name": label, "official_name": row["name"],
                "service_object": service_object, "source_url": guide["source_url"], "region_code": code,
                "required": row["required"], "instructions": row["instructions"],
            })
            if key not in {"application", "authorization"}:
                continue
            result["templates"].append({
                "id": f"ankang-{code}-{role}-{key}-sample", "original_name": f"{label}样表",
                "service_object": service_object, "region_code": code, "source_url": guide["source_url"],
                "official_kind": "sample", "official_sha256": row["attachment_sha256"],
                "official_attachment_entry": "material_tab", "download_status": "official_link_only",
                "file_type": row["attachment_format"], "document_types": [], "can_generate": False,
            })
    return result
