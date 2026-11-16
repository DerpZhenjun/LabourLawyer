"""Stage Xiji County arbitration institute affiliation from its official disclosure."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/guyuan-xiji-own-institute/SOURCE-PROOF.json")
SOURCE_SHA256 = "fa133e304dc883f0f279b018a253648f178bbd71d6501063d2434d9761942471"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("西吉县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少西吉县核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("西吉县核验文件字节已变化")

    evidence = json.loads(raw)
    source = evidence["source"]
    return {
        "province": evidence["province"],
        "province_name": evidence["province_name"],
        "city": evidence["city"],
        "district": evidence["district"],
        "region_code": evidence["region_code"],
        "scope_level": "district",
        "authority": "",
        "service_name": "劳动人事争议仲裁申请",
        "source_title": source["title"],
        "source_url": source["url"],
        "source_id": digest(source["url"])[:24],
        "source_version": SOURCE_SHA256,
        "collected_at": evidence["collected_at"],
        "verified_at": evidence["collected_at"],
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {"县人社局直属机构": evidence["institute"]},
        "channel": {
            "raw_value": "",
            "online_status": "unverified",
            "entry_url": None,
            "submission_verified": False,
        },
        "warnings": [evidence["affiliation"], evidence["limits"]],
        "sections": {
            "机构归属": evidence["affiliation"],
            "申请资料核验": evidence["limits"],
        },
        "materials": [],
        "templates": [],
    }
