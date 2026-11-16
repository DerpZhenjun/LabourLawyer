"""Stage the independently verified arbitration guides for Wugong County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-wugong-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "6e2ce5ff25384a81d96e218c99c56341dba25c139abb33058b88dad5607d25ed"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "武功县",
        "本页仅适用于武功县。请按申请角色核对窗口、材料与附件。",
    )
