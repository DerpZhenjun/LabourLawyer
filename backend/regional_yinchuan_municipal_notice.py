"""Stage Yinchuan municipal arbitration agency and venue from its own notices."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/yinchuan-municipal-own-notice/SOURCE-PROOF.json")
SOURCE_SHA256 = "0001e4385d71a4a04e43c88a7ec29c664b338d85e84d886880fe2a224a47969d"
ANNOUNCEMENT = "https://rsj.yinchuan.gov.cn/xxgk/zdgk/tzgg/202606/t20260617_5267865.htm"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "ningxia", "银川市", "市本级", "municipal", "640100",
        ANNOUNCEMENT, digest(ANNOUNCEMENT)[:24], SOURCE_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("银川市本级核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少银川市本级核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("银川市本级核验文件字节已变化")

    source = json.loads(raw)
    return {
        "province": "ningxia",
        "province_name": "宁夏回族自治区",
        "city": source["city"],
        "district": source["district"],
        "region_code": source["region_code"],
        "scope_level": "municipal",
        "authority": source["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_url": source["notice"],
        "source_title": source["notice_title"],
        "source_id": digest(source["notice"])[:24],
        "source_version": SOURCE_SHA256,
        "collected_at": source["collected_at"],
        "verified_at": source["collected_at"],
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {"办理地点": source["office"]},
        "channel": {"raw_value": "", "online_status": "unverified",
                    "entry_url": None, "submission_verified": False},
        "sections": {"机构地址核验": source["scope_note"], "申请资料核验": source["application_note"]},
        "warnings": ["本页仅列银川市仲裁院公开地址，各区县办事信息分别核验。"],
        "materials": [],
        "templates": [],
    }
