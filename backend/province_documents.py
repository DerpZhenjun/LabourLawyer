"""Province document metadata backed by the acquired official-template catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPOSITORY_ROOT / "config" / "province_official_template_catalog.json"
TEMPLATE_ROOT = REPOSITORY_ROOT / "templates" / "_docx"


SLUGS = {
    "Beijing": "beijing", "Tianjin": "tianjin", "Hebei": "hebei", "Shanxi": "shanxi",
    "InnerMongolia": "neimenggu", "Liaoning": "liaoning", "Jilin": "jilin",
    "Heilongjiang": "heilongjiang", "Shanghai": "shanghai", "Jiangsu": "jiangsu",
    "Zhejiang": "zhejiang", "Anhui": "anhui", "Fujian": "fujian", "Jiangxi": "jiangxi",
    "Shandong": "shandong", "Henan": "henan", "Hubei": "hubei", "Hunan": "hunan",
    "Guangdong": "guangdong", "Guangxi": "guangxi", "Hainan": "hainan",
    "Chongqing": "chongqing", "Sichuan": "sichuan", "Guizhou": "guizhou",
    "Yunnan": "yunnan", "Tibet": "xizang", "Shaanxi": "shaanxi", "Gansu": "gansu",
    "Qinghai": "qinghai", "Ningxia": "ningxia", "Xinjiang": "xinjiang",
}

REGION_GROUPS = {
    '华北': ('beijing', 'tianjin', 'hebei', 'shanxi', 'neimenggu'),
    '东北': ('liaoning', 'jilin', 'heilongjiang'),
    '华东': ('shanghai', 'jiangsu', 'zhejiang', 'anhui', 'fujian', 'jiangxi', 'shandong'),
    '华中': ('henan', 'hubei', 'hunan'),
    '华南': ('guangdong', 'guangxi', 'hainan'),
    '西南': ('chongqing', 'sichuan', 'guizhou', 'yunnan', 'xizang'),
    '西北': ('shaanxi', 'gansu', 'qinghai', 'ningxia', 'xinjiang'),
}
REGIONS = {slug: region for region, slugs in REGION_GROUPS.items() for slug in slugs}


# The primary-adapter records predate the all-province ledger and therefore do
# not repeat filenames in the catalog.  These names are still taken directly
# from the acquired official files, never from a generated blank document.
KNOWN_DOCUMENTS: dict[str, dict[str, str]] = {
    "zhejiang": {"application": "《劳动人事争议仲裁申请书》.docx", "evidence": "《证据清单》.docx"},
    "guangdong": {"application": "仲裁申请书.docx", "evidence": "证据清单.docx"},
    "jiangsu": {"application": "劳动人事争议仲裁申请书.docx", "evidence": "证据清单.docx"},
    "liaoning": {"application": "仲裁申请书.docx"},
}


def _document_type(document: dict[str, Any]) -> str | None:
    kind = str(document.get("document_type") or "").lower()
    if kind in {"application", "evidence", "combined"}:
        return kind
    return None


def _filename(document: dict[str, Any]) -> str | None:
    value = document.get("output_name") or document.get("production_path")
    if not value:
        return None
    return Path(str(value)).name


def load_province_documents() -> dict[str, dict[str, Any]]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    records = payload.get("provinces", payload) if isinstance(payload, dict) else payload
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        slug = SLUGS.get(record.get("province"))
        if not slug:
            continue
        folder = record["folder"]
        documents = dict(KNOWN_DOCUMENTS.get(slug, {}))
        for item in record.get("documents", []):
            kind = _document_type(item)
            filename = _filename(item)
            if not kind or not filename:
                continue
            if kind == "combined":
                documents.setdefault("application", filename)
                documents.setdefault("evidence", filename)
            else:
                documents[kind] = filename

        # Only expose files that were actually acquired and are still present.
        documents = {
            kind: filename for kind, filename in documents.items()
            if (TEMPLATE_ROOT / folder / filename).is_file()
        }
        result[slug] = {
            "slug": slug,
            "region": REGIONS[slug],
            "name": record.get("province_zh", record.get("province")),
            "folder": folder,
            "status": record.get("status", ""),
            "authority": record.get("authority", ""),
            "scope": record.get("scope", ""),
            "source_url": record.get("source_url", ""),
            "documents": documents,
        }
    return result


PROVINCE_DOCUMENTS = load_province_documents()


def get_province_document(slug: str, document_type: str) -> tuple[dict[str, Any], Path]:
    province = PROVINCE_DOCUMENTS.get(slug.lower())
    if not province:
        raise KeyError("未知省份")
    filename = province["documents"].get(document_type)
    if not filename:
        raise FileNotFoundError(f"{province['name']}尚未取得可填充的官方{document_type}模板")
    path = (TEMPLATE_ROOT / province["folder"] / filename).resolve()
    allowed_parent = (TEMPLATE_ROOT / province["folder"]).resolve()
    if path.parent != allowed_parent or not path.is_file():
        raise FileNotFoundError(f"未找到官方模板：{path}")
    return province, path
