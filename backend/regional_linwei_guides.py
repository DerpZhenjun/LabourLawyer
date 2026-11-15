"""Stage the two Linwei District guides and preserve the attachment conflict."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("reports/overnight-gap-closure-20261030/localities/weinan-linwei-own-sources")
SOURCE = EVIDENCE / "SOURCE-OBSERVATIONS.json"
SOURCE_SHA256 = "512e5e0589aa3c2b2d90e3c6885a2375bcc2be0fca2d4dcf72d296a53fafe6b0"
CONTENT_REVIEW = EVIDENCE / "CONTENT-REVIEW.json"
CONTENT_REVIEW_SHA256 = "b38626a748d9538d65bd2fa9819975d2a84f0ba5d95c6e616d3ab8bac684cc43"


def _read_pinned(root, relative, expected):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("临渭区核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少临渭区核验文件") from exc
    if sha256(raw).hexdigest() != expected:
        raise ValueError("临渭区核验文件字节已变化")
    return json.loads(raw)


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    source = _read_pinned(root, SOURCE, SOURCE_SHA256)
    review = _read_pinned(root, CONTENT_REVIEW, CONTENT_REVIEW_SHA256)
    roles = (("worker", "劳动者"), ("employer", "用人单位"))
    region_code = source["region_code"]
    url = source["roles"]["worker"]["source_url"]
    notice = (
        f'官网标为“空表”的 {len(review["rows"])} 份附件均含已填示例。'
        "两份申请书标题写明“样本”，劳动者授权委托书也已填示例。"
        "可填写的官方空白模板仍待核验。"
    )
    location = "陕西省渭南市临渭区杜桥街道临渭区行政中心 11 号楼"
    return {
        "province": "shaanxi",
        "province_name": "陕西省",
        "city": "渭南市",
        "district": "临渭区",
        "region_code": region_code,
        "scope_level": "district",
        "authority": source["authority"],
        "service_name": "劳动人事争议仲裁申请",
        "source_title": "临渭区劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": url,
        "source_id": digest(url)[:24],
        "source_version": digest(f"{SOURCE_SHA256}:{CONTENT_REVIEW_SHA256}"),
        "role_sources": {label: source["roles"][role]["source_url"] for role, label in roles},
        "collected_at": source["roles"]["worker"]["captured_at"],
        "verified_at": review["checked_at"],
        "verification_status": "conflict",
        "published": False,
        "can_generate": False,
        "fields": {
            "实施机关": source["authority"],
            "咨询方式": source["consultation_phone"],
            "办理地点": "\n".join(
                f'{label}事项：{location}（{source["roles"][role]["window"]}）。' for role, label in roles
            ),
            "承诺办结时限": "".join(
                f'{label}事项：官网显示 {source["roles"][role]["commitment_workdays_as_displayed"]} 个工作日。'
                for role, label in roles
            ),
        },
        "channel": {"online_status": "unverified", "entry_url": None, "submission_verified": False},
        "materials": [
            {
                "id": f"{region_code}-{role}-{index}",
                "name": f'{row["name"]}（{label}）',
                "official_name": row["name"],
                "required": row["required"],
                "service_object": label,
                "source_url": source["roles"][role]["source_url"],
                "region_code": region_code,
            }
            for role, label in roles
            for index, row in enumerate(source["roles"][role]["materials"], start=1)
        ],
        "templates": [],
        "sections": {"官网附件核验": notice},
        "warnings": [notice, "用人单位事项承诺时限按官网原样显示，实际办结时间请向临渭区人社局核实。"],
    }
