"""Read-only offline F source integrity. A pending locality is never a guide."""
from pathlib import Path
from hashlib import sha256
import io
import json
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def checksum(p):
    return sha256(p.read_bytes()).hexdigest()

def verify_records(records):
    for r in records:
        relative = Path(r['path'])
        assert not relative.is_absolute() and not relative.drive and '..' not in relative.parts
        p = (ROOT / relative).resolve()
        assert p.is_relative_to(BASE) and p.is_file(), r['path']
        assert r['sha256'] == checksum(p) and r['bytes'] == p.stat().st_size, r['path']

def run():
    p = BASE / 'chunan'
    g = read(p / 'guide.json')
    raw = read(p / 'item-response.json')['data']['item']
    own = 'https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=ee47fff8-558c-4a85-88e9-8a28d2bddbdc'
    assert (g['region_code'], g['city'], g['district'], g['service_code'], g['authority']) == ('330127', '杭州市', '淳安县', '11330127593095219M4002014302002', '人社局')
    assert g['source_url'] == own and g['raw_business_fields'] == raw and len(raw) == 252
    assert (raw['jurisCode'], raw['dcode'], raw['taskCode']) == ('330127', 'ee47fff8-558c-4a85-88e9-8a28d2bddbdc', g['service_code'])
    assert g['published'] is False and g['can_generate'] is False and g['candidate_web_qa'] == 'NOT_RUN'
    assert g['fields']['咨询电话']['raw_value'] == raw['askphone'] == '0571-89601299'
    assert raw['addresssList'][0]['addressPhone'] == g['fields']['窗口联系电话']['raw_value'] == ''
    assert '环湖北路377号' in g['fields']['办理地点']['raw_value']
    search = read(p / 'search.json')
    assert 'websiteid=330127000000' in search['url'] and '淳安县' in search['text']
    index = read(p / 'directory-response.json')['data']['list']
    own_index = [v['data'] for v in index if v['data'].get('stdCateName') == '劳动人事争议仲裁申请']
    assert len(own_index) == 1 and own_index[0]['sourceReferNo'] == raw['dcode']
    request = read(p / 'native-guide-request.json')
    assert request['method'] == 'POST' and request['status'] == 200 and request['postData'] == 'localInnerCode=' + raw['dcode'] and request['guide_url'] == own
    for section in ['guide', 'basic', 'conditions', 'materials', 'flow', 'faq', 'window', 'law']:
        assert read(p / (section + '-dom.json'))['url'] == own
    assert [m['raw'] for m in g['materials']] == raw['materialList'] and len(g['materials']) == 5
    assert [m['impleCode'] for m in raw['materialList']] == ['BEDCFDA4DA66F2785CABA5A77B712D65', 'A76581A1B00195D1F1A6508F63D2E9BC', 'D508BEE2A05365A7C6C3D2AC490BBD24', 'FBC9E9D8D9254A4AB07013C05B516870', '644C2B7C6FF6701766CAAF7272B6785B']
    visible = read(p / 'materials-dom.json')
    assert all(m['name'] in visible['text'] for m in g['materials']) and len(visible['material_controls']) == 3
    records = read(p / 'originals.json')
    assert len(records) == 3 and len([r for r in records if r['official_kind'] == 'blank']) == 2
    for r in records:
        assert r['region_code'] == '330127' and r['local_inner_code'] == raw['dcode'] and r['service_code'] == raw['taskCode'] and r['source_url'] == own
        material = next(m for m in raw['materialList'] if m['impleCode'] == r['material_id'])
        assert r['download_url'] == 'https:' + material['blankForm' if r['official_kind'] == 'blank' else 'sampleForm']
        assert r['http_status'] == 200 and r['native_control_clicked'] and r['can_generate'] is False
        if r['official_kind'] == 'sample':
            assert r['public_distribution'] is False and not r.get('file')
            continue
        f = (ROOT / r['file']).resolve()
        assert f.is_relative_to(p / 'originals' / 'blank') and checksum(f) == r['sha256'] and f.stat().st_size == r['bytes']
        assert read(f.with_suffix('.docx.source.json')) == r
        with ZipFile(io.BytesIO(f.read_bytes())) as z:
            assert z.testzip() is None
            ET.fromstring(z.read('word/document.xml'))
    assert not (p / 'originals' / 'sample').exists()
    boundary = read(p / 'online-boundary.json')
    assert boundary['origin'] == 'https://user.zjzwfw.gov.cn' and boundary['path'] == '/pc/login'
    assert boundary['login_visible'] and boundary['captcha_visible'] and not boundary['authenticated'] and not boundary['submitted'] and boundary['query_saved'] is False
    assert g['channel']['entry_check'] == boundary
    t = BASE / 'tonglu'
    pending = read(t / 'discovery.json')
    assert pending['region_code'] == '330122' and pending['verification_status'] == 'pending_own_source'
    assert pending['source_url'] is None and pending['can_generate'] is False and pending['published'] is False and pending['templates_status'] == 'unverified_not_official_absence'
    assert not (t / 'guide.json').exists() and not (t / 'originals').exists()
    wrong = read(t / 'discovery-mismatch.json')
    assert wrong['requested_region_code'] == '330122' and wrong['actual_returned_region_code'] == '330101' and wrong['status'] == 'REJECTED_SCOPE_MISMATCH'
    for f in BASE.rglob('*.json'):
        text = f.read_text(encoding='utf-8-sig')
        assert not re.search(r'(?i)(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|\.runtime|"pid"|"window_pid"|"new_instance_pid"', text), f.name
        assert not re.search(r'(?i)__ssoSeq__|Bearer |access_token|Set-Cookie|[?&](?:sp|goto|ticket|token|signature)=', text), f.name
    for name in ['chunan', 'tonglu']:
        folder = BASE / name
        manifest, white = folder / 'SOURCE-MANIFEST.json', folder / 'PUBLIC-WHITELIST.json'
        if manifest.exists():
            verify_records(read(manifest)['files'])
            records = read(white)['files']
            verify_records(records)
            assert {r['path'] for r in records} == {f.relative_to(ROOT).as_posix() for f in folder.rglob('*') if f.is_file() and f != white}
    white = BASE / 'PUBLIC-WHITELIST.json'
    if white.exists():
        records = read(white)['files']
        verify_records(records)
        assert {r['path'] for r in records} == {f.relative_to(ROOT).as_posix() for f in BASE.rglob('*') if f.is_file() and f != white}
    return {'integrity_status': 'PASS', 'collection_status': 'PARTIAL', 'own_sources': ['330127'], 'pending_own_sources': ['330122'], 'public_blank_count': 2, 'generation_and_publication': 'NOT_RUN'}

if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
