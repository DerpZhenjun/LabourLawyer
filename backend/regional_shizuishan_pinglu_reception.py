"""Stage the reception function verified for Pinglu County's arbitration institute."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/shizuishan-pinglu-reception/SOURCE-PROOF.json")
SOURCE_SHA256 = "877d908ba03305a0acd1abe4148f5501583c99579f6c7f7d0cb7dc16f577a902"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("平罗县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少平罗县核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("平罗县核验文件字节已变化")

    source = json.loads(raw)
    budget = source["budget"]
    return {
        "province": source["province"],
        "province_name": source["province_name"],
        "city": source["city"],
        "district": source["district"],
        "region_code": source["region_code"],
        "scope_level": "district",
        "authority": source["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": budget["title"],
        "source_url": budget["notice_url"],
        "source_id": digest(budget["notice_url"])[:24],
        "source_version": SOURCE_SHA256,
        "collected_at": source["collected_at"],
        "verified_at": source["collected_at"],
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {"实施机关": source["authority"]},
        "channel": {
            "raw_value": "",
            "online_status": "unverified",
            "entry_url": None,
            "submission_verified": False,
        },
        "warnings": [source["reception"], source["limits"]],
        "sections": {"立案室职责": source["reception"], "资料核验": source["limits"]},
        "materials": [],
        "templates": [],
    }
