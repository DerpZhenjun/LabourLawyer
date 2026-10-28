"""Read own official directory identity for strict long/short-name re-parsing."""
import json
import re
from urllib.parse import parse_qs,urlsplit


def own_region_metadata(directory,code,city,district):
    if not re.fullmatch(r'51\d{10}',code):raise ValueError('Invalid Sichuan locality code')
    parent=code[:4]+'00000000'
    record=json.loads((directory/f'{parent}.json').read_text('utf8'))
    url=urlsplit(record['source_url'])
    group=record['response']['data']['group']
    if (url.hostname!='www.sczwfw.gov.cn' or url.path!='/jiq/interface/jitem/find-by-code'
            or parse_qs(url.query).get('code')!=[parent]
            or str(record['response'].get('code'))!='200'
            or group.get('areaCode')!=parent or group.get('shortName')!=city):
        raise ValueError('Official directory parent/city mismatch')
    matches=[a for a in group['sonAreas'] if a.get('areaCode')==code and a.get('shortName')==district]
    if len(matches)!=1 or not matches[0].get('name'):raise ValueError('Official directory locality mismatch')
    return matches[0]
