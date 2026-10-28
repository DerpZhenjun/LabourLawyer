"""Preflight every locality, then reversibly add only verified regional records."""
import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_adapters import with_reference_capabilities
from regional_guides import RegionalStore, digest

REPORT = ROOT / 'reports/chengdu-district-expansion-20261023'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    database = ROOT / 'backend/data/regional-guides.sqlite'
    if not database.is_file():
        raise RuntimeError('地区库不存在，不新建或操作案件库')
    output = REPORT / 'publication' / uuid.uuid4().hex[:12]
    output.mkdir(parents=True)
    targets = json.loads((REPORT / 'TARGETS.json').read_text(encoding='utf8'))
    proposals = []
    for target in targets:
        if target['status'] != 'captured':
            continue
        folder = REPORT / 'captures' / target['region_code']
        guide = json.loads((folder / 'guide.json').read_text(encoding='utf8'))
        raw = json.loads((folder / 'dom.json').read_text(encoding='utf8'))
        if guide['source_url'] != raw['url'] or guide['district'] != target['district'] or guide['region_code'] != target['region_code']:
            raise RuntimeError('地区、正式指南和捕获不一致，停止发布')
        if hashlib.sha256((folder / 'dom.json').read_bytes()).hexdigest() != guide['evidence']['capture_sha256']:
            raise RuntimeError('捕获证据已变化')
        for t in guide['templates']:
            p = (ROOT / t.get('file', '')).resolve()
            allowed = (ROOT / 'templates/_docx/_regional' / target['region_code']).resolve()
            if t['download_status'] != 'downloaded' or not p.is_relative_to(allowed) or hashlib.sha256(p.read_bytes()).hexdigest() != t['sha256']:
                raise RuntimeError('当地附件下载或校验未通过，停止发布')
        candidate = with_reference_capabilities(guide)
        if not any(t.get('can_generate') for t in candidate['templates']):
            raise RuntimeError('当地参考样表未独立适配，停止发布')
        proposals.append(candidate)
    # Exercise all validation and generation bindings in an independent staging DB first.
    staging = RegionalStore(output / 'preflight.sqlite')
    for guide in proposals:
        staging.put_guide(guide)
    store = RegionalStore(database)
    save(output / 'before.json', store.inventory())
    if args.apply:
        with sqlite3.connect(database) as source, sqlite3.connect(output / 'regional-before.sqlite') as backup:
            source.backup(backup)
        for guide in proposals:
            store.put_guide(guide)
            common = {k: guide[k] for k in ['province', 'city', 'district', 'region_code']}
            common.update(service=guide['service_name'], url=guide['source_url'], occurred_at=guide['collected_at'],
                          screenshot=guide['evidence']['screenshot'])
            events = [('OFFICIAL_TEMPLATE_NOT_FOUND', '官网申请书标注为示例样表，未提供申请书空白表格', '明确标注参考样表辅助填写，不冒充空白模板', 'documented')]
            status = guide['channel']['online_status']
            if status == 'unavailable':
                events.append(('ONLINE_APPLICATION_UNAVAILABLE', '官网办理形式为窗口办理，是否网办为否；这是办理能力限制，不是技术故障', '显示当地窗口、时间和材料', 'verified'))
            elif status == 'conflict':
                events.append(('OFFICIAL_SOURCE_CONFLICT', '官网基本信息为窗口办理，但流程或常见问题提及网上申请', '保留各栏目原文，向当地机构确认，不显示可用网办按钮', 'manual_review'))
            elif status == 'auth_required':
                common['screenshot'] = guide['channel']['entry_check']['screenshot']
                events.append(('AUTH_REQUIRED', '真实点击在线申请后提示用户未登录，未输入账号或提交申请', '用户自行登录官方平台', 'manual_authorization'))
            else:
                events.append(('ONLINE_CHANNEL_UNVERIFIED', '未完成有效网上申请入口核验，不判断当地不支持网上申请', '继续核对公开控件或由用户联系办理机关', 'pending'))
            for kind, reason, remediation, state in events:
                event = {**common, 'type': kind, 'reason': reason, 'remediation': remediation, 'final_status': state}
                store.record_event({'id': digest(['chengdu-20261023', guide['region_code'], kind])[:32], **event})
        qy = next(t for t in targets if t['district'] == '青羊区')
        event = {'province': 'sichuan', 'city': '成都市', 'district': '青羊区', 'region_code': qy['region_code'],
                 'service': '劳动人事争议仲裁申请', 'keyword': '劳动人事争议仲裁申请', 'url': qy['search_url'],
                 'type': 'SEARCH_NO_RESULT', 'reason': '精确事项搜索未返回本区正式指南；省站地区弹窗中本事项未列出青羊区。不把省本级办公地址在青羊区当作青羊区事项',
                 'attempts': 3, 'final_status': 'manual_review', 'remediation': '继续核验个人服务、部门目录与区政府网站，不套用邻区模板'}
        store.record_event({'id': 'chengdu-qingyang-missing-20261023', **event})
        catalog = ROOT / 'reports/government-guide-localization/SOURCE-INVENTORY.json'
        catalog_data = json.loads(catalog.read_text(encoding='utf8'))
        save(output / 'source-inventory-before.json', catalog_data)
        catalog_data['regions'] = store.inventory()
        catalog_data['latest_imported_at'] = datetime.now(timezone.utc).isoformat()
        save(catalog, catalog_data)
        save(REPORT / 'SOURCE-INVENTORY.json', {'regions': store.inventory(), 'targets': targets})
        save(REPORT / 'COLLECTION-ISSUES.json', store.events())
        save(REPORT / 'outbox/pending-public-events.json', [e for e in store.events() if e['delivery_status'] == 'PENDING_OPENCLAW'])
    save(output / 'publication.json', {'applied': args.apply, 'at': datetime.now(timezone.utc).isoformat(),
         'database': str(database), 'districts': [g['district'] for g in proposals], 'new_template_files': sum(len(g['templates']) for g in proposals),
         'total_regions_after': len(store.inventory()), 'local_ollama_started': False, 'model_calls': 0, 'openclaw_acknowledged': False})
    print(json.dumps({'report': str(output / 'publication.json'), 'applied': args.apply, 'district_count': len(proposals)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
