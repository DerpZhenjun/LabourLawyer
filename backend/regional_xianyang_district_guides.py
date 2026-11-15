"""Read verified, role-specific Xianyang district guide evidence."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


def read_guide(root, source, source_sha256, district, warning):
    root = Path(root).resolve()
    path = (root / source).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{district}核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"缺少{district}核验文件") from exc
    if sha256(raw).hexdigest() != source_sha256:
        raise ValueError(f"{district}核验文件字节已变化")

    proof = json.loads(raw)
    roles = proof["roles"]
    code = proof["region_code"]
    source_url = roles["worker"]["source_url"]
    channel = "\n".join(f'{item["name"]}：{item["handling_form"]}' for item in roles.values())
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": proof["city"],
        "district": proof["district"],
        "scope_level": "district",
        "region_code": code,
        "authority": proof["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": f"{district}劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url,
        "source_id": digest(source_url)[:24],
        "source_version": source_sha256,
        "role_sources": {item["name"]: item["source_url"] for item in roles.values()},
        "collected_at": proof["collected_at"],
        "verified_at": proof["collected_at"],
        "verification_status": "conflict",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": proof["authority"],
            "咨询方式": proof["consultation_phone"],
            "投诉方式": proof["complaint_phone"],
            "办理形式": channel,
            "办理时间": proof["hours"],
            "办理地点": "\n".join(f'{item["name"]}：{item["office"]}' for item in roles.values()),
            "法定办结时限": f'{roles["worker"]["legal_workdays"]} 个工作日',
            "承诺办结时限": "\n".join(
                f'{item["name"]}：{item["promised_workdays"]} 个工作日' for item in roles.values()
            ),
            "是否收费": "否",
        },
        "channel": {
            "raw_value": channel,
            "online_status": proof.get("online_status", "auth_required"),
            "entry_url": None,
            "submission_verified": False,
        },
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
                "instructions": row["instructions"],
            }
            for role, item in roles.items()
            for row in item["materials"]
        ],
        "sections": {
            "办理渠道核验": proof["channel_note"],
            "办理地点核验": proof["venue_note"],
            "官网附件核验": proof["attachment_note"],
        },
        "warnings": [warning],
        "templates": [],
    }
