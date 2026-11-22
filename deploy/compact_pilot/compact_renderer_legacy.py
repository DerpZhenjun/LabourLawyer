"""Run the original exact layout engines on admitted original bytes in private QA."""

from copy import deepcopy
from io import BytesIO
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from docx import Document

import regional_fujian_oct31i as fujian_i
import regional_fujian_oct31j as fujian_j
import regional_fujian_oct31k as fujian_k
import regional_jiangsu_oct29 as jiangsu_a
import regional_jiangsu_oct29c as jiangsu_c
import regional_jiangsu_oct31g as jiangsu_g
import regional_zhejiang_oct29 as ningbo
from regional_documents import PreservedPackageDocument


_JIANGSU = {jiangsu_a.ADAPTER, jiangsu_c.ADAPTER}
_FUJIAN = {
    fujian_i.ADAPTER: (fujian_i, fujian_i._text, 15),
    fujian_j.ADAPTER: (fujian_j, fujian_j.text, 15),
    fujian_k.ADAPTER: (fujian_k, fujian_k.text, 9),
}
ADAPTERS = frozenset(_JIANGSU | _FUJIAN.keys() | {jiangsu_g.ADAPTER, ningbo.ADAPTER})


def fill(adapter, original, kind, data, normalize_fujian):
    if adapter in _FUJIAN:
        provider, text, capacity = _FUJIAN[adapter]
        cleaned = normalize_fujian(kind, data, provider.APP_FIELDS, provider.ITEM_FIELDS, text, capacity)
        return _fujian_layout(provider, original, kind, cleaned)
    if adapter == jiangsu_g.ADAPTER:
        doc = _kunshan(original, kind, data)
    else:
        # The legacy selectors require a pathname. Only a privately staged
        # copy of the already verified original is supplied to them.
        with TemporaryDirectory(prefix='pl-compact-fill-') as staging:
            path = Path(staging, 'input.docx')
            path.write_bytes(original)
            if adapter == ningbo.ADAPTER:
                doc = _ningbo(path, kind, data)
            elif adapter in _JIANGSU:
                doc = _jiangsu(path, kind, data, adapter == jiangsu_c.ADAPTER)
            else:
                raise ValueError('No scoped legacy renderer')
    output = BytesIO()
    PreservedPackageDocument(doc, original).save(output)
    return output.getvalue()


def _page_counts(data):
    return [{**item, 'pageCount': re.sub(r'^\s*(\d+)\s*页\s*$', r'\1', str(item.get('pageCount', '')))}
            for item in data.get('evidenceList', [])]


def _jiangsu(path, kind, data, use_blank_request):
    values = deepcopy(data)
    if kind == 'evidence':
        values['evidenceList'] = _page_counts(values)
        return jiangsu_a.fill_evidence(values, path, profile='JiangSuSheng')
    if values.get('copyCount') is None:
        values['copyCount'] = '    '
    if use_blank_request and not values.get('requests'):
        values['requests'] = ['']
    document = jiangsu_a.fill_application(values, path, profile='JiangSuSheng')
    for paragraph in document.paragraphs:
        match = re.search(r'相关证据(?P<slot>[\d \t]+)(?=份)', paragraph.text)
        if match:
            copies = values.get('evidenceCopyCount')
            jiangsu_a.replace_span(paragraph, match.start('slot'), match.end('slot'),
                                   str(copies) if copies is not None else '    ')
    closing = False
    for paragraph in document.paragraphs:
        compact = ''.join(paragraph.text.split())
        if compact == '此致':
            closing = True
        if closing:
            if compact.endswith('日') and '年' in compact and '月' in compact:
                break
            paragraph.paragraph_format.keep_with_next = True
    return document


def _kunshan(original, kind, data):
    document = Document(BytesIO(original))
    values = jiangsu_g._validate_data(kind, data)
    if kind == 'application':
        jiangsu_g.application_fill(document, {key: value for key, value in values.items() if value is not None})
    else:
        rows = [row for row in values.get('evidenceList', []) if any(row.values())] or [{}]
        empty = dict.fromkeys(jiangsu_g.ITEM_FIELDS, '')
        values['evidenceList'] = [{**empty, **row} for row in rows]
        jiangsu_g.evidence_fill(document, values)
    return document


