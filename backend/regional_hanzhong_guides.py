"""Load independently verified official guides for Hanzhong localities."""
import json
from hashlib import sha256
from pathlib import Path

from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
PROOF = Path('reports/overnight-gap-closure-20261030/localities/hanzhong-hantai-worker/SOURCE-PROOF.json')
PROOF_SHA256 = '2a19f91974a98d0a7c246b8467dfc8b0df6e2461d89ef79d5893399330814eb7'
COUNTY_PROOF = PROOF.parent.with_name('hanzhong-nanzheng-mianxian-worker') / PROOF.name
COUNTY_PROOF_SHA256 = '0f78e6f9a4e00db87f7f2748eab69adca8ae2ec637c3b4fb7d36c4ecf01fe556'
CITY_URL = 'https://zwfw.hanzhong.gov.cn/icity/icity/proinfo/index?code=7197a41a59b8d58586007e9567536b8b'
HANTAI_URL = 'https://zwfw.hanzhong.gov.cn/hantaiqu/icity/proinfo/index?code=8b78d3ed826828562ac2d7d521d317b6'
NANZHENG_URL = 'https://zwfw.hanzhong.gov.cn/nanzhengqu/icity/proinfo/index?code=022c4091212688f29e51265d41fe5d85'
MIANXIAN_URL = 'https://zwfw.hanzhong.gov.cn/mianxian/icity/proinfo/index?code=fb75803296e3e6ca4cbf8085261f9fff'
CITY_SOURCE_VERSION = '3acd887065ff7e48e774dd3419f9173c0ccf839334d37b94e803443ae0ff7f92'
REGIONS = {
    '610700': ('市本级', 'municipal', CITY_URL, CITY_SOURCE_VERSION),
    '610702': ('汉台区', 'district', HANTAI_URL, '91fe36696df88143df09e2c01bf0c5285651938f6429199472959e8c31d75ad3'),
    '610703': ('南郑区', 'district', NANZHENG_URL, '42eabe0b29bc9fc392c60e6a23ca88e0e26e831033f1349e94e6f009b04c86c4'),
    '610725': ('勉县', 'district', MIANXIAN_URL, '894432f50897cc58217f5f313f30888b7d1721d97898a6287c17e9d6f6605cd0'),
}


def _matches_region(guide, code):
    district, level, url, version = REGIONS[code]
    keys = ('province', 'city', 'district', 'scope_level', 'region_code', 'source_url', 'source_id', 'source_version')
    return tuple(guide.get(key) for key in keys) == (
        'shaanxi', '汉中市', district, level, code, url, digest(url)[:24], version,
    )


def exact_municipal(guide):
    return _matches_region(guide, '610700')


def staged_guide(code, root=None):
    if code not in REGIONS:
        raise ValueError('该地区暂无已核验的汉中指南候选')
    proof, checksum = (COUNTY_PROOF, COUNTY_PROOF_SHA256) if code in {'610703', '610725'} else (PROOF, PROOF_SHA256)
    source = Path(ROOT if root is None else root).resolve()
    path = (source / proof).resolve()
    if not path.is_relative_to(source):
        raise ValueError('汉中指南核验文件路径无效')
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != checksum:
        raise ValueError('汉中指南核验文件已变化')
    guide = json.loads(raw)['regions'][code]['guide']
    guide['source_id'] = digest(guide['source_url'])[:24]
    if not _matches_region(guide, code):
        raise ValueError('汉中指南与当地官方事项不匹配')
    return guide
