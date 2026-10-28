"""Nansha's own image material table and original files, never Baiyun fallback."""
import copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore
from routes.regional_guides import router
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-nansha'
class NanshaCaptureTests(unittest.TestCase):
    def setUp(self):
        self.raw=json.loads((BASE/'source-round23/dom.json').read_text('utf8'))
        self.files=json.loads((BASE/'downloads-round23/original-files.json').read_text('utf8'))
    def parse(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_nansha'),'Missing own Nansha parser')
        from regional_nansha import parse_nansha_capture
        return parse_nansha_capture(self.raw,self.files)
    def test_own_image_table_has_nine_groups_and_conditional_copies_not_baiyun(self):
        g=self.parse();self.assertEqual((g['district'],g['region_code']),('南沙区','440115'))
        self.assertEqual(len(g['materials']),9)
        self.assertEqual([m['copies'] for m in g['materials'][:2]],['1份','1份'])
        self.assertIn('1个月',g['materials'][1]['details']['图片原文'])
        self.assertIn('对方当事人',g['materials'][2]['copies'])
        self.assertIn('未按照',g['materials'][3]['details']['图片原文'])
        self.assertIn('十人',g['materials'][6]['applicable_conditions'])
        self.assertTrue(all(m['details']['source_image_sha256']=='bbaf11d46ed7f45b42fa6960cefa434b051a07b81076bb53e0796b9dd21550c5' for m in g['materials']))
    def test_delivery_mini_program_is_not_online_application_and_old_dates_not_current_guarantee(self):
        g=self.parse();self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url'])
        self.assertEqual(g['fields']['办理形式']['verification_status'],'missing')
        self.assertIsNone(g['fields']['办理地点']['normalized_value'])
        self.assertIsNone(g['service_code']);self.assertEqual(g['verification_status'],'partial')
        self.assertIn('2020-04-23',g['sections']['来源与现行性'])
        self.assertTrue(any('送达' in w and '网上立案' in w for w in g['warnings']))
    def test_own_23_originals_14_blank_9_instructions_all_generation_disabled(self):
        g=self.parse();self.assertEqual(len(g['templates']),23)
        self.assertEqual(sum(t['official_kind']=='blank' for t in g['templates']),14)
        self.assertEqual(sum(t['official_kind']=='instruction' for t in g['templates']),9)
        self.assertTrue(all(not t['can_generate'] and not t['document_types'] for t in g['templates']))
        self.assertTrue(any('重叠' in w for w in g['warnings']))
    def test_changed_source_image_or_foreign_duplicate_file_is_rejected(self):
        self.parse();original=copy.deepcopy(self.raw)
        for key,value in [('url',self.raw['url'].replace('www.gzns.gov.cn','www.by.gov.cn')),('html',self.raw['html'].replace('【置顶】仲裁告知事项及申请材料下载','仲裁调解申请'))]:
            self.raw=copy.deepcopy(original);self.raw[key]=value
            with self.assertRaises(ValueError):self.parse()
        self.raw=original;files=copy.deepcopy(self.files)
        self.raw['html']=self.raw['html'].replace('https://www.gzns.gov.cn/img/0/880/880829/5801798.png','https://www.gzns.gov.cn/img/0/880/880829/changed.png')
        with self.assertRaises(ValueError):self.parse()
        self.raw=copy.deepcopy(original);self.files=copy.deepcopy(files);self.files[-1]['sha256']='f'*64
        with self.assertRaises(ValueError):self.parse()
        for key,value in [('source_url','https://www.by.gov.cn/'),('file','templates/_docx/_regional/440111/package-1/05.doc'),('sha256','f'*64),('id','foreign')]:
            self.files=copy.deepcopy(files);self.files[0][key]=value
            with self.assertRaises(ValueError):self.parse()
        self.files=files[:-1]
        with self.assertRaises(ValueError):self.parse()
    def test_isolated_api_own_downloads_distinct_sources_no_fallback_no_generation(self):
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'public.sqlite');g=s.put_guide(self.parse())
            b=s.put_guide(json.loads((BASE.parent/'guangdong-baiyun/guide.json').read_text('utf8')))
            self.assertNotEqual(g['source_id'],b['source_id']);self.assertNotEqual(g['materials'],b['materials'])
            self.assertIsNone(s.lookup('guangdong','广州市','海珠区')['source_id'])
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=s),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                for t in g['templates']:
                    r=client.get('/api/regional-guides/templates/'+t['id'],params=params)
                    self.assertEqual(r.status_code,200);self.assertEqual(hashlib.sha256(r.content).hexdigest(),t['sha256'])
                self.assertEqual(client.get('/api/regional-guides/templates/'+g['templates'][0]['id'],params={**params,'district':'白云区'}).status_code,404)
                payload={k:g[k] for k in ['province','city','district','source_id','version']}
                payload.update(template_id=g['templates'][9]['id'],kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)
    def test_changed_original_bytes_require_reclassification_even_with_updated_download_hash(self):
        self.parse()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for f in self.files:
                target=root/f['file'];target.parent.mkdir(parents=True,exist_ok=True)
                data=(ROOT/f['file']).read_bytes()
                if f['id']=='8038769':
                    data=data[:-1]+bytes([data[-1]^1]);f['sha256']=hashlib.sha256(data).hexdigest()
                target.write_bytes(data)
            with patch('regional_nansha.ROOT',root):
                with self.assertRaises(ValueError):self.parse()
if __name__=='__main__':unittest.main()
