"""Stage the independently verified arbitration guides for Liquan County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-liquan-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "b7bff774b06ddf46ecd75ed332cd524cdd25d9d22cc01b80431e18512acee814"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "礼泉县",
        "请向礼泉县人社局确认劳动者材料。已列的三项材料适用于用人单位事项。",
    )
