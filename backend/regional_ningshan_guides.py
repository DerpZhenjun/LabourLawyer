"""Use only the independently verified Ningshan guides and original classifications."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-ningshan-own-guides/SOURCE-PROOF.json")
PROOF_SHA256 = "af43558249f6f7fea23bb76ac6f790f54b33f9e14d58e05c94663e08ecbe4f81"


def _read_proof(root):
    source = Path(ROOT if root is None else root).resolve()
    path = (source / PROOF).resolve()
    if not path.is_relative_to(source):
        raise ValueError("宁陕县来源文件超出候选目录")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("缺少宁陕县已核验官方资料") from exc
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError("宁陕县已核验来源的字节已变化")
    return json.loads(raw)


def _materials(code, role_key, guide):
    return [{
        "id": f"{code}-{role_key}-{index}", "name": f'{row["name"]}（{guide["role"]}）',
        "official_name": row["name"], "required": row["required"],
        "instructions": row["instructions"], "source_url": guide["source_url"],
        "service_object": guide["role"], "region_code": code,
    } for index, row in enumerate(guide["materials"], 1)]


def _template(code, key, guide, item):
    return {
        "id": f"ankang-{code}-{key}", "region_code": code, "original_name": item["title"],
        "service_object": guide["role"], "source_url": guide["source_url"], "official_attachment_entry": "material_tab",
        "official_kind": item["actual_kind"], "official_sha256": item["sha256"], "official_bytes": item["bytes"],
        "file_type": item["format"], "download_status": "official_link_only", "document_types": [], "can_generate": False,
    }


def staged_guide(root=None):
    proof = _read_proof(root)
    area, common = proof["area"], proof["common"]
    worker, employer = proof["worker"], proof["employer"]
    code = area["region_code"]
    if (area["city"], area["district"], code) != ("安康市", "宁陕县", "610923"):
        raise ValueError("来源地区与宁陕县不匹配")
    source_url = worker["source_url"]
    attachment = proof["worker_authorization"]
    authorization = _template(code, "worker-authorization", worker, attachment)
    authorization.pop("official_attachment_entry")
    authorization.update(source_url=attachment["url"], guide_source_url=worker["source_url"])
    return {
        "province": "shaanxi", "province_name": area["province"], "city": area["city"], "district": area["district"],
        "scope_level": "district", "region_code": code, "authority": area["authority"],
        "service_name": "劳动人事争议仲裁申请", "source_title": "宁陕县劳动人事争议仲裁申请（劳动者、用人单位）",
        "source_url": source_url, "source_id": digest(source_url)[:24], "source_version": PROOF_SHA256,
        "collected_at": worker["observed_at"], "verified_at": worker["observed_at"],
        "verification_status": "partial", "published": False, "can_generate": False,
        "fields": {"实施机关": area["authority"], "咨询方式": common["phone"],
                   "到办事现场次数": str(common["onsite_visits"]), "法定办结时限": common["statutory_time"],
                   "承诺办结时限": common["commitment"],
                   "办理地点": f'劳动者事项：{worker["venue"]}。\n用人单位事项：{employer["venue"]}。'},
        "channel": {"online_status": "unverified", "entry_url": None,
                    "raw_value": "两条指南均将办理深度标为信息发布，线上提交未核验。", "submission_verified": False},
        "sections": {"申请书份数": proof["copies_note"], "授权委托书材料说明": proof["authorization_requirement_note"]},
        "materials": _materials(code, "worker", worker) + _materials(code, "employer", employer),
        "templates": [
            _template(code, "worker-application-reference", worker, worker["application"]),
            _template(code, "employer-application-reference", employer, employer["application"]),
            authorization,
        ],
        "warnings": ["用人单位与劳动者事项的办理地点不同，请按申请人身份核对对应指南。",
                     "两份申请书原件含示范事实和占位文字，按参考格式展示。劳动者委托书可下载本县官方空表。"],
    }
