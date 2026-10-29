"""Public collection reviews, separate from verified-guide publication and generation."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

TEMPLATE_STATES = {'not_checked', 'blank_found', 'sample_only',
                   'not_found_in_checked_sources', 'officially_not_provided'}


def official_url(value):
    address = urlsplit(value if isinstance(value, str) else '')
    if address.scheme != 'https' or not (address.hostname or '').endswith('.gov.cn') or address.username or address.password:
        raise ValueError('来源必须是公开的HTTPS政府网站')
    return value


def validate_record(record, root=None):
    row = deepcopy(record)
    for key in ['province', 'city', 'district', 'note']:
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError('逐地核验记录缺少明确字段：'+key)
        row[key] = row[key].strip()
    if not re.fullmatch(r'\d{6}(?:\d{6})?', str(row.get('region_code', ''))):
        raise ValueError('区县来源编码缺失')
    official_url(row.get('source_url'))
    try:
        checked = datetime.fromisoformat(row.get('checked_at', '').replace('Z', '+00:00'))
        if checked.tzinfo is None: raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('核验时间须含明确时区') from None
    if row.get('guide_status') not in {'candidate', 'discovery_only'} or row.get('generation_enabled') is not False:
        raise ValueError('采集登记不能授予发布或生成权限')
    if row['guide_status'] == 'candidate' and not row.get('authority'):
        raise ValueError('正式指南候选须核对自身实施机关')
    if not isinstance(row.get('reviewed_sections'), list) or not row['reviewed_sections']:
        raise ValueError('需要保留已查栏目，不能用未采集代替缺失')
    templates = row.get('templates', [])
    if not isinstance(templates, list): raise ValueError('附件必须逐份登记')
    for template in templates:
        if (template.get('region_code') != row['region_code']
                or template.get('source_url') != row['source_url']
                or template.get('kind') not in {'blank', 'sample', 'instruction'}
                or not re.fullmatch(r'[0-9a-f]{64}', str(template.get('sha256', '')))
                or not template.get('original_name')):
            raise ValueError('附件必须绑定本地区自己的来源、原名和SHA256')
    for kind in ['application', 'evidence']:
        status = row.get(kind+'_template_status')
        if status not in TEMPLATE_STATES: raise ValueError('模板核验状态不明确')
        own = [t for t in templates if kind in t.get('document_types', [])]
        blank = [t for t in own if t['kind'] == 'blank']
        if status == 'blank_found' and not blank:
            raise ValueError('未找到该地区自己的官方空白模板，不能将样例算作空白')
        if status == 'sample_only' and (blank or not any(t['kind'] == 'sample' for t in own)):
            raise ValueError('样例状态与实际附件不一致')
        if status in {'not_checked', 'not_found_in_checked_sources', 'officially_not_provided'} and own:
            raise ValueError('已经找到附件不能再登记为未查或未找到')
        if status == 'officially_not_provided':
            statement = row.get('official_statements', {}).get(kind, {})
            quote = statement.get('quote', '')
            if (root is None or statement.get('source_url') != row['source_url']
                    or statement.get('scope') != 'checked_source_only'
                    or ('申请书' if kind=='application' else '证据清单') not in quote
                    or not re.search(r'不提供|未提供|不设|无.{0,8}(表格|模板)', quote)):
                raise ValueError('标注官方明确未提供，须有原文声明和可核验的限定范围证据')
            base = Path(root).resolve()
            path = (base/statement.get('evidence_file', '')).resolve()
            if not path.is_relative_to(base/'reports') or not path.is_file():
                raise ValueError('官方明确声明的公开证据文件不可用')
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() != statement.get('sha256') or quote not in body.decode('utf-8'):
                raise ValueError('官方明确声明与证据原文或SHA不匹配')
    row['review_id'] = hashlib.sha256(json.dumps([row[k] for k in ['province', 'city', 'district', 'source_url']],
                                               ensure_ascii=False).encode()).hexdigest()[:24]
    return row


def load_registry(root):
    path = Path(root)/'config/regional_verifications.json'
    if not path.exists(): return []
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows, list): raise ValueError('核验登记必须为列表')
    result = [validate_record(row, root) for row in rows]
    keys = [(r['province'], r['city'], r['district']) for r in result]
    if len(set(keys)) != len(keys): raise ValueError('同一精确地区的核验登记重复')
    return result


def lookup_review(rows, province, city, district):
    own = next((r for r in rows if (r['province'], r['city'], r['district']) == (province, city, district)), None)
    return deepcopy(own) if own else {'guide_status': 'not_checked', 'application_template_status': 'not_checked',
                                    'evidence_template_status': 'not_checked', 'generation_enabled': False}
