"""Independently captured Dongcheng identity, original files and auth boundary."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import regional_beijing as module
from regional_guides import RegionalStore
from routes.regional_guides import router
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-dongcheng'
class DongchengCaptureTests(unittest.TestCase):
    def setUp(self):
        p=BASE/'capture-remaining-round28'
        self.raw={str(i):json.loads((p/f'section-{i}.json').read_text('utf8')) for i in range(7)}
        self.raw.update({k:json.loads((p/(v+'.json')).read_text('utf8')) for k,v in {'basic':'basic-expanded','materials':'materials-final','flow':'flow-final'}.items()})
        self.files=json.loads((BASE/'downloads-round28/original-files.json').read_text('utf8'))
    def parse(self):
        self.assertTrue(hasattr(module,'parse_dongcheng_capture'),'Missing own Dongcheng exact source parser')
        return module.parse_dongcheng_capture(self.raw,self.files)
    def test_own_authority_address_phone_copies_and_time_are_not_other_districts(self):
        g=self.parse();self.assertEqual((g['district'],g['region_code'],g['service_code']),('东城区','110101','11110101067308122H300201430200200'))
        self.assertEqual(g['authority'],'北京市东城区人力资源和社会保障局')
        self.assertEqual(g['fields']['办理地点']['raw_value'],'北京市东城区交道口南大街27号')
        self.assertIn('67074655',g['fields']['咨询方式']['raw_value']);self.assertNotIn('87983310',g['fields']['咨询方式']['raw_value'])
        self.assertEqual(g['fields']['到办事现场次数']['raw_value'],'1')
        self.assertEqual(g['fields']['承诺办结时限']['scope'],'acceptance_review_decision_not_case_award')
        self.assertEqual([m['copies'] for m in g['materials'][:2]],['原件3份','原件1份'])
        self.assertEqual(len(g['sections']),7)
    def test_foreign_url_heading_or_business_code_rejected(self):
        original=copy.deepcopy(self.raw)
        for key,field,old,new in [('basic','url','110101000000','110105000000'),('basic','html','<span>东城区</span>','<span>朝阳区</span>'),('materials','html','11110101067308122H300201430200200','11110105000052732A300201430200200')]:
            self.raw=copy.deepcopy(original);self.assertIn(old,self.raw[key][field]);self.raw[key][field]=self.raw[key][field].replace(old,new)
            with self.assertRaises(ValueError):self.parse()
    def test_same_sample_bytes_still_require_own_download_region_and_source(self):
        g=self.parse();self.assertEqual(len(g['templates']),3)
        self.assertTrue(all(t['official_kind']=='sample' and not t['can_generate'] for t in g['templates']))
        original=copy.deepcopy(self.files);at=next(i for i,r in enumerate(original) if r['file_type']=='docx')
        for field,value in [('source_url',module.CHAOYANG_SOURCE),('file','templates/_docx/_regional/110105/'+original[at]['id']+'.docx'),('sha256','0'*64)]:
            self.files=copy.deepcopy(original);self.files[at][field]=value
            with self.assertRaises(ValueError):self.parse()
    def test_own_actual_online_control_stops_at_official_login(self):
        self.parse();self.assertTrue(hasattr(module,'verify_dongcheng_online_capture'))
        p=BASE/'capture-remaining-round28';before=json.loads((p/'before-online.json').read_text('utf8'));after=json.loads((p/'online-after.json').read_text('utf8'))
        entry=module.verify_dongcheng_online_capture(before,after)
        self.assertEqual(entry['status'],'auth_required');self.assertFalse(entry['post_login_submission_verified'])
        before['url']=module.CHAOYANG_SOURCE
        with self.assertRaises(ValueError):module.verify_dongcheng_online_capture(before,after)
    def test_isolated_api_distinct_sources_unknown_xicheng_and_no_sample_generation(self):
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'public.sqlite');g=store.put_guide(self.parse())
            other=store.put_guide(json.loads((BASE.parent/'beijing-chaoyang/guide.json').read_text('utf8')))
            self.assertNotEqual(g['source_id'],other['source_id']);self.assertNotEqual(g['fields']['办理地点'],other['fields']['办理地点'])
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=store),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                missing=client.get('/api/regional-guides/lookup',params={**params,'district':'西城区'}).json();self.assertIsNone(missing['source_id']);self.assertEqual(missing['materials'],[])
                for t in g['templates']:
                    r=client.get('/api/regional-guides/templates/'+t['id'],params=params);self.assertEqual(r.status_code,200);self.assertEqual(hashlib.sha256(r.content).hexdigest(),t['sha256'])
                self.assertEqual(client.get('/api/regional-guides/templates/'+g['templates'][0]['id'],params={**params,'district':'西城区'}).status_code,404)
                payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=g['templates'][0]['id'],kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)
if __name__=='__main__':unittest.main()
