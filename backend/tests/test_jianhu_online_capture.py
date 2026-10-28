"""Header login text or another region must never authorize an online channel."""
import copy
import json
from pathlib import Path
import unittest
import regional_jiangsu

BASE=Path(__file__).resolve().parents[2]/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-jianhu'


class JianhuOnlineCapture(unittest.TestCase):
    def read(self,folder,file):return json.loads((BASE/folder/file).read_text('utf8'))
    def check(self,before,after):
        self.assertTrue(hasattr(regional_jiangsu,'verify_jianhu_online_capture'),'Actual own navigation validator missing')
        return regional_jiangsu.verify_jianhu_online_capture(before,after)

    def test_actual_own_button_to_official_auth_page(self):
        folder='online-recheck-tabs-0306'
        result=self.check(self.read(folder,'before.json'),self.read(folder,'after.json'))
        self.assertEqual(result['status'],'auth_required')
        self.assertEqual(result['region_code'],'320925')
        self.assertTrue(result['official_link'])
        self.assertIn('/jsjis/front/login.do',result['url'])

    def test_guide_header_login_text_is_not_authentication_evidence(self):
        folder='online-recheck-0255'
        with self.assertRaises(ValueError):self.check(self.read(folder,'before.json'),self.read(folder,'after.json'))

    def test_wrong_county_or_external_login_page_is_rejected(self):
        before=self.read('online-recheck-tabs-0306','before.json');after=self.read('online-recheck-tabs-0306','after.json')
        wrong=copy.deepcopy(before);wrong['url']=wrong['url'].replace('11320925014387568C400201430200201','not-this-task')
        with self.assertRaises(ValueError):self.check(wrong,after)
        wrong=copy.deepcopy(after);wrong['url']='https://example.com/jsjis/front/login.do'
        with self.assertRaises(ValueError):self.check(before,wrong)


if __name__=='__main__':unittest.main()
