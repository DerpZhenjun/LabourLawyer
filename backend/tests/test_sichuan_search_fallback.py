"""Query fallback must not relax exact-locality arbitration matching."""
import json
import tempfile
import unittest
from pathlib import Path

from sichuan_search import discover_service, requeue_search_misses
from regional_directory import DirectoryStore


CODE='510302000000'
URL='https://www.sczwfw.gov.cn/jiq/front/transition/ywTransToDetail?areaCode='+CODE


def row(title='劳动人事争议仲裁申请',code=CODE):
    return {'data':{'title':title,'areacode':code,'url':URL.replace(CODE,code)}}


class SichuanSearchFallback(unittest.TestCase):
    def test_alias_finds_exact_service_and_preserves_every_query(self):
        with tempfile.TemporaryDirectory() as folder:
            queries=[]
            def request(url):
                queries.append(url)
                return json.dumps({'data':[] if len(queries)==1 else [row()]},ensure_ascii=False).encode()
            result=discover_service(CODE,Path(folder),request,lambda _:None)
            self.assertEqual(result['service']['url'],URL)
            self.assertEqual([a['keyword'] for a in result['attempts']],['劳动人事争议仲裁申请','劳动人事争议仲裁'])
            self.assertTrue(result['alias_required'])
            self.assertEqual(len(list(Path(folder).rglob('*.json'))),2)
            # Successful caches are read, not overwritten or re-fetched.
            cached=discover_service(CODE,Path(folder),lambda _:self.fail('Unexpected repeat fetch'),lambda _:None)
            self.assertEqual(result['attempts'],cached['attempts'])

    def test_broader_keywords_do_not_accept_mediation_or_neighbor(self):
        with tempfile.TemporaryDirectory() as folder:
            result=discover_service(CODE,Path(folder),lambda _:json.dumps({'data':[row('劳动人事争议调解'),row(code='510303000000')]}).encode(),lambda _:None)
            self.assertIsNone(result['service'])
            self.assertEqual(len(result['attempts']),4)
            self.assertTrue(all(a['returned_rows']==2 and a['target_found'] is False for a in result['attempts']))

    def test_invalid_source_response_is_not_a_negative_result(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'列表'):
                discover_service(CODE,Path(folder),lambda _:b'{"error":"upstream unavailable"}',lambda _:None)
            failures=list((Path(folder)/'errors').glob('*.json'))
            self.assertEqual(len(failures),1)
            self.assertEqual(json.loads(failures[0].read_text('utf8'))['response'],{'error':'upstream unavailable'})

    def test_exact_v4_summary_is_a_candidate_not_a_verified_formal_guide(self):
        with tempfile.TemporaryDirectory() as folder:
            summary=row();summary['data']['url']=URL.replace('/jiq/','/jiq4/').replace('ywTransToDetail?','ywTransToDetail_summary?')
            result=discover_service(CODE,Path(folder),lambda _:json.dumps({'data':[summary]}).encode(),lambda _:None)
            self.assertIsNone(result['service'])
            self.assertEqual(result['summary_candidate'],summary['data'])
            self.assertFalse(result['attempts'][0]['target_found'])
            self.assertEqual(len(result['attempts']),1)

    def test_only_search_miss_jobs_are_explicitly_requeued_once(self):
        with tempfile.TemporaryDirectory() as folder:
            store=DirectoryStore(Path(folder)/'directory.sqlite')
            ids=[]
            for number,state,typ in [(1,'manual_review','SEARCH_NO_RESULT'),(2,'needs_browser','captured'),(3,'failed','GUIDE_PAGE_UNAVAILABLE')]:
                identity=store.enqueue('sichuan_capture',{'region_code':str(number)})
                store.finish(identity,state,{'type':typ});ids.append(identity)
            self.assertEqual(requeue_search_misses(store),[ids[0]])
            self.assertEqual(requeue_search_misses(store),[])
            self.assertEqual(store.claim('sichuan_capture')['id'],ids[0])


if __name__=='__main__':unittest.main()
