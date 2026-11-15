"""Stage the independently verified Zizhou County guides for both applicant roles."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/yulin-zizhou-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "4c6ef9075fb2c05d30d936477654ff04defd3af30967dc405a83f20cb9210845"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("子洲县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少子洲县核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("子洲县核验文件字节已变化")

    source = json.loads(raw)
    roles = tuple(source["roles"].items())
    code = source["region_code"]
    worker = source["roles"]["worker"]
    url = worker["source_url"]
    verified_at = max(guide["collected_at"] for _, guide in roles)
    notice = (
        "官网各列出两项材料的样表附件，共四个 JPEG 链接。"
        "劳动者和用人单位对应的申请书字节相同，两类授权委托书字节也相同。"
    )
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": source["city"],
        "district": source["district"],
        "region_code": code,
        "scope_level": "district",
        "authority": source["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "子洲县劳动人事争议仲裁申请",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": SOURCE_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for _, guide in roles},
        "collected_at": verified_at,
        "verified_at": verified_at,
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": source["authority"],
            "咨询方式": source["consultation_phone"],
            "投诉方式": source["complaint_phone"],
            "办理时间": worker["hours"],
            "法定办结时限": f'官网显示 {worker["statutory_workdays"]} 个工作日。',
            "收费标准": worker["fee"],
            "办理地点": "\n".join(f'{guide["name"]}事项：{guide["office"]}。' for _, guide in roles),
            "承诺办结时限": "".join(
                f'{guide["name"]}事项：官网显示 {guide["commitment_workdays"]} 个工作日。'
                for _, guide in roles
            ),
        },
        "channel": {
            "raw_value": worker["channel"],
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
                "service_object": guide["name"],
                "source_url": guide["source_url"],
                "region_code": code,
            }
            for role, guide in roles
            for row in guide["materials"]
        ],
        "templates": [],
        "sections": {"官网附件核验": notice},
        "warnings": ["官网附件标注为样表。空白模板待核验，文书暂未开放下载或生成。"],
    }
