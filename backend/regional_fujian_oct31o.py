"""UNREGISTERED private formal-root O provider proposal; no approved phase."""
'Locality-free OOXML mechanics; caller must validate its own complete source.'
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from pathlib import PureWindowsPath, PurePosixPath
from lxml import etree as E
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
N = {'w': W}

def _layout_need(ok):
    if not ok:
        raise ValueError('Own blank OOXML shape differs')

def _layout_doc(raw):
    with ZipFile(BytesIO(raw)) as z:
        _layout_need(z.testzip() is None)
        _layout_need(len(z.namelist()) == len(set(z.namelist())))
        for name in z.namelist():
            _layout_need(not PureWindowsPath(name).drive and (not PureWindowsPath(name).root) and (not PurePosixPath(name).is_absolute()) and ('..' not in PurePosixPath(name).parts) and ('\\' not in name))
            _layout_need(not name.lower().endswith(('vbaproject.bin', '.exe', '.dll')) and (not name.lower().startswith('word/embeddings/')))
            if name.endswith('.rels'):
                rels = E.fromstring(z.read(name), E.XMLParser(resolve_entities=False, no_network=True))
                _layout_need(all((r.get('TargetMode', '').lower() != 'external' for r in rels)))
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
'PRIVATE unregistered own-source parser and review-only mapping proposal.'
from pathlib import Path, PureWindowsPath, PurePosixPath
from copy import deepcopy
from hashlib import sha256
import json, re
SOURCE_BASE = PurePosixPath('reports/overnight-gap-closure-20261030/localities/fujian-o-source-projection')
SOURCE_PINS_SHA256 = '820c0c2c4611295b8de3f56ad431b1450aae690bfd1a447ef6d2c8cf8f50108e'
WORD_SHA256 = '96a4aba0d8a128e5b38611a408b69732c3826678b151092b896eb9ec3638e428'
STAGE_SHA256 = 'f811a04bedd3abaa43b07f845b6374874e5ea90bb8024eb27a5dd615ac0409d2'
PUBLICATION_SHA256 = None
REGIONS = {'350322': ('xianyou-350322', '6918d8e34e1206673434fbc9', '113503220037190969400201430200Y01', 'https://iam.e-govt.cn:8901/login'), '350502': ('quanzhou-licheng-350502', 'c95aa7b9d6cf3798036de103', '113505020038190387400201430200201', 'https://fjzc.fjzhkj.cn:7881/')}
KINDS = {'application': ('application-format.docx', 'F4048D8C91E2FF882AC6C62CC0EC4D86', '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365', 1), 'evidence': ('evidence-list-format.docx', 'CC300F5D9DD5DC404D65C68116D50C55', 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815', 2)}
LEAVES = {'own-guide.json', 'own-materials-native-dom.json', 'attachments.json', 'qualifications.json', 'source-lineage.json', 'own-layout.json', 'application-format.docx', 'evidence-list-format.docx'}
APP = ('applicantName', 'agentName', 'respondentName', 'requests', 'factsReason')
ITEM = ('name', 'pageCount', 'originalType', 'purpose', 'pageRange')

def require(ok):
    if not ok:
        raise ValueError('Own source/proposal binding refused')

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
    require(isinstance(relative, (str, PurePosixPath, PureWindowsPath, Path)))
    native = str(relative)
    w = PureWindowsPath(native)
    p = PurePosixPath(native)
    require(not w.drive and (not w.root) and (not p.is_absolute()))
    text = relative.as_posix() if isinstance(relative, (PurePosixPath, PureWindowsPath, Path)) else native
    w = PureWindowsPath(text)
    p = PurePosixPath(text)
    require(bool(text) and (not w.drive) and (not w.root) and (not p.is_absolute()) and ('\\' not in text) and (':' not in text) and (not any((c in text for c in '\x00\r\n'))) and all((part not in {'', '.', '..'} for part in text.split('/'))))
    base = Path(root).resolve()
    current = base
    for part in p.parts:
        current = current / part
        require(not current.is_symlink())
    require(current.resolve().is_relative_to(base) and current.resolve().relative_to(base).as_posix() == text)
    return current

def _raw(root, relative):
    try:
        return path_at(root, relative).read_bytes()
    except OSError as error:
        raise ValueError('Explicit own source unavailable') from error

def _json(root, relative):
    try:
        return json.loads(_raw(root, relative))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Own JSON invalid') from error

def _code(code):
    require(type(code) is str and code in REGIONS)
    return REGIONS[code]

def _kind(kind):
    require(type(kind) is str and kind in KINDS)
    return KINDS[kind]

def _source(code, root):
    own = _code(code)
    body = _raw(root, SOURCE_BASE / 'OWN-SOURCE-PINS.json')
    require(sha256(body).hexdigest() == SOURCE_PINS_SHA256)
    pin = json.loads(body)[code]
    identity = pin['identity']
    base = SOURCE_BASE / own[0]
    require(pin['folder'] == own[0] and identity['source_id'] == own[1] and (identity['service_code'] == own[2]) and (identity['region_code'] == code))
    raw = _raw(root, base / 'SOURCE-PROJECTION-MANIFEST.json')
    require(sha256(raw).hexdigest() == pin['source_manifest_sha256'])
    manifest = json.loads(raw)
    require(manifest['schema'] == 'two-own-source-projection-proposal-v1' and set(manifest['files']) == LEAVES and (manifest['can_generate'] is False) and (manifest['approval'] is None) and (manifest['private_parent_runtime_fallback'] is False))
    for key in ['source_id', 'source_url', 'region_code', 'service_code', 'observed_at_utc']:
        require(manifest[key] == identity[key])
    require(manifest['authority'].strip() == identity['authority'])
    for name, leaf in manifest['files'].items():
        b = _raw(root, base / name)
        require(type(leaf['bytes']) is int and len(b) == leaf['bytes'] and (sha256(b).hexdigest() == leaf['sha256']))
    g = _json(root, base / 'own-guide.json')
    dom = _json(root, base / 'own-materials-native-dom.json')
    attachments = _json(root, base / 'attachments.json')
    audit = _json(root, base / 'own-layout.json')
    q = _json(root, base / 'qualifications.json')
    lineage = _json(root, base / 'source-lineage.json')
    for key, value in identity.items():
        require(g[key].strip() == value if key == 'authority' else g[key] == value)
    require(g['collected_at'] == g['observed_at_utc'] == g['verified_at'] and g['guide_status'] == 'partial' and (g['can_generate'] is False))
    for key in ['committee_name', 'official_version', 'online_entry', 'generation_permission', 'stage_approval', 'publication_approval']:
        require(g[key] is None)
    require(g['online_boundary']['origin_path'] == own[3] and g['online_boundary']['login_marker'] is True and all((g['online_boundary'][k] is False for k in ['query_retained', 'login_attempted', 'QR_scanned', 'application_submitted'])))
    capture_sha = sha256(_raw(root, base / 'own-materials-native-dom.json')).hexdigest()
    for field in g['fields'].values():
        m = re.fullmatch('tables\\[(\\d+)\\]\\[(\\d+)\\]\\[(\\d+)\\]', field['source_pointer'])
        require(m is not None)
        t, r, c = map(int, m.groups())
        require(dom['tables'][t][r][c] == field['raw_value'] and field['source_id'] == identity['source_id'] and (field['source_url'] == identity['source_url']) and (field['region_code'] == code) and (field['capture_file'] == 'own-materials-native-dom.json') and (field['capture_sha256'] == capture_sha) and (field['normalized_value'] is None) and (field['verification_status'] == 'observed_unverified'))
    require(type(g['sections']) is dict and set(g['sections']) == {'conditions', 'window'} and (len(g['materials']) == 3))
    for i, m in enumerate(g['materials'], 1):
        require(m['official_material_id'] is None and m['legal_default_copies'] is None and (m['local_material_key'] == own[1] + ':dom-material:' + str(i)) and (m['source_id'] == own[1]) and (m['source_url'] == identity['source_url']) and (m['capture_sha256'] == capture_sha) and (m['source_pointer'] == 'tables[' + str(i + 1) + ']'))
        require(m['copies_raw'] == ['原件份数2份', '原件份数2份', '复印件份数2份'][i - 1])
        if code == '350502':
            require('填报须知' not in m['raw_fields'])
    require(attachments['source_id'] == own[1] and attachments['source_url'] == identity['source_url'] and (len(attachments['attachments']) == 6))
    for a in attachments['attachments']:
        require(a['source_id'] == own[1] and a['source_url'] == identity['source_url'] and (a['region_code'] == code) and (a['official_material_id'] is None) and (a['can_generate'] is False) and (a['generation_permission'] is None) and (a['http_status'] == 200) and (a['TLS_verify'] is True) and (a['auth_or_cookies_supplied'] is False) and (a['redirects_followed'] is False) and (a['native_new_request_ID_delta_verified'] is True))
        require(a['url'] == 'https://zwfw.fujian.gov.cn:732/cms-business/apasService/file/downloadFileStream?unid=' + a['public_file_unid'])
        if a['role'] in ['application-format', 'evidence-list-format']:
            kind = 'application' if a['role'] == 'application-format' else 'evidence'
            file, file_id, digest, _ = _kind(kind)
            b = _raw(root, base / file)
            require(a['local_original'] == file and a['public_file_unid'] == file_id and (a['official_control_type'] == 'format') and (a['sha256'] == digest == sha256(b).hexdigest()) and exact(_layout_inspect(b, kind), audit['own_original_checks'][kind]) and (a['ZIP_members'] == audit['own_original_checks'][kind]['member_sha256']))
        else:
            require(a['local_original'] is None and 'NOT_blank' in a['content_role'])
    require(all((obj['source_id'] == own[1] for obj in [q, audit, lineage])) and q['WORD'] is None and (q['STAGE'] is None) and (q['PUBLICATION'] is None) and (q['can_generate'] is False) and (lineage['private_parent_runtime_fallback'] is False))
    return (identity, pin, base, g, attachments['attachments'])

def source_files(root, code=None):
    codes = list(REGIONS) if code is None else [code]
    out = [str(SOURCE_BASE / 'OWN-SOURCE-PINS.json')]
    for c in codes:
        _, _, base, *_ = _source(c, root)
        out.extend([str(base / 'SOURCE-PROJECTION-MANIFEST.json'), *[str(base / f) for f in sorted(LEAVES)]])
    return out

def prepare_candidate(code, *, root):
    identity, pin, base, g, attachments = _source(code, root)
    out = deepcopy(g)
    out['authority'] = identity['authority']
    out['source_version'] = pin['source_manifest_sha256']
    for f in out['fields'].values():
        f.update(source_version=pin['source_manifest_sha256'], capture_file=str(base / f['capture_file']))
    for m in out['materials']:
        m.update(material_id=None, copies=m['copies_raw'], instructions=m['raw_fields'].get('填报须知'))
    templates = [{**deepcopy(a), 'id': a['public_file_unid'], 'document_types': [], 'official_kind': a['official_control_type'], 'original_name': a['official_label'], 'material_id': None} for a in attachments]
    out.update(templates=templates, offline_candidate=True, published=False, generation_adapter=None, source_review='PENDING_ROOT', Word_visual_review='NOT_RUN', channel={'online_status': 'auth_required', 'entry_url': None, 'entry_check': {'status': 'native_auth_boundary_observed'}})
    return _production_guide(out, base)
parse_capture = prepare_candidate

def _production_guide(guide, base):
    """Mechanical DTO aliases after exact own _source validation; raw retained."""
    guide.update(raw_verification_status=guide['verification_status'],
                 verification_status=guide['guide_status'], committee_full_name=None)
    for field in guide['fields'].values():
        field.update(collected_at=field['observed_at_utc'], verified_at=field['observed_at_utc'])
    for material in guide['materials']:
        fields=material['raw_fields']
        material.update(id=material['local_material_key'], official_badges=[],
                        required=fields.get('材料必要性'), format=fields.get('材料形式'),
                        source_channel=fields.get('来源渠道'))
    for template in guide['templates']:
        own_file=template['local_original']
        template.update(file=str(base/own_file) if own_file is not None else None,
                        download_status='downloaded' if own_file is not None else 'metadata_only')
    handling=guide['fields'].get('办理形式')
    guide['channel'].update(raw_value=handling['raw_value'] if handling else None,
                            submission_verified=False)
    return guide

def production_schema_descriptor(code, kind):
    """Label existing own slots without changing frozen Word request schema."""
    schema=deepcopy(schema_descriptor(code,kind))
    labels={'applicantName':'申请人','agentName':'委托代理人','respondentName':'被申请人',
            'requests':'仲裁请求','factsReason':'事实和理由','evidenceList':'证据清单',
            'name':'证据名称','pageCount':'页数','originalType':'原件或复印件',
            'purpose':'证明目的','pageRange':'页码范围'}
    for field in schema['fields']:
        field['label']=labels[field['key']]
        for item in field.get('fields',[]):
            item['label']=labels[item['key']]
            if item['key']=='originalType':item['choices']=['原件','复印件']
    schema['source_version']=SOURCE_VERSIONS[code]
    schema['policy'].update(invalid_xml='reject',text_controls='newline_only',trim_text=True)
    return schema

def defaults(code, kind):
    _code(code)
    _kind(kind)
    return {'applicantName': '', 'agentName': '', 'respondentName': '', 'requests': [''], 'factsReason': ''} if kind == 'application' else {'evidenceList': [{k: '' for k in ITEM}]}

def form_fields(code, kind):
    _code(code)
    _kind(kind)

    def f(key, size):
        return {'key': key, 'type': 'text', 'maxLength': size}
    return [f('applicantName', 180), f('agentName', 180), f('respondentName', 180), {'key': 'requests', 'type': 'text_list', 'maxItems': 3, 'maxLength': 360}, f('factsReason', 2400)] if kind == 'application' else [{'key': 'evidenceList', 'type': 'object_list', 'maxItems': 9, 'fields': [f(k, {'name': 60, 'pageCount': 4, 'originalType': 4, 'purpose': 80, 'pageRange': 32}[k]) for k in ITEM]}]

def schema_descriptor(code, kind):
    _code(code)
    _kind(kind)
    return {'schema_id': 'private-own-xianyou-quanzhou-' + code + '-' + kind + '-v1', 'schema_version': 1, 'region_code': code, 'source_id': REGIONS[code][1], 'fields': form_fields(code, kind), 'defaults': defaults(code, kind), 'policy': {'unknown_fields': 'reject', 'capacity_is_legal_requirement': False, 'capacity_is_official_requirement': False, 'signature_date_committee_copies': 'not_accepted'}}

def example_data(code, kind):
    _code(code)
    _kind(kind)
    return {'applicantName': '虚构申请人甲（仅测试）', 'agentName': '', 'respondentName': '虚构乙公司（仅测试）', 'requests': ['虚构请求，仅核对自身候选映射。'], 'factsReason': '全部内容虚构，不涉及真实案件。'} if kind == 'application' else {'evidenceList': [{'name': '虚构证据甲', 'pageCount': '1', 'originalType': '复印件', 'purpose': '虚构测试用途', 'pageRange': '1'}]}

def envelope(code, kind, data, *, root):
    identity, pin, *_ = _source(code, root)
    file, file_id, digest, row = _kind(kind)
    schema = schema_descriptor(code, kind)
    return {**identity, 'source_version': pin['source_manifest_sha256'], 'material_id': None, 'local_material_key': identity['source_id'] + ':dom-material:' + str(row), 'template_id': file_id, 'template_sha256': digest, 'template_version': 'sha256:' + digest, 'schema_id': schema['schema_id'], 'schema_version': 1, 'schema_sha256': sha256(json.dumps(schema, ensure_ascii=False, sort_keys=True).encode()).hexdigest(), 'kind': kind, 'mode': 'blank', 'data': deepcopy(data)}

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
            item = {k: '' for k in ITEM}
            for key, value in row.items():
                item[key] = _text(value, {'name': 60, 'pageCount': 4, 'originalType': 4, 'purpose': 80, 'pageRange': 32}[key])
            require(item['originalType'] in {'', '原件', '复印件'} and (not item['pageCount'] or re.fullmatch('[1-9][0-9]{0,3}', item['pageCount'])))
            out['evidenceList'].append(item)
    return (code, kind, out)

def original_bytes(code, kind, *, root):
    _, _, base, *_ = _source(code, root)
    return _raw(root, base / _kind(kind)[0])

def inspect_blank(code, kind, *, root):
    return _layout_inspect(original_bytes(code, kind, root=root), kind)

def candidate_fill(payload, *, root, private_review=False):
    if private_review is not True:
        raise PermissionError('No approval: explicit private review only')
    code, kind, data = validate_request(payload, root=root)
    return _layout_fill(original_bytes(code, kind, root=root), kind, data)

def published_guide(code, *, root):
    _code(code)
    raise PermissionError('No own publication approval')

# New own O phase boundaries only; existing source/schema/mapping functions stay unchanged.
ADAPTER='fujian_xianyou_quanzhou_licheng_own_blank_oct31o_v1'
QA_REPORT='reports/overnight-gap-closure-20261030/localities/fujian-o/integration-qa-v1'
WORD_MANIFEST=QA_REPORT+'/WORD-MANIFEST.json'
STAGE_RECEIPT=QA_REPORT+'/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT=QA_REPORT+'/FINAL-BROWSER-QA.json'
SOURCE_VERSIONS={'350322':'7aa1301b1a520ac1a34803afe72cd96ef3378e40d0aea90ec4ea81113c3a1e59','350502':'bb7dc30c5ec4fe6185777fc6b44ddd139c52eda1f3f36bd8023eaf0f6cf576f6'}
ROOT_WORD_REVIEW_SHA256='82b3c50fd333216c67ef4d8f5f1feedf2d1ee8db497561670e2e7abab5fa3fc8'
ROOT_SOURCE_REVIEW_SHA256='4a30d0b67dfdc7c7bd17824472df9bb8b2a5f756453ac4ac461659c78d09148c'
_METADATA={'version','region_id','content_hash'}
_FAILURES=(ValueError,OSError,KeyError,TypeError,AttributeError,StopIteration)

def _matches(guide,canonical):
    if type(guide) is not dict:return False
    if 'evidence' in guide:
        code=canonical.get('region_code') if type(canonical) is dict else None
        if type(code) is not str or code not in REGIONS:return False
        if canonical.get('source_id')!=REGIONS[code][1] or canonical.get('source_version')!=SOURCE_VERSIONS[code]:return False
        expected={'source_projection':str(SOURCE_BASE/REGIONS[code][0]/'SOURCE-PROJECTION-MANIFEST.json'),
                  'source_projection_sha256':canonical['source_version']}
        if not exact(guide['evidence'],expected):return False
        guide={key:value for key,value in guide.items() if key!='evidence'}
    if type(guide) is not dict or set(guide)-set(canonical)-_METADATA:return False
    if 'version' in guide and (type(guide['version']) is not int or guide['version']<1):return False
    region_id=sha256(json.dumps([canonical[k] for k in ['province','city','district']],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
    if 'region_id' in guide and guide['region_id']!=region_id:return False
    if 'content_hash' in guide and (type(guide['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}',guide['content_hash'])):return False
    return all(key in guide and exact(guide[key],value) for key,value in canonical.items())

def approval_requirements(*,stage=True):
    result={'scope':'PRIVATE_STAGE_PROPOSAL_NOT_REGISTERED','identities':[{'region_code':c,'source_id':REGIONS[c][1],'service_code':REGIONS[c][2],'manifest_sha256':SOURCE_VERSIONS[c]} for c in REGIONS],
            'word_manifest_sha256':WORD_SHA256,'eligible_originals':4,'approved_by':'independent_root_word_gate','visual_review':'PASS','source_projection_review':'ROOT_PRIVATE_REVIEW_PASS',
            'can_publish':False,'model_calls':0,'Root_source_review_sha256':ROOT_SOURCE_REVIEW_SHA256,'Root_Word_review_sha256':ROOT_WORD_REVIEW_SHA256,
            'stress_evidence_signature_continues_on_tenth_page':True,'browser_QA':'NOT_RUN','native_final_QA':'NOT_RUN','publication_approval':None}
    if not stage:
        # No final receipt is supplied or accepted by this private stage proposal.
        raise ValueError('Own O final/publication gate has no approval')
    return result

def _word_manifest(root):
    require(type(WORD_SHA256) is str and re.fullmatch('[a-f0-9]{64}',WORD_SHA256))
    raw=_raw(root,WORD_MANIFEST);require(sha256(raw).hexdigest()==WORD_SHA256);word=json.loads(raw)
    require(word['scope']=='OWN_O_WORD_PROOF_PRIVATE_STAGE_PROPOSAL' and exact(word['source_versions'],SOURCE_VERSIONS)
            and type(word['eligible_originals']) is int and word['eligible_originals']==4 and word['fictional_fixtures']==8 and word['word_documents']==12
            and word['original_pages']==6 and word['generated_pages']==42 and word['logical_visual_pages']==48
            and word['same_requests_as_frozen_public_context_queue'] is True and word['all12_reviewed_Word_bytes_exact'] is True and word['all48_reviewed_page_bytes_exact'] is True
            and word['stage_approved'] is False and word['can_publish'] is False and word['new_render'] is False and word['model_calls']==0
            and word['actual_Root_review_sha256']==ROOT_WORD_REVIEW_SHA256 and word['stress_evidence_signature_continues_on_tenth_page'] is True)
    leaves=word['files'];require(type(leaves) is list and len(leaves)==72 and len({f['path'] for f in leaves})==72)
    fixed={QA_REPORT+'/'+n for n in ['README.md','ROOT-VISUAL-REVIEW.json','ROOT-PAGE-REVIEW-INDEX.json','SOURCE-WORD-PARITY.json']}
    for code in REGIONS:
        for kind in KINDS:
            for scenario in ['original','normal','stress']:
                fixed.add(f'{QA_REPORT}/word/{code}-{kind}-{scenario}.docx')
                if scenario!='original':fixed.add(f'{QA_REPORT}/fixtures/{code}-{kind}-{scenario}.json')
    actual={f['path'] for f in leaves};pages=actual-fixed;require(fixed<=actual and len(pages)==48)
    leafmap={}
    for leaf in leaves:
        require(type(leaf['path']) is str and leaf['path'].startswith(QA_REPORT+'/'))
        body=_raw(root,leaf['path']);require(type(leaf['bytes']) is int and len(body)==leaf['bytes'] and sha256(body).hexdigest()==leaf['sha256']);leafmap[leaf['path']]=leaf
    reviewed_raw=_raw(root,QA_REPORT+'/ROOT-VISUAL-REVIEW.json');require(sha256(reviewed_raw).hexdigest()==ROOT_WORD_REVIEW_SHA256);review=json.loads(reviewed_raw)
    require(review['status']=='ROOT_O_OWN_WORD_VISUAL_PASS_PRIVATE_ONLY' and review['regions']==list(REGIONS) and review['documents']==12 and review['logical_pages']==48
            and review['actual_new_unique_opens']==17 and review['prior_Root_exact_SHA_matches']==8 and review['same_run_duplicates_covered_after_actual_views']==23
            and review['stress_evidence_signature_continues_on_tenth_page'] is True and review['WORD_STAGE_PUBLICATION'] is None)
    require(type(review['checked_documents']) is list and len(review['checked_documents'])==12)
    checked={(r['region_code'],r['kind'],r['role']):r for r in review['checked_documents']};require(len(checked)==12)
    groups={}
    for path in pages:
        match=re.fullmatch(re.escape(QA_REPORT)+r'/pages/(350322|350502)-(application|evidence)-(original|normal|stress)-([0-9]+)\.png',path);require(match is not None)
        code,kind,scenario,number=match.groups();key=(code,kind,scenario);number=int(number);require(number>0 and number not in groups.setdefault(key,set()));groups[key].add(number)
        require(_raw(root,path).startswith(b'\x89PNG\r\n\x1a\n'))
    for code in REGIONS:
        _source(code,root)
        for kind in KINDS:
            original=original_bytes(code,kind,root=root)
            for role,scenario in [('own_original','original'),('fictional_normal','normal'),('fictional_stress','stress')]:
                record=checked[(code,kind,role)];path=f'{QA_REPORT}/word/{code}-{kind}-{scenario}.docx';body=_raw(root,path)
                require(record['sha256']==sha256(body).hexdigest() and type(record['bytes']) is int and record['bytes']==len(body) and record['whole_and_all_ZIP_equal'] is True
                        and type(record['pages']) is int and groups[(code,kind,scenario)]==set(range(1,record['pages']+1)))
                if scenario=='original':require(body==original)
                else:
                    fixture=_json(root,f'{QA_REPORT}/fixtures/{code}-{kind}-{scenario}.json');c,k,data=validate_request(fixture,root=root);require(c==code and k==kind and '虚构' in json.dumps(data,ensure_ascii=False))
                    # Only fixed, already Root-reviewed fixture/Word pairs are replayed internally.
                    require(_layout_fill(original,kind,data)==body);_layout_assert_protected(original,body,kind)
    pageproof=_json(root,QA_REPORT+'/ROOT-PAGE-REVIEW-INDEX.json');require(pageproof['actual_Root_review_sha256']==ROOT_WORD_REVIEW_SHA256 and pageproof['logical_pages']==48 and len(pageproof['rows'])==48 and pageproof['browser_QA']=='NOT_RUN' and pageproof['publication'] is False)
    require({QA_REPORT+'/pages/'+r['page'] for r in pageproof['rows']}==pages)
    for row in pageproof['rows']:require(leafmap[QA_REPORT+'/pages/'+row['page']]['sha256']==row['sha256'])
    parity=_json(root,QA_REPORT+'/SOURCE-WORD-PARITY.json');require(parity['source_projection_review_sha256']==ROOT_SOURCE_REVIEW_SHA256 and parity['actual_Root_Word_review_sha256']==ROOT_WORD_REVIEW_SHA256 and parity['stress_evidence_signature_date_separate_tenth_page'] is True and parity['fictional_stress_page_total']==89991 and parity['browser_final_publication_approval'] is None)
    return word

def _receipt(root,stage=True):
    pin=STAGE_SHA256 if stage else PUBLICATION_SHA256
    require(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin))
    source_files(root);word=_word_manifest(root);requirements=approval_requirements(stage=stage)
    filename=STAGE_RECEIPT if stage else PUBLICATION_RECEIPT;raw=_raw(root,filename);require(sha256(raw).hexdigest()==pin);receipt=json.loads(raw)
    require(type(receipt) is dict and receipt.keys()==requirements.keys()|{'files'} and all(exact(receipt[k],v) for k,v in requirements.items()) and exact(receipt['files'],word['files']))
    return {'receipt':filename,'sha256':pin,'scope':'PRIVATE_STAGE_PROPOSAL_NOT_REGISTERED'}

def approval_files(root):
    _receipt(root);word=_word_manifest(root)
    return [WORD_MANIFEST,STAGE_RECEIPT,*[f['path'] for f in word['files']]]

def staged_candidate(code,*,root):
    guide=prepare_candidate(code,root=root);guide['candidate_adapter_evidence']=_receipt(root)
    guide.update(can_generate=True,offline_candidate=False,generation_adapter=ADAPTER,publication_status='staged_own_word_qa_private_proposal')
    for kind,(_,file_id,_,_) in KINDS.items():
        template=next(row for row in guide['templates'] if row['id']==file_id)
        require(template['official_control_type']=='format' and template['local_original']==KINDS[kind][0])
        template.update(can_generate=True,document_types=[kind],adapter=ADAPTER,generation_mode='blank',official_kind='blank',eligible_own_kind=kind)
    return guide

def _bound(guide,root,allow_source=False):
    require(type(guide) is dict);code=guide.get('region_code');raw=parse_capture(code,root=root)
    if allow_source and _matches(guide,raw):return raw
    require(guide.get('published') is not True and 'publication_adapter_evidence' not in guide)
    canonical=staged_candidate(code,root=root);require(_matches(guide,canonical));return canonical

def with_capabilities(guide,*,root):
    _bound(guide,root,allow_source=True);return deepcopy(guide)

def with_publication_evidence(guide,*,root):
    _bound(guide,root);_receipt(root,False)
    raise ValueError('Own O private stage proposal has no final/publication approval')

def checked_adapter(guide,template,kind,*,root):
    canonical=_bound(guide,root);_,file_id,_,_=_kind(kind);expected=next(row for row in canonical['templates'] if row['id']==file_id)
    require(exact(template,expected) and expected['can_generate'] is True and expected['eligible_own_kind']==kind and expected['official_kind']=='blank' and expected['generation_mode']=='blank')
    return ADAPTER

def checked_reference_adapter(guide,template,kind,*,root):
    return checked_adapter(guide,template,kind,root=root)

def template_path(code,kind,*,root):
    _,_,base,*_=_source(code,root);return path_at(root,base/_kind(kind)[0])

def public_evidence(guide,root):
    try:
        canonical=_bound(guide,root,allow_source=True)
        return {'source_projection':str(SOURCE_BASE/REGIONS[canonical['region_code']][0]/'SOURCE-PROJECTION-MANIFEST.json'),'source_projection_sha256':canonical['source_version']}
    except _FAILURES:return None

def approved_report_attachment(guide,template,root):
    try:return any(exact(row,template) and row['local_original'] is not None for row in _bound(guide,root,allow_source=True)['templates'])
    except _FAILURES:return False

class _PatchedDocument:
    def __init__(self,body,root):self.body,self.root=body,Path(root).resolve()
    def save(self,destination):
        if hasattr(destination,'write'):destination.write(self.body);return
        path=Path(destination).resolve();require(not path.is_relative_to(self.root/'reports'));path.write_bytes(self.body)

def fill_document(guide,template,kind,path,data,*,root):
    checked_adapter(guide,template,kind,root=root)
    require(Path(path).resolve()==template_path(guide['region_code'],kind,root=root))
    request=envelope(guide['region_code'],kind,data,root=root)
    return _PatchedDocument(candidate_fill(request,root=root,private_review=True),root)
