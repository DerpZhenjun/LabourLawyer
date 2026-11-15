"""Expose verified local blank forms through their official links."""

from hashlib import sha256
import json
from pathlib import Path

from regional_xian_high_tech_application import matches_guide_source
from regional_xian_high_tech_guide import SOURCE


PROOF = SOURCE.with_name("ATTACHMENT-LINKS-PROOF.json")
PROOF_SHA256 = "4820089884d0c8499c4cbebd16fc10a8c4e28fea7d8197398eee947382ab6836"


def with_official_attachments(guide, root):
    if not matches_guide_source(guide, root):
        return guide
    root = Path(root).resolve()
    path = (root / PROOF).resolve()
    if not path.is_relative_to(root):
        return guide
    try:
        raw = path.read_bytes()
    except OSError:
        return guide
    if sha256(raw).hexdigest() != PROOF_SHA256:
        return guide
    proof = json.loads(raw)
    existing = {template.get("id") for template in guide["templates"]}
    additions = [
        {
            "id": item["id"], "original_name": item["official_name"],
            "region_code": proof["region_code"], "source_url": item["official_url"],
            "guide_source_url": proof["guide_url"], "official_sha256": item["official_sha256"],
            "official_kind": "blank", "original_format": item["format"], "file_type": item["format"].lower(),
            "download_status": "official_link_only", "document_types": [], "can_generate": False,
        }
        for item in proof["attachments"] if item["id"] not in existing
    ]
    return {**guide, "templates": [*guide["templates"], *additions]}
