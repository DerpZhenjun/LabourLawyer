"""Source-bound application drafts for the two verified municipal blank layouts."""

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from string import ascii_letters, punctuation

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from pydantic import BaseModel, ConfigDict, Field

from regional_fixed_layout import fixed_line
from regional_guides import digest


ROOT = Path(__file__).resolve().parents[1]
MUNICIPAL_SELECTION = '市本级'
_ASSETS = Path('templates/_docx/_regional/yangquan-jinzhou')
_REPORT = Path('reports/yangquan-jinzhou-application')

PROFILES = {
    '140300': {
        'adapter': 'shanxi_yangquan_application_v1',
        'source': _REPORT / '140300-SOURCE.json',
        'source_sha': '3f22f02a6d6b42a53ba7c7ed15bfbcf8c554c44091dbd67ab6d8073e10447607',
        'original': _ASSETS / '140300-original.docx',
        'layout': _ASSETS / '140300-layout.docx',
        'origin': 'official-blank-filled',
    },
    '210700': {
        'adapter': 'liaoning_jinzhou_application_v1',
        'source': _REPORT / '210700-SOURCE.json',
        'source_sha': '50879100f7d1a980f37796515c1aac534fd2d6bc91708ab74a6787d41bcdc9e9',
        'original': _ASSETS / '210700-original.doc',
        'layout': _ASSETS / '210700-layout.docx',
        'origin': 'official-blank-converted-filled',
    },
}
YANGQUAN_ADAPTER = PROFILES['140300']['adapter']
JINZHOU_ADAPTER = PROFILES['210700']['adapter']
ADAPTERS = frozenset({YANGQUAN_ADAPTER, JINZHOU_ADAPTER})
NAME_WIDTH = 22
BODY_WIDTH = 40
WIDE_LATIN = ascii_letters + punctuation


