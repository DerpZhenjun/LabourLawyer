"""Project Shiquan's verified official attachments without enabling platform filling."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-shiquan-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "dfd8b38e5bbc2a08d0df111c5d0be1ff069e96905a3b2af485bb2ede6fa1b807"


def _read_proof(root):
    source = Path(ROOT if root is None else root).resolve()
    path = (source / PROOF).resolve()
    if not path.is_relative_to(source):
        raise ValueError("石泉县来源核验文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少石泉县来源核验文件") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("石泉县来源核验文件字节已变化")
    return json.loads(raw)


def _role_materials(code, key, guide, notes):
    return [{
        "id": f"{code}-{key}-{index}", "name": f'{row["name"]}（{guide["role"]}）',
        "official_name": row["name"], "required": row["required"],
        "service_object": guide["role"], "source_url": guide["source_url"], "region_code": code,
        "instructions": notes.get(row["name"], ""),
    } for index, row in enumerate(guide["materials"], 1)]


def _official_template(code, key, item, guide_url):
    return {
        "id": f"ankang-{code}-{key}", "region_code": code, "original_name": item["title"],
        "source_url": item["url"], "guide_source_url": guide_url, "official_kind": "blank",
        "official_sha256": item["sha256"], "official_bytes": item["bytes"], "file_type": item["file_type"],
        "download_status": "official_link_only", "document_types": [], "can_generate": False,
        **({"fill_method": item["fill_method"]} if "fill_method" in item else {}),
    }


def staged_guide(root=None):
    proof = _read_proof(root)
    area, common = proof["area"], proof["common"]
    worker, employer = proof["worker"], proof["employer"]
    code = area["region_code"]
    if (area["city"], area["district"], code) != ("安康市", "石泉县", "610922"):
        raise ValueError("来源地区与石泉县不匹配")
    primary = worker["source_url"]
    materials = _role_materials(code, "worker", worker, {"授权委托书": worker["authorization_note"]})
    materials.extend(_role_materials(code, "employer", employer, {
        "劳动人事争议仲裁申请书": employer["application_copies_note"],
        "主体资格证明材料": employer["qualification_note"],
    }))
    templates = [
        _official_template(code, "worker-application", worker["application"], primary),
        _official_template(code, "employer-application", employer["application"], employer["source_url"]),
        _official_template(code, "authorization", proof["authorization"], primary),
        _official_template(code, "representative-qualification", proof["qualification"], employer["source_url"]),
    ]
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"], "district": area["district"],
        "scope_level": "district", "region_code": code, "authority": area["authority"],
        "service_name": "劳动人事争议仲裁申请", "source_title": "石泉县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": primary, "source_id": digest(primary)[:24], "source_version": PROOF_SHA256,
        "collected_at": worker["observed_at"], "verified_at": worker["observed_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "办理地点": common["venue"], "咨询方式": common["phone"],
                   "到办事现场次数": "1", "法定办结时限": "5 个自然日", "承诺办结时限": common["commitment"]},
        "channel": {"online_status": common["online_status"], "entry_url": None,
                    "raw_value": "两项官网指南均显示暂不支持在线办理", "submission_verified": False},
        "materials": materials, "templates": templates,
        "sections": {
            "申请书填写": "劳动者与用人单位使用各自的官方空表。两份原表说明均要求在 A4 纸上用钢笔或黑色碳素笔撰写，由申请人本人签字。",
            "用人单位申请书份数": employer["application_copies_note"],
        },
        "warnings": ["请按申请人身份选择石泉县劳动者或用人单位手写空表，按原表要求用笔填写并本人签字。"],
    }
