"""Stage the official employer arbitration guide for Xi'an Gaoling District."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xian-gaoling-employer-guide/SOURCE-PROOF.json")
SOURCE_SHA256 = "5aa0fcc97c4e2be806481edbf35cde0a2e8f70642df23470551803f6659c6afc"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("西安市高陵区核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少西安市高陵区核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("西安市高陵区核验文件字节已变化")

    source = json.loads(raw)
    role = source["role"]
    code = source["region_code"]
    url = source["source_url"]
    service_name = "劳动人事争议仲裁申请"
    term = f'官网显示 {source["workdays"]} 个工作日。'
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": source["city"],
        "district": source["district"],
        "region_code": code,
        "scope_level": "district",
        "authority": source["authority"],
        "service_name": service_name,
        "source_title": f"{service_name}（{role}）",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": SOURCE_SHA256,
        "role_sources": {role: url},
        "collected_at": source["collected_at"],
        "verified_at": source["collected_at"],
        "verification_status": "conflict",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": source["authority"],
            "服务对象": role,
            "办理时间": source["hours"],
            "办理地点": source["office"],
            "咨询方式": source["phone"],
            "投诉方式": source["complaint_phone"],
            "办理形式": source["channel"],
            "到办事现场次数": source["in_person_visits"],
            "法定办结时限": term,
            "承诺办结时限": term,
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
                "id": f'{code}-employer-{row["key"]}',
                "official_name": row["name"],
                "name": row["name"],
                "original_copy": row["original_copy"],
                "format": "纸质",
                "copies": row["copies"],
                "required": row["required"],
                "instructions": row["instructions"],
                "service_object": role,
                "source_url": url,
                "region_code": code,
            }
            for row in source["materials"]
        ],
        "sections": {"官网附件核验": source["attachment_note"]},
        "warnings": ["本页记录用人单位事项。劳动者办理指南及空白表格仍待核验。"],
        "templates": [],
    }
