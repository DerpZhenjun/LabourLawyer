"""Candidate guides for independently verified Tongchuan district matters."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path('reports/overnight-gap-closure-20261030/localities/tongchuan-district-worker/SOURCE-PROOF.json')
PROOF_SHA256 = '46e022230016bc4f495eb8e6ccd24857955a34bc657e1d5958e7f0469aa39a9e'


def staged_guide(code, root=None):
    source = Path(ROOT if root is None else root).resolve()
    path = (source / PROOF).resolve()
    if not path.is_relative_to(source):
        raise ValueError('铜川区县指南核验文件路径无效')
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != PROOF_SHA256:
        raise ValueError('铜川区县官方材料核验文件已变化')
    region = json.loads(raw)['regions'].get(code)
    if region is None or region['guide']['region_code'] != code:
        raise ValueError('该区县暂无已核验的铜川指南候选')
    guide = region['guide']
    guide['source_id'] = digest(guide['source_url'])[:24]
    return guide
