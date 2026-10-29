"""Read-only source-stage checks, including an exact-public-only clean root."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
BASE = Path('reports/nationwide-verification-20261029-f/jiangsu')


def read(path):
    return json.loads(path.read_text('utf8'))


def check(directory):
    whitelist = read(directory / 'PUBLIC-WHITELIST.json')
    assert len(whitelist['files']) == len(set(whitelist['files']))
    for name, expected in whitelist['files'].items():
        relative = Path(name).relative_to(BASE)
        path = (directory / relative).resolve()
        assert path.is_relative_to(directory.resolve()) and path.is_file()
        assert path.stat().st_size == expected['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected['sha256']
        assert '/originals/sample/' not in name
    for locality, code, webid, authority in [
        ('changshu', '320581', '30', '常熟市人力资源和社会保障局'),
        ('zhangjiagang', '320582', '31', '张家港市人力资源和社会保障局'),
    ]:
        guide = read(directory / locality / 'guide.json')
        raw = read(directory / locality / 'formal-controls/page.json')
        search = read(directory / locality / 'personal-controls/page.json')
        assert guide['region_code'] == code and guide['authority'] == authority
        assert guide['source_url'] == raw['url']
        assert parse_qs(urlsplit(raw['url']).query)['webId'] == [webid]
        assert parse_qs(urlsplit(raw['url']).query)['iddept_yw_inf'] == [guide['service_code']]
        assert parse_qs(urlsplit(search['url']).query)['webId'] == [webid]
        assert search['text'].startswith(guide['district'] + '\n')
        controls = read(directory / locality / 'directory-controls.json')
        assert any(c['onclick'] == "showBszn('" + webid + "','" + guide['service_code'] + "','20','" +
                   parse_qs(urlsplit(raw['url']).query)['iddept_ql_inf'][0] + "')" and
                   c['label'] == '办事指南' for c in controls['controls'])
        assert guide['source_id'] == hashlib.sha256(json.dumps(guide['source_url'], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
        assert guide['capture_version'] == 'sha256:' + hashlib.sha256((directory / locality / 'formal-controls/page.json').read_bytes()).hexdigest()
        assert not guide['can_generate'] and guide['generation_adapter'] is None
        assert not guide['published'] and guide['candidate_web_qa'] == 'NOT_RUN'
        assert guide['source_update_date'] is None
        assert len(guide['materials']) == 4 and len(raw['download_controls']) == 8
        assert [m['copies'] for m in guide['materials']] == ['2', '2', '1', '4']
        assert len(guide['templates']) == 9
        for template in guide['templates']:
            assert not template['can_generate'] and not template['document_types']
            if template['official_kind'] == 'sample':
                assert template['download_status'] == 'reference_sample_not_distributed'
                assert template['file'] is None
                assert template['file'] not in whitelist['files']
            else:
                assert template['file'] in whitelist['files']
        boundary = guide['online_boundary']
        assert boundary['source_url'] == guide['source_url'] and boundary['status'] == 'auth_required'
        assert boundary['path'] == '/jsjis/front/login.do' and boundary['password_input_count'] == 2
        assert boundary['captcha_visible'] and not boundary['submitted']
        assert guide['fields']['到办事现场次数']['raw_value'] == ('3' if locality == 'changshu' else '0')
    return len(whitelist['files'])


count = check(HERE)
with tempfile.TemporaryDirectory(prefix='source-public-') as temporary:
    clean = Path(temporary) / BASE
    clean.mkdir(parents=True)
    for name in read(HERE / 'PUBLIC-WHITELIST.json')['files']:
        relative = Path(name).relative_to(BASE)
        target = clean / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / relative, target)
    shutil.copyfile(HERE / 'PUBLIC-WHITELIST.json', clean / 'PUBLIC-WHITELIST.json')
    assert not list(clean.glob('*/originals/sample/*/*'))
    assert check(clean) == count
    result = subprocess.run([sys.executable, str(clean / 'finalize.py'), '--verify'], capture_output=True, text=True)
    assert result.returncode == 0, 'Clean-root source manifest verification failed'
    manifest_result = json.loads(result.stdout)
print(json.dumps({'status': 'PASS', 'own_profiles': 2, 'exact_public_files': count,
                  'source_files': manifest_result['source_files_sha_passed'],
                  'clean_root': 'PASS', 'sample_bytes_present_in_clean_root': False,
                  'source_only': True, 'network_word_model_db_service_calls': 0,
                  'read_only_verification': True}))
