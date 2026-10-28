"""Strict discovery of a local arbitration guide from observed official search."""
from urllib.parse import parse_qs, urlsplit


def select_service(response, region_code):
    found = {}
    for row in response.get('data', []):
        item = row.get('data', {})
        url = item.get('url', '')
        parsed = urlsplit(url)
        if (item.get('title') != '劳动人事争议仲裁申请'
                or item.get('areacode') != region_code
                or parsed.hostname != 'www.sczwfw.gov.cn'
                or parsed.path != '/jiq/front/transition/ywTransToDetail'
                or parse_qs(parsed.query).get('areaCode') != [region_code]):
            continue
        found[url] = item
    if len(found) > 1:
        raise ValueError('多个不同正式指南，需人工核验')
    return next(iter(found.values()), None)
