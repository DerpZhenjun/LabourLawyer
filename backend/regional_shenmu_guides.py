"""Stage the independently verified Shenmu City guides for both applicant roles."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/yulin-shenmu-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "ede4e027cfcb4635226c504b330bebfca02f47289c35f694c02b360019789f56"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("神木市核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少神木市核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("神木市核验文件字节已变化")

    source = json.loads(raw)
    roles = tuple(source["roles"].items())
    code = source["region_code"]
    worker = source["roles"]["worker"]
    url = worker["source_url"]
    verified_at = max(guide["collected_at"] for _, guide in roles)
    notice = (
        "两类事项的仲裁申请书样表逐字节相同，内容是劳动者申请书样本汇编。"
        "劳动者事项的劳动（人事）关系证明材料下提供空白证据清单，"
        "清单设十个空白条目及提交人、提交时间栏，待完成文书适配。"
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
        "source_title": "神木市劳动人事争议仲裁申请",
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
        "warnings": ["仲裁申请书空白模板仍待核验。证据清单暂未开放下载或生成。"],
    }
