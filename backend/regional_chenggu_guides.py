"""Load the independently verified worker guide for Chenggu County."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path('reports/overnight-gap-closure-20261030/localities/chenggu-district-worker/SOURCE-PROOF.json')
PROOF_SHA256 = 'dc40703307effa2649f297d16bb3d4f8fce53fda1a6b9713e4fc9171635eb4b1'
AUTHORIZATION_PROOF = PROOF.parent.with_name('chenggu-authorization') / PROOF.name
AUTHORIZATION_PROOF_SHA256 = '8c251399d2d539a2da81ab480378a4563f1936f86c61db856aa91777d0ac6dee'


def _read_proof(root, proof, expected_sha256):
    source = Path(ROOT if root is None else root).resolve()
    path = (source / proof).resolve()
    if not path.is_relative_to(source):
        raise ValueError('城固县指南核验文件路径无效')
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('城固县官方材料核验文件已变化')
    return json.loads(raw)


def staged_guide(root=None):
    guide = _read_proof(root, PROOF, PROOF_SHA256)['guide']
    if (guide['city'], guide['district'], guide['region_code']) != ('汉中市', '城固县', '610722'):
        raise ValueError('城固县指南与办理地区不匹配')
    guide['source_id'] = digest(guide['source_url'])[:24]
    return guide


def staged_authorization_guide(root=None):
    guide = staged_guide(root)
    proof = _read_proof(root, AUTHORIZATION_PROOF, AUTHORIZATION_PROOF_SHA256)
    if (proof['region_code'], proof['source_url']) != (guide['region_code'], guide['source_url']):
        raise ValueError('城固县委托书与办理地区或来源不匹配')

    guide['source_version'] = digest(guide['source_version'] + AUTHORIZATION_PROOF_SHA256)
    guide['warnings'].remove('城固县委托书空表已取得，文件结构与版式待核验。')
    guide['warnings'].append('城固县委托书空表可从官网申报材料下载。请按实际委托填写收件机关名称、代理权限和签名。')
    guide['templates'].append({
        'id': 'chenggu-610722-authorization',
        'region_code': proof['region_code'],
        'source_url': proof['source_url'],
        'official_attachment_entry': 'material_tab',
        'original_name': '城固县授权委托书（官网空表入口）',
        'official_kind': 'blank',
        'file_type': 'doc',
        'official_sha256': proof['official_sha256'],
        'official_bytes': proof['official_bytes'],
        'download_status': proof['download_status'],
        'document_types': [],
        'can_generate': False,
    })
    return guide
