"""Stage the independently verified arbitration guides for Xunyi County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-xunyi-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "3f74c0dd19201d275ee9a4f5dec2544bea58fb5b2ba7d8bcf5516318104c2f7b"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "旬邑县",
        "本页仅适用于旬邑县。请按申请角色核对窗口、材料与附件。",
    )
