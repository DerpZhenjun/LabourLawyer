"""Own Hunan guide boundaries, conditional exemptions, sample safety and history."""
import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore
from routes.regional_guides import router
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong'
class FurongCaptureTests(unittest.TestCase):
    def setUp(self):
        paths={'list':'list-round26/dom.json','basic':'control-flow-recovery-round26/stable-header.json','online':'online-recovery-round26/boundary.json'}
        paths.update({n:'sections-round26/'+n+'.json' for n in ['权利与义务','结果样本','常见问题','法律依据']})
        self.raw={k:json.loads((BASE/p).read_text('utf8')) for k,p in paths.items()}
        self.files=json.loads((BASE/'downloads-round26/original-files.json').read_text('utf8'))
    def parse(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_furong'),'Missing own Furong formal-guide parser')
        from regional_furong import parse_furong_capture
        return parse_furong_capture(self.raw,self.files)
    def test_four_own_materials_preserve_variable_copies_and_conditional_exemptions(self):
        g=self.parse();self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('hunan','长沙市','芙蓉区','430102'))
        self.assertEqual([m['name'] for m in g['materials']],['劳动仲裁申请书','居民身份证','营业执照','证据材料'])
        self.assertIn('当事人数量基础上+1',g['materials'][0]['copies']);self.assertIn('2份',g['materials'][0]['raw_copies'])
        self.assertIn('已有共享数据',g['materials'][1]['details']['免提交条件'])
        self.assertEqual(g['materials'][1]['required'],'必要（符合共享条件可免提交）')
        self.assertIn('当事人数量基础上+1',g['materials'][3]['copies'])
        self.assertIn('189号',g['fields']['办理地点']['normalized_value']);self.assertIn('0731-84683311',g['fields']['咨询方式']['raw_value'])
        self.assertEqual(g['fields']['认证等级需求']['verification_status'],'missing')
    def test_counter_clock_and_faq_conflicts_remain_raw_not_zero_visit_guarantee(self):
        g=self.parse();self.assertEqual(g['fields']['法定办结时限']['raw_value'],'60工作日')
        self.assertIn('四十五日',g['fields']['法定办结时限说明']['raw_value'])
        self.assertEqual(g['fields']['到办事现场次数']['raw_value'],'0次')
        self.assertEqual(g['fields']['必须到现场原因']['verification_status'],'conflict')
        self.assertIn('需要',g['sections']['常见问题']);self.assertIn('41个工作日',g['sections']['办理流程'])
        self.assertEqual(g['channel']['online_status'],'auth_required');self.assertFalse(g['online_evidence']['submission_tested'])
        self.assertEqual(g['channel']['form'],'window_and_online')
    def test_own_originals_are_classified_by_actual_control_and_never_auto_adapted(self):
        g=self.parse();self.assertEqual(len(g['templates']),4)
        self.assertEqual([t['official_kind'] for t in g['templates']],['blank','blank','sample','sample'])
        self.assertTrue(all(not t['can_generate'] and t['document_types']==[] for t in g['templates']))
        old=copy.deepcopy(self.files);self.files[1]['official_kind']='sample_control_unclassified'
        with self.assertRaises(ValueError):self.parse()
        self.files=copy.deepcopy(old);self.files[1]['sha256']='0'*64
        with self.assertRaises(ValueError):self.parse()
        self.files=copy.deepcopy(old);self.files[1]['region_code']='430103'
        with self.assertRaises(ValueError):self.parse()
    def test_other_area_mediation_or_different_auth_redirect_fails_closed(self):
        original=copy.deepcopy(self.raw)
        changes=[('basic','url','0661f202529745928ad2d4bc532e233a','different'),('basic','html','芙蓉区人力资源和社会保障局','天心区人力资源和社会保障局'),('list','html','劳动人事争议仲裁申请','劳动人事争议调解申请'),('online','url','auth.zwfw.hunan.gov.cn','example.com')]
        for key,field,old,new in changes:
            self.raw=copy.deepcopy(original);self.assertIn(old,self.raw[key][field]);self.raw[key][field]=self.raw[key][field].replace(old,new)
            with self.assertRaises(ValueError):self.parse()
    def test_real_kaifu_search_target_is_generic_not_an_own_locality_guide(self):
        # Characterizes the existing fail-closed guard using an actual newly
        # observed fallback, not a synthetic claim that Kaifu lacks a service.
        generic=json.loads((BASE.parent/'hunan-kaifu/observed-generic-target-round27/dom.json').read_text('utf8'))
        self.raw['basic']=generic
        with self.assertRaises(ValueError):self.parse()
        self.raw['basic']=copy.deepcopy(generic)
        self.raw['basic']['url']='https://zwfw-new.hunan.gov.cn/hnywtb/service/guide.html?id=aYcZ8ELbR56Me61a8eSG0A&rightsCode=002014302002&ywCode=01&approve_id=0661f202529745928ad2d4bc532e233a'
        with self.assertRaises(ValueError):self.parse()
    def test_isolated_exact_api_and_versions_do_not_leak_to_tianxin_or_generate_sample(self):
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'public.sqlite');before=self.parse();g=s.put_guide(before)
            n=s.put_guide(json.loads((BASE.parent/'beijing-tongzhou/guide.json').read_text('utf8')))
            self.assertNotEqual(g['source_id'],n['source_id'])
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=s),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                own=client.get('/api/regional-guides/lookup',params=params).json();self.assertEqual(len(own['materials']),4)
                downloaded=client.get('/api/regional-guides/templates/'+g['templates'][0]['id'],params=params)
                self.assertEqual(downloaded.status_code,200)
                import hashlib
                self.assertEqual(hashlib.sha256(downloaded.content).hexdigest(),'c6bbebf6eed3a11f1cbe5ee14cd6de9937f741c9fcda37165e06d0706e18ea97')
                other=client.get('/api/regional-guides/lookup',params={**params,'district':'天心区'}).json();self.assertEqual(other['materials'],[]);self.assertIsNone(other['source_id'])
                self.assertEqual(client.get('/api/regional-guides/templates/'+g['templates'][0]['id'],params={**params,'district':'天心区'}).status_code,404)
                payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=g['templates'][2]['id'],kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)
            for page in self.raw.values():page['captured_at']='2026-10-24T00:00:00.000Z'
            same=s.put_guide(self.parse());self.assertEqual(same['version'],g['version'])
            self.raw['basic']['html']=self.raw['basic']['html'].replace('根据当事人数量基础上+1','根据当事人数量基础上+2')
            changed=s.put_guide(self.parse());self.assertEqual(changed['source_id'],g['source_id']);self.assertNotEqual(changed['version'],g['version'])
            self.assertIn('+1',s.versions('hunan','长沙市','芙蓉区')[1]['materials'][0]['copies'])
if __name__=='__main__':unittest.main()
