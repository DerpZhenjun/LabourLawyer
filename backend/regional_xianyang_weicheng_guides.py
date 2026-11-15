"""Stage the independently verified arbitration guides for Xianyang's Weicheng District."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-weicheng-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "7d671b9af16a2b7f41366546a4725fad2ddd407cc1f18e51b2afea109bb61915"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "渭城区",
        "本页仅适用于渭城区。劳动者劳动关系材料的形式和份数表述请向渭城区人社局核对。",
    )
