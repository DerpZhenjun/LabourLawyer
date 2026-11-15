"""Stage the verified guide from Xi'an High-Tech Zone's own authority."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xian-high-tech-own-guide/SOURCE-PROOF.json")
SOURCE_SHA256 = "9000ae6965973430df94d882daa99c6facb707c9917394ae0c0e49499b8da80f"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("西安高新区核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少西安高新区核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("西安高新区核验文件字节已变化")

    source = json.loads(raw)
    code = source["region_code"]
    url = source["source_url"]
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": source["city"],
        "district": source["district"],
        "region_code": code,
        "scope_level": "district",
        "authority": source["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": source["source_title"],
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": SOURCE_SHA256,
        "role_sources": {},
        "collected_at": source["collected_at"],
        "verified_at": source["collected_at"],
        "verification_status": "partial",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": source["authority"],
            "办理地点": source["office"],
            "办理时间": source["hours"],
            "咨询方式": source["phone"],
            "是否收费": source["fee"],
            "收费标准": source["fee"],
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {
                "id": f'{code}-{item["key"]}',
                "name": item["name"],
                "official_name": item["name"],
                "required": item["required"],
                "source_url": url,
                "region_code": code,
                **{key: item[key] for key in ("copies", "original_copy", "instructions") if key in item},
            }
            for item in source["materials"]
        ],
        "templates": [],
        "sections": {
            "conditions": source["conditions"],
            "官网附件核验": "官网原指南列出六份附件。附件列表标明各份文书的下载与填写范围。",
        },
        "warnings": ["本指南适用西安高新区。可用文书和官方链接见附件列表。"],
    }
