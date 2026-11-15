"""Stage the independently verified arbitration guides for Sanyuan County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-sanyuan-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "6e23016effd4382181d94b1aeeadef2ef74642eb63948f9aa95bc4c161ebcb41"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "三原县",
        "本页仅适用于三原县。请核对收件信息，按官网原件说明处理角色、收件机关和签章。",
    )
