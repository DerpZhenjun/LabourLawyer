"""Real eight-tab fixtures: wrong region/tab/hash must never publish."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
import regional_capture
import sichuan_v4_capture
from sichuan_night_evidence import own_region_metadata

BASE=ROOT/'reports/nationwide-localization-20261023-night/sichuan/v4/captures'
DIRECTORY=ROOT/'reports/nationwide-localization-20261023-night/sichuan/directory'


class NewPortalCaptureTests(unittest.TestCase):
    def fixture(self,code='510704000000'):
        folder=BASE/code
        manifest=json.loads((folder/'manifest.json').read_text('utf8'))
        captures=[json.loads((folder/s['file']).read_text('utf8')) for s in manifest['sections']]
        metadata=own_region_metadata(DIRECTORY,code,manifest['city'],manifest['district'])
        return manifest,captures,metadata

    def parse(self,code='510704000000'):
        self.assertTrue(hasattr(regional_capture,'parse_sichuan_v4_capture'),
                        'New portal needs its own verified eight-tab parser, not old div IDs')
        return regional_capture.parse_sichuan_v4_capture(*self.fixture(code))

    def test_own_material_counts_and_sample_not_blank(self):
        guide=self.parse()
        self.assertEqual(guide['authority'],'绵阳市游仙区人力资源和社会保障局')
        self.assertEqual(guide['fields']['办理形式']['raw_value'],'窗口办理')
        self.assertEqual(guide['fields']['事项版本']['raw_value'],'5')
        self.assertEqual(guide['fields']['咨询方式']['raw_value'],'咨询电话：0816-5037200;')
        self.assertEqual([(m['name'],m['copies']) for m in guide['materials']],
                         [('劳动人事争议仲裁申请书','2'),('法定代表人（负责人）身份证明及基本情况','1'),('营业执照','2'),('居民身份证','2')])
        self.assertEqual(guide['materials'][1]['details']['填报须知'],
                         '申劳动者申请仲裁，无需提供该项资料，只需在申请书载明法定代表人或主要负责人的姓名、职务等。但用人单位申请时，需要提供。')
        own=next(t for t in guide['templates'] if t['original_name']=='仲裁申请书(模板).docx')
        self.assertEqual(own['annex_id'],'4310863847776096256')
        self.assertEqual(own['official_kind'],'sample')
        self.assertEqual(len(guide['templates']),6)
        self.assertTrue(all(t['can_generate'] is False for t in guide['templates']))
        self.assertIsNone(guide['channel']['entry_url'])
        self.assertEqual(guide['channel']['online_status'],'unverified')
        self.assertIn('窗口工作人员',guide['sections']['办理流程'])
        self.assertNotIn('网站标识码',guide['sections']['办理流程'])
        self.assertIn('劳动合同履行地',guide['sections']['常见问题'])

    def test_missing_materials_are_partial_not_no_materials_needed(self):
        guide=self.parse('510681000000')
        self.assertEqual(guide['district'],'广汉市')
        self.assertEqual(guide['verification_status'],'partial')
        self.assertEqual(guide['materials'],[])
        self.assertEqual(guide['templates'],[])
        self.assertIn('暂无申请材料',guide['sections']['申请材料'])
        self.assertTrue(any('不代表无需' in w for w in guide['warnings']))

    def test_each_locality_uses_own_source_and_different_materials(self):
        a=self.parse();b=self.parse('510723000000')
        self.assertNotEqual(a['source_url'],b['source_url'])
        self.assertEqual(b['district'],'盐亭县')
        self.assertEqual([m['copies'] for m in b['materials']],['2','1','3'])
        self.assertNotEqual(a['materials'],b['materials'])

    def test_material_reduction_badge_is_not_part_of_name_or_universal_exemption(self):
        guide=self.parse('513333000000')
        self.assertEqual(guide['materials'][0]['name'],'中华人民共和国居民身份证')
        self.assertEqual(guide['materials'][0]['official_badges'],['免'])
        self.assertEqual(guide['materials'][0]['required'],'必要')

    def test_rejects_cross_region_wrong_service_and_wrong_active_tab(self):
        self.parse()
        manifest,captures,metadata=self.fixture()
        mutations=[('url',lambda m,c,r:c[2].update(url=c[2]['url'].replace('510704000000','510723000000'))),
                   ('city',lambda m,c,r:m.update(city='德阳市')),
                   ('metadata',lambda m,c,r:r.update(areaCode='510723000000')),
                   ('service',lambda m,c,r:c[0].update(html=c[0]['html'].replace('劳动人事争议仲裁申请','劳动人事争议调解'))),
                   ('tab',lambda m,c,r:c.__setitem__(1,copy.deepcopy(c[0]))),
                   ('item',lambda m,c,r:m.update(source_url=m['source_url'].replace('11510602451223748A4512014135001','OTHER')))]
        for name,mutate in mutations:
            with self.subTest(name=name):
                m,c,r=copy.deepcopy((manifest,captures,metadata));mutate(m,c,r)
                with self.assertRaises(ValueError):regional_capture.parse_sichuan_v4_capture(m,c,r)

    def test_loader_rejects_modified_bytes_and_outside_paths(self):
        self.assertTrue(hasattr(regional_capture,'load_sichuan_v4_capture'),
                        'Manifest hashes and contained paths must be checked before parsing')
        manifest,captures,metadata=self.fixture()
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            m=copy.deepcopy(manifest)
            m['sections'][0]['file']='outside.json'
            (folder/'manifest.json').write_text(json.dumps(m),'utf8')
            (folder/'outside.json').write_text(json.dumps(captures[0]),'utf8')
            with self.assertRaises(ValueError):regional_capture.load_sichuan_v4_capture(folder,metadata)
            m['sections'][0]['file']='../escape.json'
            (folder/'manifest.json').write_text(json.dumps(m),'utf8')
            with self.assertRaises(ValueError):regional_capture.load_sichuan_v4_capture(folder,metadata)

    def test_all_fifteen_original_manifests_are_independently_parsed(self):
        self.parse()
        self.assertEqual(len(list(BASE.glob('*/manifest.json'))),15)
        sources=set()
        for path in BASE.glob('*/manifest.json'):
            manifest,_,metadata=self.fixture(path.parent.name)
            guide=regional_capture.load_sichuan_v4_capture(path.parent,metadata)
            self.assertEqual(guide['region_code'],path.parent.name)
            self.assertEqual(guide['city'],manifest['city'])
            self.assertEqual(guide['source_url'],manifest['source_url'])
            self.assertEqual(len(guide['sections']),8)
            self.assertTrue(all(not t['can_generate'] for t in guide['templates']))
            sources.add(guide['source_url'])
        self.assertEqual(len(sources),15)

    def test_actual_gateway_timeout_is_local_and_never_enables_a_generator(self):
        self.assertTrue(hasattr(sichuan_v4_capture,'annotate_download_failure'),
                        'Observed own-source HTTP failure must reach the actual guide')
        guide=self.parse()
        file=ROOT/'reports/nationwide-localization-20261023-night/batches/v4-forms-0215/official-downloads-verified/510704000000/actual-network.json'
        network=json.loads(file.read_text('utf8'))
        result=sichuan_v4_capture.annotate_download_failure(guide,network,'2026-10-23T18:16:45.492185+00:00',str(file.relative_to(ROOT)))
        template=next(t for t in result['templates'] if t['original_name']=='仲裁申请书(模板).docx')
        self.assertEqual(template['download_status'],'failed')
        self.assertEqual(template['download_http_status'],504)
        self.assertIn('rowguid=4310863847776096256',template['download_endpoint'])
        self.assertNotIn('sha256',template)
        self.assertFalse(template['can_generate'])
        self.assertEqual(result['fields'],guide['fields'])
        self.assertEqual(result['collected_at'],guide['collected_at'])
        self.assertEqual(guide['templates'][0]['download_status'],'not_downloaded')

    def test_gateway_failure_from_another_referer_cannot_be_attached(self):
        self.assertTrue(hasattr(sichuan_v4_capture,'annotate_download_failure'))
        guide=self.parse()
        file=ROOT/'reports/nationwide-localization-20261023-night/batches/v4-forms-0215/official-downloads-verified/510704000000/actual-network.json'
        network=json.loads(file.read_text('utf8'))
        for request in network['requests']:
            if request.get('headers',{}).get('Referer')==guide['source_url']:
                request['headers']['Referer']=guide['source_url'].replace('510704000000','510723000000')
        with self.assertRaises(ValueError):
            sichuan_v4_capture.annotate_download_failure(guide,network,'2026-10-23T18:16:45Z','own-network.json')


if __name__=='__main__':unittest.main()
