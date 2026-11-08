"""Locality-free OOXML mechanics; invoke only after complete own API/source proof."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from pathlib import PureWindowsPath,PurePosixPath
from lxml import etree as E
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
N={'w':W}

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
