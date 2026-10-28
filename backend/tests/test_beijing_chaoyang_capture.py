"""Own source binding despite shared official sample bytes; no county fallback."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import regional_beijing as module
from regional_guides import RegionalStore,resolve_channel
from routes.regional_guides import router
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-chaoyang'
def captures():
    p=BASE/'sections-round23-resumed'
    return {**{str(i):json.loads((p/f'section-{i}.json').read_text('utf8')) for i in range(7)},
        **{k:json.loads((p/f'{v}.json').read_text('utf8')) for k,v in {'basic':'basic-expanded','materials':'materials-final','flow':'flow-final'}.items()}}
class ChaoyangCaptureTests(unittest.TestCase):
    def setUp(self):self.raw=captures();self.files=json.loads((BASE/'downloads-round23/original-files.json').read_text('utf8'))
    def parse(self):
        self.assertTrue(hasattr(module,'parse_chaoyang_capture'),'Missing own Chaoyang parser')
        return module.parse_chaoyang_capture(self.raw,self.files)
    def test_own_address_phone_authority_service_and_acceptance_time_not_tongzhou(self):
        g=self.parse()
        self.assertEqual((g['district'],g['region_code'],g['authority'],g['service_code']),('朝阳区','110105','北京市朝阳区人力资源和社会保障局','11110105000052732A300201430200200'))
        self.assertEqual(g['fields']['办理地点']['raw_value'],'北京市朝阳区将台路5号院15号楼B、C座')
        self.assertIn('09:00-12:00',g['fields']['办理时间']['raw_value'])
        self.assertIn('12:00-17:00',g['fields']['办理时间']['raw_value'])
        self.assertIn('87983310',g['fields']['咨询方式']['raw_value'])
        self.assertNotIn('80579377',g['fields']['咨询方式']['raw_value'])
        self.assertEqual(g['fields']['到办事现场次数']['raw_value'],'1')
        self.assertEqual(g['fields']['承诺办结时限']['scope'],'acceptance_review_decision_not_case_award')
        self.assertEqual(g['fields']['办理形式']['raw_value'],'窗口办理、网上办理')
        self.assertEqual([m['copies'] for m in g['materials']][:2],['原件3份','原件1份'])
        self.assertEqual(len(g['sections']),7)
    def test_own_heading_not_global_site_header_establishes_locality_and_rejects_foreign_capture(self):
        self.parse()
        for part,key,old,new in [('basic','html','<span>朝阳区</span>','<span>通州区</span>'),
                ('materials','url','110105000000','110112000000'),
                ('basic','html','11110105000052732A300201430200200','11110112000082974B300201430200200')]:
            saved=copy.deepcopy(self.raw);self.assertIn(old,self.raw[part][key]);self.raw[part][key]=self.raw[part][key].replace(old,new)
            with self.assertRaises(ValueError):self.parse()
            self.raw=saved
        from test_beijing_tongzhou_capture import captures as other
        with self.assertRaises(ValueError):module.parse_chaoyang_capture(other(),self.files)
        with self.assertRaises(ValueError):module.parse_tongzhou_capture(self.raw,self.files)
    def test_independent_download_path_and_source_required_even_when_sha_and_official_ids_equal(self):
        g=self.parse();self.assertEqual(len(g['templates']),3)
        self.assertTrue(all(t['official_kind']=='sample' and not t['can_generate'] for t in g['templates']))
        originals=copy.deepcopy(self.files)
        for field,value in [('file','templates/_docx/_regional/110112/705e848d-4775-4fda-8f07-2b8d90003426.docx'),
                ('source_url',module.SOURCE),('sha256','f'*64)]:
            self.files=copy.deepcopy(originals);self.files[1][field]=value
            with self.assertRaises(ValueError):self.parse()
    def test_actual_native_own_online_boundary_and_foreign_before_rejection(self):
        self.parse();self.assertTrue(hasattr(module,'verify_chaoyang_online_capture'))
        p=BASE/'sections-round23-resumed';before=json.loads((p/'before-online.json').read_text('utf8'));after=json.loads((p/'online-after.json').read_text('utf8'))
        entry=module.verify_chaoyang_online_capture(before,after)
        self.assertEqual(entry['status'],'auth_required');self.assertFalse(entry['post_login_submission_verified'])
        foreign=copy.deepcopy(before);foreign['url']=module.SOURCE
        with self.assertRaises(ValueError):module.verify_chaoyang_online_capture(foreign,after)
    def test_distinct_stored_source_ids_and_own_api_downloads_generation_stays_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'test.sqlite');g=s.put_guide(self.parse())
            other=json.loads((BASE.parent/'beijing-tongzhou/guide.json').read_text('utf8'));t=s.put_guide(other)
            self.assertNotEqual(g['source_id'],t['source_id'])
            self.assertNotEqual(s.lookup('beijing','北京市','通州区')['fields']['办理地点']['raw_value'],g['fields']['办理地点']['raw_value'])
            self.assertIsNone(s.lookup('beijing','北京市','海淀区')['source_id'])
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=s),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                for template in g['templates']:
                    r=client.get('/api/regional-guides/templates/'+template['id'],params=params)
                    self.assertEqual(r.status_code,200);self.assertEqual(hashlib.sha256(r.content).hexdigest(),template['sha256'])
                payload={k:g[k] for k in ['province','city','district','source_id','version']}
                payload.update(template_id=g['templates'][0]['id'],kind='application',mode='reference_adaptation',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)
if __name__=='__main__':unittest.main()
