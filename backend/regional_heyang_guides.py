"""Stage Heyang County guide links while retaining official attachment conflicts."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/weinan-heyang-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "f2ae5703d81bf6a8aec36303497409f4c8d878efee0e5e53c296b35c19e62c27"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("合阳县核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少合阳县核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("合阳县核验文件字节已变化")

    source = json.loads(raw)
    roles = tuple(source["roles"].items())
    code = source["region_code"]
    worker, employer = source["roles"]["worker"], source["roles"]["employer"]
    url = worker["source_url"]
    notice = (
        "两类申请书标为“空表”的 DOC 与劳动者身份证栏的“空表”字节相同。"
        "文件正文为自然人申请人格式的劳动仲裁申请书。"
        "劳动者版可填栏位仍待核验，用人单位格式没有完成核验。样表单独保留。"
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
        "source_title": "合阳县劳动人事争议仲裁申请（劳动者、用人单位）",
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
        "warnings": [notice, "用人单位事项承诺时限按官网原样显示，请向合阳县人社局核实。"],
    }
