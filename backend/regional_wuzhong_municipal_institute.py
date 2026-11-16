"""Stage Wuzhong municipal arbitration institute office details from its own records."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/wuzhong-municipal-institute/SOURCE-PROOF.json")
SOURCE_SHA256 = "b87cf30ce90e0c361cbd860825859705f44ffca8135906eb01cef7a8e8c637ab"
ANNOUNCEMENT = "https://www.wuzhong.gov.cn/xxgk/jgzn/szfzcbm/rlzyhshbzj_42775/zsjg_42780/wzsldrszyzcy/jbxx_55710/"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "ningxia", "吴忠市", "市本级", "municipal", "640300",
        ANNOUNCEMENT, digest(ANNOUNCEMENT)[:24], SOURCE_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("吴忠市本级核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少吴忠市本级核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("吴忠市本级核验文件字节已变化")

    source = json.loads(raw)
    office_notice = f'机构办公地址：{source["office"]}。办公电话：{source["phone"]}。办公时间：{source["hours"]}'
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
        "fields": {
            "机构办公地址": source["office"],
            "机构办公电话": source["phone"],
            "机构办公时间": source["hours"],
        },
        "channel": {"raw_value": "", "online_status": "unverified",
                    "entry_url": None, "submission_verified": False},
        "sections": {"机构办公信息": office_notice, "申请资料核验": source["scope_note"]},
        "warnings": [office_notice, source["scope_note"]],
        "materials": [],
        "templates": [],
    }
