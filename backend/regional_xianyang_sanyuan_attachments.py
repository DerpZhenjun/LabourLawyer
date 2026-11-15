"""Expose the verified Sanyuan County Word originals via official links."""

from regional_guides import digest
from regional_official_attachment_links import with_verified_attachment_links
from regional_xianyang_sanyuan_guides import SOURCE, SOURCE_SHA256


LINK_PROOF = SOURCE.with_name("ATTACHMENT-LINKS-PROOF.json")
LINK_PROOF_SHA256 = "618f2cbb742de049a201c15170d12ac2f39b0d4b8d2e33f3565e8b390117328f"
WORKER_SOURCE = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1116001147713&siteCode=610422000000"


def with_sanyuan_official_attachments(guide, root):
    keys = ("province", "city", "district", "scope_level", "region_code",
            "source_url", "source_id", "source_version")
    if tuple(guide.get(key) for key in keys) != (
        "shaanxi", "咸阳市", "三原县", "district", "610422",
        WORKER_SOURCE, digest(WORKER_SOURCE)[:24], SOURCE_SHA256,
    ):
        return guide
    return with_verified_attachment_links(guide, root, LINK_PROOF, LINK_PROOF_SHA256)
