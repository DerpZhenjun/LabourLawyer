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
YANGXIAN_XIXIANG_PROOF = PROOF.parent.with_name('hanzhong-yangxian-xixiang-worker') / PROOF.name
YANGXIAN_XIXIANG_PROOF_SHA256 = 'ad9511b7dead0944471df466f4896221aa0094af8ce3dfa04af1a647c9dda5dc'
NINGQIANG_LUEYANG_PROOF = PROOF.parent.with_name('hanzhong-ningqiang-lueyang-worker') / PROOF.name
NINGQIANG_LUEYANG_PROOF_SHA256 = '2a1193be7a1080559c4a9de00220f3f5805ddae2707d04ff1fff41ad9709c668'
ZHENBA_LIUBA_FOPING_PROOF = PROOF.parent.with_name('hanzhong-zhenba-liuba-foping-worker') / PROOF.name
ZHENBA_LIUBA_FOPING_PROOF_SHA256 = '70c834460d8c4e3fd5ae757cdaf4302638ab9da7cfb84dbcaa1c0ad486c69ba6'
CITY_URL = 'https://zwfw.hanzhong.gov.cn/icity/icity/proinfo/index?code=7197a41a59b8d58586007e9567536b8b'
HANTAI_URL = 'https://zwfw.hanzhong.gov.cn/hantaiqu/icity/proinfo/index?code=8b78d3ed826828562ac2d7d521d317b6'
NANZHENG_URL = 'https://zwfw.hanzhong.gov.cn/nanzhengqu/icity/proinfo/index?code=022c4091212688f29e51265d41fe5d85'
MIANXIAN_URL = 'https://zwfw.hanzhong.gov.cn/mianxian/icity/proinfo/index?code=fb75803296e3e6ca4cbf8085261f9fff'
YANGXIAN_URL = 'https://zwfw.hanzhong.gov.cn/yangxian/icity/proinfo/index?code=ca7e76a18fe2bb86f512f62c375347e4'
XIXIANG_URL = 'https://zwfw.hanzhong.gov.cn/xixiangxian/icity/proinfo/index?code=b0a9823a38c72404ba37e4f1ad839637'
NINGQIANG_URL = 'https://zwfw.hanzhong.gov.cn/ningqiangxian/icity/proinfo/index?code=40c1d8c82ac016906c57ab9558a8965a'
LUEYANG_URL = 'https://zwfw.hanzhong.gov.cn/lueyang/icity/proinfo/index?code=db398b8a59ada537b50c5d30e5f33063'
ZHENBA_URL = 'https://zwfw.hanzhong.gov.cn/zhenbaxian/icity/proinfo/index?code=3460b023b5fbf0eed211346a41eed716'
LIUBA_URL = 'https://zwfw.hanzhong.gov.cn/liubaxian/icity/proinfo/index?code=791654819cab7692af12cb4e6f78530e'
FOPING_URL = 'https://zwfw.hanzhong.gov.cn/fopingxian/icity/proinfo/index?code=7f5f636163abf3c40ce645a322944808'
CITY_SOURCE_VERSION = '3acd887065ff7e48e774dd3419f9173c0ccf839334d37b94e803443ae0ff7f92'
REGIONS = {
    '610700': ('市本级', 'municipal', CITY_URL, CITY_SOURCE_VERSION),
    '610702': ('汉台区', 'district', HANTAI_URL, '91fe36696df88143df09e2c01bf0c5285651938f6429199472959e8c31d75ad3'),
    '610703': ('南郑区', 'district', NANZHENG_URL, '42eabe0b29bc9fc392c60e6a23ca88e0e26e831033f1349e94e6f009b04c86c4'),
    '610725': ('勉县', 'district', MIANXIAN_URL, '894432f50897cc58217f5f313f30888b7d1721d97898a6287c17e9d6f6605cd0'),
    '610723': ('洋县', 'district', YANGXIAN_URL, '7e3ac1c77970d764482db4e3669c8ba240475799b04bd4b0ab4d79e9e7c7550c'),
    '610724': ('西乡县', 'district', XIXIANG_URL, '304b08175345a4da6bf3b30753a82233d08e0fb7fd5f55b765d66472b5849185'),
    '610726': ('宁强县', 'district', NINGQIANG_URL, '862136c2d597b27f2c2e33896dc1714393d475919a2e0b3fc582412a922ee153'),
    '610727': ('略阳县', 'district', LUEYANG_URL, '3b0a9b7512853f0e97aa6ec942d084d2e81cd4845e94e13ec31acb38ad2db1cf'),
    '610728': ('镇巴县', 'district', ZHENBA_URL, 'ab6f86708ee31a9007839f57eadb834b49b7fd5450410db2c7b5b37176d131c9'),
    '610729': ('留坝县', 'district', LIUBA_URL, '3a64bc8c40196c6467c59462aa423e19fe5125288a8f041d7e413715e2c33f74'),
    '610730': ('佛坪县', 'district', FOPING_URL, '7ea1fb0d2420200bb19db418b3944d4793c8fe78e60689224ef6f8b361bb90c7'),
}
PROOFS_BY_CODE = {
    '610700': (PROOF, PROOF_SHA256),
    '610702': (PROOF, PROOF_SHA256),
    '610703': (COUNTY_PROOF, COUNTY_PROOF_SHA256),
    '610725': (COUNTY_PROOF, COUNTY_PROOF_SHA256),
    '610723': (YANGXIAN_XIXIANG_PROOF, YANGXIAN_XIXIANG_PROOF_SHA256),
    '610724': (YANGXIAN_XIXIANG_PROOF, YANGXIAN_XIXIANG_PROOF_SHA256),
    '610726': (NINGQIANG_LUEYANG_PROOF, NINGQIANG_LUEYANG_PROOF_SHA256),
    '610727': (NINGQIANG_LUEYANG_PROOF, NINGQIANG_LUEYANG_PROOF_SHA256),
    '610728': (ZHENBA_LIUBA_FOPING_PROOF, ZHENBA_LIUBA_FOPING_PROOF_SHA256),
    '610729': (ZHENBA_LIUBA_FOPING_PROOF, ZHENBA_LIUBA_FOPING_PROOF_SHA256),
    '610730': (ZHENBA_LIUBA_FOPING_PROOF, ZHENBA_LIUBA_FOPING_PROOF_SHA256),
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
    proof, checksum = PROOFS_BY_CODE[code]
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
