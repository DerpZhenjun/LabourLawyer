"""Stage Zhongwei municipal arbitration institute and its reception duties."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/zhongwei-municipal-institute/SOURCE-PROOF.json")
SOURCE_SHA256 = "638ec874580e8b2787e22171f2098b05adfee9c584151fd79de01ce6369bcf61"
NOTICE = "https://www.nxzw.gov.cn/zwgk/bmxxgkml/srlzyhshbzj/fdzdgknr_49501/gkxx_49502/zsdw_49505/202212/t20221203_3870615.html"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "ningxia", "中卫市", "市本级", "municipal", "640500",
        NOTICE, digest(NOTICE)[:24], SOURCE_SHA256,
    )


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("中卫市本级核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少中卫市本级核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("中卫市本级核验文件字节已变化")

    evidence = json.loads(raw)
    return {
        "province": evidence["province"],
        "province_name": evidence["province_name"],
        "city": evidence["city"],
        "district": evidence["district"],
        "region_code": evidence["region_code"],
        "scope_level": "municipal",
        "authority": evidence["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": evidence["notice"]["title"],
        "source_url": NOTICE,
        "source_id": digest(NOTICE)[:24],
        "source_version": SOURCE_SHA256,
        "collected_at": evidence["collected_at"],
        "verified_at": evidence["collected_at"],
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {
            "机构办公地址": evidence["office_address"],
            "机构办公电话": evidence["office_phone"],
        },
        "channel": {
            "raw_value": "",
            "online_status": "unverified",
            "entry_url": None,
            "submission_verified": False,
        },
        "warnings": [evidence["duties"], evidence["limits"]],
        "sections": {
            "受理职责": evidence["duties"],
            "机构办公信息": (
                f"机构办公地址：{evidence['office_address']}。"
                f"机构办公电话：{evidence['office_phone']}。"
            ),
            "申请资料核验": evidence["limits"],
        },
        "materials": [],
        "templates": [],
    }
