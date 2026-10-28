"""Normalize only the sealed 2026-10-28 own-source Yuhang/Xihu capture bundle.

Public parsers take ``capture_root`` (the Zhejiang report directory or an exact
copy) and ``manifest`` (the retained SHA256-MANIFEST.json path or its decoded
mapping). The manifest is pinned to the observed capture inventory; a newly
hashed replacement manifest cannot authorize different evidence. Only raw DOM,
own native request/control traces, attachment metadata/originals and institutional
identity evidence are read. Derived district guide.json files are never inputs.
This module performs no network, database, publication or document generation.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
import zipfile
import io
from lxml import html, etree

from regional_guides import digest

MANIFEST_DIGEST = '1550a0e143244cb4201dea1361a990364204bee2be86ce02b706d6c605a56ef8'
REPORT = 'reports/nationwide-localization-20261028/zhejiang'
SERVICE = '劳动人事争议仲裁申请'
STANDARD = 'fc266994-f669-4861-acdc-799f3ea2decc'
CATEGORY = '8d0494f2-74c9-11e9-b64f-6c92bf669f92'
MATERIALS = ['用人单位登记注册材料', '劳动者身份证', '《劳动人事争议仲裁申请书》',
             '《证据清单》', '存在劳动关系的证据和可证实申请人主张的证据']
ANNEXES = {
    'blank_application': ('application.docx', '21B24C52D2AC3EB007AA7F55CE0AAD79',
        '0eab0f0a2ee98e8ca1e4d2fa5469fcb5738d0c0f24671345bebc8394099ae41f', 2, 'blank', MATERIALS[2]),
    'blank_evidence_list': ('evidence-list.docx', '872DFF90A8578907CB947197A784AA48',
        '4965bf3d2bf76404ab190d1e47d2fa250c8cb8bd93762949df94be38b2d4ca8c', 3, 'blank', MATERIALS[3]),
    'sample_identity_document': ('id-example.jpg', '2CD6D8BA9380D21B19B90B9292B23140',
        '1a992bf994963a6a03f7344e9a766246c0b495756eb4877406b052d039272b09', 1, 'sample', MATERIALS[1]),
}
SPECS = {
    'yuhang': {'district': '余杭区', 'code': '330110', 'local': '8f1bc917-6583-4541-be13-231de0b91d0b',
        'window': 'yuhang-window', 'place': '杭州市余杭区公共法律服务中心（杭州市余杭区仓前街道龙潭路22号（余杭区社会治理中心））一楼9号、10号窗口',
        'phone': '0571-89391163', 'native_button': '@e441', 'agency_pdf': '3f2e538824574b3ea09ec72e93c24d0d'},
    'xihu': {'district': '西湖区', 'code': '330106', 'local': '2b882c41-1fc2-4689-9f56-631917cf63fe',
        'window': 'xihu-window-actual', 'place': '西湖区政务服务中心（杭州市西湖区蒋村街道文一西路858号）西4楼大厅2号窗口',
        'phone': '0571-89510755', 'native_button': '@e619', 'agency_pdf': '51b1123e0fd746e8818ee431af75da15'},
}


def parse_yuhang_capture(capture_root, manifest):
    """Parse the sealed Yuhang bundle; see module docstring for both arguments."""
    return _parse(capture_root, manifest, 'yuhang')


def parse_xihu_capture(capture_root, manifest):
    """Parse the sealed Hangzhou Xihu bundle, never Nanchang's same-named district."""
    return _parse(capture_root, manifest, 'xihu')


def _text(node):
    return re.sub(r'\s+', ' ', node.text_content()).strip()


def _class(node, name):
    return node.xpath('.//*[contains(concat(" ", normalize-space(@class), " "), $name)]', name=' ' + name + ' ')


