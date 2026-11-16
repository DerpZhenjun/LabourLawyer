"""Stage Yangling's own municipal guides and Yangling District's separate notice."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
MUNICIPAL_SOURCE = Path("reports/overnight-gap-closure-20261030/localities/yangling-municipal-own-guides/SOURCE-PROOF.json")
DISTRICT_SOURCE = Path("reports/overnight-gap-closure-20261030/localities/yangling-district-own-notice/SOURCE-PROOF.json")
MUNICIPAL_SHA256 = "1be0bfa9176ec1ff9a8607c2734e929935e8a7654071ae075a5c48811e096fa5"
DISTRICT_SHA256 = "ec742c239ab5bafaae68770f9f9c18ec56b54dfdb2cf3a4254b5fcc86fe213e8"
PRIMARY_SOURCE = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1111818134236&siteCode=611100000000"


def exact_municipal(guide):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    return tuple(guide.get(key) for key in keys) == (
        "shaanxi", "杨凌示范区", "市本级", "municipal", "611100",
        PRIMARY_SOURCE, digest(PRIMARY_SOURCE)[:24], MUNICIPAL_SHA256,
    )


def _read_source(root, relative_path, expected_sha256):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("杨凌核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少杨凌核验文件") from exc
    if sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("杨凌核验文件字节已变化")
    return json.loads(raw)


def _base(proof, url, version, scope, status):
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": proof["city"],
        "district": proof["district"],
        "scope_level": scope,
        "region_code": proof["region_code"],
        "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": version,
        "collected_at": proof["collected_at"],
        "verified_at": proof["collected_at"],
        "verification_status": status,
        "published": False,
        "can_generate": False,
        "templates": [],
    }


def staged_municipal_guide(root=None):
    proof = _read_source(root, MUNICIPAL_SOURCE, MUNICIPAL_SHA256)
    roles = proof["roles"]
    period = f'{proof["workdays"]} 个工作日'
    channel = "指南列出现场窗口"
    return {
        **_base(proof, roles["worker"]["source_url"], MUNICIPAL_SHA256, "municipal", "conflict"),
        "source_title": "杨凌示范区本级劳动人事争议仲裁申请（劳动者、用人单位）",
        "role_sources": {item["name"]: item["source_url"] for item in roles.values()},
        "fields": {
            "实施机关": proof["authority"],
            "办理地点": "\n".join(f'{item["name"]}：{item["office"]}' for item in roles.values()),
            "办理时间": proof["hours"],
            "办理形式": channel,
            "咨询方式": proof["phone"],
            "法定办结时限": period,
            "承诺办结时限": period,
            "是否收费": proof["fee"],
            "到现场次数": "\n".join(f'{item["name"]}：{item["in_person_visits"]}次' for item in roles.values()),
        },
        "channel": {"raw_value": channel, "online_status": "unavailable",
                    "entry_url": None, "submission_verified": False},
        "materials": [
            {
                "id": f'611100-{role}-{row["key"]}',
                "official_name": row["name"],
                "name": f'{row["name"]}（{item["name"]}）',
                "source_url": item["source_url"],
                "service_object": item["name"],
                "region_code": "611100",
                "required": row["required"],
                "original_copy": row["original_copy"],
                "format": row["format"],
                "copies": row["copies"],
                "instructions": row["instructions"],
            }
            for role, item in roles.items()
            for row in item["materials"]
        ],
        "sections": {"办理渠道核验": proof["channel_note"], "官网附件核验": proof["attachment_note"],
                     "人社部门公开流程": f'流程与附件见 {proof["process_source_url"]}'},
        "warnings": ["此页适用于杨凌示范区本级。请按申请角色核对办理地点和材料。"],
    }


def staged_district_notice(root=None):
    proof = _read_source(root, DISTRICT_SOURCE, DISTRICT_SHA256)
    return {
        **_base(proof, proof["source_url"], DISTRICT_SHA256, "district", "partial"),
        "source_title": proof["source_title"],
        "fields": {"办理地点": proof["office"], "咨询方式": proof["phone"]},
        "channel": {"raw_value": "", "online_status": "unverified",
                    "entry_url": None, "submission_verified": False},
        "materials": [],
        "sections": {"搬迁公告": proof["relocation_note"]},
        "warnings": ["此页为杨陵区仲裁院搬迁通知。区级两角色办事指南、材料及模板仍待核验。"],
    }
