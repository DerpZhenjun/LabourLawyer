"""Audited writable slots shared by the web, Android and WeChat clients."""
import json
from pathlib import Path

FORM_SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'config/document_forms.json').read_text(encoding='utf8'))


def province_form(slug):
    return {
        'version': FORM_SCHEMA['version'],
        'applicationFields': FORM_SCHEMA['applicationSupportedFields'].get(slug, []),
        'evidenceFields': FORM_SCHEMA['evidenceSupportedFields'].get(slug, []),
        'limits': FORM_SCHEMA['limits'].get(slug, FORM_SCHEMA['limits']['default']),
        'fieldDefinitions': FORM_SCHEMA['fields'],
    }


def validate_content(slug, payload, kind):
    limits = province_form(slug)['limits']
    if kind == 'application':
        if len(payload.requests) > limits['maxRequests']:
            raise ValueError(f"当前模板最多支持 {limits['maxRequests']} 项请求")
        if any(len(item) > limits['requestLength'] for item in payload.requests):
            raise ValueError(f"单项请求不能超过 {limits['requestLength']} 字")
        if len(payload.factsReason) > limits['factsLength']:
            raise ValueError(f"事实与理由不能超过 {limits['factsLength']} 字")
    else:
        if len(payload.evidenceList) > limits['maxEvidence']:
            raise ValueError(f"证据清单最多支持 {limits['maxEvidence']} 项")
        for index, item in enumerate(payload.evidenceList, 1):
            if not item.name.strip() and any(str(value).strip() for key, value in item.model_dump().items() if key != 'name'):
                raise ValueError(f'第 {index} 项证据填写了内容，请补充证据名称')
