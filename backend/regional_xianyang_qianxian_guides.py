"""Stage the independently verified arbitration guides for Qianxian County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-qianxian-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "81df5486ed1ea0ec5376599ef585b05cbdbc86b5dcbacb206d8b6cc48e07cc23"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "乾　县",
        "本页仅适用于乾县。请向乾县人社局核对外国人就业证适用情形和对应角色窗口。",
    )
