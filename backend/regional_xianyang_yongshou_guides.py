"""Stage the independently verified arbitration guides for Yongshou County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-yongshou-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "00fc2b5eeef531107c562977c3023807feb895b6b688b4daa4af39dac2c06998"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "永寿县",
        "本页仅适用于永寿县。劳动者请向办理机关核对申请书名称与适用范围。",
    )
