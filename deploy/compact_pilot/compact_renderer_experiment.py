"""Private renderer experiment gated by the compact contract and original proof."""

from copy import deepcopy
from io import BytesIO
import re

from docx import Document

import compact_renderer_legacy as legacy
import regional_fujian_oct31m as fujian_m
import regional_fujian_oct31o as fujian_o
import regional_fujian_oct31p as fujian_p
import regional_jiangsu_oct29e as jiangsu_e
import regional_jiangsu_oct30f as jiangsu_f
import regional_zhejiang_chunan_oct30 as chunan
import regional_zhejiang_oct29d as zhejiang_d
import regional_zhejiang_oct29e as zhejiang_e
from regional_documents import PreservedPackageDocument
from regional_form_contracts import validate_contract_data
from routes.regional_guides import generation_request_model


_JIANGSU = {provider.ADAPTER: provider for provider in (jiangsu_e, jiangsu_f)}
_ZHEJIANG = {provider.ADAPTER: provider for provider in (zhejiang_d, zhejiang_e, chunan)}
_FUJIAN = {provider.ADAPTER: provider for provider in (fujian_m, fujian_o, fujian_p)}
SUPPORTED_ADAPTERS = frozenset(_JIANGSU.keys() | _ZHEJIANG.keys() | _FUJIAN.keys() | legacy.ADAPTERS)


def render(proof, binding, raw_data):
    contract, original = proof.read(binding)
    adapter = contract['context']['adapter']
    kind = binding['kind']
    if adapter not in SUPPORTED_ADAPTERS:
        raise ValueError('No pilot renderer for this adapter')
    fields = validate_contract_data(contract, raw_data)
    data = generation_request_model(adapter, kind).model_validate(fields).model_dump()
    if adapter in legacy.ADAPTERS:
        return legacy.fill(adapter, original, kind, data, _fujian_values)
    if adapter in _FUJIAN:
        provider = _FUJIAN[adapter]
        cleaned = _fujian_values(kind, data, provider.APP, provider.ITEM, provider._text, 9)
        return provider._layout_fill(original, kind, cleaned)
    if adapter in _JIANGSU:
        provider = _JIANGSU[adapter]
        values = provider._validate_data(kind, data)
    else:
        provider = _ZHEJIANG[adapter]
        provider._validate_data(kind, data)
        values = deepcopy(data)
    document = Document(BytesIO(original))
    fill = provider._application if kind == 'application' else provider._evidence
    fill(document, values)
    output = BytesIO()
    PreservedPackageDocument(document, original).save(output)
    return output.getvalue()


def _fujian_values(kind, data, app_fields, item_fields, clean_text, row_limit):
    """Keep each selected provider's text and evidence-row validation."""
    if kind == 'application':
        if set(data).difference(app_fields):
            raise ValueError('Unknown application field')
        cleaned = dict.fromkeys((key for key in app_fields if key != 'requests'), '')
        cleaned['requests'] = []
        for key, value in data.items():
            if key == 'requests':
                if type(value) is not list or len(value) > 3:
                    raise ValueError('Invalid request list')
                cleaned[key] = [clean_text(item, 360) for item in value]
            else:
                cleaned[key] = clean_text(value, 2400 if key == 'factsReason' else 180)
        return cleaned

    if set(data).difference({'evidenceList'}):
        raise ValueError('Unknown evidence field')
    rows = data.get('evidenceList', [])
    if type(rows) is not list or len(rows) > row_limit:
        raise ValueError('Invalid evidence list')
    capacities = {'name': 60, 'pageCount': 4, 'originalType': 4, 'purpose': 80, 'pageRange': 32}
    cleaned = []
    for row in rows:
        if type(row) is not dict or set(row).difference(item_fields):
            raise ValueError('Unknown evidence item field')
        item = dict.fromkeys(item_fields, '')
        item.update({key: clean_text(value, capacities[key]) for key, value in row.items()})
        pages = item['pageCount']
        if item['originalType'] not in {'', '原件', '复印件'} or (pages and not re.fullmatch('[1-9][0-9]{0,3}', pages)):
            raise ValueError('Invalid page count or original/copy role')
        cleaned.append(item)
    return {'evidenceList': cleaned}
