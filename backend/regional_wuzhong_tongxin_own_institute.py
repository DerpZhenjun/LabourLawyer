"""Stage Tongxin County arbitration institute details from its official disclosure."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/wuzhong-tongxin-own-institute/SOURCE-PROOF.json")
SOURCE_SHA256 = "673949ea623568d1af3d69541177f3b0dcb9a6d9ee9c24e41ab6ce1752c2150c"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("同心县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少同心县核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("同心县核验文件字节已变化")

    evidence = json.loads(raw)
    source = evidence["source"]
    office = f'机构办公地址：{evidence["office"]}。办公电话/传真：{evidence["phone_fax"]}。'
    return {
        "province": evidence["province"],
        "province_name": evidence["province_name"],
        "city": evidence["city"],
        "district": evidence["district"],
        "region_code": evidence["region_code"],
        "scope_level": "district",
        "authority": evidence["authority"],
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
        "fields": {
            "机构办公地址": evidence["office"],
            "机构办公电话/传真": evidence["phone_fax"],
        },
        "channel": {
            "raw_value": "",
            "online_status": "unverified",
            "entry_url": None,
            "submission_verified": False,
        },
        "warnings": [office, evidence["limits"]],
        "sections": {
            "仲裁院职责": evidence["duties"],
            "机构办公信息": office,
            "申请资料核验": evidence["limits"],
        },
        "materials": [],
        "templates": [],
    }
