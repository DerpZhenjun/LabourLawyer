"""Real Anhui fixtures: prevent wrong-locality binding and unchecked form provenance."""
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
BASE = ROOT / 'reports/nationwide-localization-20261028/anhui'


def fixtures(locality):
    # These are raw captured DOM/model records, never the pre-normalized candidates.
    paths = {'basic': 'basic', 'conditions': 'conditions', 'materials': 'materials',
             'process': 'process-success', 'intermediary': 'intermediary-success', 'faq': 'faq-success',
             'detail_id': 'detail-id', 'detail_evidence': 'detail-evidence',
             'detail_application': 'detail-application-success' if locality == 'shushan' else 'detail-application',
             'online': 'online-boundary-success' if locality == 'shushan' else 'online-boundary'}
    if locality == 'baohe':
        paths['instructions'] = 'filling-instructions-tooltip-visible'
    captures = {key: json.loads((BASE / locality / path / 'dom.json').read_text('utf8'))
                for key, path in paths.items()}
    captures['public_data'] = json.loads((BASE / locality / 'public-guide-viewmodel.json').read_text('utf8'))
    originals = json.loads((BASE / locality / 'downloads/manifest.json').read_text('utf8'))
    return captures, originals


@unittest.skipUnless((BASE / 'shushan/downloads/manifest.json').is_file() and (BASE / 'baohe/downloads/manifest.json').is_file(),
                     'Local HTTP capture retains response cookies; not distributed in public checkout')
