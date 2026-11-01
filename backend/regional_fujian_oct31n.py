"""Putian Licheng/Xiuyu own N proposal; unregistered and without phase approval."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from lxml import etree as E
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
N = {'w': W}

def _layout_need(ok):
    if not ok:
        raise ValueError('Own blank OOXML shape differs')

def _layout_doc(raw):
    with ZipFile(BytesIO(raw)) as z:
        _layout_need(z.testzip() is None)
        _layout_need(len(z.namelist()) == len(set(z.namelist())) and 'word/vbaProject.bin' not in z.namelist())
        return E.fromstring(z.read('word/document.xml'), E.XMLParser(resolve_entities=False, no_network=True))

def _layout_inspect(raw, kind):
    d = _layout_doc(raw)
    ps = d.findall('w:body/w:p', N)
    _layout_need(len(d.findall('w:body/w:sectPr', N)) == 1)
    if kind == 'application':
        _layout_need(len(ps) == 22 and (not d.findall('.//w:tbl', N)))
        for i, label in [(0, '仲裁申请书'), (2, '申请人：'), (3, '委托代理人：'), (4, '被申请人：'), (19, '申请人：')]:
            _layout_need(''.join(ps[i].itertext()).strip() == label)
        _layout_need(all((''.join(ps[7 + i].itertext()).strip() == str(i + 1) + '、' and len(ps[7 + i].findall('w:r', N)) == 2 for i in range(3))))
        _layout_need(all((not ''.join(p.itertext()).strip() for p in ps[11:15])))
        shape = {'paragraphs': 22, 'request_slots': 3}
    else:
        _layout_need(kind == 'evidence')
        tables = d.findall('.//w:tbl', N)
        _layout_need(len(tables) == 1 and len(ps) == 2)
        rows = tables[0].findall('w:tr', N)
        _layout_need(len(rows) == 11 and [''.join(c.itertext()) for c in rows[0].findall('w:tc', N)] == ['序号', '证据名称', '页数', '原件/复印件', '证明对象', '页码'])
        _layout_need(all((len(r.findall('w:tc', N)) == 6 and all((not ''.join(c.itertext()).strip() for c in r.findall('w:tc', N))) for r in rows[1:-1])))
        shape = {'paragraphs': 2, 'evidence_rows_capacity': 9}
    with ZipFile(BytesIO(raw)) as z:
        members = {n: sha256(z.read(n)).hexdigest() for n in z.namelist()}
    return {**shape, 'CRC': True, 'member_sha256': members, 'visual_review': False, 'filling_approved': False}

def _layout_run_text(run, value):
    for child in list(run):
        if child.tag != '{' + W + '}rPr':
            run.remove(child)
    for i, line in enumerate(value.split('\n')):
        if i:
            E.SubElement(run, '{' + W + '}br')
        t = E.SubElement(run, '{' + W + '}t')
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = line

def _layout_paragraph(p, value):
    runs = p.findall('w:r', N)
    if runs:
        r = runs[0]
        for extra in runs[1:]:
            p.remove(extra)
    else:
        r = E.SubElement(p, '{' + W + '}r')
        style = p.find('w:pPr/w:rPr', N)
        if style is not None:
            r.append(deepcopy(style))
    _layout_run_text(r, value)

def _layout_row_prop(row, name):
    p = row.find('w:trPr', N)
    if p is None:
        p = E.Element('{' + W + '}trPr')
        row.insert(0, p)
    if p.find('w:' + name, N) is None:
        E.SubElement(p, '{' + W + '}' + name)

def _layout_assert_protected(original, filled, kind):
    a = _layout_doc(original).findall('w:body/w:p', N)
    b = _layout_doc(filled).findall('w:body/w:p', N)
    _layout_need(len(a) == len(b))
    mutable = {2, 3, 4, 7, 8, 9, 11} if kind == 'application' else set()
    for i in range(len(a)):
        if i not in mutable:
            _layout_need(E.tostring(a[i]) == E.tostring(b[i]))

def _layout_fill(raw, kind, data):
    _layout_inspect(raw, kind)
    active = any((any(row.values()) for row in data['evidenceList'])) if kind == 'evidence' else any((value for key, value in data.items() if key != 'requests')) or any(data['requests'])
    if not active:
        return raw
    d = _layout_doc(raw)
    ps = d.findall('w:body/w:p', N)
    if kind == 'application':
        for i, key, label in [(2, 'applicantName', '申请人：'), (3, 'agentName', '委托代理人：'), (4, 'respondentName', '被申请人：')]:
            if data[key]:
                _layout_paragraph(ps[i], label + data[key])
        for i, value in enumerate(data['requests']):
            if value:
                _layout_run_text(ps[7 + i].findall('w:r', N)[1], value)
        if data['factsReason']:
            _layout_paragraph(ps[11], data['factsReason'])
    else:
        table = d.find('.//w:tbl', N)
        rows = table.findall('w:tr', N)
        items = [row for row in data['evidenceList'] if any(row.values())]
        _layout_row_prop(rows[0], 'tblHeader')
        for row in rows[1 + len(items):-1]:
            table.remove(row)
        rows = table.findall('w:tr', N)
        for i, row in enumerate(rows[1:-1]):
            _layout_row_prop(row, 'cantSplit')
            for cell, value in zip(row.findall('w:tc', N), [str(i + 1), *[items[i][k] for k in ['name', 'pageCount', 'originalType', 'purpose', 'pageRange']]]):
                _layout_paragraph(cell.find('w:p', N), value)
        pages = str(sum((int(r['pageCount']) for r in items))) if all((r['pageCount'] for r in items)) else '____'
        _layout_paragraph(rows[-1].find('w:tc/w:p', N), f'以上证据材料合计 {len(items)}份（组） {pages}页')
    xml = E.tostring(d, encoding='UTF-8', xml_declaration=True, standalone=True)
    out = BytesIO()
    with ZipFile(BytesIO(raw)) as source, ZipFile(out, 'w') as target:
        for member in source.infolist():
            target.writestr(member, xml if member.filename == 'word/document.xml' else source.read(member.filename))
    result = out.getvalue()
    _layout_assert_protected(raw, result, kind)
    return result
import json, re
from pathlib import Path, PurePosixPath, PureWindowsPath
TEMPLATES = {'application': {'file': 'application-own-format.docx', 'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86', 'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365', 'row': 1}, 'evidence': {'file': 'evidence-list-own-format.docx', 'file_id': 'CC300F5D9DD5DC404D65C68116D50C55', 'sha256': 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815', 'row': 2}}
APP = ('applicantName', 'agentName', 'respondentName', 'requests', 'factsReason')
ITEM = ('name', 'pageCount', 'originalType', 'purpose', 'pageRange')

def exact(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(b, dict):
        return a.keys() == b.keys() and all((exact(a[k], v) for k, v in b.items()))
    if isinstance(b, list):
        return len(a) == len(b) and all((exact(x, y) for x, y in zip(a, b)))
    return a == b

def path_at(root, relative):
    require(root is not None and str(root).strip())
    base = Path(root).resolve()
    rel = Path(relative)
    require(not rel.is_absolute() and (not rel.drive) and ('..' not in rel.parts))
    windows = PureWindowsPath(relative)
    posix = PurePosixPath(relative)
    require(not windows.drive and not windows.root and not posix.is_absolute() and ('..' not in windows.parts) and ('..' not in posix.parts))
    path = base / rel
    require(path.resolve().is_relative_to(base) and path.resolve().relative_to(base).as_posix() == rel.as_posix() and (not path.is_symlink()))
    return path

def _raw(root, relative):
    try:
        return path_at(root, relative).read_bytes()
    except OSError as error:
        raise ValueError('Explicit own standalone source unavailable') from error

def _json(root, relative):
    return json.loads(_raw(root, relative))

def _code(code):
    require(type(code) is str and code in REGIONS)
    return REGIONS[code]

def _kind(kind):
    require(type(kind) is str and kind in TEMPLATES)
    return TEMPLATES[kind]

def defaults(code, kind):
    _code(code)
    _kind(kind)
    return {'applicantName': '', 'agentName': '', 'respondentName': '', 'requests': [''], 'factsReason': ''} if kind == 'application' else {'evidenceList': [{key: '' for key in ITEM}]}

def form_fields(code, kind):
    _code(code)
    _kind(kind)
    labels = {'applicantName': '申请人', 'agentName': '委托代理人', 'respondentName': '被申请人', 'factsReason': '事实与理由', 'name': '证据名称', 'pageCount': '页数', 'originalType': '原件/复印件', 'purpose': '证明对象', 'pageRange': '页码'}

    def field(key, size):
        return {'key': key, 'label': labels[key], 'type': 'text', 'maxLength': size, 'nullable': False}
    return [field('applicantName', 180), field('agentName', 180), field('respondentName', 180), {'key': 'requests', 'label': '仲裁请求', 'type': 'text_list', 'maxItems': 3, 'maxLength': 360}, field('factsReason', 2400)] if kind == 'application' else [{'key': 'evidenceList', 'label': '证据清单', 'type': 'object_list', 'maxItems': 9, 'fields': [field(key, {'name': 60, 'pageCount': 4, 'originalType': 4, 'purpose': 80, 'pageRange': 32}[key]) for key in ITEM]}]

def schema_descriptor(code, kind):
    _code(code)
    _kind(kind)
    return {'schema_id': 'fujian-n-' + code + '-' + kind + '-v1', 'schema_version': 1, 'region_code': code, 'source_id': REGIONS[code]['source_id'], 'source_version': SOURCE_SHAS[code], 'fields': form_fields(code, kind), 'defaults': defaults(code, kind), 'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'capacity_is_official_requirement': False, 'capacity_is_legal_requirement': False, 'trim_text': True, 'text_controls': 'newline_only', 'committee_date_signature_copies_fields': 'not accepted'}}

def _normal_example_data(code, kind):
    d = _code(code)['district']
    _kind(kind)
    return {'applicantName': '虚构' + d + '申请人甲（仅测试）', 'agentName': '', 'respondentName': '虚构' + d + '乙公司（仅测试）', 'requests': ['虚构请求，仅验证自身候选映射，不提出真实申请。'], 'factsReason': '所有内容均为虚构，不涉及真实案件或当事人。'} if kind == 'application' else {'evidenceList': [{'name': '虚构' + d + '材料甲', 'pageCount': '1', 'originalType': '复印件', 'purpose': '虚构测试，仅核对候选表格。', 'pageRange': '1'}]}

def envelope(code, kind, data, *, root):
    identity, pin, _, *_ = _source(code, root)
    t = _kind(kind)
    s = schema_descriptor(code, kind)
    return {**{k: v for k, v in identity.items() if k not in {'folder','observed_at_utc'}}, 'source_version': pin['source_manifest_sha256'], 'material_id': None, 'local_material_key': identity['source_id'] + ':dom-material:' + str(t['row']), 'template_id': t['file_id'], 'template_sha256': t['sha256'], 'template_version': 'sha256:' + t['sha256'], 'schema_id': s['schema_id'], 'schema_version': 1, 'schema_sha256': sha256(json.dumps(s, ensure_ascii=False, sort_keys=True).encode()).hexdigest(), 'kind': kind, 'mode': 'blank', 'data': deepcopy(data)}

def _text(value, capacity):
    require(type(value) is str and len(value) <= capacity and all((c == '\n' or 32 <= ord(c) <= 55295 or 57344 <= ord(c) <= 65533 or (65536 <= ord(c) <= 1114111) for c in value)))
    return value.strip()

def validate_request(payload, *, root):
    require(type(payload) is dict)
    code = payload.get('region_code')
    kind = payload.get('kind')
    expected = envelope(code, kind, {}, root=root)
    require(payload.keys() == expected.keys() and all((exact(payload[k], v) for k, v in expected.items() if k != 'data')))
    data = payload['data']
    require(type(data) is dict)
    if kind == 'application':
        require(not set(data) - set(APP))
        out = {k: '' for k in APP if k != 'requests'}
        out['requests'] = []
        for key, value in data.items():
            if key == 'requests':
                require(type(value) is list and len(value) <= 3)
                out[key] = [_text(x, 360) for x in value]
            else:
                out[key] = _text(value, 2400 if key == 'factsReason' else 180)
    else:
        require(not set(data) - {'evidenceList'})
        rows = data.get('evidenceList', [])
        require(type(rows) is list and len(rows) <= 9)
        out = {'evidenceList': []}
        for row in rows:
            require(type(row) is dict and (not set(row) - set(ITEM)))
            item = {key: '' for key in ITEM}
            for key, value in row.items():
                item[key] = _text(value, {'name': 60, 'pageCount': 4, 'originalType': 4, 'purpose': 80, 'pageRange': 32}[key])
            require(item['originalType'] in {'', '原件', '复印件'} and (not item['pageCount'] or re.fullmatch('[1-9][0-9]{0,3}', item['pageCount'])))
            out['evidenceList'].append(item)
    return (code, kind, out)

def original_bytes(code, kind, *, root):
    _, _, base, *_ = _source(code, root)
    return _raw(root, base / _kind(kind)['file'])

def inspect_blank(code, kind, *, root):
    return _layout_inspect(original_bytes(code, kind, root=root), kind)
_METADATA = {'version', 'region_id', 'content_hash'}

def _source_projection_evidence(canonical):
    require(type(canonical) is dict)
    code = canonical.get('region_code')
    require(type(code) is str and code in REGIONS)
    require(type(canonical.get('source_version')) is str and canonical['source_version'] == SOURCE_SHAS[code])
    return {'source_projection': (SOURCE_BASE / REGIONS[code]['folder'] / 'SOURCE-PROJECTION-MANIFEST.json').as_posix(),
            'source_projection_sha256': canonical['source_version']}


def _matches(guide, canonical):
    if type(guide) is not dict:
        return False
    if 'evidence' in guide:
        try:
            expected_evidence = _source_projection_evidence(canonical)
        except (ValueError, KeyError, TypeError):
            return False
        if not exact(guide['evidence'], expected_evidence):
            return False
        guide = {key: value for key, value in guide.items() if key != 'evidence'}
    if set(guide) - set(canonical) - _METADATA:
        return False
    if 'version' in guide and (type(guide['version']) is not int or guide['version'] < 1):
        return False
    region_id = sha256(json.dumps([canonical[key] for key in ['province', 'city', 'district']], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
    if 'region_id' in guide and guide['region_id'] != region_id:
        return False
    if 'content_hash' in guide and (type(guide['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}', guide['content_hash'])):
        return False
    return all((key in guide and exact(guide[key], value) for key, value in canonical.items()))
SOURCE_BASE=Path('reports/overnight-gap-closure-20261030/localities/fujian-n-source-projection')
ADAPTER='fujian_putian_licheng_xiuyu_own_blank_oct31n_v1'
WORD_SHA='d69237a1afedf9eecf5fc8e66d539bb9e3bfe4e3678ed15856b891c2b8edae37'
STAGE_SHA256='1defd082be8040f33ae560c94124411bbac4b122af86fa83e7c71c6a33ab6908'
PUBLICATION_SHA256='38658d121da435652f0a79adee3048a14e189f293dac9bc47717eb70bf9444ac'
REGIONS={'350304': {'folder': 'licheng-350304', 'province': 'fujian', 'city': '莆田市', 'district': '荔城区', 'region_code': '350304', 'source_id': 'c2f441391f073f71f55ce9de', 'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=BDE5EC9DAD4CFE0ADED039A84F96B29B&infoType=1', 'service_code': '113503210037128046400201430200Y01', 'observed_at_utc': '2026-10-31T05:11:03.027Z', 'authority': '莆田市荔城区人力资源和社会保障局'}, '350305': {'folder': 'xiuyu-350305', 'province': 'fujian', 'city': '莆田市', 'district': '秀屿区', 'region_code': '350305', 'source_id': '758cc6043c5d57e5574a766e', 'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=EC90D061D8C4ECCCBF8F1E48EE8693E8&infoType=1', 'service_code': '1135030448877165XX400201430200Y01', 'observed_at_utc': '2026-10-31T05:14:13.731Z', 'authority': '莆田市秀屿区人力资源和社会保障局'}}
SOURCE_SHAS={'350304': 'd14f537bfd0137533112f380bf3e162f0207e23fe5aef75510db1a914a00cb91', '350305': '9e3b53ede88fc12346504c94725d6a7987b8f263ac3caf3df51a1b1e2b11c96f'}
_METADATA={'version','region_id','content_hash'}
LEAVES={'OWN-SOURCE.json','own-materials-native-dom.json','own-official-bindings.json','OOXML-CONTENT-AUDIT.json','SOURCE-QUALIFICATIONS.json','SOURCE-LINEAGE.json','application-own-format.docx','evidence-list-own-format.docx'}

def require(ok):
    if not ok:
        raise ValueError('Own N source/schema/canonical boundary refused')


def _source(code, root):
    identity = _code(code)
    base = SOURCE_BASE / identity['folder']
    raw = _raw(root, base / 'SOURCE-PROJECTION-MANIFEST.json')
    require(sha256(raw).hexdigest() == SOURCE_SHAS[code])
    manifest = json.loads(raw)
    require(manifest['schema'] == 'private-putian-lx-own-safe-projection-v1'
            and set(manifest['files']) == LEAVES)
    require(all(exact(manifest[key], value) for key, value in identity.items() if key != 'folder'))
    require(sha256(json.dumps(identity['source_url'], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24] == identity['source_id'])
    require(manifest['official_material_IDs'] is None and manifest['committee_full_name'] is None
            and manifest['official_version'] is None and manifest['private_parent_runtime_dependency'] is False
            and manifest['can_generate'] is False and manifest['published'] is False
            and manifest['Word_approval'] is None and manifest['stage_approval'] is None
            and manifest['publication_approval'] is None)
    for name, leaf in manifest['files'].items():
        body = _raw(root, base / name)
        require(type(leaf['bytes']) is int and len(body) == leaf['bytes']
                and sha256(body).hexdigest() == leaf['sha256'])
    own = _json(root, base / 'OWN-SOURCE.json')
    dom = _json(root, base / 'own-materials-native-dom.json')
    q = _json(root, base / 'SOURCE-QUALIFICATIONS.json')
    bound = _json(root, base / 'own-official-bindings.json')
    audits = _json(root, base / 'OOXML-CONTENT-AUDIT.json')
    for obj in [own, q, bound]:
        require(obj['source_id'] == identity['source_id'] and obj['source_url'] == identity['source_url'])
    require(dom['url'] == identity['source_url'] and own['region_code'] == code
            and own['service_code'] == identity['service_code']
            and own['authority'].strip() == identity['authority']
            and own['observed_at_utc'] == identity['observed_at_utc']
            and own['collected_at'] == own['observed_at_utc']
            and own['verified_at'] == own['observed_at_utc']
            and own['official_version'] is None and own['committee_name'] is None
            and own['private_parent_runtime_dependency'] is False and own['can_generate'] is False
            and own['generation_permission'] is None and own['stage_approval'] is None
            and own['publication_approval'] is None)
    capture_sha = sha256(_raw(root, base / 'own-materials-native-dom.json')).hexdigest()
    for name, field in own['fields'].items():
        pointer = re.fullmatch(r'tables\[(\d+)\]\[(\d+)\]\[(\d+)\]', field['source_pointer'])
        require(pointer is not None)
        table, row, cell = map(int, pointer.groups())
        require(field['raw_value'] == dom['tables'][table][row][cell]
                and field['raw_label'] == dom['tables'][table][row][cell - 1]
                and field['raw_label'].strip().rstrip('：:') == name
                and field['normalized_value'] is None
                and field['source_id'] == identity['source_id'] and field['source_url'] == identity['source_url']
                and field['region_code'] == code and field['capture_file'] == 'own-materials-native-dom.json'
                and field['capture_sha256'] == capture_sha and field['verification_status'] == 'observed_unverified')
    boundary = q['online_boundary']
    require(boundary['origin_path'] == 'https://iam.e-govt.cn:8901/login'
            and boundary['login_marker'] is True and boundary['query_retained'] is False
            and boundary['login_attempted'] is False and boundary['QR_scanned'] is False
            and boundary['application_submitted'] is False and q['online_entry'] is None
            and q['visit_scope_relationship'] == 'compatible_different_scopes'
            and q['own_visit_badge_raw'] in dom['raw_public_text']
            and q['generic_II_raw'] in dom['raw_public_text'] and q['operational_issue_events'] == [])
    materials = own['materials']
    require(len(materials) == 3)
    for index, material in enumerate(materials, 1):
        pointer = re.fullmatch(r'tables\[(\d+)\]', material['source_pointer'])
        require(pointer is not None)
        rows = dom['tables'][int(pointer[1])]
        require(material['raw_fields'] == {row[0]: row[1] for row in rows if len(row) == 2}
                and material['source_id'] == identity['source_id'] and material['source_url'] == identity['source_url']
                and material['capture_sha256'] == capture_sha and material['official_material_id'] is None
                and material['legal_default_copies'] is None
                and material['local_material_key'] == identity['source_id'] + ':dom-material:' + str(index)
                and material['local_key_kind'] == 'local_source_row_pointer_not_official_ID')
    attachments = bound['attachments']
    require(len(attachments) == 6 and len({a['public_file_unid'] for a in attachments}) == 6
            and bound['same_bytes_grant_other_source_authority'] is False)
    for attachment in attachments:
        require(attachment['source_id'] == identity['source_id'] and attachment['source_url'] == identity['source_url']
                and attachment['region_code'] == code and attachment['official_material_id'] is None
                and attachment['can_generate'] is False and attachment['generation_permission'] is None
                and attachment['TLS_verify'] is True and attachment['auth_supplied'] is False
                and attachment['native_http_status'] == 200 and attachment['http_status'] == 200
                and attachment['public_download_url'] == 'https://zwfw.fujian.gov.cn:732/cms-business/apasService/file/downloadFileStream?unid=' + attachment['public_file_unid'])
        kind = attachment['eligible_own_kind']
        if kind is None:
            require(attachment['local_original'] is None and attachment['content_role'] in
                    {'scanning_instruction_NOT_blank_template', 'official_SAMPLE_NOT_blank_template'})
        else:
            template = _kind(kind)
            require(attachment['official_control_type'] == 'format'
                    and attachment['public_file_unid'] == template['file_id']
                    and attachment['local_original'] == template['file']
                    and attachment['sha256'] == template['sha256'])
            original = _raw(root, base / template['file'])
            require(sha256(original).hexdigest() == template['sha256'])
            inspection = _layout_inspect(original, kind)
            require(inspection['member_sha256'] == audits[attachment['role']]['all_ZIP_members'])
    require(sum(a['eligible_own_kind'] is not None for a in attachments) == 2)
    require(all(value in dom['raw_public_text'] for value in own['sections'].values()))
    return identity, {'source_manifest_sha256': SOURCE_SHAS[code]}, base, own, materials, attachments, q, audits


def source_files(root, code=None):
    result = []
    for code in REGIONS if code is None else [code]:
        _, _, base, *_ = _source(code, root)
        result.extend([(base / 'SOURCE-PROJECTION-MANIFEST.json').as_posix(),
                       *[(base / name).as_posix() for name in sorted(LEAVES)]])
    return result


def parse_capture(code, *, root):
    identity, pin, base, own, materials, attachments, q, _ = _source(code, root)
    fields = deepcopy(own['fields'])
    for field in fields.values():
        field['capture_file'] = (base / field['capture_file']).as_posix()
        field['source_version'] = SOURCE_SHAS[code]
        field['collected_at'] = field['observed_at_utc']
        field['verified_at'] = field['observed_at_utc']
    for display, raw in {'承诺办结时限': '承诺时限', '法定办结时限': '法定时限',
                         '咨询方式': '联系电话', '必须到现场原因': '必须现场办理原因', '服务对象': '申报对象'}.items():
        fields[display] = deepcopy(fields[raw])
    dom = _json(root, base / 'own-materials-native-dom.json')
    def additional(label, value, pointer):
        fields[label] = {**deepcopy(fields['承诺时限']), 'raw_value': value,
                         'source_pointer': pointer}
    fees = [(ti, ri, row[1]) for ti, table in enumerate(dom['tables'])
            for ri, row in enumerate(table) if len(row) == 2 and row[0] == '是否收费：']
    require(len(fees) == 1 and fees[0][2] == own['fee_raw'])
    ti, ri, value = fees[0]
    additional('是否收费', value, f'tables[{ti}][{ri}][1]')
    text = dom['raw_public_text']
    badge = q['own_visit_badge_raw']
    start = text.index(badge)
    additional('到办事现场次数', badge.split('\n')[1], f'raw_public_text@{start}:{start + len(badge)}')
    for label in ['办理时间', '办理地点', '交通指引']:
        matches = list(re.finditer(r'(?:^|\n)' + label + '：([^\n]+)', text))
        require(len(matches) == 1)
        match = matches[0]
        additional(label, match[1], f'raw_public_text@{match.start(1)}:{match.end(1)}')
    templates = [{**deepcopy(a), 'id': a['public_file_unid'], 'material_id': None,
                  'file': (base / a['local_original']).as_posix() if a['local_original'] else None,
                  'download_url': a['public_download_url'],
                  'download_status': 'downloaded' if a['local_original'] else 'metadata_only',
                  'official_kind': a['official_control_type'], 'original_name': a['official_label'],
                  'document_types': []} for a in attachments]
    display_materials = [{**deepcopy(m), 'id': m['local_material_key'],
                          'id_kind': 'local_source_row_pointer_not_official_ID', 'material_id': None,
                          'copies': m['copies_raw'], 'instructions': m['raw_fields'].get('填报须知', ''),
                          'format': m['raw_fields'].get('材料形式', ''),
                          'required': m['raw_fields'].get('材料必要性', '')} for m in materials]
    return {**{key: value for key, value in identity.items() if key != 'folder'},
            'collected_at': own['observed_at_utc'], 'verified_at': own['observed_at_utc'],
            'service_name': own['service_name'], 'source_version': pin['source_manifest_sha256'],
            'fields': fields, 'sections': deepcopy(own['sections']), 'materials': display_materials,
            'templates': templates, 'qualifications': q, 'committee_full_name': None,
            'committee_autofill_allowed': False, 'official_version': None,
            'channel': {'online_status': 'auth_required', 'entry_url': None,
                        'entry_check': {'status': 'native_auth_boundary_observed'}, 'submission_verified': False},
            'guide_status': 'partial', 'verification_status': 'partial', 'source_review': 'PENDING_ROOT',
            'Word_visual_review': 'NOT_RUN', 'publication_status': 'unregistered_source_proposal',
            'generation_permission': None, 'generation_adapter': None, 'can_generate': False, 'published': False}


def prepare_candidate(code, *, root):
    guide = parse_capture(code, root=root)
    guide.update(offline_candidate=True, generation_adapter=ADAPTER)
    return guide


def example_data(code, kind, stress=False, *, root):
    _source(code, root)
    _kind(kind)
    require(type(stress) is bool)
    if not stress:
        return _normal_example_data(code, kind)
    district = REGIONS[code]['district']
    def bounded(prefix, unit, capacity):
        return (prefix + unit * capacity)[:capacity]
    if kind == 'application':
        return {'applicantName': bounded('虚构' + district + '申请人：', '甲', 180),
                'agentName': bounded('虚构' + district + '代理人：', '乙', 180),
                'respondentName': bounded('虚构' + district + '公司：', '丙', 180),
                'requests': [bounded('虚构请求' + str(i + 1) + '：', '仅测试自身格式，不提出真实申请。', 360) for i in range(3)],
                'factsReason': bounded('虚构' + district + '事实：\n', '仅测试自身空表技术容量，不涉及真实当事人或争议。\n', 2400)}
    return {'evidenceList': [{'name': bounded('虚构' + district + '证据' + str(i + 1) + '：', '测试', 60),
                             'pageCount': str(i + 1), 'originalType': '复印件' if i % 2 == 0 else '原件',
                             'purpose': bounded('虚构证明对象：', '仅为自身表格测试，不是实际证据。', 80),
                             'pageRange': bounded('虚构页码：', '示例', 32)} for i in range(9)]}


def candidate_fill(payload, *, root, private_review=False):
    if private_review is not True:
        raise PermissionError('Private synthetic review only; no generation approval')
    code, kind, data = validate_request(payload, root=root)
    return _layout_fill(original_bytes(code, kind, root=root), kind, data)


def with_capabilities(guide, *, root):
    _bound(guide, root, allow_source=True)
    return deepcopy(guide)


def staged_candidate(code, *, root):
    guide = prepare_candidate(code, root=root)
    guide['candidate_adapter_evidence'] = _receipt(root)
    guide.update(can_generate=True, offline_candidate=False, publication_status='staged_own_word_qa')
    for kind, template in TEMPLATES.items():
        row = next(row for row in guide['templates'] if row['id'] == template['file_id'])
        require(row['eligible_own_kind'] == kind and row['local_original'] == template['file'])
        row.update(can_generate=True, document_types=[kind], adapter=ADAPTER,
                   generation_mode='blank', official_kind='blank')
    return guide


def with_publication_evidence(guide, *, root):
    require(type(guide) is dict and _matches(guide, staged_candidate(guide.get('region_code'), root=root)))
    result = _published(guide['region_code'], root)
    for key in _METADATA & set(guide):
        result[key] = deepcopy(guide[key])
    return result


def checked_adapter(guide, template, kind, *, root):
    canonical = _bound(guide, root)
    own_template = _kind(kind)
    expected = next(row for row in canonical['templates'] if row['id'] == own_template['file_id'])
    require(exact(template, expected) and expected['can_generate'] is True
            and expected['official_kind'] == 'blank' and expected['eligible_own_kind'] == kind
            and expected['generation_mode'] == 'blank')
    return ADAPTER


QA_REPORT = 'reports/overnight-gap-closure-20261030/localities/fujian-n/integration-qa-v1'
WORD_MANIFEST = QA_REPORT + '/WORD-MANIFEST.json'
STAGE_RECEIPT = QA_REPORT + '/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT = QA_REPORT + '/FINAL-BROWSER-QA.json'
_FAILURES = (ValueError, OSError, KeyError, TypeError, AttributeError, StopIteration)


def template_path(code, kind, *, root):
    _, _, base, *_ = _source(code, root)
    return path_at(root, base / _kind(kind)['file'])


def approval_requirements(*, stage=True):
    result = {'identities': [{**{key: identity[key] for key in ['region_code', 'source_id', 'service_code']},
                             'manifest_sha256': SOURCE_SHAS[code]} for code, identity in REGIONS.items()],
              'word_manifest_sha256': WORD_SHA, 'eligible_originals': 4,
              'approved_by': 'independent_root', 'visual_review': 'PASS',
              'source_projection_review': 'PASS', 'can_publish': not stage, 'model_calls': 0}
    if not stage:
        result.update(stage_receipt_sha256=STAGE_SHA256, native_confirmation_download_own_forms=True)
    return result


def _word_manifest(root):
    require(type(WORD_SHA) is str and re.fullmatch('[a-f0-9]{64}', WORD_SHA))
    raw = _raw(root, WORD_MANIFEST)
    require(sha256(raw).hexdigest() == WORD_SHA)
    word = json.loads(raw)
    require(exact(word['source_versions'], SOURCE_SHAS) and word['eligible_originals'] == 4
            and word['fictional_fixtures'] == 8 and word['word_documents'] == 12
            and word['original_pages'] == 6 and word['generated_pages'] == 42
            and word['logical_visual_pages'] == 48 and word['stage_approved'] is False
            and word['can_publish'] is False and word['actual_new_safe_projection_regeneration'] is True
            and word['same_requests_as_frozen_public_context_queue'] is True)
    require(type(word['files']) is list and len(word['files']) == 72
            and len({leaf['path'] for leaf in word['files']}) == 72)
    expected = {QA_REPORT + '/' + name for name in
                ['README.md', 'ROOT-VISUAL-REVIEW.json', 'ROOT-PAGE-REVIEW-INDEX.json', 'SOURCE-WORD-PARITY.json']}
    for code in REGIONS:
        for kind in TEMPLATES:
            for scenario in ['original', 'normal', 'stress']:
                expected.add(f'{QA_REPORT}/word/{code}-{scenario}-{kind}.docx')
                if scenario != 'original':
                    expected.add(f'{QA_REPORT}/fixtures/{code}-{scenario}-{kind}.json')
    actual = {leaf['path'] for leaf in word['files']}
    pages = actual - expected
    require(len(pages) == 48 and expected <= actual
            and all(re.fullmatch(re.escape(QA_REPORT) + r'/pages/(350304|350305)-(application|evidence)-(original|normal|stress)-[1-9][0-9]*\.png', path) for path in pages))
    for leaf in word['files']:
        require(type(leaf['path']) is str and leaf['path'].startswith(QA_REPORT + '/'))
        body = _raw(root, leaf['path'])
        require(type(leaf['bytes']) is int and len(body) == leaf['bytes']
                and sha256(body).hexdigest() == leaf['sha256'])
    for code in REGIONS:
        for kind in TEMPLATES:
            for stress, scenario in [(False, 'normal'), (True, 'stress')]:
                fixture = _json(root, f'{QA_REPORT}/fixtures/{code}-{scenario}-{kind}.json')
                require(exact(fixture, envelope(code, kind, example_data(code, kind, stress, root=root), root=root)))
                validate_request(fixture, root=root)
    return word


def _receipt(root, stage=True):
    pin = STAGE_SHA256 if stage else PUBLICATION_SHA256
    require(type(pin) is str and re.fullmatch('[a-f0-9]{64}', pin))
    source_files(root)
    word = _word_manifest(root)
    if not stage:
        _receipt(root, True)
    filename = STAGE_RECEIPT if stage else PUBLICATION_RECEIPT
    raw = _raw(root, filename)
    require(sha256(raw).hexdigest() == pin)
    receipt = json.loads(raw)
    require(all(key in receipt and exact(receipt[key], value)
                for key, value in approval_requirements(stage=stage).items()))
    require(type(receipt['files']) is list and receipt['files']
            and len({leaf['path'] for leaf in receipt['files']}) == len(receipt['files']))
    if stage:
        require(exact(receipt['files'], word['files']))
    else:
        final = {leaf['path']: leaf for leaf in receipt['files']}
        require(all(leaf['path'] in final and exact(final[leaf['path']], leaf) for leaf in word['files']))
    for leaf in receipt['files']:
        require(type(leaf['path']) is str and leaf['path'].startswith(QA_REPORT + '/'))
        body = _raw(root, leaf['path'])
        require(type(leaf['bytes']) is int and len(body) == leaf['bytes']
                and sha256(body).hexdigest() == leaf['sha256'])
    return {'receipt': filename, 'sha256': pin}


def _published(code, root):
    guide = staged_candidate(code, root=root)
    guide['publication_adapter_evidence'] = _receipt(root, False)
    guide.update(published=True, publication_status='published')
    return guide


def _bound(guide, root, allow_source=False):
    require(type(guide) is dict)
    raw = parse_capture(guide.get('region_code'), root=root)
    if allow_source and _matches(guide, raw):
        return raw
    canonical = _published(guide['region_code'], root) if guide.get('published') is True or 'publication_adapter_evidence' in guide else staged_candidate(guide['region_code'], root=root)
    require(_matches(guide, canonical))
    return canonical


def public_evidence(guide, root):
    try:
        canonical = _bound(guide, root, allow_source=True)
        return _source_projection_evidence(canonical)
    except _FAILURES:
        return None


def approved_report_attachment(guide, template, root):
    try:
        return any(exact(row, template) and row['download_status'] == 'downloaded'
                   and row['local_original'] is not None
                   for row in _bound(guide, root, allow_source=True)['templates'])
    except _FAILURES:
        return False


class _PatchedDocument:
    def __init__(self, body, root):
        self.body, self.root = body, Path(root).resolve()

    def save(self, destination):
        if hasattr(destination, 'write'):
            destination.write(self.body)
            return
        path = Path(destination).resolve()
        require(not path.is_relative_to(self.root / 'reports'))
        path.write_bytes(self.body)


def fill_document(guide, template, kind, path, data, *, root):
    checked_adapter(guide, template, kind, root=root)
    require(Path(path).resolve() == template_path(guide['region_code'], kind, root=root))
    request = envelope(guide['region_code'], kind, data, root=root)
    return _PatchedDocument(candidate_fill(request, root=root, private_review=True), root)