class Application(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    applicantName: fixed_line(NAME_WIDTH, WIDE_LATIN) = ''
    respondentName: fixed_line(NAME_WIDTH, WIDE_LATIN) = ''
    facts: list[fixed_line(BODY_WIDTH, WIDE_LATIN)] = Field(default_factory=list, max_length=6)


class YangquanApplication(Application):
    requests: list[fixed_line(BODY_WIDTH, WIDE_LATIN)] = Field(default_factory=list, max_length=3)


class JinzhouApplication(Application):
    requests: list[fixed_line(BODY_WIDTH, WIDE_LATIN)] = Field(default_factory=list, max_length=7)
    evidence: list[fixed_line(BODY_WIDTH, WIDE_LATIN)] = Field(default_factory=list, max_length=2)


MODELS = {YANGQUAN_ADAPTER: YangquanApplication, JINZHOU_ADAPTER: JinzhouApplication}


def _verified_bytes(root, relative, checksum):
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError('市本级证据路径超出候选根目录')
    try:
        contents = target.read_bytes()
    except OSError as exc:
        raise ValueError('缺少市本级已核对原件或版式文件') from exc
    if sha256(contents).hexdigest() != checksum:
        raise ValueError('市本级证据原件或版式文件字节已变化')
    return contents


def _source(code, root):
    if code not in PROFILES:
        raise ValueError('该市未绑定本级申请书')
    profile = PROFILES[code]
    return json.loads(_verified_bytes(root, profile['source'], profile['source_sha']))


def staged_guide(code, root=None):
    root = Path(ROOT if root is None else root).resolve()
    source = _source(code, root)
    profile = PROFILES[code]
    _verified_bytes(root, profile['original'], source['original_sha256'])
    _verified_bytes(root, profile['layout'], source['layout_sha256'])
    url = source['guide_url']
    fields = {'实施机关': source['authority'], '办理地点': source['office']}
    if source.get('consultation'):
        fields['咨询方式'] = source['consultation']
    return {
        'province': source['province'], 'province_name': source['province_name'],
        'city': source['city'], 'district': MUNICIPAL_SELECTION, 'scope_level': 'municipal',
        'region_code': code, 'authority': source['authority'], 'fields': fields,
        'service_name': '劳动人事争议仲裁申请', 'source_title': source['city'] + '劳动人事争议仲裁申请',
        'source_url': url, 'source_id': digest(url)[:24], 'source_version': profile['source_sha'],
        'collected_at': source['source_capture']['collected_at'] if code == '140300' else source['source_capture']['captured_at'],
        'verified_at': source['verified_at'], 'verification_status': 'partial',
        'published': False, 'can_generate': True, 'materials_complete': False,
        'channel': {'online_status': 'unverified', 'entry_url': None, 'submission_verified': False},
        'materials': [
            {'id': f'{code}-material-{index}', 'name': row['name'], 'copies': row['copies'],
             'required': '必要', 'source_url': row.get('source_url', url), 'region_code': code}
            for index, row in enumerate(source['rows'], 1)
        ],
        'templates': [{
            'id': f'{code}-municipal-application', 'original_name': source['original_name'],
            'region_code': code, 'guide_source_url': url, 'source_url': url,
            'official_kind': 'blank', 'original_format': source['source_format'],
            'official_sha256': source['original_sha256'], 'file': profile['layout'].as_posix(),
            'sha256': source['layout_sha256'], 'file_type': 'docx',
            'file_origin': 'official-blank-converted-layout' if code == '210700' else 'official-blank-layout',
            'download_status': 'official_link_only', 'adapter': profile['adapter'],
            'document_types': ['application'], 'can_generate': True, 'generation_mode': 'blank',
        }],
        'sections': {'待核材料': source['unresolved']},
        'warnings': [
            '阳泉空表按自然人申请人版式填写。' if code == '140300' else '锦州原表设姓名或单位名称栏，单位提交材料仍待核。',
            '请在原表补全其他当事人信息、附件份数和签章日期。', source['unresolved'],
        ],
    }


def exact_municipal(guide, root=None):
    if guide.get('region_code') not in PROFILES:
        return False
    try:
        expected = staged_guide(guide['region_code'], root)
    except ValueError:
        return False
    keys = ('province', 'city', 'district', 'region_code', 'scope_level', 'authority',
            'source_id', 'source_url', 'source_version')
    return all(guide.get(key) == expected[key] for key in keys)


def checked_adapter(guide, template, kind, root=None):
    if kind != 'application' or guide.get('region_code') not in PROFILES:
        raise ValueError('仅能填写本级申请书')
    expected = staged_guide(guide['region_code'], root)
    keys = ('province', 'city', 'district', 'region_code', 'scope_level', 'authority',
            'source_id', 'source_url', 'source_version', 'materials_complete')
    if any(guide.get(key) != expected[key] for key in keys) or template != expected['templates'][0]:
        raise ValueError('市本级申请书与已核验原件绑定不匹配')
    return template['adapter']


def schema_descriptor(adapter, source_version):
    labels = {'applicantName': '申请人姓名或名称', 'respondentName': '被申请人姓名或名称',
              'requests': '仲裁请求（逐行）', 'facts': '事实和理由（逐行）', 'evidence': '证据和证据来源（逐行）'}
    if adapter == YANGQUAN_ADAPTER:
        labels['applicantName'] = '自然人申请人姓名'
    model = MODELS[adapter]
    fields = []
    for key, prop in model.model_json_schema()['properties'].items():
        field = {'key': key, 'label': labels[key], 'type': 'text'}
        if prop['type'] == 'array':
            field.update(type='text_list', maxItems=prop['maxItems'], maxLength=BODY_WIDTH)
        else:
            field['maxLength'] = NAME_WIDTH
        fields.append(field)
    return {'schema_id': adapter, 'schema_version': 1, 'source_version': source_version,
            'fields': fields, 'defaults': model().model_dump(),
            'policy': {'unknown_fields': 'reject', 'invalid_xml': 'reject', 'text_controls': 'newline_only',
                       'trim_text': True, 'capacity_is_official_requirement': False, 'signature_field': 'manual_only'}}


def _append_in_style(paragraph, value):
    props = paragraph._p.xpath('./w:pPr/w:rPr')
    run = paragraph.add_run(value)
    if props:
        run._r.insert(0, deepcopy(props[0]))


def fill_application(adapter, layout, values):
    data = MODELS[adapter].model_validate(values)
    doc = Document(BytesIO(layout))
    if adapter == YANGQUAN_ADAPTER:
        paragraphs = doc.paragraphs
        if len(paragraphs) != 40 or doc.tables or paragraphs[22].text != '×××劳动人事争议仲裁委员会':
            raise ValueError('阳泉申请书空白结构已变化')
        paragraphs[22].runs[0].text = '阳泉市劳动人事争议仲裁委员会'
        if data.applicantName:
            paragraphs[2].runs[1].text = data.applicantName + '  '
        if data.respondentName:
            _append_in_style(paragraphs[7], data.respondentName)
        if data.requests:
            for index in range(3):
                runs = paragraphs[16 + index].runs
                if index < len(data.requests):
                    runs[3].text = data.requests[index]
                else:
                    for run in runs:
                        run.text = ''
            paragraphs[19].runs[0].text = ''
        if data.facts:
            runs = paragraphs[20].runs
            runs[1].text = '\n'.join(data.facts)
            for run in runs[2:]:
                run.text = ''
            # Preserve the explanatory note on page two when added facts occupy
            # space taken by the source's empty signature-to-note spacer rows.
            for paragraph in paragraphs[29:29 + len(data.facts) - 1]:
                paragraph._p.getparent().remove(paragraph._p)
        if data.requests or data.facts:
            paragraphs[21].paragraph_format.keep_with_next = True
        return doc

    if len(doc.tables) != 1 or len(doc.tables[0].rows) != 27 or '锦州市劳动人事争议仲裁院' != doc.paragraphs[6].text:
        raise ValueError('锦州申请书空白结构已变化')
    rows = doc.tables[0].rows
    unique_cells = list({cell._tc: cell for cell in rows[1].cells}.values())
    for cell, value in ((unique_cells[1], data.applicantName), (unique_cells[3], data.respondentName)):
        if value:
            _append_in_style(cell.paragraphs[0], value)
    for start, values in ((10, data.requests), (18, data.facts), (25, data.evidence)):
        for index, value in enumerate(values, start):
            if value:
                paragraph = rows[index].cells[0].paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                # The original empty request rows carry 26pt bold paragraph
                # marks. Use the 12pt size of the adjacent printed field label.
                for props in paragraph._p.xpath('./w:pPr/w:rPr'):
                    props.getparent().remove(props)
                run = paragraph.add_run(value)
                run.font.size = Pt(12)
                run.bold = False
    return doc
