"""Stage the independently verified arbitration guides for Xingping City."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-xingping-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "68332551e13a16d73e883da6c7f63bfa2d50ebc8817c5478e6dab2672a683a5e"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "兴平市",
        "本页仅适用于兴平市本级。请向兴平市人社局核对劳动者材料名称、用人单位表格及邮寄收件信息。",
    )
