"""Stage Huazhou District guide links while retaining official attachment conflicts."""

from hashlib import sha256
import json
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/weinan-huazhou-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "0bd95013936694e73f2bb10b160251b159c63a2c8247ca3012804d04a5b300e3"


def staged_guide(root=None):
    root = Path(ROOT if root is None else root).resolve()
    path = (root / SOURCE).resolve()
    if not path.is_relative_to(root):
        raise ValueError("华州区核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少华州区核验文件") from exc
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("华州区核验文件字节已变化")

    source = json.loads(raw)
    roles = tuple(source["roles"].items())
    code = source["region_code"]
    worker, employer = source["roles"]["worker"], source["roles"]["employer"]
    url = worker["source_url"]
    conflict = source["employer_relation_label_conflict"]
    notice = (
        f'共有 {source["sample_blank_same_bytes_pairs"]} 对“样表”和“空表”逐字节相同，'
        "包括两类申请书和授权委托书。"
        f'用人单位指南的{conflict["expected_material"]}栏目中，标为“空表”的 DOC 标题为'
        f'《{conflict["word_title"]}》。'
        "可填写的官方空白模板仍待核验。"
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
        "source_title": "华州区劳动人事争议仲裁申请（劳动者、用人单位）",
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
            "办理地点": "\n".join(f'{guide["name"]}事项：{guide["venue"]}。' for _, guide in roles),
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
        "warnings": [notice, "两类事项承诺时限按官网原样显示，实际办结时间请向华州区人社局核实。"],
    }
