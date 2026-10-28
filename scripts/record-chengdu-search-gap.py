"""Retain the unresolved Qingyang search path and public outbox, without models."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_guides import RegionalStore

spec = importlib.util.spec_from_file_location('chengdu_browser_capture', ROOT / 'scripts/collect-chengdu-districts.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
OUT = capture.OUT


def main():
    capture.browser('open', 'https://www.sczwfw.gov.cn/jiq/front/item/gr_index?areaCode=510105000000')
    capture.browser('find', 'text', '按主题', 'click', '--exact')
    capture.browser('wait', '--fn', "!!document.querySelector('#search1')?.getClientRects().length && (typeof jQuery === 'undefined' || jQuery.active === 0)")
    capture.browser('fill', '#search1', '仲裁')
    # Use the search input's observed adjacent button, not a synthetic JS action.
    html = capture.evaluate("document.querySelector('#search1').parentElement.outerHTML")
    capture.save(OUT / 'qingyang-search-control.json', html)
    capture.browser('click', '#searchSub')
    capture.browser('wait', '--text', '受理农村土地承包经营纠纷仲裁申请')
    capture.save(OUT / 'qingyang-wrong-service-dom.json', capture.evaluate(capture.CAPTURE_JS))
    capture.browser('fill', '#search1', '劳动人事争议仲裁申请')
    capture.browser('click', '#searchSub')
    capture.browser('wait', '--text', '共0个事项')
    capture.save(OUT / 'qingyang-empty-search-dom.json', capture.evaluate(capture.CAPTURE_JS))
    capture.browser('screenshot', str(OUT / 'qingyang-empty-search-final.png'))
    store = RegionalStore(ROOT / 'backend/data/regional-guides.sqlite')
    store.record_event({'id': 'chengdu-qingyang-wrong-service-20261023', 'type': 'WRONG_SERVICE_MATCH',
                       'province': 'sichuan', 'city': '成都市', 'district': '青羊区', 'region_code': '510105000000',
                       'service': '劳动人事争议仲裁申请', 'keyword': '仲裁',
                       'url': 'https://www.sczwfw.gov.cn/jiq/front/item/gr_index?areaCode=510105000000',
                       'screenshot': 'reports/chengdu-district-expansion-20261023/qingyang-wrong-service.png',
                       'reason': '个人服务按主题搜索“仲裁”仅返回农村土地承包经营纠纷仲裁申请，不是劳动仲裁；完整关键词0事项。法人主题与省站精确搜索也未找到目标',
                       'attempts': 4, 'final_status': 'manual_review', 'remediation': '拒绝错误匹配，不展示该区确定性材料或伪造当地模板；继续向当地机构核验'})
    targets = json.loads((OUT / 'TARGETS.json').read_text(encoding='utf8'))
    for target in targets:
        if target['status'] == 'captured' and target.get('error'):
            target.setdefault('resolved_errors', []).append(target.pop('error'))
    capture.save(OUT / 'TARGETS.json', targets)
    capture.save(OUT / 'COLLECTION-ISSUES.json', store.events())
    capture.save(OUT / 'outbox/pending-public-events.json', [e for e in store.events() if e['delivery_status'] == 'PENDING_OPENCLAW'])
    print(json.dumps({'pending': sum(e['delivery_status'] == 'PENDING_OPENCLAW' for e in store.events()), 'models_called': 0}))


if __name__ == '__main__':
    main()
