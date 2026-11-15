"""Stage the independently verified arbitration guides for Jingyang County."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-jingyang-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "09bb4bf980d77fa0dca331e5e757e08090abe4881817b4b1b1eb991311a274b7"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "泾阳县",
        "本页仅适用于泾阳县。请向泾阳县人社局核对外国人就业证适用情形及物流办理。",
    )
