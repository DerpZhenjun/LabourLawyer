"""Stage Xianyang's two independently verified municipal service guides."""

import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/xianyang-municipal-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "5c0b3a6be32c21572def10caee3acac34728bf91c762d5cdbbce608e9451615d"
PRIMARY_SOURCE = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1117369317238&siteCode=610400000000"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "shaanxi", "咸阳市", "市本级", "municipal", "610400",
        PRIMARY_SOURCE, digest(PRIMARY_SOURCE)[:24], PROOF_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        raise ValueError("咸阳市本级核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少咸阳市本级核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("咸阳市本级核验文件字节已变化")

    proof = json.loads(raw)
    roles = proof["roles"]
    code = proof["region_code"]
    url = roles["worker"]["source_url"]
    channel = "\n".join(f'{item["name"]}：{item["handling_form"]}' for item in roles.values())
    term = f'{proof["workdays"]} 个工作日'
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": proof["city"],
        "district": "市本级",
        "scope_level": "municipal",
        "region_code": code,
        "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "咸阳市本级劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": PROOF_SHA256,
        "role_sources": {item["name"]: item["source_url"] for item in roles.values()},
        "collected_at": proof["collected_at"],
        "verified_at": proof["collected_at"],
        "verification_status": "conflict",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": proof["authority"],
            "咨询方式": proof["consultation_phone"],
            "办理形式": channel,
            "办理时间": roles["worker"]["hours"],
            "办理地点": "\n".join(f'{item["name"]}：{item["office"]}' for item in roles.values()),
            "是否收费": proof["fee"],
            "法定办结时限": term,
            "承诺办结时限": term,
        },
        "channel": {"raw_value": channel, "online_status": "conflict", "entry_url": None, "submission_verified": False},
        "materials": [
            {
                "id": f'{code}-{role}-{row["key"]}',
                "official_name": row["name"],
                "name": f'{row["name"]}（{item["name"]}）',
                "service_object": item["name"],
                "source_url": item["source_url"],
                "region_code": code,
                "required": row["required"],
                "original_copy": row["original_copy"],
                "format": row["format"],
                "copies": row["copies"],
                "standard": row["standard"],
                "instructions": row["instructions"],
            }
            for role, item in roles.items()
            for row in item["materials"]
        ],
        "templates": [],
        "sections": {"办理渠道核验": proof["channel_note"], "官网附件核验": proof["attachment_note"]},
        "warnings": ["此页仅适用于咸阳市本级。办理渠道和附件份数请向市人社局核对。"],
    }
