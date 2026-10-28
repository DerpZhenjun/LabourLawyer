import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('report_review', ROOT / 'scripts/review-province-reports.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class OpenClawReportReviewTests(unittest.TestCase):
    def payload(self, pages):
        return {'engine': 'OpenClaw', 'base_url': review.SERVER, 'model': 'ollama/' + review.MODEL,
                'exit_code': 0, 'timed_out': False, 'completed_output_captured': True,
                'result': {'outputs': [{'text': json.dumps(pages)}]}}

    def test_rejects_missing_or_duplicate_pages(self):
        page = {'page': 1, 'issues': [], 'notes': 'ok'}
        with self.assertRaises(ValueError): review.parse_pages(self.payload([page]), [1, 2])
        with self.assertRaises(ValueError): review.parse_pages(self.payload([page, page]), [1, 2])

    def test_rejects_local_server_and_timeout(self):
        page = {'page': 1, 'issues': [], 'notes': 'ok'}
        payload = self.payload([page]); payload['base_url'] = 'http://localhost:11434'
        with self.assertRaises(ValueError): review.parse_pages(payload, [1])
        payload = self.payload([page]); payload['timed_out'] = True
        with self.assertRaises(ValueError): review.parse_pages(payload, [1])

    def test_rejects_issue_without_visible_evidence(self):
        page = {'page': 1, 'issues': [{'type': 'font', 'severity': 'major', 'evidence': ''}], 'notes': 'bad'}
        with self.assertRaises(ValueError): review.parse_pages(self.payload([page]), [1])

    def test_cache_requires_unchanged_completed_raw_result(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as temp:
            folder = Path(temp); raw = folder / 'raw.json'; cache = folder / 'review.json'
            pages = [{'page': 1, 'issues': [], 'notes': 'ok'}]
            review.save(raw, self.payload(pages))
            review.save(cache, {'input_key': 'key', 'status': 'completed', 'page_numbers': [1],
                                'pages': pages, 'raw_file': str(raw), 'raw_sha256': review.digest(raw)})
            self.assertIsNotNone(review.valid_cache(cache, 'key'))
            self.assertIsNone(review.valid_cache(cache, 'changed input'))
            raw.write_text('{}', 'utf8')
            self.assertIsNone(review.valid_cache(cache, 'key'))

    def test_reused_pages_preserve_checked_decisions_only_for_identical_sources(self):
        doc={'document':'report.docx','source_sha256':'source','pdf_sha256':'pdf'}
        previous={'status':'completed','documents':[doc],'findings_state':'checked','confirmed_report_layout_issues':0}
        current={'documents':[dict(doc)],'findings_state':'pending'}
        review.restore_checked_metadata(current,previous,True)
        self.assertEqual(current['findings_state'],'checked')
        changed={'documents':[{**doc,'pdf_sha256':'changed'}],'findings_state':'pending'}
        review.restore_checked_metadata(changed,previous,True)
        self.assertEqual(changed['findings_state'],'pending')
        uncached={'documents':[dict(doc)],'findings_state':'pending'}
        review.restore_checked_metadata(uncached,previous,False)
        self.assertEqual(uncached['findings_state'],'pending')


if __name__ == '__main__': unittest.main()
