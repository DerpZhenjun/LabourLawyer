"""Stage the independently verified Wubao County guides for both applicant roles."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/yulin-wubao-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "10ddf78abb13e85581301d6c1ec28dd3b4da43d5b7e960bc6f85acd0a391cdc9"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("吴堡县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少吴堡县核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("吴堡县核验文件字节已变化")

    source = json.loads(raw)
    roles = tuple(source["roles"].items())
    code = source["region_code"]
    worker = source["roles"]["worker"]
    url = worker["source_url"]
    verified_at = max(guide["collected_at"] for _, guide in roles)
    notice = (
        "两个事项分别保留各自办理楼层。"
        "两类仲裁申请书附件由同一组四个 JPG 样表组成，排列次序不同。"
        "用人单位主体资格证明附件标为样表，正文用途待继续核验。"
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
        "source_title": "吴堡县劳动人事争议仲裁申请",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": SOURCE_SHA256,
        "role_sources": {guide["name"]: guide["source_url"] for _, guide in roles},
        "collected_at": verified_at,
        "verified_at": verified_at,
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
        "warnings": ["两类事项请按各自楼层查询。空白模板仍待核验，文书暂未开放下载或生成。"],
    }
