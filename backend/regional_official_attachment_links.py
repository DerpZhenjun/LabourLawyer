"""Read verified, direct-download official attachment link records."""

from hashlib import sha256
import json
from pathlib import Path


def with_verified_attachment_links(guide, root, proof_path, proof_sha256):
    root = Path(root).resolve()
    path = (root / proof_path).resolve()
    if not path.is_relative_to(root):
        return guide
    try:
        raw = path.read_bytes()
    except OSError:
        return guide
    if sha256(raw).hexdigest() != proof_sha256:
        return guide
    proof = json.loads(raw)
    existing = {template.get("id") for template in guide["templates"]}
    additions = [
        {
            "id": attachment["id"],
            "original_name": attachment["official_name"],
            "region_code": proof["region_code"],
            "source_url": attachment["official_url"],
            "guide_source_url": attachment["guide_source_url"],
            "official_sha256": attachment["official_sha256"],
            "official_kind": "blank",
            "original_format": attachment["format"],
            "file_type": attachment["format"].lower(),
            "download_status": "official_link_only",
            "document_types": [],
            "can_generate": False,
        }
        for attachment in proof["attachments"] if attachment["id"] not in existing
    ]
    return {**guide, "templates": [*guide["templates"], *additions]}
