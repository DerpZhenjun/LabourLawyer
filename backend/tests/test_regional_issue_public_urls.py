"""Public item selectors survive real pending workspace export; no service ACK."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import regional_issue_delivery as delivery
from regional_guides import RegionalStore

FJ_PATH = '/person-todo/todo-fingerpost'
JS_PATH = '/jszwfw/publicservice/itemlist/showDetail.do'
FJ = 'https://zwfw.fujian.gov.cn' + FJ_PATH + '?unid=76D5D6C31E91AC25E948E44CF0D90043&infoType=1'
JS = 'https://szks.jszwfw.gov.cn' + JS_PATH + '?webId=32&iddept_ql_inf=1132058301418949XF4002014302002&ql_kind=20&iddept_yw_inf=1132058301418949XF400201430200201'
JS_F = (
    'https://szcs.jszwfw.gov.cn' + JS_PATH + '?webId=30&iddept_ql_inf=11320581014173412K4002014302002&ql_kind=20&iddept_yw_inf=11320581014173412K400201430200201',
    'https://szzjg.jszwfw.gov.cn' + JS_PATH + '?webId=31&iddept_ql_inf=11320582551232000Y4002014302002&ql_kind=20&iddept_yw_inf=11320582551232000Y400201430200201',
)
ZJ = 'https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=ee47fff8-558c-4a85-88e9-8a28d2bddbdc'


class PublicIssueURLTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='public-selector-export-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = self.root / 'workspace'; self.workspace.mkdir()
        self.store = RegionalStore(self.root / 'fixture-outbox.sqlite')

    def event(self, url, identifier='public-selector-fixture'):
        province, city, district, code = ('fujian', '福州市', '鼓楼区', '350102')
        for prefix, own in [('https://szks.jszwfw.gov.cn/', ('jiangsu', '苏州市', '昆山市', '320583')),
                            ('https://szcs.jszwfw.gov.cn/', ('jiangsu', '苏州市', '常熟市', '320581')),
                            ('https://szzjg.jszwfw.gov.cn/', ('jiangsu', '苏州市', '张家港市', '320582')),
                            ('https://www.zjzwfw.gov.cn/', ('zhejiang', '杭州市', '淳安县', '330127'))]:
            if url.startswith(prefix): province, city, district, code = own
        return {'id': identifier, 'type': 'SOURCE_STALE', 'province': province, 'city': city,
                'district': district, 'region_code': code, 'url': url,
                'reason': '公开事项链接待人工复核', 'occurred_at': '2026-10-31T03:00:00Z'}

    def project(self, url):
        event = self.event(url)
        return delivery._public_event(json.dumps(event), event['id'])

    def test_own_fj_and_js_pending_export_bytes_and_receipt_readback_keep_full_item_url(self):
        expected = {'own-fujian': FJ, 'own-kunshan': JS, 'own-chunan': ZJ,
                    'own-changshu': JS_F[0], 'own-zhangjiagang': JS_F[1]}
        for name, url in expected.items():
            self.store.record_event(self.event(url, name))
        result = delivery.deliver_pending(self.store.path, self.workspace, record_receipts=True)
        self.assertEqual((result['workspace_exported'], result['pending'], result['acknowledged'], result['failed']), (5, 5, 0, 0))
        for saved in self.store.events():
            self.assertEqual(saved['delivery_status'], 'PENDING_OPENCLAW')
            receipt = saved['receipt']; raw = (self.workspace / receipt['content_file']).read_bytes()
            self.assertEqual(sha256(raw).hexdigest(), receipt['content_sha256'])
            self.assertIn(expected[saved['id']].encode(), raw)
            exported = json.loads(raw)['events'][0]
            self.assertEqual(exported['url'], expected[saved['id']])
            self.assertEqual(delivery._public_event(json.dumps(exported), saved['id']), exported)
            disk_receipt = json.loads((self.workspace / receipt['receipt_file']).read_bytes())
            self.assertIs(disk_receipt['service_acknowledged'], False)
            self.assertIs(disk_receipt['ai_reviewed'], False)
        self.assertEqual(delivery.delivery_summary(self.store.path),
                         {'total': 5, 'pending': 5, 'workspace_exported': 5, 'acknowledged': 0, 'ai_reviewed': 0})

    def test_unknown_identity_credentials_and_generic_id_are_never_copied(self):
        extra = '&id=11010519491231002X&userId=PRIVATE_USER&access_token=PRIVATE_TOKEN&ApiKey=PRIVATE_KEY&sessionId=PRIVATE_SESSION&cookie=PRIVATE_COOKIE&signature=PRIVATE_SIG&opaque=PRIVATE_OPAQUE'
        for url in (FJ, JS, ZJ):
            # ZJ selectors live in its workguide fragment; append there too.
            projected = self.project(url + extra)
            self.assertEqual(projected['url'], url)
            self.assertNotIn('PRIVATE_', json.dumps(projected))
            self.assertNotIn('11010519491231002X', json.dumps(projected))

    def test_provider_selectors_cannot_borrow_another_path_or_workguide_fragment(self):
        fj_query, js_query = urlsplit(FJ).query, urlsplit(JS).query
        for url in [
            'https://www.zjzwfw.gov.cn/guide?' + fj_query,
            'https://www.zjzwfw.gov.cn/guide?' + js_query,
            'https://zwfw.fujian.gov.cn' + FJ_PATH + '?' + js_query,
            'https://szks.jszwfw.gov.cn' + JS_PATH + '?' + fj_query,
            'https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?' + js_query,
            'https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?' + fj_query,
        ]:
            with self.subTest(url=url):
                actual = urlsplit(self.project(url)['url'])
                self.assertEqual(actual.query, '')
                self.assertEqual(actual.fragment, '')

    def test_native_fj_js_paths_cannot_borrow_zj_workguide_fragment_selectors(self):
        workguide = urlsplit(ZJ).fragment
        for url in (FJ, JS):
            with self.subTest(url=url): self.assertEqual(self.project(url + '#' + workguide)['url'], url)

    def test_fj_duplicate_blank_wrong_type_and_nonpublic_unid_values_fail_closed(self):
        for query in [
            'unid=76D5D6C31E91AC25E948E44CF0D90043&unid=76D5D6C31E91AC25E948E44CF0D90043&infoType=1',
            'unid=76D5D6C31E91AC25E948E44CF0D90043&%75nid=76D5D6C31E91AC25E948E44CF0D90043&infoType=1',
            'unid=76D5D6C31E91AC25E948E44CF0D90043&infoType=01',
            'unid=76D5D6C31E91AC25E948E44CF0D90043&infoType=2',
            'unid=&infoType=1', 'unid=11010519491231002X&infoType=1',
            'unid=PRIVATE_TOKEN&infoType=1', 'unid=76D5D6C31E91AC25E948E44CF0D90043',
        ]:
            with self.subTest(query=query), self.assertRaises(ValueError):
                self.project('https://zwfw.fujian.gov.cn' + FJ_PATH + '?' + query)

    def test_js_only_bounded_numbers_and_matching_official_31_33_character_codes(self):
        for before, after in [('webId=32', 'webId=100000'), ('webId=32', 'webId=032'),
                              ('ql_kind=20', 'ql_kind=200000'), ('ql_kind=20', 'ql_kind='),
                              ('1132058301418949XF4002014302002&', 'PRIVATE_TOKEN&'),
                              ('1132058301418949XF4002014302002&', '11010519491231002X&'),
                              ('1132058301418949XF400201430200201', '11320581014173412K400201430200201'),
                              ('1132058301418949XF400201430200201', '1133058301418949XF400201430200201')]:
            with self.subTest(after=after), self.assertRaises(ValueError): self.project(JS.replace(before, after))
        for extra in ['&webId=32', '&WEBID=32', '&ql_kind=20', '&unknown=x&unknown=y']:
            with self.subTest(extra=extra), self.assertRaises(ValueError): self.project(JS + extra)

    def test_invalid_pending_url_fails_without_export_ack_or_impact_on_other_event(self):
        self.store.record_event(self.event(FJ + '&unid=duplicate', 'invalid-item'))
        self.store.record_event(self.event(JS, 'valid-item'))
        result = delivery.deliver_pending(self.store.path, self.workspace, record_receipts=True)
        self.assertEqual((result['failed'], result['workspace_exported'], result['pending'], result['acknowledged']), (1, 1, 2, 0))
        saved = {event['id']: event for event in self.store.events()}
        self.assertIsNone(saved['invalid-item']['receipt'])
        self.assertEqual({event['delivery_status'] for event in saved.values()}, {'PENDING_OPENCLAW'})
        self.assertEqual(len(list(self.workspace.rglob('events.json'))), 1)

    def test_auth_userinfo_private_identity_paths_and_encoded_controls_are_omitted_or_refused(self):
        urls = [FJ.replace('https://', 'https://user:PRIVATE_PASSWORD@'),
                FJ.replace('https://', 'https://@'), FJ + '\r\nCookie:PRIVATE_COOKIE',
                FJ.replace(FJ_PATH, '/login'), FJ.replace(FJ_PATH, '/private/guide'),
                FJ.replace(FJ_PATH, '/%2570rivate/guide'), FJ.replace(FJ_PATH, '/session/guide'),
                FJ.replace(FJ_PATH, '/guide/11010519491231002X'), FJ.replace(FJ_PATH, FJ_PATH + '/../login'),
                FJ + '&unknown=%0D%0APRIVATE', FJ.replace('unid=', 'unid=%0D%0A'),
                FJ.replace('.gov.cn/', '.gov.cn.evil/'), FJ.replace('https://', 'file://'),
                FJ.replace(FJ_PATH, '/guide\\private')]
        for url in urls:
            with self.subTest(url=url):
                try: event = self.project(url)
                except ValueError: continue
                self.assertNotIn('url', event)

    def test_existing_zj_and_legacy_public_item_selectors_are_idempotent(self):
        old = 'https://www.jszwfw.gov.cn/guide?itemId=6de260dc797c433b82e0eb2a4dd9a419&taskCode=11320900717413933Q3322014317000&areaCode=320900'
        for url in (ZJ, old):
            self.assertEqual(delivery.public_source_url(url), url)
            self.assertEqual(delivery.public_source_url(delivery.public_source_url(url)), url)


if __name__ == '__main__': unittest.main(verbosity=2)
