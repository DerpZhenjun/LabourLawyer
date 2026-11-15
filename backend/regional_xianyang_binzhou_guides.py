"""Stage the independently verified arbitration guides for Binzhou City."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-binzhou-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "4a6082fa0890d750b5fd7fbef23a53ad4dbaa06c69607c58901037c5005a358c"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "彬州市",
        "本页仅适用于彬州市本级。办理渠道、角色联系电话和材料份数请向办理机关核对。",
    )
