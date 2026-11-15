"""Stage the independently verified arbitration guides for Xianyang's Qindu District."""

from pathlib import Path

from regional_xianyang_district_guides import read_guide


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/overnight-gap-closure-20261030/localities/xianyang-qindu-own-guides/SOURCE-PROOF.json")
SOURCE_SHA256 = "57dd902aa7b7099a0f8b97b5b86fc3bfc350e8877574e2cd1050d689679022bf"


def staged_guide(root=None):
    return read_guide(
        ROOT if root is None else root,
        SOURCE,
        SOURCE_SHA256,
        "秦都区",
        "本页仅适用于秦都区。用人单位指南所列空表的申请人类型不符，请向秦都区人社局核对。",
    )
