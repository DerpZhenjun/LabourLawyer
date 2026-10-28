"""Only Haizhou's independently visited legacy callback can gain auth status."""
import base64,copy,json,sys,unittest
from pathlib import Path
from urllib.parse import parse_qs,urlsplit,urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import regional_jiangsu
BASE=Path(__file__).resolve().parents[2]/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'


class HaizhouOnlineTests(unittest.TestCase):
    def setUp(self):
        self.before=json.loads((BASE/'online-boundary-0530/before.json').read_text('utf8'))
        self.after=json.loads((BASE/'online-boundary-0530/after.json').read_text('utf8'))
        self.callback=json.loads((BASE/'callback-source-0605/callback-page.json').read_text('utf8'))
        self.redirect=json.loads((BASE/'callback-source-0605/capture-only.json').read_text('utf8'))
    def verify(self,after=None,callback=None,redirect=None):
        self.assertTrue(hasattr(regional_jiangsu,'verify_haizhou_online_capture'),'Missing own legacy callback boundary verification')
        return regional_jiangsu.verify_haizhou_online_capture(self.before,after or self.after,
            callback or self.callback,redirect or self.redirect)

    def test_own_native_click_login_and_independently_visited_https_guide(self):
        value=self.verify()
        self.assertEqual(value['status'],'auth_required');self.assertEqual(value['region_code'],'320706')
        self.assertEqual(value['url'],self.after['url'])
        self.assertEqual(value['verified_callback_source_url'],self.before['url'])
        self.assertEqual(value['observed_legacy_callback'],self.redirect['observed_callback'])
        self.assertTrue(value['observed_legacy_callback'].startswith('http://lyghz.jszwfw.gov.cn/'))
        self.assertEqual(self.callback['url'],self.redirect['actual_final_url'])

    def test_missing_independent_callback_evidence_cannot_authorize_legacy_return(self):
        self.verify()
        with self.assertRaises(ValueError):regional_jiangsu.verify_haizhou_online_capture(self.before,self.after)
        with self.assertRaises(ValueError):regional_jiangsu.verify_haizhou_online_capture(self.before,self.after,self.callback)
        changed=copy.deepcopy(self.redirect);changed['observed_callback']=self.before['url']
        with self.assertRaises(ValueError):self.verify(redirect=changed)

    def test_wrong_county_task_final_host_or_auth_page_rejected(self):
        self.verify()
        for key,old,new in [('html','class="area_local">海州区','class="area_local">赣榆区'),
                            ('url','lyghz.jszwfw.gov.cn','example.com')]:
            changed=copy.deepcopy(self.callback);self.assertIn(old,changed[key]);changed[key]=changed[key].replace(old,new)
            with self.assertRaises(ValueError):self.verify(callback=changed)
        changed=copy.deepcopy(self.after);url=urlsplit(changed['url']);query=parse_qs(url.query)
        target=base64.b64decode(query['gotoUrl'][0]).decode().replace('11320706014267312C400201430200201','11320925014387568C400201430200201')
        query['gotoUrl']=[base64.b64encode(target.encode()).decode()]
        changed['url']=url._replace(query=urlencode(query,doseq=True)).geturl()
        with self.assertRaises(ValueError):self.verify(after=changed)
        with self.assertRaises(ValueError):self.verify(after=self.before)


if __name__=='__main__':unittest.main()
