"""Stage official sample entries from the current Xunyang city portal."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-xunyang-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "458ebccb08dd246419bbb77fd36b3e2e70147575f8e6f54addded71745d61103"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("旬阳市来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少旬阳市官方来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("旬阳市来源核验文件字节已变化")
    proof = json.loads(raw)
    area = proof["area"]
    code = area["region_code"]
    if (area["city"], area["district"], code) != ("安康市", "旬阳市", "610981"):
        raise ValueError("来源地区与旬阳市不匹配")

    materials, templates = [], []
    for role, guide in proof["roles"].items():
        service_object = guide["label"]
        url = guide["source_url"]
        for row in guide["materials"]:
            key = row["key"]
            label = f'{row["name"]}（{service_object}）'
            materials.append({
                "id": f"{code}-{role}-{key}", "name": label, "official_name": row["name"],
                "service_object": service_object, "region_code": code, "source_url": url,
                "required": row["required"], "instructions": row["instructions"],
            })
            if key != "application":
                continue
            templates.append({
                "id": f"ankang-{code}-{role}-application-sample", "original_name": f"{label}样表",
                "service_object": service_object, "region_code": code, "source_url": url,
                "official_kind": "sample", "official_sha256": row["official_sample_sha256"],
                "official_attachment_entry": "material_tab", "download_status": "official_link_only",
                "file_type": "jpg", "document_types": [], "can_generate": False,
            })

    worker, employer = (proof["roles"][role] for role in ("worker", "employer"))
    source_url = worker["source_url"]
    return {
        "province": "shaanxi", **area, "scope_level": "district", "service_name": "劳动人事争议仲裁申请",
        "source_title": "旬阳市劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "collected_at": employer["captured_at"], "verified_at": worker["captured_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {
            "实施机关": area["authority"], "咨询方式": proof["phone"],
            "承诺办结时限": f'{worker["commitment_workdays"]} 个工作日',
            "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。',
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": materials, "templates": templates, "sections": {},
        "warnings": ["两类申请人各有一份官方申请书样表。用人单位事项的主体资格证明材料栏当前未列下载链接。"],
    }
