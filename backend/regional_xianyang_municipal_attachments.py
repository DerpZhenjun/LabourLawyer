"""Expose the verified Xianyang municipal Word originals via official links."""

from regional_official_attachment_links import with_verified_attachment_links
from regional_xianyang_municipal_guides import PROOF, exact_municipal


LINK_PROOF = PROOF.with_name("ATTACHMENT-LINKS-PROOF.json")
LINK_PROOF_SHA256 = "41747e95efb4b1be185d724284fc182f126fcd561755523f6dfbad16a89e5aba"


def with_xianyang_official_attachments(guide, root):
    if not exact_municipal(guide):
        return guide
    return with_verified_attachment_links(guide, root, LINK_PROOF, LINK_PROOF_SHA256)
