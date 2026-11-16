"""Expose reviewed Yangling municipal originals through their official download URLs."""

from regional_official_attachment_links import with_verified_attachment_links
from regional_yangling_guides import MUNICIPAL_SOURCE, exact_municipal


LINK_PROOF = MUNICIPAL_SOURCE.with_name("ATTACHMENT-LINKS-PROOF.json")
LINK_PROOF_SHA256 = "4e2b1f4df0ae9f1c70c0fa12c3d1fc91e6e9a9f57cdc18f118607149f046f148"


def with_yangling_official_attachments(guide, root):
    if not exact_municipal(guide):
        return guide
    return with_verified_attachment_links(guide, root, LINK_PROOF, LINK_PROOF_SHA256)
