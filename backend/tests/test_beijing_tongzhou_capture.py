"""Prevent sample-as-blank, neighbour fallback, and five-day verdict claims."""
import copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore
from routes.regional_guides import router
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-tongzhou'

def captures():
    p=BASE/'sections-0650'
    return {**{str(i):json.loads((p/f'section-{i}.json').read_text('utf8')) for i in range(7)},
        'basic':json.loads((p/'basic-expanded.json').read_text('utf8')),
        'materials':json.loads((p/'materials-final.json').read_text('utf8')),
        'flow':json.loads((p/'flow-final.json').read_text('utf8'))}

class TongzhouCaptureTests(unittest.TestCase):
    def setUp(self):self.raw=captures();self.files=json.loads((BASE/'downloads-0700/original-files.json').read_text('utf8'))
    def parse(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_beijing'),'Own Tongzhou parser missing')
        import regional_beijing
        return regional_beijing.parse_tongzhou_capture(self.raw,self.files)

    def test_own_identity_materials_and_five_days_only_for_acceptance_decision(self):
        g=self.parse()
        self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('beijing','北京市','通州区','110112'))
        self.assertEqual(g['service_code'],'11110112000082974B300201430200200')
        self.assertEqual(g['authority'],'北京市通州区人力资源和社会保障局')
        self.assertEqual(g['fields']['办理形式']['raw_value'],'窗口办理、网上办理')
        self.assertEqual(g['channel']['form'],'window_and_online')
        self.assertEqual(g['channel']['online_status'],'unverified')
        self.assertIsNone(g['channel']['entry_url'])
        self.assertEqual(g['fields']['审查与决定时限']['raw_value'],'5个工作日')
        self.assertIn('不是仲裁案件整体结案时限',' '.join(g['warnings']))
        self.assertEqual([m['name'] for m in g['materials']],['仲裁申请书','授权委托书','身份证件'])
        self.assertEqual([m['copies'] for m in g['materials']],['原件3份','原件1份','正本原件1份（正本原件仅供查验）；副本原件1份（副本原件仅供查验）'])
        self.assertIn('委托他人',g['materials'][1]['details']['提供材料依据'])
        self.assertIn('官方标注必要',g['materials'][1]['applicable_conditions'])
        self.assertEqual(len(g['sections']),7)
        self.assertIn('08:30-17:30',g['fields']['办理时间']['raw_value'])
        self.assertIn('玉桥西里4号楼',g['fields']['办理地点']['raw_value'])

    def test_header_raw_times_and_onsite_count_are_preserved_with_stage_qualification(self):
        g=self.parse()
        self.assertEqual(g['fields']['到办事现场次数']['raw_value'],'1')
        self.assertEqual(g['fields']['法定办结时限']['raw_value'],'5工作日')
        self.assertEqual(g['fields']['承诺办结时限']['raw_value'],'5工作日')
        self.assertIn('审查与决定',g['fields']['承诺时限办结说明']['raw_value'])
        self.assertEqual(g['fields']['承诺办结时限']['scope'],'acceptance_review_decision_not_case_award')

    def test_foreign_region_task_authority_material_change_and_missing_tab_fail_closed(self):
        self.parse()
        for part,key,old,new in [('basic','url','110112000000','110105000000'),
                ('materials','html','北京市通州区人力资源和社会保障局','北京市朝阳区人力资源和社会保障局'),
                ('basic','html','11110112000082974B300201430200200','11110105000000000X300201430200200'),
                ('materials','html','仲裁申请书','劳动争议调解申请书')]:
            before=copy.deepcopy(self.raw);self.assertIn(old,self.raw[part][key]);self.raw[part][key]=self.raw[part][key].replace(old,new)
            with self.assertRaises(ValueError):self.parse()
            self.raw=before
        del self.raw['6']
        with self.assertRaises(ValueError):self.parse()

    def test_own_sample_download_identity_sha_and_no_blank_generation(self):
        g=self.parse();self.assertEqual(len(g['templates']),3)
        self.assertTrue(all(t['official_kind']=='sample' and not t['can_generate'] and not t['document_types'] for t in g['templates']))
        saved=copy.deepcopy(self.files)
        for field,value in [('source_url','https://other.gov.cn/guide'),('file','templates/_docx/_regional/320706/other.docx'),
                ('sha256','0'*64),('download_url','https://banshi.beijing.gov.cn/pubtask/download/other.docx')]:
            self.files=copy.deepcopy(saved);self.files[1][field]=value
            with self.assertRaises(ValueError):self.parse()

    def test_real_download_api_generation_block_and_no_city_or_neighbour_inheritance(self):
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'test.sqlite');g=store.put_guide(self.parse())
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=store),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                for t in g['templates']:
                    r=client.get('/api/regional-guides/templates/'+t['id'],params=params)
                    self.assertEqual(r.status_code,200);self.assertEqual(hashlib.sha256(r.content).hexdigest(),t['sha256'])
                for district in ['朝阳区','']:
                    self.assertIsNone(client.get('/api/regional-guides/lookup',params={**params,'district':district}).json()['source_id'])
                payload={k:g[k] for k in ['province','city','district','source_id','version']}
                payload.update(template_id=g['templates'][0]['id'],kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)
                payload['mode']='reference_adaptation'
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)

    def test_requirement_versions_preserve_history_and_distinct_source_from_jiangsu(self):
        with tempfile.TemporaryDirectory() as d:
            store=RegionalStore(Path(d)/'test.sqlite');first=store.put_guide(self.parse())
            changed=copy.deepcopy(self.parse());changed['materials'][0]['copies']='待重新核验份数'
            second=store.put_guide(changed)
            self.assertNotEqual(first['version'],second['version'])
            self.assertEqual(store.versions('beijing','北京市','通州区')[-1]['materials'][0]['copies'],'原件3份')
            other=json.loads((BASE.parent/'jiangsu-haizhou/staging-0540/reviewed-guide.json').read_text('utf8'))
            own_other=store.put_guide(other);self.assertNotEqual(first['source_id'],own_other['source_id'])

    def test_actual_own_online_link_reaches_login_choice_without_claiming_post_login_submission(self):
        import regional_beijing
        self.assertTrue(hasattr(regional_beijing,'verify_tongzhou_online_capture'),'Missing own observed online boundary verifier')
        p=BASE/'sections-0650';before=json.loads((p/'before-online.json').read_text('utf8'));after=json.loads((p/'online-after.json').read_text('utf8'))
        checked=regional_beijing.verify_tongzhou_online_capture(before,after)
        self.assertEqual(checked['status'],'auth_required');self.assertTrue(checked['official_link'])
        self.assertFalse(checked['post_login_submission_verified'])
        for key,old,new in [('url','banshi.beijing.gov.cn','other.gov.cn'),
                ('url','aHR0cHM6Ly9mdXd1','ZmFrZQ=='),('html','请选择登录','并非登录页面')]:
            wrong=copy.deepcopy(after);self.assertIn(old,wrong[key]);wrong[key]=wrong[key].replace(old,new)
            with self.assertRaises(ValueError):regional_beijing.verify_tongzhou_online_capture(before,wrong)

if __name__=='__main__':unittest.main()