class AnhuiCaptureTests(unittest.TestCase):
    def parse(self, locality, captures=None, originals=None, **kwargs):
        self.assertIsNotNone(importlib.util.find_spec('regional_anhui'), 'Missing raw Anhui source parser')
        from regional_anhui import parse_baohe_capture, parse_shushan_capture
        raw, files = fixtures(locality)
        return {'shushan': parse_shushan_capture, 'baohe': parse_baohe_capture}[locality](
            captures if captures is not None else raw, originals if originals is not None else files, **kwargs)

    # Break caught: material and field values copied from another district or from normalized JSON.
    def test_shushan_derives_own_rows_fields_and_faq_conflict_from_raw_html(self):
        g = self.parse('shushan')
        self.assertEqual((g['province'], g['city'], g['district'], g['region_code']),
                         ('anhui', '合肥市', '蜀山区', '340104'))
        self.assertEqual(g['service_code'], '11340104796446883A400201430200201')
        self.assertEqual(g['authority'], '合肥市蜀山区人力资源和社会保障局')
        self.assertEqual([m['name'] for m in g['materials']], ['中华人民共和国居民身份证', '劳动仲裁申请书', '证据'])
        self.assertEqual([m['raw_copies'] for m in g['materials']], ['复印件2份', '原件1份', '复印件1份'])
        self.assertEqual(g['fields']['咨询方式']['raw_value'], '0551-65597684')
        self.assertIn('怀宁北路99号', g['fields']['办理地点']['raw_value'])
        self.assertEqual(g['fields']['办理时间']['raw_value'], '正常工作日上午9:00~12:00，下午12:00~5:00')
        self.assertEqual(g['fields']['承诺办结时限']['raw_value'], '1个工作日')
        self.assertIn('具体时间视案件具体情况依法办理', g['sections']['时限说明'])
        self.assertIn('以上材料一式三份', g['sections']['常见问题'])
        self.assertIn('OFFICIAL_SOURCE_CONFLICT', [i['type'] for i in g['source_issues']])
        self.assertEqual(g['verification_status'], 'conflict')
        self.assertIn('basic/dom.json', g['fields']['办理地点']['capture_file'])
        self.assertEqual(g['materials'][0]['collected_at'], fixtures('shushan')[0]['materials']['captured_at'])

    # Break caught: electronic table counts overwrite window rules, or Baohe title is misidentified.
    def test_baohe_preserves_original_title_electronic_counts_and_window_instructions(self):
        g = self.parse('baohe')
        self.assertEqual(g['region_code'], '340111')
        self.assertEqual(g['service_name'], '劳动人事争议仲裁申请')
        self.assertEqual(g['original_service_name'], '劳动人事争议调仲裁申请')
        self.assertEqual([m['name'] for m in g['materials']], ['仲裁申请书', '证据材料', '身份证'])
        self.assertEqual([m['raw_copies'] for m in g['materials']], ['0份', '0份', '复印件2份'])
        self.assertEqual([m['format'] for m in g['materials']], ['电子', '电子', '纸质或电子'])
        self.assertIn('窗口办理提供原件，网上办理提供电子件', g['materials'][0]['details']['填报须知'])
        self.assertEqual(g['fields']['咨询方式']['raw_value'], '0551-63357381')
        self.assertIn('包河大道118号', g['fields']['办理地点']['raw_value'])
        self.assertEqual(g['fields']['办理时间']['raw_value'], '正常工作日上午9:00~11:30，下午12:30~5:00')
        self.assertIn('皖事通app', g['sections']['预约方式'])
        self.assertEqual(g['fields']['法定办结时限']['raw_value'], '45个工作日')
        self.assertEqual(g['fields']['承诺办结时限']['raw_value'], '1个工作日')

    # Break caught: distinct official labels are treated as proof of distinct or filled document content.
    def test_labels_files_and_unreviewed_content_stay_separate_without_generation_flag(self):
        a = self.parse('shushan'); b = self.parse('baohe')
        self.assertEqual([t['official_kind'] for t in a['templates']], ['blank', 'sample', 'sample', 'instruction'])
        self.assertEqual([t['file_type'] for t in a['templates']], ['doc', 'docx', 'png', 'png'])
        self.assertEqual(b['templates'][0]['sha256'], b['templates'][1]['sha256'])
        self.assertNotEqual(b['templates'][0]['annex_id'], b['templates'][1]['annex_id'])
        self.assertNotEqual(b['templates'][0]['file'], b['templates'][1]['file'])
        self.assertEqual(b['templates'][2]['content_classification'], 'instruction_image')
        self.assertEqual(a['templates'][2]['content_classification'], 'blank_contract_specimen_image')
        for g in [a, b]:
            self.assertEqual(len(g['templates']), 4)
            self.assertTrue(all(t['download_status'] == 'downloaded' and len(t['sha256']) == 64 for t in g['templates']))
            self.assertTrue(all('can_generate' not in t and t['document_types'] == [] for t in g['templates']))
            self.assertTrue(all(t['content_verification_status'] == 'not_reviewed' for t in g['templates'][:2]))
            for t in g['templates']:
                self.assertTrue(t['file'].startswith('templates/_docx/_regional/' + g['official_service_region_code'] + '/'))

    # Break caught: generic SSO callback upgrades an unverified local business channel.
    def test_observed_generic_sso_never_becomes_verified_local_online_entry(self):
        for locality in ['shushan', 'baohe']:
            with self.subTest(locality=locality):
                g = self.parse(locality)
                self.assertEqual(g['channel']['form'], 'window_and_online')
                self.assertEqual(g['channel']['online_status'], 'unverified')
                self.assertIsNone(g['channel']['entry_url'])
                self.assertEqual(g['online_evidence']['observed_status'], 'auth_required')
                self.assertFalse(g['online_evidence']['exact_service_callback_verified'])
                self.assertIn('transition.html', g['online_evidence']['observed_url'])

    # Break caught: accepts a right-looking footer with a wrong URL, agency, region or body panel.
    def test_refuses_wrong_url_code_region_agency_or_main_body(self):
        raw, files = fixtures('shushan')
        mutations = [
            ('basic', 'url', 'hf.ahzwfw.gov.cn', 'example.com'),
            ('basic', 'url', '53018b8b19c540cd95ec66e2acdf07d1', '4bff399fd9af44849ea2a5d2f115e7da'),
            ('basic', 'html', '蜀山区', '包河区'),
            ('basic', 'html', '合肥市蜀山区人力资源和社会保障局', '其他机关'),
            ('conditions', 'html', '因确认劳动关系发生的争议', '借贷纠纷'),
            ('basic', 'text', '蜀山区', '包河区')]
        for key, field, old, new in mutations:
            with self.subTest(field=(key, field, old)):
                altered = copy.deepcopy(raw)
                self.assertIn(old, altered[key][field])
                altered[key][field] = altered[key][field].replace(old, new)
                with self.assertRaises(ValueError): self.parse('shushan', altered, files)
        altered = copy.deepcopy(raw); altered['materials'] = fixtures('baohe')[0]['materials']
        with self.assertRaises(ValueError): self.parse('shushan', altered, files)

    # Break caught: uses unchecked viewmodel material records or trusts normalized candidate fields.
    def test_refuses_swapped_material_records_and_unnormalized_source_missing(self):
        raw, files = fixtures('baohe')
        altered = copy.deepcopy(raw)
        altered['public_data']['data']['clJson'][0], altered['public_data']['data']['clJson'][1] = (
            altered['public_data']['data']['clJson'][1], altered['public_data']['data']['clJson'][0])
        with self.assertRaises(ValueError): self.parse('baohe', altered, files)
        altered = copy.deepcopy(raw); altered['public_data']['data']['ssqdZoneCode'] = '340104000000'
        with self.assertRaises(ValueError): self.parse('baohe', altered, files)
        candidate = json.loads((BASE / 'baohe/guide-candidate.json').read_text('utf8'))
        with self.assertRaises(ValueError): self.parse('baohe', candidate, files)

    # Break caught: accepts relabelled, foreign, moved or unhashed downloaded originals.
    def test_refuses_download_provenance_sha_path_label_or_material_substitution(self):
        raw, files = fixtures('baohe')
        for field, value in [('source_url', files[0]['source_url'].replace('4bff399fd9af44849ea2a5d2f115e7da', '53018b8b19c540cd95ec66e2acdf07d1')),
                             ('requested_url', 'https://example.com/form.docx'), ('path', '../shushan/form.docx'),
                             ('sha256', '0' * 64), ('kind', 'sample'), ('material', '身份证'), ('http_status', 403),
                             ('downloaded_at', '2000-01-01T00:00:00Z')]:
            with self.subTest(field=field):
                altered = copy.deepcopy(files); altered[0][field] = value
                with self.assertRaises(ValueError): self.parse('baohe', raw, altered)
        altered = copy.deepcopy(files); altered[1] = copy.deepcopy(altered[0])
        with self.assertRaises(ValueError): self.parse('baohe', raw, altered)

    # Break caught: only checks declared digests and never checks actual local source/file bytes.
    def test_refuses_capture_integrity_change_and_actual_download_file_corruption(self):
        raw, files = fixtures('shushan')
        altered = copy.deepcopy(raw); altered['basic']['html'] += '<!-- modified captured bytes -->'
        with self.assertRaises(ValueError): self.parse('shushan', altered, files)
        with tempfile.TemporaryDirectory(dir=BASE, prefix='parser-corruption-') as folder:
            root = Path(folder)
            for f in files:
                p = root / 'templates/_docx/_regional/340104000000' / Path(f['path']).name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((BASE / f['path']).read_bytes())
            (root / 'templates/_docx/_regional/340104000000' / Path(files[0]['path']).name).write_bytes(b'corrupt')
            with self.assertRaises(ValueError): self.parse('shushan', raw, files, attachment_root=root)


if __name__ == '__main__': unittest.main()
