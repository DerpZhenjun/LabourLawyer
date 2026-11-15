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

MUNICIPAL_PROOF = Path('reports/overnight-gap-closure-20261030/localities/tongchuan-municipal-own-source/SOURCE-PROOF.json')
MUNICIPAL_PROOF_SHA256 = '4a17fb18bfcd0fc6c53724a87266677bb66a2d29c61192abc106deff2b86221a'
MUNICIPAL_URL = 'https://rs.tongchuan.gov.cn/micro/onlineItemDetail.jspx?saa004=00000283'
MUNICIPAL_SOURCE_VERSION = 'c5ae6fd988596088b3412c177c26f198846f089f372e528a2158d486f3b6e1d7'


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


def exact_municipal(guide):
    keys = ('province', 'city', 'district', 'region_code', 'scope_level', 'source_url', 'source_id', 'source_version')
    return tuple(guide.get(key) for key in keys) == (
        'shaanxi', '铜川市', '市本级', '610200', 'municipal', MUNICIPAL_URL,
        digest(MUNICIPAL_URL)[:24], MUNICIPAL_SOURCE_VERSION,
    )


def staged_municipal_guide(root=None):
    guide = _read_proof(root, MUNICIPAL_PROOF, MUNICIPAL_PROOF_SHA256)['guide']
    guide['source_id'] = digest(guide['source_url'])[:24]
    if not exact_municipal(guide):
        raise ValueError('铜川市本级办理说明与当地来源不匹配')
    return guide
