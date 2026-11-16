"""Stage the independently verified arbitration guides for Chunhua County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-chunhua-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "04896af98420ab6432fb7de8c9953b302e84cd9857107cb0e57291eb8f3cbf45"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "淳化县",
        "本页仅适用于淳化县。请按申请角色核对窗口、材料与附件。",
    )
