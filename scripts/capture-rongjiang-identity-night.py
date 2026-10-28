"""Visit the own public introduction linked by the already captured notice."""
import importlib,json,os,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
c=importlib.import_module('collect-chengdu-districts')
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang'
OUT=BASE/'identity-0430'


def main():
    if (OUT/'identity.json').exists():raise ValueError('Preserve completed own identity evidence')
    links=json.loads((BASE/'source-0425/links.json').read_text('utf8'))
    entry=next(a['url'] for a in links if a['text']=='走进蓉江')
    if entry!='https://rjxq.ganzhou.gov.cn/rjxq/zjyd/zjyd.shtml':raise ValueError('Unexpected own profile entry')
    OUT.mkdir(exist_ok=True);c.OUT=OUT;c.ENV={**os.environ,'AGENT_BROWSER_SESSION':'labourlawyer-rongjiang-identity-20261024-0430'}
    launched=False
    try:
        if (OUT/'own-profile.json').exists():
            page=json.loads((OUT/'own-profile.json').read_text('utf8'))
        else:
            launched=True
            c.browser('open',entry)
            page=c.evaluate(c.CAPTURE_JS);c.save(OUT/'own-profile.json',page)
            c.save(OUT/'snapshot.json',c.browser('snapshot','-i'))
            c.browser('screenshot',str(OUT/'own-profile.png'))
        with sqlite3.connect((ROOT/'backend/data/regional-directory.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            rows=[json.loads(r[0]) for r in db.execute('SELECT payload FROM directory_areas WHERE province=? AND city=? AND district=?',('jiangxi','赣州市','蓉江新区'))]
        if len(rows)!=1 or rows[0]['code']!='360798':raise ValueError('Own service-directory identity missing or changed')
        if page['url']!=entry or '蓉江新区' not in page['text'] or '管理委员会' not in page['text']:raise ValueError('Own introduction identity not established')
        c.save(OUT/'identity.json',{'directory_record':rows[0],'own_profile_url':entry,'own_profile_captured_at':page['captured_at'],
            'notice_district_display':'赣州蓉江新区','lookup_district':'蓉江新区','region_code':'360798',
            'region_code_kind':'official_service_directory_code_not_independently_verified_administrative_division',
            'no_jurisdiction_inference':True,'published':False})
        print(json.dumps({'identity':'own_site_and_existing_official_service_directory','code':'360798','district':'蓉江新区','profile_excerpt':page['text'][:1400]},ensure_ascii=True))
    finally:
        # No fresh browser is created when validating an existing successful capture.
        if launched:c.browser('close')


if __name__=='__main__':main()
