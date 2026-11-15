"""Stage Weinan High-Tech Zone guides with separately verified applicant roles."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/weinan-high-tech-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "08a8bbceccccf976357d9e5017866a07b8d369b14831480d3a1d4e81f6eed1f2"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("高新区核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少高新区核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("高新区核验文件字节已变化")

    source = json.loads(raw)
    roles = tuple(source["roles"].items())
    code = source["region_code"]
    worker, employer = source["roles"]["worker"], source["roles"]["employer"]
    url = worker["source_url"]
    notice = (
        "劳动者的四项材料各有样表和空表链接，每一对返回的文件逐字节相同。"
        "两类申请书、用人单位主体资格证明和劳动关系证明的相关链接返回同一份图片。"
        "附件用途和空白模板仍待核验。"
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
        "source_title": "高新区劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": SOURCE_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for _, guide in roles},
        "collected_at": worker["collected_at"],
        "verified_at": employer["collected_at"],
        "verification_status": "conflict",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": source["authority"],
            "咨询方式": source["consultation_phone"],
            "办理地点": "\n".join(f'{guide["name"]}事项：{guide["office"]}。' for _, guide in roles),
            "承诺办结时限": "".join(
                f'{guide["name"]}事项：官网显示 {guide["commitment_workdays"]} 个工作日。'
                for _, guide in roles
            ),
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {
                "id": f'{code}-{role}-{row["key"]}',
                "name": f'{row["name"]}（{guide["name"]}）',
                "official_name": row["name"],
                "required": row["required"],
                "service_object": guide["name"],
                "source_url": guide["source_url"],
                "region_code": code,
            }
            for role, guide in roles
            for row in guide["materials"]
        ],
        "templates": [],
        "sections": {"官网附件核验": notice},
        "warnings": ["官网多项附件重复，空白模板仍待核验。"],
    }
