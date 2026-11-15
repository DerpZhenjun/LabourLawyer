"""Stage the independently verified arbitration guides for Changwu County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-changwu-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "77207416ad9eb071768bfee4e36728675819532df5938b8fbf82c19333e64ac5"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "长武县",
        "本页仅适用于长武县。请按申请角色核对办理途径和容缺后补条件。",
    )
