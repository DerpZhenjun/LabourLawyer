"""Candidate guides for independently verified Tongchuan district matters."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path('reports/overnight-gap-closure-20261030/localities/tongchuan-district-worker/SOURCE-PROOF.json')
PROOF_SHA256 = '46e022230016bc4f495eb8e6ccd24857955a34bc657e1d5958e7f0469aa39a9e'

YAOZHOU_AUTHORIZATION_PROOF = Path('reports/overnight-gap-closure-20261030/localities/tongchuan-yaozhou-authorization/SOURCE-PROOF.json')
YAOZHOU_AUTHORIZATION_SHA256 = '9d436185fe49b375bd2f6ab727bfedd60d5ec7a35470f5d912639a645269de5d'


def _read_proof(root, source_file, checksum):
    source = Path(ROOT if root is None else root).resolve()
    path = (source / source_file).resolve()
    if not path.is_relative_to(source):
        raise ValueError('铜川区县指南核验文件路径无效')
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != checksum:
        raise ValueError('铜川区县官方材料核验文件已变化')
    return json.loads(raw)


def staged_guide(code, root=None):
    region = _read_proof(root, PROOF, PROOF_SHA256)['regions'].get(code)
    if region is None or region['guide']['region_code'] != code:
        raise ValueError('该区县暂无已核验的铜川指南候选')
    guide = region['guide']
    guide['source_id'] = digest(guide['source_url'])[:24]
    return guide


def staged_yaozhou_authorization_guide(root=None):
    guide = staged_guide('610204', root)
    proof = _read_proof(root, YAOZHOU_AUTHORIZATION_PROOF, YAOZHOU_AUTHORIZATION_SHA256)
    if (proof['region_code'], proof['source_url']) != (guide['region_code'], guide['source_url']):
        raise ValueError('耀州区委托书官方来源与当地办理事项不匹配')
    guide['source_version'] = digest(guide['source_version'] + ':' + YAOZHOU_AUTHORIZATION_SHA256)
    guide['warnings'].remove('官方授权委托书空表已取得，内容和版式仍在核验。')
    guide['warnings'].append('耀州区委托书空表可从官网申报材料下载。收件机关名称、代理权限和签章请按实际委托填写。')
    guide['templates'].append({
        'id': 'tongchuan-610204-authorization', 'region_code': guide['region_code'],
        'official_kind': 'blank', 'source_url': guide['source_url'], 'official_attachment_entry': 'material_tab',
        'original_name': '耀州区授权委托书（官网空表入口）', 'official_sha256': proof['original_sha256'],
        'official_bytes': proof['original_bytes'], 'file_type': 'docx', 'download_status': 'official_link_only',
        'document_types': [], 'can_generate': False,
    })
    return guide