def _ningbo(path, kind, data):
    values = deepcopy(data)
    if values.get('copyCount') is None:
        values['copyCount'] = '    '
    if kind == 'application':
        document = ningbo.generate_LAdocx(values, path)
        for cell in document.tables[0].rows[12].cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = True
        tail = document.add_paragraph()
        tail.paragraph_format.space_before = ningbo.Pt(0)
        tail.paragraph_format.space_after = ningbo.Pt(0)
        tail.paragraph_format.line_spacing = ningbo.Pt(1)
        run_properties = ningbo.OxmlElement('w:rPr')
        size = ningbo.OxmlElement('w:sz')
        size.set(ningbo.qn('w:val'), '2')
        run_properties.append(size)
        tail._p.get_or_add_pPr().append(run_properties)
        return document

    case_number = values.pop('caseNumber', None)
    values['evidenceList'] = _page_counts(values)
    document = ningbo.fill_evidence(values, path, profile='ZheJiangSheng')
    table = document.tables[0]
    if case_number:
        ningbo.set_cell_text(table.rows[0].cells[1], case_number)
    for row in table.rows[:2]:
        _set_row_property(row, 'w:tblHeader')
    for row in table.rows:
        _set_row_property(row, 'w:cantSplit')
    for row in table.rows[-2:]:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = True
    return document


def _set_row_property(row, element):
    props = row._tr.get_or_add_trPr()
    if props.find(ningbo.qn(element)) is None:
        props.append(ningbo.OxmlElement(element))


def _fujian_layout(provider, raw, kind, values):
    if not any(values.values()) or (
        kind == 'evidence' and not any(any(row.values()) for row in values['evidenceList'])
    ) or (
        kind == 'application' and not any(values['requests'])
        and not any(value for key, value in values.items() if key != 'requests')
    ):
        return raw
    ns, xml, uri = provider.N, provider.E, '{' + provider.W + '}'
    document = provider.blank_layout(raw, kind)
    paragraphs = document.findall('w:body/w:p', ns)
    if kind == 'application':
        _fujian_application(provider, values, paragraphs, ns, xml, uri)
    else:
        _fujian_evidence(provider, values, document, ns, xml, uri)
    patched = xml.tostring(document, encoding='UTF-8', xml_declaration=True, standalone=True)
    output = BytesIO()
    with ZipFile(BytesIO(raw)) as source, ZipFile(output, 'w') as result:
        for member in source.infolist():
            result.writestr(member, patched if member.filename == 'word/document.xml' else source.read(member.filename))
    return output.getvalue()


def _fujian_application(provider, values, paragraphs, ns, xml, uri):
    spots = [(2, 'applicantName', '申请人：'), (3, 'agentName', '委托代理人：'), (4, 'respondentName', '被申请人：')]
    for index, key, label in spots:
        if values[key]:
            provider.replace_text(paragraphs[index], label + values[key])
    for paragraph, claim in zip(paragraphs[7:10], values['requests']):
        if claim:
            paragraph.findall('.//w:t', ns)[1].text = claim
    if values['factsReason']:
        provider.replace_text(paragraphs[11], values['factsReason'])
    for paragraph in paragraphs[15:20]:
        props = paragraph.find('w:pPr', ns)
        if props is None:
            props = xml.Element(uri + 'pPr')
            paragraph.insert(0, props)
        keep = props.find('w:keepNext', ns)
        if keep is None:
            keep = xml.SubElement(props, uri + 'keepNext')
        keep.set(uri + 'val', '1')


def _fujian_evidence(provider, values, document, ns, xml, uri):
    table = document.find('.//w:tbl', ns)
    rows = table.findall('w:tr', ns)
    items = [row for row in values['evidenceList'] if any(row.values())]
    xml.SubElement(rows[0].find('w:trPr', ns), uri + 'tblHeader')
    for unused in rows[1 + len(items):-1]:
        table.remove(unused)
    rows = table.findall('w:tr', ns)
    while provider is not fujian_k and len(rows) - 2 < len(items):
        node = deepcopy(rows[1])
        table.insert(list(table).index(rows[-1]), node)
        rows = table.findall('w:tr', ns)
    for index, (row, item) in enumerate(zip(rows[1:-1], items, strict=True), start=1):
        xml.SubElement(row.find('w:trPr', ns), uri + 'cantSplit')
        fields = [str(index), item['name'], item['pageCount'], item['originalType'], item['purpose'], item['pageRange']]
        for cell, value in zip(row.findall('w:tc', ns), fields, strict=True):
            provider.replace_text(cell.find('w:p', ns), value)
    pages = str(sum(int(row['pageCount']) for row in items)) if all(row['pageCount'] for row in items) else '____'
    provider.replace_text(rows[-1].find('w:tc/w:p', ns), f'以上证据材料合计 {len(items)}份（组） {pages}页')
