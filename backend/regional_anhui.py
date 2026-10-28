"""Parse only the independently captured Shushan/Baohe official source versions.

Inputs are raw DOM captures plus the public component record and download manifest.
No normalized candidate, locality fallback, generation adapter or database is used.
New official versions require fresh source review and updated immutable evidence pins.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from lxml import html
from regional_guides import digest, resolve_channel

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path('reports/nationwide-localization-20261028/anhui')
BASE = ROOT / RELATIVE
HOST = 'hf.ahzwfw.gov.cn'
GUIDE_PATH = '/bog-bsdt/static/workProcess/components/applicationMaterial.html'
PATHS = {'basic': 'basic/dom.json', 'conditions': 'conditions/dom.json', 'materials': 'materials/dom.json',
         'process': 'process-success/dom.json', 'intermediary': 'intermediary-success/dom.json',
         'faq': 'faq-success/dom.json', 'detail_id': 'detail-id/dom.json', 'detail_evidence': 'detail-evidence/dom.json',
         'public_data': 'public-guide-viewmodel.json'}
SPECS = {
    'shushan': {
        'district': '蜀山区', 'region': '340104', 'code': '53018b8b19c540cd95ec66e2acdf07d1',
        'service_code': '11340104796446883A400201430200201', 'title': '劳动人事争议仲裁申请',
        'agency': '合肥市蜀山区人力资源和社会保障局',
        'manifest_sha256': '79ddcfe7397dc0aded0f66fb5ec8d327da6116171263debcf8c67977b9915d65',
        'names': ['中华人民共和国居民身份证', '劳动仲裁申请书', '证据'],
        'paths': {'detail_application': 'detail-application-success/dom.json', 'online': 'online-boundary-success/dom.json'},
        'hashes': {
            'basic': '411ec874de3c488c0eb6f5b68445ba9c9aa7acb5f6525fdb9774bf485a5ab41d',
            'conditions': '9678d1be42629650e1a07581df96f9618543b3e1e5c46938033cc26de4ce0aa6',
            'materials': '890ba6291fee555e5721edf64c344b72349fa96094dc3b4dbd84ca644c164eac',
            'detail_id': '72aeb300740872d68025505d61d4bd95363af75228e44613e1b407a75d203fb2',
            'detail_application': '38bf88ae53eb57f6337fae994ebbe13e1d85c2de481ef3608d97cbd0a6298f4e',
            'detail_evidence': '8a9f71749ad022806f9fa02740433a112f6e21c995db45f9803f79c98a8401c0',
            'process': '0b92b6ec75fe854172dac341c06d7126452c0009b660993353c95d7f4bd9287c',
            'intermediary': 'd1f329858bf806318f3ec54e9c903a6ce680c07168c81e0522e72c68d6bf315c',
            'faq': '2e4afc216d464f40badb4252caf777c4b55057e16859197c20334aa86bf3f855',
            'online': '4b4b136f459ba998b0bd45fc32f4e90b8849b5d8b5a858b37e29875598e05a82',
            'public_data': 'abd50d92bd51c3f1afb19e03b7fd835827b7562c2f65dd55829dd58430c14f58'},
        'files': {
            'ff8080819b0b50f2019eb0f823ac0f9c': '3b61756d584a3764c6e7986df03ead01e0f2ef5f0b37e1002ccaaf06981fe188',
            'ff8080819b0b50f2019eb0f823b00fa7': '78e77030c1e1c7ab9d4231e99084b820c989581b0c14316d911a49643dbcad76',
            'ff8080819b0b50f2019eb0f823ae0fa2': '87e3736ed3a859286b7d01040f5b62bdf43b391197dc677af492b72469802de7',
            'ff8080819b0b50f2019eb0f823aa0f94': '0a37d44dd9e14b0c5e1f2ee52052b2836f2367455717fdfa0addd33ca7a4aa0e'}},
    'baohe': {
        'district': '包河区', 'region': '340111', 'code': '4bff399fd9af44849ea2a5d2f115e7da',
        'service_code': '11340111002992648A400201430200201', 'title': '劳动人事争议调仲裁申请',
        'agency': '合肥市包河区人力资源和社会保障局', 'names': ['仲裁申请书', '证据材料', '身份证'],
        'manifest_sha256': '79ed66ef8ef3961b2eb1ac27a884bfb2082a3242ab5530b392d40e081c089d1f',
        'paths': {'detail_application': 'detail-application/dom.json', 'online': 'online-boundary/dom.json',
                  'instructions': 'filling-instructions-tooltip-visible/dom.json'},
        'hashes': {
            'basic': 'd8a40f741bc16fa4e9d67c7591d99fd40c12533c21ba4f7327ebfca2a2c59790',
            'conditions': 'b7c0823bb325c4f09bfa62414c45dfec5060e58fa2ef20ea12d16a7ab219f675',
            'materials': '0eb4cb2de9bbc57c29d2d958ea09a67d118a1a4915393684d8a1b0a975b2f36d',
            'detail_id': 'd3695f2a0b3a025d6fd8dadb2d4051b47b48d28f607d5b4185b5ae462702d951',
            'detail_application': '2ab7a2674f068ee47e17fdb2f04f0f04b516aa32ff88c67eafd149019c8547bd',
            'detail_evidence': '0c8f47219c2d627f935ec8d47ca4128c695911b82c828972db16b2f8a1424ce9',
            'process': 'ad87b9391955d07a1c2f3688a1d8a262c3d41ea61a78cea633664f37586ed2e0',
            'intermediary': '94b08a6c4c34627d6672059e9e1b893163771c0e3fe75c8088f9ef8e99b69945',
            'faq': '0aa2d4588b90828ae7708de80a2cd7d1dfa1e4b6f6dfcc6c47023166d29e772e',
            'online': '7b270dcec7c6f0dc077617e65c31979d29bd08a64a6ee6c080f3178b4b12505b',
            'instructions': '5f07a73a5d6c3e07db8451247a7a016df2a37989a46de15ef916cfaedf23fd93',
            'public_data': 'd1c5e40f08982fb4fa020c74788e42cb6285db7398cc91eb851aea5a0d5c30d0'},
        'files': {
            'ff8080819b0b50f201a03800d0c704bc': 'f7561e40a0295e05058b9a86417a4a0d483fb409e2e3dc22b2ff53162a25332e',
            'ff8080819b0b50f201a03800d0c404af': 'f7561e40a0295e05058b9a86417a4a0d483fb409e2e3dc22b2ff53162a25332e',
            'ff8080819b0b50f201a03800d0b504a7': 'e89d2bdbb788c12394d86049ba260f09d403aecd748f280eb3953d408395eeb9',
            'ff8080819b0b50f201a03800d0b0048e': 'd91deede0a54599798f5062b0b647af5b0378d95edd6f2633529ad5ecd462c9a'}}}


def parse_shushan_capture(captures, originals, *, attachment_root=ROOT):
    """Raw Shushan panels/model + own four download records; returns unpublished guide."""
    return _parse('shushan', captures, originals, attachment_root)


def parse_baohe_capture(captures, originals, *, attachment_root=ROOT):
    """Raw Baohe panels/model + own four download records; returns unpublished guide."""
    return _parse('baohe', captures, originals, attachment_root)


def _text(node):
    return re.sub(r'\s+', ' ', node.text_content()).strip()


def _same(left, right):
    return re.sub(r'\s+', '', left) == re.sub(r'\s+', '', right)


def _source(locality, spec, key, value):
    """Bind raw input to an immutable public source file, not a candidate summary."""
    relative = spec['paths'].get(key, PATHS.get(key))
    if not relative or not isinstance(value, dict):
        raise ValueError('缺少自己的原始来源采集')
    path = BASE / locality / relative
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != spec['hashes'][key] or digest(value) != digest(json.loads(body)):
        raise ValueError('原始来源采集SHA或输入内容不匹配，需要重新核验')
    return {'capture_file': (RELATIVE / locality / relative).as_posix(),
            'capture_sha256': spec['hashes'][key], 'collected_at': value['captured_at'],
            'verified_at': value['captured_at']}


def _own_dom(page, spec):
    try:
        address = urlsplit(page['url'])
        if (address.scheme, address.hostname, address.path, parse_qs(address.query)) != (
                'https', HOST, GUIDE_PATH, {'ssqdCode': [spec['code']]}):
            raise ValueError('不是本区自身事项URL')
        dom = html.fromstring(page['html'])
        headings = dom.xpath('//h1')
        if len(headings) != 1 or _text(headings[0]) != spec['title'] or spec['agency'] not in page['text']:
            raise ValueError('自身事项标题、实施机关或正文不符')
        return dom
    except (KeyError, TypeError, html.etree.ParserError) as exc:
        raise ValueError('必须提供自己的原始官方DOM采集') from exc


def _section(dom, identifier):
    nodes = dom.xpath('//*[@id=$identifier]', identifier=identifier)
    if len(nodes) != 1 or not _text(nodes[0]):
        raise ValueError('缺少正式指南自身正文栏目：' + identifier)
    return nodes[0]


def _table_fields(section):
    raw = {}
    for table in section.xpath('.//table[not(ancestor::table)]'):
        for row in table.xpath('./tr|./tbody/tr'):
            cells = row.xpath('./td|./th')
            if len(cells) not in {2, 4}:
                continue
            for index in range(0, len(cells), 2):
                label = _text(cells[index])
                visible = cells[index + 1].xpath('.//text()[not(ancestor::*[contains(@class,"el-dialog__wrapper")])]')
                value = re.sub(r'\s+', ' ', ' '.join(visible)).strip()
                # UI toggles are not part of the official field value.
                value = re.sub(r'\s*(说明|查看地图)$', '', value).strip()
                if label in raw and not _same(raw[label], value):
                    raise ValueError('本页同一字段出现冲突值，不能静默覆盖')
                raw[label] = value
    return raw


def _templates(locality, spec, model, originals, material_ids, proof, url, attachment_root):
    if not isinstance(originals, list) or len(originals) != 4:
        raise ValueError('自己的四个公开附件下载记录不完整')
    manifest_file = BASE / locality / 'downloads/manifest.json'
    manifest_body = manifest_file.read_bytes()
    if (hashlib.sha256(manifest_body).hexdigest() != spec['manifest_sha256']
            or digest(originals) != digest(json.loads(manifest_body))):
        raise ValueError('自己的下载来源记录、响应头或时间SHA不符')
    records = {a.get('id'): a for a in originals}
    if len(records) != 4 or set(records) != set(spec['files']):
        raise ValueError('附件ID重复或不是本区自身原件')
    expected = []
    for row in model['clJson']:
        for field, kind in [('materialEmpty', 'blank'), ('materialSample', 'sample')]:
            for item in row['json'][field]:
                expected.append((item, kind, row['materialName']))
    expected.extend((item, 'instruction', '办理流程图') for item in model['processImgJson'])
    if len(expected) != 4 or {item['id'] for item, _, _ in expected} != set(records):
        raise ValueError('公开材料附件和本区下载记录未逐项匹配')
    result = []
    root = Path(attachment_root).resolve()
    for item, kind, name in expected:
        record = records[item['id']]
        relative = Path(locality) / 'downloads' / (item['id'] + '-' + item['fileName'])
        final_relative = Path('templates/_docx/_regional') / (spec['region'] + '000000') / relative.name
        path = root / final_relative
        actual_relative = record.get('path', '').replace('\\', '/')
        addr = urlsplit(item['filePath'])
        if (addr.scheme != 'https' or addr.hostname != HOST or not addr.path.startswith('/intranet/group')
                or actual_relative != relative.as_posix() or not path.resolve().is_relative_to(root)
                or record.get('source_url') != url or record.get('requested_url') != item['filePath']
                or record.get('final_url') != item['filePath'] or record.get('filePath') != item['filePath']
                or record.get('kind') != kind or record.get('material') != name
                or record.get('fileName') != item['fileName'] or record.get('fileExt') != item['fileExt']
                or record.get('status') != 'downloaded' or record.get('http_status') != 200
                or record.get('sha256') != spec['files'][item['id']] or not path.is_file()):
            raise ValueError('自己的附件来源、标签、路径或下载SHA不符')
        body = path.read_bytes()
        original_body = (BASE / relative).read_bytes()
        if (hashlib.sha256(body).hexdigest() != record['sha256'] or len(body) != record.get('bytes')
                or len(body) != int(item['fileSize']) or original_body != body):
            raise ValueError('自己的附件实际文件字节校验失败')
        is_document = item['fileExt'] in {'doc', 'docx'}
        classification = ('unreviewed_application_document' if is_document else 'workflow_instruction' if kind == 'instruction'
                          else 'blank_contract_specimen_image' if locality == 'shushan' else 'instruction_image')
        result.append({**proof, 'id': item['id'], 'annex_id': item['id'], 'source_url': url,
                       'region_code': spec['region'], 'material_id': material_ids.get(name),
                       'original_name': item['fileName'], 'official_kind': kind,
                       'official_label': {'blank': '空白表格', 'sample': '示例样表', 'instruction': '办理流程图'}[kind],
                       'file': final_relative.as_posix(), 'file_type': item['fileExt'],
                       'download_url': item['filePath'], 'final_download_url': record['final_url'],
                       'sha256': record['sha256'], 'bytes': len(body), 'download_status': 'downloaded',
                       'downloaded_at': record['downloaded_at'], 'document_types': [],
                       'download_manifest': {'file': (RELATIVE / locality / 'downloads/manifest.json').as_posix(),
                                             'sha256': spec['manifest_sha256']},
                       'content_classification': classification,
                       'content_verification_status': 'not_reviewed' if is_document else 'image_inspected',
                       'classification_note': '官方标签与实际内容分类分别保留；DOC/DOCX未进行逐页渲染验收，无填写适配批准。',
                       'download_provenance': {key: record[key] for key in ['source_url', 'requested_url', 'final_url', 'http_status', 'response_headers', 'downloaded_at']}})
    return result


def _parse(locality, captures, originals, attachment_root):
    spec = SPECS[locality]
    if not isinstance(captures, dict) or not set(spec['hashes']).issubset(captures):
        raise ValueError('必须提供全部本区原始DOM和公开材料元数据，不接受已归一化摘要')
    url = 'https://' + HOST + GUIDE_PATH + '?ssqdCode=' + spec['code']
    doms = {key: _own_dom(captures[key], spec) for key in spec['hashes'] if key not in {'public_data', 'online'}}
    raw = _table_fields(_section(doms['basic'], 'section1'))
    if (raw.get('所属区划') != spec['district'] or raw.get('实施主体') != spec['agency']
            or raw.get('所属部门') != spec['agency'] or raw.get('实施清单编码') != spec['service_code']
            or raw.get('事项名称') != spec['title'] or raw.get('基本编码') != '002014302002'):
        raise ValueError('正式正文地区、机关、事项编码或事项名称不匹配')
    public = captures['public_data']; model = public.get('data', {})
    if (public.get('source_url') != url or model.get('ssqdCode') != spec['code']
            or model.get('ssqdZoneCode') != spec['region'] + '000000' or model.get('ssqdZoneName') != spec['district']
            or model.get('ssqdDeptName') != spec['agency'] or model.get('ssqdBaseCode') != spec['service_code']
            or model.get('ssqdName') != spec['title']):
        raise ValueError('公开元数据不是自身机关、地区和事项')
    sections = {name: _text(_section(doms[key], identifier)) for key, name, identifier in [
        ('basic', '基本信息', 'section1'), ('conditions', '受理条件', 'section2'),
        ('materials', '申请材料', 'section3'), ('process', '办理流程', 'section4'),
        ('intermediary', '中介服务', 'section5'), ('faq', '常见问题', 'section7')]}
    if (not _same(sections['受理条件'], model.get('acceptCondition', ''))
            or re.sub(r'\s+', '', model.get('hanleProc', '')) not in re.sub(r'\s+', '', sections['办理流程'])
            or not _same(raw.get('办理时间', ''), model.get('hanleTime', ''))
            or raw.get('承诺办结时限') != model.get('promiseTime') + '个工作日'
            or raw.get('法定办结时限') != model.get('legalTime') + '个工作日'):
        raise ValueError('原始正文条件、办理流程或时限与公开字段不一致')
    for question in model.get('cjwtJson', []):
        if not all(re.sub(r'\s+', '', question[key]) in re.sub(r'\s+', '', sections['常见问题']) for key in ['problemTitle', 'problemAnswer']):
            raise ValueError('常见问题原始正文缺失，不使用摘要代替')
    rows = _section(doms['materials'], 'section3').xpath('.//table[contains(@class,"el-table__body")]//tr')
    model_rows = model.get('clJson', [])
    if len(rows) != 3 or len(model_rows) != 3:
        raise ValueError('自身材料表数量改变')
    parsed_rows = []
    for row, record, expected_name in zip(rows, model_rows, spec['names']):
        cells = row.xpath('./td')
        if len(cells) != 9:
            raise ValueError('自己的材料表列结构改变')
        values = [_text(cell) for cell in cells]
        name = values[0].replace('已关联电子证照', '').strip()
        detail = record['json']
        if (name != expected_name or record.get('materialName') != name
                or values[2:6] != [detail['gbcllxTxt'], detail['ggfs'], detail['gbclxsTxt'], record['materialNeedTxt']]
                or values[1].replace('来源渠道说明', '').strip() != record['sourceChannelTxt']):
            raise ValueError('原始材料行和自己的元数据发生错配或交换')
        labels = [_text(a) for a in cells[7].xpath('.//a')]
        expected_labels = ['空白表格'] * bool(detail['materialEmpty']) + ['示例样表'] * bool(detail['materialSample'])
        if labels != expected_labels:
            raise ValueError('原始材料表的附件标签与公开附件记录不同')
        if locality == 'shushan' and not _same(values[6], record['editNotice']):
            raise ValueError('填报须知缺少自己的完整原文')
        if locality == 'baohe' and record['editNotice'] not in captures['instructions']['text']:
            # Browser tooltip renders some adjacent text without spaces; compare content as displayed.
            if re.sub(r'\s+', '', record['editNotice']) not in re.sub(r'\s+', '', _text(doms['instructions'])):
                raise ValueError('窗口与网上填报须知未被真实tooltip采集验证')
        detail_key = 'detail_id' if name in {'身份证', '中华人民共和国居民身份证'} else 'detail_evidence' if name in {'证据', '证据材料'} else 'detail_application'
        modals = _section(doms[detail_key], 'section3').xpath('.//div[contains(@class,"el-dialog__wrapper") and not(contains(@style,"display: none"))]')
        if len(modals) != 1 or not all(re.sub(r'\s+', '', record[key]) in re.sub(r'\s+', '', _text(modals[0])) for key in ['materialEvidence', 'acceptStandard']):
            raise ValueError('自己的材料依据或受理标准未在真实详情框中核验')
        parsed_rows.append((name, values, record, detail_key))
    # Integrity pins cover public raw bytes as well as semantic cross-checks above.
    proof = {key: _source(locality, spec, key, captures[key]) for key in spec['hashes']}
    provenance = {'source_url': url, 'region_code': spec['region']}
    fields = {key: {**provenance, **proof['basic'], 'raw_value': value, 'normalized_value': value or None,
                    'verification_status': 'verified' if value else 'missing'} for key, value in raw.items()}
    fields['咨询方式'] = {**fields['咨询方式'], 'original_label': '咨询方式'}
    materials = []
    for name, values, record, detail_key in parsed_rows:
        materials.append({**provenance, **proof['materials'], 'id': digest([url, record['id']])[:20],
                          'name': name, 'required': values[5], 'original_copy': values[2],
                          'copies': values[3], 'raw_copies': values[3], 'format': values[4],
                          'purpose': None, 'applicable_conditions': None, 'verification_status': 'conflict',
                          'details': {'来源渠道': record['sourceChannelTxt'], '填报须知': record['editNotice'],
                                      '材料依据': record['materialEvidence'], '受理标准': record['acceptStandard'],
                                      '原始材料行': values}, 'detail_evidence': proof[detail_key]})
    templates = _templates(locality, spec, model, originals, {m['name']: m['id'] for m in materials},
                           {**proof['public_data'], 'region_code': spec['region']}, url, attachment_root)
    sections['时限说明'] = '\n'.join(value for value in [model.get('promiseTimeDesc'), model.get('legalTimeDesc')] if value)
    sections['预约方式'] = '\n'.join(value for value in [model.get('bookPhone'), model.get('bookUrl')] if value)
    online = captures['online']; auth = urlsplit(online['url']); auth_dom = html.fromstring(online['html'])
    if (auth.scheme != 'https' or auth.hostname != 'sso.ahzwfw.gov.cn' or auth.path != '/uccp-server/login'
            or parse_qs(auth.query).get('service') != ['https://hf.ahzwfw.gov.cn/bog-bsdt/transition.html']
            or not auth_dom.xpath('//input[@type="password"]') or '统一认证中心' not in online['text']):
        raise ValueError('不是本次实际读取的官方认证表单边界')
    channel = resolve_channel(raw, sections['办理流程'])
    fields['办理形式']['normalized_value'] = channel['form']
    issues = [{'type': 'OFFICIAL_SOURCE_CONFLICT', 'reason': '材料表、FAQ或窗口须知的份数/原件要求未能统一，保留各自原文。',
               'evidence': [proof['materials'], proof['faq'] if locality == 'shushan' else proof['instructions']]}]
    if locality == 'baohe':
        issues.append({'type': 'DUPLICATE_ATTACHMENT_BYTES', 'reason': '官方空白和样表标签不同，但两个申请书下载字节完全相同；未据标签断言填写示例。'})
    return {'province': 'anhui', 'province_name': '安徽省', 'city': '合肥市', 'district': spec['district'],
            'region_code': spec['region'], 'official_service_region_code': model['ssqdZoneCode'],
            'service_name': '劳动人事争议仲裁申请', 'original_service_name': raw['事项名称'],
            'service_code': raw['实施清单编码'], 'source_url': url, 'source_title': spec['title'],
            'source_type': 'official_service_guide', 'authority': raw['实施主体'],
            'collected_at': captures['basic']['captured_at'], 'verified_at': public['captured_at'],
            'verification_status': 'conflict', 'fields': fields, 'materials': materials,
            'templates': templates, 'sections': sections, 'channel': channel, 'source_issues': issues,
            'online_evidence': {**proof['online'], 'observed_status': 'auth_required', 'observed_url': online['url'],
                                'exact_service_callback_verified': False,
                                'note': '认证回跳仅为通用transition.html，不含本事项编码；登录后本区业务能力未核验。'},
            'official_identity': {key: model[key] for key in ['ssqdCode', 'ssqdZoneCode', 'ssqdZoneName', 'ssqdDeptCode', 'ssqdDeptName', 'ssqdBaseCode', 'ssqdVersion', 'updateTime']},
            'evidence': proof, 'publication_status': 'unpublished',
            'warnings': ['仅适用本区自身来源，不代表合肥市全市或其他区县。',
                         '保留官方表格与FAQ、填报须知的份数和原件要求差异，请向本区机构核实。',
                         '法定与承诺时限按原标签分别保留，不把1个工作日解释为案件裁决保证。',
                         '官网宣传网上办理；实际认证回跳未包含本事项编码，网办入口仍未核验。',
                         '下载标签、字节来源和内容分类分别记录；DOC/DOCX未逐页渲染验收，未批准生成。']}
