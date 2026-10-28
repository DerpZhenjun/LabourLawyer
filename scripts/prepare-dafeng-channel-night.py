"""Validate actual own auth boundary and keep the raw collection history."""
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_jiangsu import verify_dafeng_online_capture
from regional_guides import resolve_channel
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng'
RAW=BASE/'online-boundary-0345'


def main():
    if (RAW/'online-check.json').exists():raise ValueError('Preserve successful check')
    before=json.loads((RAW/'before.json').read_text('utf8'));after=json.loads((RAW/'after.json').read_text('utf8'))
    callback=json.loads((BASE/'callback-source-0352/formal-guide.json').read_text('utf8'))
    entry=verify_dafeng_online_capture(before,after,callback)
    entry.update(screenshot=(RAW/'authentication-boundary.png').relative_to(ROOT).as_posix(),
        before_sha256=hashlib.sha256((RAW/'before.json').read_bytes()).hexdigest(),
        after_sha256=hashlib.sha256((RAW/'after.json').read_bytes()).hexdigest())
    entry['callback_capture_sha256']=hashlib.sha256((BASE/'callback-source-0352/formal-guide.json').read_bytes()).hexdigest()
    path=BASE/'guide.json';original=json.loads(path.read_text('utf8'));guide=copy.deepcopy(original)
    if original['channel']['online_status']!='unverified':raise ValueError('Preserve updated channel')
    guide['channel']=resolve_channel({k:v['raw_value'] for k,v in guide['fields'].items()},guide['sections']['办理流程'],entry)
    assert guide['materials']==original['materials'] and guide['templates']==original['templates']
    (BASE/'guide-before-channel.json').write_bytes(path.read_bytes())
    (RAW/'online-check.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2),encoding='utf8')
    path.write_text(json.dumps(guide,ensure_ascii=False,indent=2),encoding='utf8')
    print('Own Dafeng auth boundary verified; source, materials and annexes unchanged; not published')


if __name__=='__main__':main()
