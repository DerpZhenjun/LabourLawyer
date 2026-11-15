"""Stage the two official Xi'an Chanba International Port arbitration guides."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xian-chanba-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "54a2f06f9abfbe20b4e269c2b0288b92ae6ed77665c8d1c6580f05f42fef41b3"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("西安浐灞国际港核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少西安浐灞国际港核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("西安浐灞国际港核验文件字节已变化")

    source = json.loads(raw)
    roles = source["roles"]
    worker = roles["worker"]
    code = source["region_code"]
    url = worker["source_url"]
    term = f'官网显示 {source["workdays"]} 个工作日。'
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": source["city"],
        "district": source["district"],
        "region_code": code,
        "scope_level": "district",
        "authority": source["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "西安浐灞国际港劳动人事争议仲裁申请",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": SOURCE_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for guide in roles.values()},
        "collected_at": source["collected_at"],
        "verified_at": source["collected_at"],
        "verification_status": "conflict",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": source["authority"],
            "办理时间": worker["hours"],
            "办理地点": "\n".join(f'{guide["name"]}事项：{guide["office"]}。' for guide in roles.values()),
            "咨询方式": source["consultation_phone"],
            "投诉方式": source["complaint_phone"],
            "法定办结时限": term,
            "承诺办结时限": term,
            "办理形式": source["channel"],
            "到办事现场次数": source["in_person_visits"],
            "是否收费": source["fee"],
            "收费标准": source["fee"],
        },
        "channel": {
            "raw_value": source["channel"],
            "form": "offline",
            "online_status": "unavailable",
            "entry_url": None,
            "submission_verified": False,
        },
        "materials": [
            {
                "id": f'{code}-{role}-{row["key"]}',
                "name": f'{row["name"]}（{guide["name"]}）',
                "official_name": row["name"],
                "required": row["required"],
                "original_copy": row["original_copy"],
                "format": row["format"],
                "copies": row["copies"],
                "standard": row["standard"],
                "instructions": row["instructions"],
                "service_object": guide["name"],
                "source_url": guide["source_url"],
                "region_code": code,
            }
            for role, guide in roles.items()
            for row in guide["materials"]
        ],
        "templates": [],
        "sections": {
            "办理地点核验": source["office_note"],
            "官网附件核验": source["attachment_notice"],
        },
        "warnings": ["用人单位申请书与委托书的适用性待核验，当前仅提供办理指南和材料要求。"],
    }
