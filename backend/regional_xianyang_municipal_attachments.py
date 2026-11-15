"""Expose the verified Xianyang municipal Word originals via official links."""

from hashlib import sha256
import json
from pathlib import Path

from regional_xianyang_municipal_guides import PROOF, exact_municipal


LINK_PROOF = PROOF.with_name("ATTACHMENT-LINKS-PROOF.json")
LINK_PROOF_SHA256 = "41747e95efb4b1be185d724284fc182f126fcd561755523f6dfbad16a89e5aba"


def with_xianyang_official_attachments(guide, root):
    if not exact_municipal(guide):
        return guide
    root = Path(root).resolve()
    path = (root / LINK_PROOF).resolve()
    if not path.is_relative_to(root):
        return guide
    try:
        raw = path.read_bytes()
    except OSError:
        return guide
    if sha256(raw).hexdigest() != LINK_PROOF_SHA256:
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
