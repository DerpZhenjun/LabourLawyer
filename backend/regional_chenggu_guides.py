"""Load the independently verified worker guide for Chenggu County."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path('reports/overnight-gap-closure-20261030/localities/chenggu-district-worker/SOURCE-PROOF.json')
PROOF_SHA256 = 'dc40703307effa2649f297d16bb3d4f8fce53fda1a6b9713e4fc9171635eb4b1'


def staged_guide(root=None):
    source = Path(ROOT if root is None else root).resolve()
    path = (source / PROOF).resolve()
    if not path.is_relative_to(source):
        raise ValueError('城固县指南核验文件路径无效')
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError('城固县官方材料核验文件已变化')
    guide = json.loads(raw)['guide']
    if (guide['city'], guide['district'], guide['region_code']) != ('汉中市', '城固县', '610722'):
        raise ValueError('城固县指南与办理地区不匹配')
    guide['source_id'] = digest(guide['source_url'])[:24]
    return guide
