"""Actual login DOM plus exact own callback, not a guide header login link."""
import base64
import copy
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import urlsplit,parse_qs,urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import regional_jiangsu
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-dafeng/online-boundary-0345'


class DafengOnlineTests(unittest.TestCase):
    def setUp(self):
        self.before=json.loads((BASE/'before.json').read_text('utf8'))
        self.after=json.loads((BASE/'after.json').read_text('utf8'))
        self.callback=json.loads((BASE.parent/'callback-source-0352/formal-guide.json').read_text('utf8'))
    def verify(self,after=None):
        self.assertTrue(hasattr(regional_jiangsu,'verify_dafeng_online_capture'),'Own Dafeng auth validator missing')
        return regional_jiangsu.verify_dafeng_online_capture(self.before,after or self.after,self.callback)
    def test_actual_own_online_click_reaches_auth_required_without_submission(self):
        result=self.verify()
        self.assertEqual((result['district'],result['region_code'],result['status']),('大丰区','320904','auth_required'))
        self.assertEqual(result['url'],self.after['url'])
    def test_rejects_guide_header_login_or_foreign_auth_host(self):
        with self.assertRaises(ValueError):self.verify(self.before)
        changed=copy.deepcopy(self.after);changed['url']=changed['url'].replace('www.jszwfw.gov.cn','not-government.example')
        with self.assertRaises(ValueError):self.verify(changed)
    def test_rejects_other_county_callback_even_on_real_official_login(self):
        changed=copy.deepcopy(self.after);url=urlsplit(changed['url']);query=parse_qs(url.query)
        target=base64.b64decode(query['gotoUrl'][0]).decode('utf8').replace('11320982553776482X400201430200201','11320925014387568C400201430200201')
        query['gotoUrl']=[base64.b64encode(target.encode()).decode()]
        changed['url']=url._replace(query=urlencode(query,doseq=True)).geturl()
        with self.assertRaises(ValueError):self.verify(changed)
    def test_canonical_alias_requires_its_own_actual_guide_capture(self):
        with self.assertRaises(ValueError):regional_jiangsu.verify_dafeng_online_capture(self.before,self.after)
        changed=copy.deepcopy(self.callback);changed['html']=changed['html'].replace('class="area_local">大丰区','class="area_local">建湖县')
        with self.assertRaises(ValueError):regional_jiangsu.verify_dafeng_online_capture(self.before,self.after,changed)


if __name__=='__main__':unittest.main()
