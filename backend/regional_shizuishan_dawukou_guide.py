"""Stage the verified parts of Dawukou District's own arbitration guidance."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/shizuishan-dawukou-own-guide/SOURCE-PROOF.json")
SOURCE_SHA256 = "18a1d9d6493f2dbe63e956e3460a0640393bfd447d7f95d0ebd41905b066fd7f"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("大武口区核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少大武口区核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("大武口区核验文件字节已变化")

    source = json.loads(raw)
    checklist = source["checklist"]
    procedure = source["procedure"]
    code = source["region_code"]
    return {
        "province": source["province"],
        "province_name": source["province_name"],
        "city": source["city"],
        "district": source["district"],
        "region_code": code,
        "scope_level": "district",
        "authority": source["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_url": checklist["url"],
        "source_title": checklist["title"],
        "source_id": digest(checklist["url"])[:24],
        "source_version": SOURCE_SHA256,
        "collected_at": source["collected_at"],
        "verified_at": source["collected_at"],
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "role_sources": {"劳动者": procedure["url"]},
        "fields": {
            "实施机关": source["authority"],
            "办理地点": source["office"],
            "办理形式": source["channel"],
        },
        "channel": {
            "raw_value": source["channel"],
            "form": "offline",
            "online_status": "unverified",
            "entry_url": None,
            "submission_verified": False,
        },
        "materials": [
            {
                "id": f'{code}-worker-{row["key"]}',
                "official_name": row["name"],
                "name": row["name"],
                "original_copy": row["original_copy"],
                "copies": "",
                "service_object": "劳动者",
                "source_url": procedure["url"],
                "region_code": code,
            }
            for row in procedure["materials"]
        ],
        "warnings": [source["application_note"]],
        "sections": {"资料核验": source["application_note"]},
        "templates": [],
    }
