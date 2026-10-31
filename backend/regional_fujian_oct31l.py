"""Pingtan own source and reviewed Word mapping; public phases independently pinned."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json, re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
ADAPTER = 'fujian_pingtan_own_blank_oct31l_v1'
BASE = Path('reports/overnight-gap-closure-20261030/localities/fujian-l-source-projection/pingtan-350128')
SOURCE_BASE = BASE
SOURCE_ID = '511e7f64c9481b5a0b6ff4a1'
SOURCE_URL = 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=DB9193FF4D772DB2CDBBA1BCA7369872&infoType=1'
SOURCE_SHA = '85c9f528deb21b5da68c0d5f108c72e5a4f6a7d0ebf2e56da960f87a228b607e'
IDENTITY = {'province': 'fujian', 'city': '平潭综合实验区', 'district': '平潭综合实验区', 'region_code': '350128', 'source_id': SOURCE_ID, 'source_url': SOURCE_URL, 'service_code': '1135012806039606XH300201430200201', 'authority': '平潭综合实验区社会事业局'}
TEMPLATES = {'application': {'file': 'application-own-format.docx', 'material_id': 'CAAD35DCD8944729A80E6C5A251CB294', 'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86', 'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365'}, 'evidence': {'file': 'evidence-own-format.docx', 'material_id': '59560ABC219CCB4AF2E8840A20C74607', 'file_id': 'CC300F5D9DD5DC404D65C68116D50C55', 'sha256': 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815'}}
STAGE_SHA256 = '03d20d8b80848d199ddd843d9c968470cfaea868b7ebfe43c51a80bbbadc20d9'
PUBLICATION_SHA256 = None
WORD_SHA = '33a5d258b6d1e857074b5d4732db753e7cd4b796445c48300e337c28e3f283e3'
APP = ('applicantName', 'agentName', 'respondentName', 'requests', 'factsReason')
ITEM = ('name', 'pageCount', 'originalType', 'purpose', 'pageRange')
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
N = {'w': W}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def exact(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(b, dict):
        return a.keys() == b.keys() and all((exact(a[k], v) for k, v in b.items()))
    if isinstance(b, list):
        return len(a) == len(b) and all((exact(x, y) for x, y in zip(a, b)))
    return a == b

def path_at(root, relative):
    require(root is not None and str(root).strip(), 'Explicit standalone L source root required')
    base = Path(root).resolve()
    rel = Path(relative)
    require(not rel.is_absolute() and (not rel.drive) and ('..' not in rel.parts), 'Own relative path required')
    path = (base / rel).resolve()
    require(path.is_relative_to(base) and path.relative_to(base).as_posix() == rel.as_posix(), 'Own path escaped or linked')
    return path

def _bytes(root, relative):
    try:
        return path_at(root, relative).read_bytes()
    except OSError as e:
        raise ValueError('Own source unavailable in explicit root') from e

def _read(root, relative):
    return json.loads(_bytes(root, relative))

def _kind(kind):
    require(type(kind) is str and kind in TEMPLATES, 'Only own application/evidence blanks considered')
    return TEMPLATES[kind]

def _sources(root):
    body = _bytes(root, BASE / 'SOURCE-PROJECTION-MANIFEST.json')
    require(sha256(body).hexdigest() == SOURCE_SHA, 'Own L source projection version differs')
    m = json.loads(body)
    require(all((exact(m.get(k), v) for k, v in IDENTITY.items())) and sha256(json.dumps(SOURCE_URL, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24] == SOURCE_ID, 'Own Pingtan identity differs')
    require(m['schema'] == 'fujian-pingtan-own-public-source-v1' and m['raw_parent_is_runtime_dependency'] is False and (m['parent_v1_is_runtime_dependency'] is False), 'Standalone v2 source required')
    require(m['can_generate'] is False and m['published'] is False and (m['committee_full_name'] is None) and (m['official_version'] is None) and (m['root_stage_receipt'] is None) and (m['root_final_receipt'] is None), 'Source phase changed')
    expected = {'NORMALIZED-OWN-SOURCE.json', 'SOURCE-QUALIFICATIONS.json', 'own-guide-native-dom.json', 'own-official-bindings.json', *[t['file'] for t in TEMPLATES.values()]}
    require(type(m['files']) is dict and set(m['files']) == expected, 'Exact six own source leaves required')
    for name, pin in m['files'].items():
        raw = _bytes(root, BASE / name)
        require(type(pin['bytes']) is int and len(raw) == pin['bytes'] and (sha256(raw).hexdigest() == pin['sha256']), 'Own source leaf changed')
    n = _read(root, BASE / 'NORMALIZED-OWN-SOURCE.json')
    d = _read(root, BASE / 'own-guide-native-dom.json')
    b = _read(root, BASE / 'own-official-bindings.json')
    q = _read(root, BASE / 'SOURCE-QUALIFICATIONS.json')
    require(all((exact(n['region'].get(k), v) for k, v in IDENTITY.items() if k not in {'service_code', 'authority'})) and n['service_code_literal'] == IDENTITY['service_code'] and (n['authority_literal'] == IDENTITY['authority']), 'Own normalized identity differs')
    require(all((exact(b.get(k), v) for k, v in IDENTITY.items())) and b['byte_identity_grants_other_region_authority'] is False, 'Own binding identity differs')
    require(n['official_version'] is None and n['committee_full_name'] is None and (q['official_version'] is None) and (q['committee_full_name'] is None) and (q['committee_autofill_allowed'] is False), 'No committee/version inference allowed')
    require(q['can_generate'] is False and q['published'] is False and (q['root_stage_receipt'] is None) and (q['root_final_receipt'] is None) and (q['eligible_generation_kinds'] == []), 'No approved generation phase')
    scope = q['source_conflicts_and_scope_notes'][0]
    require(scope['kind'] == 'COMPATIBLE_SCOPE_NOTE' and scope['resolution'] == 'COMPATIBLE_DIFFERENT_SCOPES' and (scope['eligible_issue_event'] is False) and (q['operational_issue_events'] == []) and (q['compatible_scope_note']['issue_export_or_ACK_authorized'] is False), 'Compatible visit scopes must not become a conflict event')
    require(scope['raw_A'] == '服务承诺到现场次数\n1 次' and '不超过2次' in scope['raw_B'] and (scope['raw_A'] in d['raw_public_text']) and (scope['raw_B'] in d['raw_public_text']), 'Own visit raw text changed')
    require(len(n['materials']) == 3 and len(b['attachments']) == 6 and (len({x['file_id'] for x in b['attachments']}) == 6), 'Own three materials/six attachments required')
    for key, row in n['raw_fields'].items():
        pos = re.fullmatch('tables\\[(\\d+)\\]\\[(\\d+)\\]\\[(\\d+)\\]', row['source_pointer'])
        require(pos is not None and row['source_url'] == SOURCE_URL, 'Own field provenance missing')
        ti, ri, ci = map(int, pos.groups())
        require(exact(row['raw_value'], d['tables'][ti][ri][ci]) and row['normalized_value'] == row['raw_value'].strip(), 'Own raw cell differs')
    for panel in n['materials']:
        for a in panel['attachments']:
            rows = [x for x in b['attachments'] if x['material_id'] == panel['material_id'] and x['file_id'] == a['file_id']]
            require(len(rows) == 1 and rows[0]['official_type_raw'] == a['official_type_raw'] and (rows[0]['official_label'] == a['label']), 'Own material/file/type differs')
    for kind, t in TEMPLATES.items():
        require(exact(m['templates'][kind], {**t, 'role': 'own_FORMAT_blank_candidate_no_generation_approval'}), 'Own template frame differs')
        rows = [x for x in b['attachments'] if x['file_id'] == t['file_id']]
        require(len(rows) == 1, 'Unique own blank binding required')
        row = rows[0]
        require(row['material_id'] == t['material_id'] and row['source_url'] == SOURCE_URL and (row['official_type_raw'] == '1') and (row['eligible_kind'] == kind) and (row['file'] == t['file']) and (row['sha256'] == t['sha256']) and (row['TLS_verified'] is True) and (row['download_status'] == 'own_anonymous_TLS_bytes_retained') and (row['can_generate'] is False), 'Own anonymous-TLS FORMAT binding required despite shared bytes')
        require(sha256(_bytes(root, BASE / t['file'])).hexdigest() == t['sha256'], 'Own blank bytes differ')
    for row in b['attachments']:
        if row['eligible_kind'] is None:
            require(row['file'] is None and row['sha256'] is None and (row['download_status'] == 'metadata_only') and (row['can_generate'] is False), 'Sample/reference must remain metadata only')
    return (m, n, d, b, q)

def _own_original_bytes(kind, *, root):
    t = _kind(kind)
    _sources(root)
    return _bytes(root, BASE / t['file'])

def _own_inspect_blank(kind, *, root):
    raw = _own_original_bytes(kind, root=root)
    with ZipFile(BytesIO(raw)) as z:
        require(z.testzip() is None, 'Own original ZIP CRC invalid')
        xml = z.read('word/document.xml')
        parser = E.XMLParser(resolve_entities=False, no_network=True)
        doc = E.fromstring(xml, parser)
        ps = doc.findall('w:body/w:p', N)
        require(len(doc.findall('w:body/w:sectPr', N)) == 1, 'Own section count differs')
        if kind == 'application':
            require(len(ps) == 22 and (not doc.findall('.//w:tbl', N)), 'Own application paragraph/table layout differs')
            for i, label in [(0, '仲裁申请书'), (2, '申请人：'), (3, '委托代理人：'), (4, '被申请人：'), (19, '申请人：')]:
                require(''.join(ps[i].itertext()).strip() == label, 'Own blank application label differs')
            require(all((''.join(ps[7 + i].itertext()).strip() == f'{i + 1}、' for i in range(3))) and all((not ''.join(x.itertext()).strip() for x in ps[11:15])), 'Filled text is not an original blank')
            return {'paragraphs': 22, 'request_slots': 3, 'signature_date_committee_untouched': True, 'visual_review': False, 'filling_approved': False}
        tables = doc.findall('.//w:tbl', N)
        require(len(ps) == 2 and len(tables) == 1, 'Own evidence layout differs')
        rows = tables[0].findall('w:tr', N)
        require(len(rows) == 11 and [''.join(c.itertext()) for c in rows[0].findall('w:tc', N)] == ['序号', '证据名称', '页数', '原件/复印件', '证明对象', '页码'], 'Own evidence header/capacity differs')
        require(all((len(r.findall('w:tc', N)) == 6 and all((not ''.join(c.itertext()).strip() for c in r.findall('w:tc', N))) for r in rows[1:-1])), 'Filled evidence is not an original blank')
        return {'paragraphs': 2, 'evidence_rows_capacity': 9, 'all_body_cells_blank': True, 'visual_review': False, 'filling_approved': False}

def _own_defaults(kind):
    _kind(kind)
    return {'applicantName': '', 'agentName': '', 'respondentName': '', 'requests': [''], 'factsReason': ''} if kind == 'application' else {'evidenceList': [{k: '' for k in ITEM}]}

def _own_form_fields(kind):
    _kind(kind)

    def text(key, label, size, **extra):
        return {'key': key, 'label': label, 'type': 'text', 'nullable': False, 'maxLength': size, **extra}
    if kind == 'application':
        return [text('applicantName', '申请人信息', 180), text('agentName', '委托代理人信息', 180), text('respondentName', '被申请人信息', 180), {'key': 'requests', 'label': '仲裁请求', 'type': 'text_list', 'nullable': False, 'maxItems': 3, 'maxLength': 360}, text('factsReason', '事实与理由', 2400)]
    return [{'key': 'evidenceList', 'label': '证据内容', 'type': 'object_list', 'nullable': False, 'maxItems': 9, 'fields': [text('name', '证据名称', 60), text('pageCount', '页数', 4), text('originalType', '原件或复印件', 4, choices=['原件', '复印件']), text('purpose', '证明对象', 80), text('pageRange', '页码', 32)]}]

def _own_schema_descriptor(kind):
    _kind(kind)
    return {'schema_id': f'fujian-l-350128-{kind}-v1', 'schema_version': 1, 'region_code': '350128', 'source_id': SOURCE_ID, 'source_version': SOURCE_SHA, 'fields': _own_form_fields(kind), 'defaults': _own_defaults(kind), 'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only', 'trim_text': True, 'capacity_is_official_requirement': False}}

def _own_example_data(kind):
    _kind(kind)
    if kind == 'application':
        return {'applicantName': '虚构平潭申请人甲（仅测试）', 'agentName': '', 'respondentName': '虚构平潭乙公司（仅测试）', 'requests': ['虚构请求：仅测试自身空表字段，不提出真实仲裁申请。'], 'factsReason': '所有内容均为虚构，仅用于自身候选表格验证，不涉及真实当事人或争议。'}
    return {'evidenceList': [{'name': '虚构平潭材料甲', 'pageCount': '1', 'originalType': '复印件', 'purpose': '虚构测试：核对自身证据表字段。', 'pageRange': '1'}]}

def _own_envelope(kind, data, *, root):
    t = _kind(kind)
    _sources(root)
    s = _own_schema_descriptor(kind)
    return {**IDENTITY, 'source_version': SOURCE_SHA, 'material_id': t['material_id'], 'template_id': t['file_id'], 'template_file': (BASE / t['file']).as_posix(), 'template_sha256': t['sha256'], 'template_version': 'sha256:' + t['sha256'], 'schema_id': s['schema_id'], 'schema_version': 1, 'kind': kind, 'mode': 'blank', 'data': deepcopy(data)}

def _text(v, capacity):
    require(type(v) is str and len(v) <= capacity and all((c == '\n' or 32 <= ord(c) <= 55295 or 57344 <= ord(c) <= 65533 or (65536 <= ord(c) <= 1114111) for c in v)), 'Invalid own text type/XML/technical capacity')
    return v.strip()

def _own_validate_request(payload, *, root):
    require(type(payload) is dict, 'Own candidate request object required')
    kind = payload.get('kind')
    expected = _own_envelope(kind, {}, root=root)
    require(payload.keys() == expected.keys() and all((exact(payload[k], v) for k, v in expected.items() if k != 'data')), 'Own Pingtan source/template/schema tuple differs')
    data = payload['data']
    require(type(data) is dict, 'Own data object required')
    if kind == 'application':
        require(not set(data) - set(APP), 'Unknown application field')
        values = {k: '' for k in APP if k != 'requests'}
        values['requests'] = []
        for k, v in data.items():
            if k == 'requests':
                require(type(v) is list and len(v) <= 3, 'Own technical request capacity exceeded')
                values[k] = [_text(x, 360) for x in v]
            else:
                values[k] = _text(v, 2400 if k == 'factsReason' else 180)
    else:
        require(not set(data) - {'evidenceList'}, 'Unknown evidence field')
        rows = data.get('evidenceList', [])
        require(type(rows) is list and len(rows) <= 9, 'Own technical evidence capacity exceeded')
        values = {'evidenceList': []}
        for row in rows:
            require(type(row) is dict and (not set(row) - set(ITEM)), 'Unknown evidence item')
            item = {k: '' for k in ITEM}
            for k, v in row.items():
                item[k] = _text(v, {'name': 60, 'pageCount': 4, 'originalType': 4, 'purpose': 80, 'pageRange': 32}[k])
            require(item['originalType'] in ('', '原件', '复印件') and (not item['pageCount'] or re.fullmatch('[1-9][0-9]{0,3}', item['pageCount'])), 'Invalid page count or original/copy value')
            values['evidenceList'].append(item)
    return (kind, values)
def _word_example_data(kind, stress=False):
    d = _own_example_data(kind)
    if not stress:
        return d

    def bounded(prefix, unit, count):
        return (prefix + unit * count)[:count]
    if kind == 'application':
        return {'applicantName': bounded('虚构平潭申请人甲：', '甲', 180), 'agentName': bounded('虚构平潭代理人乙：', '乙', 180), 'respondentName': bounded('虚构平潭丙公司：', '丙', 180), 'requests': [bounded(f'虚构请求{i + 1}：', '仅作自身表格测试，不提出真实申请。', 360) for i in range(3)], 'factsReason': bounded('虚构事实与理由：\n', '仅作平潭自身空白表格容量测试，不涉及真实当事人、真实争议或法律请求。\n', 2400)}
    return {'evidenceList': [{'name': bounded(f'虚构平潭证据{i + 1}：', '测试', 60), 'pageCount': str(i + 1), 'originalType': '复印件' if i % 2 == 0 else '原件', 'purpose': bounded(f'虚构平潭证明对象{i + 1}：', '仅测试自身表格，不是实际证据。', 80), 'pageRange': bounded(f'虚构页码{i + 1}：', '示例', 32)} for i in range(9)]}
def _run_text(run, value):
    for child in list(run):
        if child.tag != '{' + W + '}rPr':
            run.remove(child)
    for i, line in enumerate(value.split('\n')):
        if i:
            E.SubElement(run, '{' + W + '}br')
        t = E.SubElement(run, '{' + W + '}t')
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = line
def _paragraph_text(paragraph, value):
    runs = paragraph.findall('w:r', N)
    if runs:
        run = runs[0]
        for extra in runs[1:]:
            paragraph.remove(extra)
    else:
        run = E.SubElement(paragraph, '{' + W + '}r')
        style = paragraph.find('w:pPr/w:rPr', N)
        if style is not None:
            run.append(deepcopy(style))
    _run_text(run, value)
def _row_property(row, name):
    prop = row.find('w:trPr', N)
    if prop is None:
        prop = E.Element('{' + W + '}trPr')
        row.insert(0, prop)
    if prop.find('w:' + name, N) is None:
        E.SubElement(prop, '{' + W + '}' + name)
def candidate_fill(payload, *, root):
    kind, v = validate_request(payload, root=root)
    raw = _own_original_bytes(kind, root=root)
    _own_inspect_blank(kind, root=root)
    active = any((v[k] for k in APP if k != 'requests')) or any(v['requests']) if kind == 'application' else any((any(row.values()) for row in v['evidenceList']))
    if not active:
        return raw
    with ZipFile(BytesIO(raw)) as src:
        require(src.testzip() is None, 'Own original CRC differs')
        parser = E.XMLParser(resolve_entities=False, no_network=True)
        document = E.fromstring(src.read('word/document.xml'), parser)
        ps = document.findall('w:body/w:p', N)
        if kind == 'application':
            for index, key, label in [(2, 'applicantName', '申请人：'), (3, 'agentName', '委托代理人：'), (4, 'respondentName', '被申请人：')]:
                if v[key]:
                    _paragraph_text(ps[index], label + v[key])
            for i, value in enumerate(v['requests']):
                if value:
                    runs = ps[7 + i].findall('w:r', N)
                    require(len(runs) == 2, 'Own request run layout changed')
                    _run_text(runs[1], value)
            if v['factsReason']:
                _paragraph_text(ps[11], v['factsReason'])
        else:
            table = document.find('.//w:tbl', N)
            rows = table.findall('w:tr', N)
            items = [r for r in v['evidenceList'] if any(r.values())]
            _row_property(rows[0], 'tblHeader')
            for unused in rows[1 + len(items):-1]:
                table.remove(unused)
            rows = table.findall('w:tr', N)
            for i, row in enumerate(rows[1:-1]):
                _row_property(row, 'cantSplit')
                values = [str(i + 1), *[items[i][k] for k in ITEM]]
                for cell, value in zip(row.findall('w:tc', N), values):
                    _paragraph_text(cell.find('w:p', N), value)
            pages = str(sum((int(r['pageCount']) for r in items))) if all((r['pageCount'] for r in items)) else '____'
            _paragraph_text(rows[-1].find('w:tc/w:p', N), f'以上证据材料合计 {len(items)}份（组） {pages}页')
        xml = E.tostring(document, encoding='UTF-8', xml_declaration=True, standalone=True)
        out = BytesIO()
        with ZipFile(out, 'w') as target:
            for member in src.infolist():
                target.writestr(member, xml if member.filename == 'word/document.xml' else src.read(member.filename))
    return out.getvalue()

QA_REPORT='reports/overnight-gap-closure-20261030/localities/fujian-l/integration-qa-v1'
WORD_MANIFEST=QA_REPORT+'/WORD-MANIFEST.json'
STAGE_RECEIPT=QA_REPORT+'/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT=QA_REPORT+'/FINAL-BROWSER-QA.json'
REGIONS={'350128':{**IDENTITY,'manifest_sha256':SOURCE_SHA,'allowed_kinds':['application','evidence'],'templates':{kind:{**t,'source_file':(BASE/t['file']).as_posix()} for kind,t in TEMPLATES.items()}}}
_METADATA={'version','region_id','content_hash'}
_FAILURES=(ValueError,OSError,KeyError,TypeError,StopIteration,AttributeError)
def _code(code):
 require(type(code) is str and code=='350128','Only exact own Pingtan350128 identity supported')
 return REGIONS[code]
def source_files(root,code=None):
 if code is not None:_code(code)
 m,*_=_sources(root)
 return [(BASE/'SOURCE-PROJECTION-MANIFEST.json').as_posix(),*[(BASE/name).as_posix() for name in m['files']]]
def _field(value,n,capture_sha,pointer,label):
 return {'raw_value':value,'normalized_value':value.strip(),'source_url':SOURCE_URL,'region_code':'350128','source_label':label,'source_pointer':pointer,'capture_file':(BASE/'own-guide-native-dom.json').as_posix(),'capture_sha256':capture_sha,'collected_at':n['observed_at'],'verified_at':n['observed_at'],'verification_status':'verified'}
def parse_capture(code,*,root):
 _code(code);m,n,d,b,q=_sources(root);cap=m['files']['own-guide-native-dom.json']['sha256'];fields={}
 for name,item in n['raw_fields'].items():fields[name]={**deepcopy(item),**_field(item['raw_value'],n,cap,item['source_pointer'],item.get('raw_label',name))}
 for display,name in {'承诺办结时限':'承诺时限','法定办结时限':'法定时限','咨询方式':'联系电话','必须到现场原因':'必须现场办理原因','服务对象':'申报对象'}.items():fields[display]=deepcopy(fields[name])
 for label in ['办理时间','办理地点','交通指引']:
  match=re.search(r'(?:^|\n)'+label+'：([^\n]+)',d['raw_public_text']);require(match is not None,'Own window statement missing')
  fields[label]=_field(match.group(1),n,cap,f'text/{label}@{match.start(1)}:{match.end(1)}',label)
 fees=[(ti,ri,row[1]) for ti,table in enumerate(d['tables']) for ri,row in enumerate(table) if len(row)==2 and row[0].strip().rstrip('：:')=='是否收费']
 require(len(fees)==1 and fees[0][2]==n['fee_literal'],'Own fee source differs')
 ti,ri,value=fees[0];fields['是否收费']=_field(value,n,cap,f'tables[{ti}][{ri}][1]','是否收费')
 require(n['visit_count_badge_literal']=='服务承诺到现场次数\n1 次' and n['visit_count_badge_literal'] in d['raw_public_text'],'Own visit badge differs')
 fields['到办事现场次数']=_field('1 次',n,cap,'text/服务承诺到现场次数','到现场次数')
 materials=[]
 for panel in n['materials']:
  raw=panel['raw_public_text'];labels=list(re.finditer(r'(?:^|\n)([^\n\t]{1,40})\t[ \t]*',raw));details={}
  for i,label in enumerate(labels):details[label.group(1).rstrip('：:').strip()]=raw[label.end():labels[i+1].start() if i+1<len(labels) else len(raw)].strip()
  copies=re.search(r'(\d+)份',panel['copies_literal']);original=re.search(r'材料类型：([^\n]+)',details.get('材料要求',''));require(copies and original,'Own material copy source missing')
  materials.append({'id':panel['material_id'],'name':panel['name'],'required':details.get('材料必要性',''),'format':details.get('材料形式',''),'copies':int(copies.group(1)),'paper_copies':int(copies.group(1)),'copies_source_literal':panel['copies_literal'],'copies_are_source_metadata':True,'original_copy':original.group(1).strip(),'instructions':panel['notes_literal'] or '', 'details':details,'raw_source_text':raw,'source_url':SOURCE_URL,'capture_file':(BASE/'own-guide-native-dom.json').as_posix(),'capture_sha256':cap})
 templates=[]
 for a in b['attachments']:
  kind=a['eligible_kind']
  templates.append({'id':a['file_id'],'annex_id':a['file_id'],'material_id':a['material_id'],'region_code':'350128','official_kind':'blank' if kind else 'sample' if a['official_type_raw']=='2' else 'reference','official_reported_type':a['official_type_raw'],'original_name':a['official_label'],'file_type':'docx','source_url':SOURCE_URL,'download_url':a['public_download_url'],'file':(BASE/a['file']).as_posix() if a['file'] else None,'sha256':a['sha256'],'bytes':a['bytes'],'download_status':'downloaded' if kind else 'metadata_only','can_generate':False,'document_types':[],'eligible_own_kind':kind,'content_role':a['content_role'],'sample_contents_verified':False})
 conditions=re.search(r'受理条件\n(1[、.].+?)\n申报材料',d['raw_public_text'],re.S);require(conditions is not None,'Own reception conditions unavailable')
 return {**IDENTITY,'province_name':'福建省','service_name':n['service_name_literal'],'source_version':SOURCE_SHA,'official_version':None,'committee_full_name':None,'committee_autofill_allowed':False,'verification_status':'partial','guide_status':'partial','collected_at':n['observed_at'],'verified_at':n['observed_at'],'fields':fields,'materials':materials,'templates':templates,'sections':{'本区公开办事指南原文':d['raw_public_text'],'办理流程与窗口办理':n['source_workflow_and_window_literal'],'受理条件':conditions.group(1)},'can_generate':False,'published':False,'publication_status':'source_only','channel':{'raw_value':n['handling_literal'],'online_status':'unverified','entry_url':None,'entry_check':{'status':'unverified','scope':n['online_depth_literal']},'submission_verified':False},'evidence':{'capture_file':(BASE/'own-guide-native-dom.json').as_posix(),'capture_sha256':cap,'source_projection':(BASE/'SOURCE-PROJECTION-MANIFEST.json').as_posix(),'source_projection_sha256':SOURCE_SHA},'warnings':['已核对本地区公开来源；资料版本和仲裁委员会全称仍需向办理机构确认。','官网份数和按人数提供副本的说明均保留，请在提交前向办理机构核对。','网上办理情况仍待核实；未核实不表示当地不支持。示例样表和材料说明不用于自动生成。']}
def prepare_candidate(code,*,root):
 g=parse_capture(code,root=root);g.update(offline_candidate=True,generation_adapter=ADAPTER,publication_status='unregistered_offline_candidate');return g
def defaults(code,kind):_code(code);return _own_defaults(kind)
def form_fields(code,kind):_code(code);return _own_form_fields(kind)
def schema_descriptor(code,kind):_code(code);return _own_schema_descriptor(kind)
def example_data(code,kind,stress=False,*,root):
 _code(code);_sources(root);return _word_example_data(kind,stress)
def envelope(code,kind,data,*,root):_code(code);return _own_envelope(kind,data,root=root)
def validate_request(payload,*,root):
 require(type(payload) is dict,'Own L request object required');_code(payload.get('region_code'));return _own_validate_request(payload,root=root)
def original_bytes(code,kind,*,root):_code(code);return _own_original_bytes(kind,root=root)
def template_path(code,kind,*,root):
 _code(code);t=_kind(kind);_sources(root);return path_at(root,BASE/t['file'])
def _word_manifest(root):
 require(type(WORD_SHA) is str and re.fullmatch('[a-f0-9]{64}',WORD_SHA),'Own Word proof not independently pinned')
 raw=_bytes(root,WORD_MANIFEST);require(sha256(raw).hexdigest()==WORD_SHA,'Own public Word proof changed');m=json.loads(raw)
 require(m['eligible_originals']==2 and m['fictional_fixtures']==4 and m['word_documents']==6 and m['original_pages']==3 and m['generated_pages']==23 and m['stage_approved'] is False and m['can_publish'] is False,'Own Word scope differs')
 require(m['source_versions']=={'350128':SOURCE_SHA} and m['actual_new_safe_projection_regeneration'] is True and m['same_request_claimed'] is False,'Own public source rebind proof required')
 require(type(m['files']) is list and m['files'] and len({x['path'] for x in m['files']})==len(m['files']),'Own Word leaf set differs')
 for leaf in m['files']:
  require(leaf['path'].startswith(QA_REPORT+'/'),'Own Word leaf outside public QA');body=_bytes(root,leaf['path'])
  require(type(leaf['bytes']) is int and len(body)==leaf['bytes'] and sha256(body).hexdigest()==leaf['sha256'],'Own Word leaf changed')
 return m
def approval_requirements(*,stage=True):
 result={'identities':[{**{k:IDENTITY[k] for k in ['region_code','source_id','service_code']},'manifest_sha256':SOURCE_SHA}],'word_manifest_sha256':WORD_SHA,'eligible_originals':2,'approved_by':'independent_root','visual_review':'PASS','source_projection_review':'PASS','can_publish':not stage,'model_calls':0}
 if not stage:result.update(stage_receipt_sha256=STAGE_SHA256,native_confirmation_download_own_forms=True)
 return result
def _receipt(root,stage=True):
 pin=STAGE_SHA256 if stage else PUBLICATION_SHA256
 require(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin),'Own independent phase not approved')
 _sources(root);word=_word_manifest(root)
 if not stage:_receipt(root,True)
 raw=_bytes(root,STAGE_RECEIPT if stage else PUBLICATION_RECEIPT);require(sha256(raw).hexdigest()==pin,'Own approval bytes changed');r=json.loads(raw)
 require(all(k in r and exact(r[k],v) for k,v in approval_requirements(stage=stage).items()),'Own approval scope differs')
 require(type(r.get('files')) is list and r['files'] and len({x['path'] for x in r['files']})==len(r['files']),'Own approval leaf set invalid')
 if stage:require(exact(r['files'],word['files']),'Complete own Word proof must be stage-approved')
 else:
  final={x['path']:x for x in r['files']}
  require(all(x['path'] in final and exact(final[x['path']],x) for x in word['files']),'Final must preserve all own Word leaves')
 for leaf in r['files']:
  require(leaf['path'].startswith(QA_REPORT+'/'),'Approval leaf outside own QA');body=_bytes(root,leaf['path'])
  require(type(leaf['bytes']) is int and len(body)==leaf['bytes'] and sha256(body).hexdigest()==leaf['sha256'],'Own approval leaf changed')
 return {'receipt':STAGE_RECEIPT if stage else PUBLICATION_RECEIPT,'sha256':pin}
def staged_candidate(code,*,root):
 g=prepare_candidate(code,root=root);g['candidate_adapter_evidence']=_receipt(root);g.update(can_generate=True,offline_candidate=False,publication_status='staged_own_word_qa')
 for kind,t in TEMPLATES.items():
  row=next(x for x in g['templates'] if x['id']==t['file_id']);row.update(can_generate=True,document_types=[kind],adapter=ADAPTER,generation_mode='blank')
 return g
def _published(code,root):
 g=staged_candidate(code,root=root);g['publication_adapter_evidence']=_receipt(root,False);g.update(published=True,publication_status='published');return g
def _matches(g,c):
 if type(g) is not dict or set(g)-set(c)-_METADATA:return False
 if 'version' in g and (type(g['version']) is not int or g['version']<1):return False
 key=sha256(json.dumps(['fujian','平潭综合实验区','平潭综合实验区'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
 if 'region_id' in g and g['region_id']!=key:return False
 if 'content_hash' in g and (type(g['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}',g['content_hash'])):return False
 return all(k in g and exact(g[k],v) for k,v in c.items())
def _bound(g,root,allow_source=False):
 require(type(g) is dict,'Own guide object required');code=g.get('region_code');raw=parse_capture(code,root=root)
 if allow_source and _matches(g,raw):return raw
 canonical=_published(code,root) if g.get('published') is True or 'publication_adapter_evidence' in g else staged_candidate(code,root=root)
 require(_matches(g,canonical),'Own canonical guide binding differs');return canonical
def with_capabilities(g,*,root):_bound(g,root,True);return deepcopy(g)
def with_publication_evidence(g,*,root):
 require(type(g) is dict and _matches(g,staged_candidate(g.get('region_code'),root=root)),'Own staged guide required')
 result=_published(g['region_code'],root)
 for key in _METADATA&set(g):result[key]=deepcopy(g[key])
 return result
def checked_adapter(g,t,kind,*,root):
 c=_bound(g,root);_kind(kind);expected=next(x for x in c['templates'] if x['id']==TEMPLATES[kind]['file_id'])
 require(exact(t,expected) and expected['can_generate'] is True and expected['official_kind']=='blank','Own stage-approved blank required');return ADAPTER
def public_evidence(g,root):
 try:return deepcopy(_bound(g,root,True)['evidence'])
 except _FAILURES:return None
def approved_report_attachment(g,t,root):
 try:return any(exact(row,t) and row['download_status']=='downloaded' for row in _bound(g,root,True)['templates'])
 except _FAILURES:return False
class _PatchedDocument:
 def __init__(self,body,root):self.body=body;self.root=Path(root).resolve()
 def save(self,destination):
  if hasattr(destination,'write'):destination.write(self.body);return
  path=Path(destination).resolve();require(not path.is_relative_to(self.root/'reports'),'Cannot overwrite source or QA');path.write_bytes(self.body)
def fill_document(g,t,kind,path,data,*,root):
 checked_adapter(g,t,kind,root=root);require(Path(path).resolve()==template_path(g['region_code'],kind,root=root),'Own original path differs')
 return _PatchedDocument(candidate_fill(envelope(g['region_code'],kind,data,root=root),root=root),root)