class _Evidence:
    def __init__(self, root, manifest):
        self.root = Path(root).resolve()
        try:
            retained = json.loads(Path(manifest).read_text(encoding='utf8')) if isinstance(manifest, (str, Path)) else manifest
            if digest(retained) != MANIFEST_DIGEST:
                raise ValueError('不是已核验的浙江原始采集清单，不能自行重新签发SHA')
            self.files = {k.replace('\\', '/'): v for k, v in retained['files'].items()}
        except (TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
            raise ValueError('缺少原始采集清单') from exc
        self.used = {}

    def read(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError('证据路径越界或文件缺失：' + relative)
        body = path.read_bytes()
        record = self.files.get(relative)
        actual = hashlib.sha256(body).hexdigest()
        if not record or record['sha256'] != actual or record['bytes'] != len(body):
            raise ValueError('原始文件SHA或大小不匹配：' + relative)
        self.used[relative] = {'sha256': actual, 'bytes': len(body)}
        return body

    def load(self, relative):
        return json.loads(self.read(relative).decode('utf8'))


def _guide_page(evidence, folder, source):
    capture = evidence.load(folder + '/dom.json')
    if capture['url'] != source or SERVICE not in capture['title']:
        raise ValueError('不是该区自身正式指南来源')
    dom = html.fromstring(capture['html'])
    if SERVICE not in _text(dom) or SERVICE not in capture['text']:
        raise ValueError('指南正文实际事项不匹配')
    datetime.fromisoformat(capture['captured_at'].replace('Z', '+00:00'))
    evidence.read(folder + '/page.png')
    return capture, dom


def _parse(root, manifest, name):
    evidence = _Evidence(root, manifest)
    spec = SPECS[name]
    source = 'https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=' + spec['local']
    authority = '杭州市' + spec['district'] + '人力资源和社会保障局'
    search = evidence.load(name + '-search/dom.json')
    address = urlsplit(search['url'])
    if (address.scheme != 'https' or address.hostname != 'search.zj.gov.cn'
        or address.path != '/api-gateway/jpaas-jsearch-web-server/search'
        or parse_qs(address.query).get('websiteid') != [spec['code'] + '000000']
        or ('当前搜索范围为： ' + spec['district']) not in search['text']):
        raise ValueError('官方目录所选地区或城市不匹配')
    search_dom = html.fromstring(search['html'])
    controls = search_dom.xpath('//a[@title=$title and @data-local-inner-code=$local]', title=SERVICE, local=spec['local'])
    if len(controls) != 1 or controls[0].get('data-stdcateguid') != STANDARD or controls[0].get('categorysourcereferno') != CATEGORY:
        raise ValueError('自身目录服务标识不匹配')
    capture, dom = _guide_page(evidence, name + '-expanded', source)
    window, window_dom = _guide_page(evidence, spec['window'], source)
    faq, _ = _guide_page(evidence, name + '-faq', source)
    law, _ = _guide_page(evidence, name + '-law', source)
    if spec['place'] not in window['text'] or spec['phone'] not in window['text']:
        raise ValueError('本区实际窗口、完整市区或电话不匹配')
    basic = {}
    for row in _class(dom, 'subtit'):
        spans = row.xpath('./span')
        if len(spans) == 2:
            basic[_text(spans[0]).rstrip('：:')] = _text(spans[1])
    if basic.get('实施主体') != '区人力社保局' or basic.get('法定办结时限') != '60天':
        raise ValueError('自身实施主体或原始法定时限改变')
    header = {}
    for item in _class(dom, 'summary-item'):
        value = _text(item)
        for label in ['到现场次数', '承诺办结时限']:
            if value.startswith(label):
                header[label] = value.removeprefix(label).replace(' ', '')
    if header != {'到现场次数': '0次', '承诺办结时限': '44工作日'}:
        raise ValueError('已观察的承诺时限或跑动次数改变')
    identity_pdf = evidence.read(name + '/agency-identity.pdf')
    identity_text = evidence.read(name + '/agency-identity.txt').decode('utf8')
    if not identity_pdf.startswith(b'%PDF') or authority not in re.sub(r'\s+', '', identity_text):
        raise ValueError('完整办理机关缺少已核验的本区身份旁证')
    own = {'source_url': source, 'region_code': spec['code'], 'collected_at': capture['captured_at'],
           'verified_at': capture['captured_at']}
    def field(value, normalized=None, **extra):
        return {**own, 'raw_value': value, 'normalized_value': normalized if normalized is not None else value,
                'verification_status': 'verified' if value else 'missing', **extra}
    fields = {k: field(v) for k, v in basic.items() if k != '设定依据'}
    fields.update({k: field(v) for k, v in header.items()})
    fields['实施主体'] = field(basic['实施主体'], authority, normalization_basis='own district selector/window and sealed institutional PDF')
    conditions = _class(dom, 'condition')
    flow_nodes = _class(dom, 'flow-rich-text-body')
    if len(conditions) != 1 or len(flow_nodes) != 1 or '管辖范围' not in _text(conditions[0]):
        raise ValueError('缺少真实展开条件或流程')
    flow = flow_nodes[0].text_content().strip()
    if '在5个工作日内作出是否受理的决定' not in flow or '现场或邮寄提交申请材料' not in flow or '线上申请' not in flow:
        raise ValueError('已观察的申请方式或受理阶段不完整')
    fields['受理决定时限'] = field('5个工作日', scope='acceptance_decision_only', official_context=flow)
    window_raw = window['text'].split('基本信息\n')[-1].split('好差评\n')[0].strip()
    fields['办理地点'] = field(spec['place'])
    fields['办理时间'] = field(window_raw.split('工作时间\n', 1)[1].split('联系电话\n')[0].strip())
    fields['咨询电话'] = field(spec['phone'])
    material_nodes = _class(dom, 'material-name-row')
    if [_text(n) for n in material_nodes] != MATERIALS:
        raise ValueError('本区实际材料行数量或名称改变')
    materials = []
    for i, node in enumerate(material_nodes):
        item = node.getparent().getparent()
        modules = [_text(x) for x in _class(item, 'small-module')]
        copies = re.sub(r'\s+', ' ', modules[0]) if modules else ''
        if copies != '纸质材料 2份，A4' or modules[1:] != ['原件']:
            raise ValueError('原始材料份数、规格或原复印件字段改变')
        labels = [_text(x) for x in _class(item, 'download') + _class(item, 'exampleOne')]
        expected = ['示例'] if i == 1 else ['下载'] if i in {2, 3} else []
        if labels != expected:
            raise ValueError('材料空白/示例控件身份不匹配')
        materials.append({**own, 'id': digest([source, MATERIALS[i]])[:20], 'name': MATERIALS[i],
            'required': None, 'copies': '2', 'raw_copies': copies, 'format': '纸质材料，A4', 'original_copy': '原件',
            'purpose': None, 'applicable_conditions': None,
            'details': {'原始材料行': _text(item), '材料来源': '自备材料', '必要性': '当前页面未另行公示必要或可选'},
            'verification_status': 'verified'})
    boundary = evidence.load(name + '-online-boundary/dom.json')
    login = urlsplit(boundary['url'])
    login_dom = html.fromstring(boundary['html'])
    if (login.scheme != 'https' or login.hostname != 'user.zjzwfw.gov.cn' or login.path != '/pc/login'
        or '个人用户登录' not in boundary['text'] or not login_dom.xpath('//input[@type="password"]')):
        raise ValueError('没有自身实际登录表单边界')
    boundary_time = datetime.fromisoformat(boundary['captured_at'].replace('Z', '+00:00'))
    gap = (boundary_time - datetime.fromisoformat(capture['captured_at'].replace('Z', '+00:00'))).total_seconds()
    actions = [json.loads(line) for line in evidence.read('browser-actions.jsonl').decode('utf8').splitlines()]
    clicks = [a for a in actions if a.get('success') and a.get('args') == ['click', spec['native_button']]]
    if not 0 <= gap <= 600 or not any(0 <= (boundary_time - datetime.fromisoformat(a['at'])).total_seconds() <= 60 for a in clicks):
        raise ValueError('登录边界与实际本区在线按钮点击时间不匹配')
    evidence.read(name + '-online-boundary/page.png')
    entry_check = {**own, 'url': boundary['url'], 'checked_at': boundary['captured_at'], 'official_link': True,
        'status': 'auth_required', 'post_login_flow': 'unknown', 'submitted': False,
        'result': '实际点击自身在线办理进入官方登录表单；未登录、未提交。'}
    network = evidence.load(name + '-attachment-network.json')
    downloads = evidence.load(name + '/attachments.json')
    if len(downloads) != 3 or {d['kind'] for d in downloads} != set(ANNEXES):
        raise ValueError('自身三份公开附件身份不完整')
    templates = []
    attachment_note = ''
    for item in downloads:
        filename, annex, checksum, index, kind, original_name = ANNEXES[item['kind']]
        relative = name + '/attachments/' + filename
        url = item['source_url']
        parsed = urlsplit(url)
        if (str(Path(item['file'])).replace('\\', '/') != relative or parsed.scheme != 'https'
            or parsed.hostname != 'portal.zjzwfw.gov.cn' or '/media/oss/' not in parsed.path
            or annex not in parsed.path or item.get('final_url') != url or item.get('status') != 200
            or item.get('sha256') != checksum):
            raise ValueError('附件文件名、本区路径、来源、类别或原件SHA不匹配')
        matching = [r for r in network if r['url'] == url and r.get('status') == 200 and r.get('method') == 'GET']
        start = datetime.fromisoformat(capture['captured_at'].replace('Z', '+00:00')).timestamp() * 1000
        if not matching or not any(start <= r['timestamp'] <= boundary_time.timestamp() * 1000 for r in matching):
            raise ValueError('没有自身指南点击后公开附件网络证据')
        body = evidence.read(relative)
        if hashlib.sha256(body).hexdigest() != checksum:
            raise ValueError('附件原件SHA不匹配')
        if kind == 'blank':
            try:
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    xml = etree.fromstring(archive.read('word/document.xml'))
                    content = ''.join(xml.itertext())
            except (zipfile.BadZipFile, KeyError, etree.XMLSyntaxError) as exc:
                raise ValueError('附件不是已核验的OOXML正文') from exc
            if original_name.strip('《》') not in content:
                raise ValueError('空白文书内容身份不匹配')
            if item['kind'] == 'blank_application':
                attachment_note = '申请书副本份数，应按对方当事人人数提交。'
                if attachment_note not in content or '用于劳动者申请' not in content or '用于用人单位申请' not in content:
                    raise ValueError('申请书两种主体或副本说明不完整')
        elif not body.startswith(b'\xff\xd8'):
            raise ValueError('身份证示例不是已核验的JPEG')
        templates.append({**own, 'id': digest([source, annex, kind])[:24], 'official_annex_id': annex,
            'annex_id': annex,
            'material_id': materials[index]['id'], 'original_name': original_name,
            'source_filename': parsed.path.rsplit('/', 1)[-1],
            'control_label': '下载' if kind == 'blank' else '示例',
            'official_kind': kind, 'file_type': 'docx' if kind == 'blank' else 'jpg',
            'file': f"templates/_docx/_regional/{spec['code']}/{annex}-{original_name.strip('《》')}."+('docx' if kind=='blank' else 'jpg'),
            'retained_download_file': REPORT + '/' + relative, 'sha256': checksum, 'bytes': len(body),
            'download_url': url, 'final_download_url': url, 'http_status': 200,
            'download_status': 'downloaded', 'download_acquisition': item['acquisition'],
            'downloaded_at': item['captured_at'], 'can_generate': False, 'document_types': [],
            'classification_note': '各自指南实际控件及公共网络URL已独立核验；原字节由公开GET取得，非CLI浏览器下载字节。'})
    sections = {'基本信息': '\n'.join(k + '：' + v for k, v in basic.items()),
        '受理条件': _text(conditions[0]), '申请材料': '\n'.join(m['details']['原始材料行'] for m in materials),
        '办理流程': flow, '窗口办理': window_raw,
        '常见问题': faq['text'].split('基本信息\n')[-1].split('好差评\n')[0].strip(),
        '设定依据': law['text'].split('设定依据\n')[-1]}
    return {'province': 'zhejiang', 'province_name': '浙江省', 'city': '杭州市', 'district': spec['district'],
        'region_code': spec['code'], 'service_name': SERVICE, 'service_code': spec['local'],
        'service_code_type': 'observed_localInnerCode_not_national_implementation_code',
        'service_ids': {'localInnerCode': spec['local'], 'stdcateguid': STANDARD, 'categorysourcereferno': CATEGORY},
        'authority': authority, 'source_url': source, 'source_id': digest(source)[:24],
        'source_title': capture['title'], 'source_type': 'official_service_guide',
        'collected_at': own['collected_at'], 'verified_at': own['verified_at'], 'verification_status': 'partial',
        'fields': fields, 'materials': materials, 'templates': templates, 'sections': sections,
        'copy_conflict': {'status': 'retained_unresolved', 'guide_raw': '纸质材料 2份，A4；原件', 'attachment_note': attachment_note},
        'channel': {'raw_value': flow, 'form': 'window_and_online', 'online_status': 'auth_required',
            'entry_url': source, 'mentioned_urls': [], 'entry_check': entry_check},
        'authority_evidence': {'raw_value': basic['实施主体'], 'normalized_value': authority,
            'source_url': 'https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/'
                + ('web3095' if name == 'yuhang' else 'web1838') + '/site/attach/0/' + spec['agency_pdf'] + '.pdf',
            'file': REPORT + '/' + name + '/agency-identity.pdf',
            'sha256': evidence.used[name + '/agency-identity.pdf']['sha256'],
            'scope': 'historical institution identity corroboration only; current contacts from own guide'},
        'evidence': {'manifest_digest': MANIFEST_DIGEST, 'capture_file': REPORT + '/' + name + '-expanded/dom.json',
            'capture_sha256': evidence.used[name + '-expanded/dom.json']['sha256'], 'source_files': evidence.used},
        'warnings': ['仅适用于杭州市该区自身已采集事项，不据共享附件字节扩大到全省。',
            '法定60天、承诺44工作日按原文保留；5个工作日仅为受理决定阶段，未作单位换算。',
            '材料表2份原件与申请书按对方人数提交副本的说明均保留，请向受理机关核实具体份数。',
            '当前界面未分别标注必要或可选；不能因五项清单遗漏委托情形就推断其无需代理手续。',
            '在线入口仅核验至登录边界；登录后流程、提交及到场要求未知。',
            '空白文件及身份证示例分别保存；未启用适配填写或生成。']}
